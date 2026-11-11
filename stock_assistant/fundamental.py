"""Fundamental analysis: valuation, profitability, leverage, growth."""
from __future__ import annotations


def summarise(info: dict) -> dict:
    i = info.get("info", {})
    pe, fpe, pb = i.get("trailingPE"), i.get("forwardPE"), i.get("priceToBook")
    valuation_notes = []
    if pe:
        valuation_notes.append(
            f"P/E {pe:.1f} is " + ("high vs a typical 10-25 market range — growth is priced in"
                                   if pe > 25 else "within a typical 10-25 market range"
                                   if pe >= 10 else "low — either undervalued or facing problems"))
    if pb:
        valuation_notes.append(f"Price/Book {pb:.2f}")
    if i.get("dividendYield"):
        valuation_notes.append(f"Dividend yield {i['dividendYield'] * 100:.2f}%")
    return {
        "company": i.get("longName"), "sector": i.get("sector"), "industry": i.get("industry"),
        "market_cap": i.get("marketCap"), "current_price": i.get("currentPrice"),
        "valuation": {"trailing_pe": pe, "forward_pe": fpe, "price_to_book": pb,
                      "dividend_yield": i.get("dividendYield"), "notes": valuation_notes},
        "profitability": {"profit_margins": i.get("profitMargins"),
                          "return_on_equity": i.get("returnOnEquity")},
        "risk": {"beta": i.get("beta"), "debt_to_equity": i.get("debtToEquity"),
                 "week52_high": i.get("fiftyTwoWeekHigh"), "week52_low": i.get("fiftyTwoWeekLow")},
        "growth": {"revenue_growth": i.get("revenueGrowth"),
                   "earnings_growth": i.get("earningsGrowth")},
        "source": info.get("source"),
    }
