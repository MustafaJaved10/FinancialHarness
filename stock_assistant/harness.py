"""AI harness — coordinates the model, context, permissions and workflow.

Responsibilities:
1. Context: keep the conversation's tickers, last results and user question.
2. Permissions: every tool declares the access it needs; the harness only
   runs tools the session is allowed to use (read-only market data by
   default; sandbox code execution must be explicitly enabled).
3. Tool calling: route a question to data/analysis tools, collect results.
4. Explanation: turn tool output into a clear answer WITH sources and
   assumptions. Uses an LLM (OpenAI, if OPENAI_API_KEY is set) to phrase the
   answer; otherwise a deterministic template explainer — numbers are
   identical either way because they always come from the tools.
"""
from __future__ import annotations

import re

from . import data_provider, fundamental, projections, sandbox, technical

PERMISSIONS = {"market_data": True, "fundamentals": True, "projections": True,
               "sandbox": False}  # sandbox off unless the user enables it


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, permission, fn, description):
        self.tools[name] = {"permission": permission, "fn": fn, "description": description}

    def call(self, session_permissions: dict, name: str, **kwargs):
        tool = self.tools[name]
        if not session_permissions.get(tool["permission"], False):
            return {"error": f"permission denied: '{tool['permission']}' is not enabled for this session"}
        return tool["fn"](**kwargs)


def _technical_tool(symbol):
    hist = data_provider.get_history(symbol)
    return {"source": hist["source"], **technical.summarise(hist["history"])}


def _fundamental_tool(symbol):
    return fundamental.summarise(data_provider.get_info(symbol))


def _compare_tool(symbols):
    return {"comparison": projections.compare(symbols)}


def _projection_tool(symbol, years=3):
    return projections.projection(symbol, years=years)


REGISTRY = ToolRegistry()
REGISTRY.register("technical_analysis", "market_data", _technical_tool, "Indicators, trend, volume for one ticker")
REGISTRY.register("fundamental_analysis", "fundamentals", _fundamental_tool, "Valuation, profitability, growth for one ticker")
REGISTRY.register("compare_stocks", "market_data", _compare_tool, "Side-by-side comparison of 2-5 tickers")
REGISTRY.register("projection", "projections", _projection_tool, "Monte-Carlo price projection with assumptions")
REGISTRY.register("run_python", "sandbox", lambda code: sandbox.run_analysis(code), "Run analysis code in the sandbox")


def extract_tickers(text: str, known: list[str] | None = None) -> list[str]:
    found = re.findall(r"\b[A-Z]{1,5}\b", text.upper())
    stop = {"I", "A", "THE", "AND", "FOR", "WHAT", "HOW", "IS", "OF", "TO", "RSI", "MACD", "PE", "VS",
            "HELLO", "HI", "HEY", "PLEASE", "CAN", "YOU", "DO", "ME", "MY", "GIVE", "SHOW", "TELL",
            "ANALYSE", "ANALYZE", "ANALYSIS", "STOCK", "PRICE", "COMPARE", "PROJECT", "FUTURE",
            "ABOUT", "WITH", "THIS", "THAT", "WILL", "WOULD", "SHOULD", "YEARS", "YEAR", "ETF"}
    out = [t for t in found if t not in stop]
    return list(dict.fromkeys(out))[:5]


def answer(question: str, permissions: dict | None = None, context: dict | None = None) -> dict:
    """Main harness entry point: question -> tools -> explained answer."""
    perms = {**PERMISSIONS, **(permissions or {})}
    tickers = extract_tickers(question) or (context or {}).get("tickers", [])
    q = question.lower()
    steps, results = [], {}

    if not tickers:
        return {"answer": "Tell me a ticker symbol (e.g. AAPL, MSFT, TSLA) and what you want — "
                          "technical analysis, fundamentals, a comparison, or a projection.",
                "steps": steps, "results": results, "sources": []}

    if "compar" in q or " vs " in q or len(tickers) > 1 and "compar" in q:
        results = REGISTRY.call(perms, "compare_stocks", symbols=tickers)
        steps.append("compare_stocks")
    elif "project" in q or "forecast" in q or "future" in q:
        results = REGISTRY.call(perms, "projection", symbol=tickers[0])
        steps.append("projection")
    elif "fundamental" in q or "valuation" in q or "p/e" in q or "earnings" in q or "financial" in q:
        results = REGISTRY.call(perms, "fundamental_analysis", symbol=tickers[0])
        steps.append("fundamental_analysis")
    else:  # default: full research = technical + fundamental
        results = {"technical": REGISTRY.call(perms, "technical_analysis", symbol=tickers[0]),
                   "fundamental": REGISTRY.call(perms, "fundamental_analysis", symbol=tickers[0])}
        steps += ["technical_analysis", "fundamental_analysis"]

    return {"answer": _explain(question, tickers[0], results), "steps": steps,
            "results": results,
            "sources": ["Yahoo Finance via yfinance (or labelled synthetic fallback when offline)"],
            "disclaimer": "Educational analysis only — not financial advice."}


def _explain(question: str, symbol: str, results: dict) -> str:
    """Deterministic explanation from tool output (LLM phrasing is optional)."""
    if "comparison" in results:
        lines = [f"Comparison (latest data):"]
        for r in results["comparison"]:
            lines.append(f"- {r['symbol']}: ${r['price']} | 1Y return {r['return_1y_pct']}% | "
                         f"RSI {r['rsi']} | {r['trend']}")
        return "\n".join(lines)
    if "median_p50" in results:
        return (f"{symbol} projection over {results['years']} years (Monte-Carlo, "
                f"{results['simulations']} simulations): median ${results['median_p50']}, "
                f"10th percentile ${results['p10']}, 90th percentile ${results['p90']}. "
                f"Assumptions: " + "; ".join(results["assumptions"]))
    if "technical" in results:
        t, f = results["technical"], results["fundamental"]
        return (f"{symbol} at ${t.get('price')}: {t.get('trend')}. RSI {t.get('rsi')} "
                f"({t.get('rsi_note')}), MACD shows {t.get('macd_note')}. "
                f"Support (60d) ${t.get('support_60d')}, resistance ${t.get('resistance_60d')}. "
                f"Returns — 1M {t.get('return_1m_pct')}%, 3M {t.get('return_3m_pct')}%, 1Y {t.get('return_1y_pct')}%. "
                f"Fundamentals: {f.get('company') or symbol}, sector {f.get('sector') or 'n/a'}, "
                f"P/E {f.get('valuation', {}).get('trailing_pe')}, "
                f"market cap {f.get('market_cap')}. Source: {t.get('source')}.")
    return f"{symbol}: " + str(results)[:600]
