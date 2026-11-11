"""Adapt MCP data and the existing harness to the web response format."""
import asyncio
import re

from brain_live import call_tool
from .isolated_analysis import run_isolated

SUPPORTED = {"IBM", "AAPL", "MSFT"}


def response(tool, answer, sources=(), assumptions=(), chart=None, table=None):
    return {
        "tool": tool, "answer": answer, "sources": list(sources),
        "assumptions": list(assumptions), "chart": chart, "table": table,
    }


def symbols_in(question):
    aliases = {"apple": "AAPL", "microsoft": "MSFT"}
    return list(dict.fromkeys(
        aliases.get(word.lower(), word.upper())
        for word in re.findall(r"\b[A-Za-z]+\b", question)
        if word.upper() in SUPPORTED or word.lower() in aliases
    ))


async def prepare(question, previous_symbol="IBM"):
    text = question.lower()
    symbols = symbols_in(question)
    unknown = set(re.findall(r"\b[A-Z]{2,5}\b", question)) - SUPPORTED - {
        "I", "RSI", "EPS", "USD", "PE", "P", "Q", "OHLCV", "ROI", "SMA", "EMA", "MACD",
    }
    if not symbols and unknown:
        return "refusal", {"answer": "I cannot answer that ticker yet. Available tickers are IBM, AAPL, and MSFT."}
    symbol = symbols[0] if symbols else previous_symbol
    if "what if" in text or "what-if" in text:
        amount = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", question)
        change = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", question)
        if not amount or not change:
            return "refusal", {"answer": "Include an amount and a percentage, for example: What if $1,000 rises 10%?"}
        percentage = float(change[1])
        if percentage > 0 and re.search(r"\b(falls?|drops?|down|decreases?|loses?)\b", text):
            percentage = -percentage
        return "what_if", {"amount": float(amount[1].replace(",", "")), "change": percentage}
    if "compar" in text or " vs " in text:
        if len(symbols) != 2:
            return "refusal", {"answer": "Name two supported stocks, for example: Compare IBM and MSFT."}
        candles = await asyncio.gather(*(
            call_tool("get_daily_candles", {"symbol": ticker, "limit": 100}) for ticker in symbols
        ))
        return "compare", {"series": candles}
    if any(word in text for word in ("company", "fundamental", "earnings", "financial", "valuation", "revenue", "profit", "eps", "balance sheet", "cash flow")):
        return "fundamental", {"data": await call_tool("get_company_data", {"symbol": symbol})}
    series = await call_tool("get_daily_candles", {"symbol": symbol, "limit": 100})
    if any(word in text for word in ("project", "future", "forecast")) or re.search(r"\byears?\b", text):
        years = re.search(r"\b(\d+)\s+years?\b", text)
        return "projection", {"data": series, "years": int(years[1]) if years else 3}
    return "technical", {"data": series}


def answer_question(question, previous_symbol="IBM", progress=lambda *_: None):
    progress(20, "Fetching stock data")
    operation, payload = asyncio.run(prepare(question, previous_symbol))
    progress(65, "Running analysis in the Python sandbox")
    return run_isolated(operation, payload)
