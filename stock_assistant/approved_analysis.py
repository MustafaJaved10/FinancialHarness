"""Approved calculations that can run without network or credentials."""
import math
import statistics

from brain_live import decide, rsi, rsi_label

from .integration import response


def price_source(data):
    return f"{data['source']} · through {data['latest_date']}"


def technical(data):
    if "error" in data:
        return response("technical", data["error"])
    rows = [row for row in reversed(data["candles"]) if all(
        row.get(key) is not None for key in ("open", "high", "low", "close", "volume")
    )]
    if len(rows) < 21:
        return response("technical", "At least 21 complete daily prices are needed for these indicators.",
                        [price_source(data)])
    closes = [row["close"] for row in rows]
    latest = rows[-1]
    _, trend, momentum = decide(closes[-21:])
    strength = rsi(closes[-21:])
    symbol = data["symbol"]
    return response(
        "technical",
        f"{symbol} closed at ${latest['close']:,.2f} on {latest['date']}, with {latest['volume']:,.0f} shares traded. "
        f"Trend: {trend.lower()}. The 10-day change was {momentum:+.1f}% and RSI was {strength:.1f} ({rsi_label(strength).lower()}).",
        [price_source(data)], ["Daily historical prices. Trend compares the 5-day and 20-day averages."],
        chart={"symbol": symbol, "currency": "USD", "candles": rows[-45:]},
    )


def fundamental(data):
    if "error" in data:
        return response("fundamental", data["error"])
    names = {
        "sales_revenue": "Revenue", "net_profit": "Net income", "eps_reported": "Earnings per share",
        "gross_profit": "Gross profit", "operating_income": "Operating income", "ebitda": "EBITDA",
        "total_assets": "Total assets", "total_liabilities": "Total liabilities",
        "total_equity": "Total equity", "cash_and_equivalents": "Cash and equivalents",
        "operating_cashflow": "Operating cash flow", "capital_expenditures": "Capital spending",
        "market_cap": "Market cap", "pe_ratio": "Price-to-earnings ratio", "forward_pe": "Forward P/E",
        "price_to_book": "Price-to-book ratio",
    }
    metrics = {**data["quarterly"], **data["valuation"]}
    period = data.get("reporting_period") or "Unknown period"
    return response(
        "fundamental", f"Here are {data['symbol']}'s reported financials for the period ending {period}, with available valuation figures.",
        [data["source"]], ["Amounts use the reported currency. Valuation ratios are shown separately from reported earnings."],
        table={"columns": ["Metric", "Value", "Unit", "Period"], "rows": [
            [label, metrics[key], ("ratio" if key in {"pe_ratio", "forward_pe", "price_to_book"} else data.get("currency")),
             (period if key in data["quarterly"] else "Provider snapshot")]
            for key, label in names.items() if metrics.get(key) is not None
        ]},
    )


def compare(series):
    errors = [data["error"] for data in series if "error" in data]
    if errors:
        return response("compare", " ".join(errors))
    indexed = [{row["date"]: row["close"] for row in data["candles"] if row.get("close")} for data in series]
    dates = sorted(set(indexed[0]) & set(indexed[1]))[-21:]
    if len(dates) < 2:
        return response("compare", "The two sources do not have enough overlapping trading dates.")
    rows = [[data["symbol"], round(prices[dates[-1]], 2), round((prices[dates[-1]] / prices[dates[0]] - 1) * 100, 2)]
            for data, prices in zip(series, indexed)]
    return response(
        "compare", f"Price comparison for {rows[0][0]} and {rows[1][0]} from {dates[0]} to {dates[-1]}.",
        [price_source(data) for data in series], ["Both stocks use the same trading dates. Returns exclude dividends."],
        table={"columns": ["Stock", "Closing price (USD)", "Price change (%)"], "rows": rows},
    )


def projection(data, years):
    if "error" in data:
        return response("projection", data["error"])
    if not 1 <= years <= 10:
        return response("projection", "Choose a projection between 1 and 10 years.")
    closes = [row["close"] for row in reversed(data["candles"]) if row.get("close")]
    if len(closes) < 21:
        return response("projection", "At least 21 daily prices are needed for this scenario.")
    volatility = statistics.stdev(math.log(b / a) for a, b in zip(closes, closes[1:]))
    spread = volatility * math.sqrt(252 * years)
    price = closes[-1]
    return response(
        "projection", f"Illustrative {years}-year price scenarios for {data['symbol']}, starting at ${price:,.2f}.",
        [price_source(data)],
        ["Zero drift. Daily historical volatility is scaled using 252 trading days per year. This is a scenario, not a forecast."],
        table={"columns": ["Scenario", "Price (USD)"], "rows": [
            ["Lower", round(price * math.exp(-spread), 2)], ["Flat", round(price, 2)],
            ["Higher", round(price * math.exp(spread), 2)],
        ]},
    )


def what_if(amount, change):
    if not 0 < amount <= 1_000_000_000 or not -100 <= change <= 1000:
        return response("what_if", "Use a positive amount up to $1 billion and a change between -100% and 1,000%.")
    end = round(amount * (1 + change / 100), 2)
    return response(
        "what_if", f"A ${amount:,.2f} position would be worth ${end:,.2f} after a {change:+g}% move.",
        assumptions=["The price move is supplied by the user. Fees, dividends and taxes are excluded."],
        table={"columns": ["Starting value (USD)", "Price change (%)", "Ending value (USD)"],
               "rows": [[amount, change, end]]},
    )


def calculate(operation, payload):
    if operation == "refusal":
        return response("none", payload["answer"])
    return {"technical": technical, "fundamental": fundamental, "compare": compare,
            "projection": projection, "what_if": what_if}[operation](**payload)
