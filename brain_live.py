# brain_live.py - STEP 6 v2: harness on live MCP data, TWO symbols (IBM + AAPL).
# v2 changes: (1) candles load for IBM and AAPL (the personal API key unlocks them);
# (2) fundamentals are built from Yahoo fundamental_analysis ALONE (growth + P/E),
# because Alpha Vantage's company tool knocks 5 times in seconds and the free key
# has a speed limit - Yahoo gives the same three numbers in one free call;
# (3) a failed fetch no longer kills the run: the symbol is simply not loaded,
# and the harness refuses questions about it honestly.
# Save in the repo root:  N:\Internship\FinancialHarness\for-mustafa-data-connector
# Run from that folder:   python brain_live.py
#
# WHAT CHANGED vs Step 5: the SAMPLE tables are deleted. The harness now FETCHES
# real data through Yasir's MCP tools first (this is called "loading the context"),
# then answers questions from that real data. The brain rules (trend, momentum,
# RSI, fundamental scoring) are the SAME lines as Steps 2-5.
#
# DATA SOURCES (named honestly in every answer):
#   get_daily_candles / get_company_data        -> Alpha Vantage (via Yasir's MCP server)
#   fundamental_analysis / compare / projection -> Yahoo Finance (yfinance, via same server)

import asyncio
import json
import sys

sys.path.insert(0, ".")


# ---------- MCP tool calling (the harness's hands) ----------

async def call_tool(name, args):
    """Call one of Yasir's MCP tools and return its answer as a Python dict."""
    from stock_assistant.mcp_server import mcp

    result = await mcp.call_tool(name, args)
    if isinstance(result, tuple):
        content, structured = result
        if isinstance(structured, dict):
            return structured
    else:
        content = result
    return json.loads(content[0].text)


# ---------- The brain (Steps 2-4: rules unchanged) ----------

def average(numbers):
    return sum(numbers) / len(numbers)


def trend(prices):
    last5 = average(prices[-5:])
    all20 = average(prices[-20:])
    diff_pct = (last5 - all20) / all20 * 100
    if diff_pct > 0.5:
        return "UP"
    if diff_pct < -0.5:
        return "DOWN"
    return "FLAT"


def momentum(prices):
    return (prices[-1] - prices[-11]) / prices[-11] * 100


def rsi(prices):
    changes = []
    for i in range(1, len(prices)):
        changes.append(prices[i] - prices[i - 1])
    last14 = changes[-14:]
    gains = [c for c in last14 if c > 0]
    losses = [-c for c in last14 if c < 0]
    avg_gain = sum(gains) / len(last14)
    avg_loss = sum(losses) / len(last14)
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_label(value):
    if value >= 70:
        return "Overbought"
    if value <= 30:
        return "Oversold"
    return "Neutral"


def decide(prices):
    t = trend(prices)
    m = momentum(prices)
    if t == "UP" and m > 2:
        return ("BUY (LONG)", t, m)
    if t == "DOWN" and m < -2:
        return ("SELL (SHORT)", t, m)
    return ("HOLD", t, m)


def fundamental(symbol, c):
    """Step 4 scoring, unchanged. ONE honest edit: the company numbers now arrive
    as an input (real data) instead of being read from the practice table.
    c = {'earnings_growth': %, 'revenue_growth': %, 'pe_ratio': number}"""
    score = 0
    reasons = []
    if c["earnings_growth"] >= 10:
        score += 1
        reasons.append("earnings are growing fast")
    elif c["earnings_growth"] < 0:
        score -= 1
        reasons.append("earnings are falling")
    if c["revenue_growth"] >= 5:
        score += 1
        reasons.append("sales are growing")
    elif c["revenue_growth"] < 0:
        score -= 1
        reasons.append("sales are falling")
    if c["pe_ratio"] <= 25:
        score += 1
        reasons.append("price is fair for its earnings")
    elif c["pe_ratio"] >= 40:
        score -= 1
        reasons.append("price is very expensive for its earnings")
    if score >= 2:
        label = "Strong"
    elif score <= -1:
        label = "Weak"
    else:
        label = "Mixed"
    if reasons:
        text = f"{symbol} company is {label}: " + "; ".join(reasons) + "."
    else:
        text = f"{symbol} company is {label}: no strong signals in the numbers."
    return text


# ---------- Adapter: Yasir's data shapes -> the brain's shapes ----------

def closes_from_candles(candle_data):
    """His candles arrive NEWEST first; the brain wants closes OLDEST first.
    So: take each candle's close, then reverse the list."""
    closes = [c["close"] for c in reversed(candle_data["candles"])]
    return closes


async def load_context():
    """The harness loads its context BEFORE answering: it calls Yasir's tools
    and keeps the results. Each symbol is loaded separately; if one fetch
    fails, that symbol is skipped (the harness will refuse its questions)."""
    ctx = {"closes": {}, "company": {}, "candle_source": {}}
    for symbol in ["IBM", "AAPL"]:
        try:
            candles = await call_tool("get_daily_candles", {"symbol": symbol, "limit": 100})
            if "candles" not in candles:
                print(f"  ({symbol} candles unavailable: {candles.get('error', 'no data')})")
                continue
            ctx["closes"][symbol] = closes_from_candles(candles)
            ctx["candle_source"][symbol] = candles["source"] + f" (latest {candles['latest_date']})"
            fund = await call_tool("fundamental_analysis", {"symbol": symbol})
            growth = fund.get("growth", {})
            ctx["company"][symbol] = {
                # Yahoo gives growth as decimals (0.25) -> our brain wants percent (25.0)
                "earnings_growth": (growth.get("earnings_growth") or 0) * 100,
                "revenue_growth": (growth.get("revenue_growth") or 0) * 100,
                "pe_ratio": fund["valuation"]["trailing_pe"],
            }
            print(f"  Loaded {symbol}: {len(ctx['closes'][symbol])} closes + company data.")
        except Exception as e:
            print(f"  ({symbol} could not be loaded: {e})")
    ctx["compare"] = await call_tool("compare_stocks", {"symbols": ["IBM", "MSFT"]})
    ctx["projection"] = await call_tool("projection", {"symbol": "IBM", "years": 3})
    return ctx


# ---------- Tools of the harness (Step 5 jobs, now on live data) ----------

def tool_technical(symbol, ctx):
    closes = ctx["closes"][symbol][-21:]  # the brain's window: last 21 closes
    action, t, m = decide(closes)
    r = rsi(closes)
    text = (f"{symbol}: {action} | Trend {t} | Momentum {m:.1f}% | "
            f"RSI {r:.1f} ({rsi_label(r)})")
    if action.startswith("BUY"):
        reason = "Price is going up and moving fast. Buy now, hold for the short term."
    elif action.startswith("SELL"):
        reason = "Price is falling and moving fast down. Safer to sell/avoid for now."
    else:
        reason = "No clear fast move. Wait and watch for a clear direction."
    if rsi_label(r) == "Overbought":
        reason += " But RSI is overbought, so be careful - it has risen a lot."
    if rsi_label(r) == "Oversold":
        reason += " RSI is oversold - it has fallen a lot, a bounce is possible."
    return text + f"\n         Reason: {reason}"


def tool_fundamental(symbol, ctx):
    return fundamental(symbol, ctx["company"][symbol])


def tool_compare(ctx):
    rows = ctx["compare"]["comparison"]
    lines = []
    for row in rows:
        lines.append(f"{row['symbol']}: ${row['price']} | {row['trend']} | "
                     f"RSI {row['rsi']:.1f} | 1-month {row['return_1m_pct']}% | "
                     f"3-month {row['return_3m_pct']}%")
    a, b = rows[0], rows[1]
    lines.append(f"On the 3-month return, {max(a, b, key=lambda x: x['return_3m_pct'])['symbol']} "
                 f"is ahead ({max(a['return_3m_pct'], b['return_3m_pct'])}% vs "
                 f"{min(a['return_3m_pct'], b['return_3m_pct'])}%); "
                 f"on the 1-month return, {max(a, b, key=lambda x: x['return_1m_pct'])['symbol']} "
                 f"is ahead ({max(a['return_1m_pct'], b['return_1m_pct'])}% vs "
                 f"{min(a['return_1m_pct'], b['return_1m_pct'])}%).")
    return "\n         ".join(lines)


def tool_projection(ctx):
    p = ctx["projection"]
    return (f"IBM in {p['years']} years (scenario model, {p['simulations']} simulations): "
            f"start ${p['start_price']} -> median ${p['median_p50']}; "
            f"low case (p10) ${p['p10']}; high case (p90) ${p['p90']}. "
            f"This is a scenario range, NOT a prediction.")


# ---------- The harness (Step 5): understand -> pick tool -> answer in format ----------

RULES = ("Trend = 5-day vs 20-day average. Momentum = 10-day change. RSI = 14 changes. "
         "P/E fair <= 25, expensive >= 40. Analysis runs on the last 21 daily closes.")


def ask(question, ctx):
    q = question.lower()
    loaded = sorted(ctx["closes"].keys())
    symbol = None
    for s in loaded:
        if s.lower() in q:
            symbol = s

    if "compar" in q:
        return ("compare", tool_compare(ctx),
                "Yahoo Finance (yfinance) via MCP compare_stocks",
                "Returns are past performance, not a promise of future results. " + RULES)
    if "year" in q or "future" in q or "projection" in q:
        p = ctx["projection"]
        return ("projection", tool_projection(ctx),
                "Yahoo Finance (yfinance) via MCP projection",
                " ".join(p["assumptions"]))
    if symbol is None:
        return ("none (not allowed)",
                "I cannot answer that yet. Live data is loaded for: "
                + ", ".join(loaded)
                + ". Ask me to buy/sell a loaded stock, about its company, "
                  "to compare IBM and MSFT, or for a projection.",
                "No data used", RULES)
    if "company" in q or "fundamental" in q or "business" in q or "earnings" in q:
        return ("fundamental", tool_fundamental(symbol, ctx),
                "Yahoo Finance (yfinance) via MCP fundamental_analysis (growth + P/E)",
                "Growth is year-over-year from Yahoo Finance. " + RULES)
    return ("technical", tool_technical(symbol, ctx),
            ctx["candle_source"][symbol] + " via MCP get_daily_candles", RULES)


async def main():
    print("Loading live data through Yasir's MCP tools...")
    ctx = await load_context()
    print()

    questions = [
        "Should I buy IBM?",
        "How is the IBM company?",
        "Should I buy AAPL?",
        "How is the AAPL company?",
        "Compare IBM and MSFT",
        "Where could IBM be in 3 years?",
        "Should I buy TSLA?",
    ]
    for q in questions:
        tool, answer, sources, assumptions = ask(q, ctx)
        print(f"Question: {q}")
        print(f"Tool called: {tool}")
        print(f"Answer: {answer}")
        print(f"Sources: {sources}")
        print(f"Assumptions: {assumptions}")
        print()
    print("Done: harness answered 7 questions on LIVE data (v2).")


if __name__ == "__main__":
    asyncio.run(main())
