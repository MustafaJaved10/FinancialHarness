"""Market and company data from Alpha Vantage and SEC EDGAR.

This is the data layer Mustafa's AI harness calls through the MCP tools in
``mcp_server.py``. Only the Python standard library is used (urllib), so the
connector runs anywhere with no extra installs.

Shared candles format (the group-agreed format used by the Charts screen):

    {
      "symbol": "IBM",
      "source": "Alpha Vantage — TIME_SERIES_DAILY",
      "latest_date": "2026-11-10",
      "candles": [
        {"date": "2026-11-10", "open": 244.38, "high": 246.0,
         "low": 242.7, "close": 244.53, "volume": 2971839},
        ... newest first ...
      ]
    }

API key: environment variable ALPHAVANTAGE_API_KEY. Without one the public
"demo" key is used, which Alpha Vantage allows for IBM only.
If the live provider is blocked / rate-limited and a saved copy exists in
data/samples/<SYMBOL>_*.json, the saved copy is returned and the source
string says so — the format and the connector stay testable either way.
Set SEC_CONTACT_EMAIL to try SEC filings first for supported company tickers.
"""
from __future__ import annotations

import json
import csv
import os
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from time import monotonic

from . import sec_data

BASE = "https://www.alphavantage.co/query"
SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
TIMEOUT = 30


def _api_key() -> str:
    return os.environ.get("ALPHAVANTAGE_API_KEY", "demo")


def _fetch(function: str, symbol: str) -> dict:
    if os.environ.get("STOCK_DATA_MODE") == "saved":
        raise urllib.error.URLError("Using saved data")
    url = f"{BASE}?function={function}&symbol={symbol}&apikey={_api_key()}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return json.load(resp)


def _num(value):
    """Alpha Vantage sends numbers as strings; 'None'/'-' means missing -> None."""
    if value in (None, "None", "-", ""):
        return None
    try:
        f = float(value)
        return int(f) if f == int(f) and abs(f) >= 1000 else f
    except (TypeError, ValueError):
        return None


def _provider_error(payload: dict) -> str | None:
    if "Error Message" in payload:
        return "invalid_symbol"
    info = str(payload.get("Information", ""))
    if "demo" in info.lower():
        return "demo_key"  # demo key works for IBM only
    if "Note" in payload or "Information" in payload:
        return "provider_limit"
    return None


DEMO_KEY_MSG = ("The free demo key only works for IBM. For other symbols, claim a free "
                "API key at alphavantage.co and set ALPHAVANTAGE_API_KEY.")


def _saved(symbol: str, kind: str) -> dict | None:
    path = SAMPLES / f"{symbol}_{kind}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


# ---------------------------------------------------------------- prices ---
def parse_daily(payload: dict, symbol: str, source: str) -> dict:
    series = payload.get("Time Series (Daily)")
    if not series:
        return {"error": f"No daily data returned for '{symbol}'.", "symbol": symbol}
    candles = []
    for date in sorted(series.keys(), reverse=True):
        row = series[date]
        candles.append({
            "date": date,
            "open": _num(row.get("1. open")), "high": _num(row.get("2. high")),
            "low": _num(row.get("3. low")), "close": _num(row.get("4. close")),
            "volume": _num(row.get("5. volume")),
        })
    return {"symbol": symbol, "source": source,
            "latest_date": candles[0]["date"] if candles else None, "candles": candles}


def get_daily_candles(symbol: str, limit: int = 100) -> dict:
    """Daily OHLCV candles for one stock code, in the shared format."""
    symbol = symbol.upper().strip()
    if not symbol.isalnum() or len(symbol) > 10:
        return {"error": f"Invalid stock code '{symbol}': use letters only, e.g. IBM, AAPL.", "symbol": symbol}
    source = "Alpha Vantage — TIME_SERIES_DAILY"
    try:
        payload = _fetch("TIME_SERIES_DAILY", symbol)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        payload = None
    if payload is not None:
        err = _provider_error(payload)
        if err == "invalid_symbol":
            return {"error": f"Invalid stock code '{symbol}': Alpha Vantage has no such symbol.", "symbol": symbol}
        if err is None and payload.get("Time Series (Daily)"):
            result = parse_daily(payload, symbol, source)
            result["candles"] = result["candles"][:limit]
            return result
    # Provider blocked / rate-limited / empty -> saved copy keeps us testable
    saved = _saved(symbol, "daily")
    if saved:
        result = parse_daily(saved, symbol, source + " (saved copy — live provider unavailable)")
        result["candles"] = result["candles"][:limit]
        return result
    training_path = SAMPLES.parent / "training" / f"{symbol}_daily_5y.csv"
    if training_path.is_file():
        with training_path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))[-limit:]
        candles = [
            {"date": row["Date"][:10], **{key.lower(): _num(row[key]) for key in (
                "Open", "High", "Low", "Close", "Volume"
            )}}
            for row in reversed(rows)
        ]
        if candles:
            return {"symbol": symbol, "source": "Yahoo Finance (saved training data)",
                    "latest_date": candles[0]["date"], "candles": candles}
    if payload is not None and _provider_error(payload) == "demo_key":
        return {"error": DEMO_KEY_MSG, "symbol": symbol}
    if payload is not None and _provider_error(payload) == "provider_limit":
        return {"error": "Alpha Vantage rate limit reached. Try again in a minute or set your own ALPHAVANTAGE_API_KEY.", "symbol": symbol}
    return {"error": f"Provider error: no data for '{symbol}' and no saved copy available.", "symbol": symbol}


# --------------------------------------------------------------- company ---
def _quarter_label(fiscal_date: str | None) -> str | None:
    if not fiscal_date:
        return None
    year, month = fiscal_date[:4], int(fiscal_date[5:7])
    return f"Q{(month - 1) // 3 + 1} {year}"


def parse_company(symbol: str, income: dict, balance: dict, cashflow: dict,
                  earnings: dict, overview: dict, source: str) -> dict:
    qi = (income.get("quarterlyReports") or [{}])[0]
    qb = (balance.get("quarterlyReports") or [{}])[0]
    qc = (cashflow.get("quarterlyReports") or [{}])[0]
    qe = (earnings.get("quarterlyEarnings") or [{}])[0]
    period = qi.get("fiscalDateEnding") or qe.get("fiscalDateEnding")
    return {
        "symbol": symbol,
        "company_name": overview.get("Name"),
        "source": source,
        "reporting_period": period,
        "period_label": _quarter_label(period),
        "reported_date": qe.get("reportedDate"),
        "currency": qi.get("reportedCurrency") or overview.get("Currency"),
        "quarterly": {
            "sales_revenue": _num(qi.get("totalRevenue")),
            "gross_profit": _num(qi.get("grossProfit")),
            "operating_income": _num(qi.get("operatingIncome")),
            "net_profit": _num(qi.get("netIncome")),
            "ebitda": _num(qi.get("ebitda")),
            "eps_reported": _num(qe.get("reportedEPS")),
            "total_assets": _num(qb.get("totalAssets")),
            "total_liabilities": _num(qb.get("totalLiabilities")),
            "total_equity": _num(qb.get("totalShareholderEquity")),
            "cash_and_equivalents": _num(qb.get("cashAndCashEquivalentsAtCarryingValue")),
            "operating_cashflow": _num(qc.get("operatingCashflow")),
            "capital_expenditures": _num(qc.get("capitalExpenditures")),
        },
        "valuation": {
            "market_cap": _num(overview.get("MarketCapitalization")),
            "pe_ratio": _num(overview.get("PERatio")),
            "forward_pe": _num(overview.get("ForwardPE")),
            "price_to_book": _num(overview.get("PriceToBookRatio")),
            "eps_ttm": _num(overview.get("EPS")),
            "dividend_yield": _num(overview.get("DividendYield")),
            "beta": _num(overview.get("Beta")),
            "week52_high": _num(overview.get("52WeekHigh")),
            "week52_low": _num(overview.get("52WeekLow")),
        },
    }


@lru_cache(maxsize=16)
def _valuation_quote(symbol, window):
    return get_daily_candles(symbol, limit=1)


def _sec_company(symbol, contact_email, include_valuation):
    try:
        company = sec_data.get_company_data(symbol, contact_email)
    except (OSError, ValueError):
        return None
    if company is None:
        return None

    valuation = company["valuation"].copy()
    result = {**company, "valuation": valuation}
    eps = valuation.get("eps_ttm")
    if include_valuation and eps and eps > 0:
        prices = _valuation_quote(symbol, int(monotonic() // 900))
        candles = prices.get("candles") or []
        if candles and candles[0].get("close"):
            valuation["pe_ratio"] = round(candles[0]["close"] / eps, 2)
            result["valuation_source"] = f"{prices['source']} · closing price on {candles[0]['date']}"
            result["valuation_date"] = candles[0]["date"]
    return result


def get_company_data(symbol: str, include_valuation: bool = True) -> dict:
    """Latest reported quarter + valuation for one stock code.

    Any value the source does not report is returned as None (null) — never guessed.
    """
    symbol = symbol.upper().strip()
    if not symbol.isalnum() or len(symbol) > 10:
        return {"error": f"Invalid stock code '{symbol}': use letters only, e.g. IBM, AAPL.", "symbol": symbol}
    contact_email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if contact_email and symbol in sec_data.CIKS and os.environ.get("STOCK_DATA_MODE") != "saved":
        company = _sec_company(symbol, contact_email, include_valuation)
        if company is not None:
            return company
    source = ("Alpha Vantage — INCOME_STATEMENT / BALANCE_SHEET / CASH_FLOW / "
              "EARNINGS / OVERVIEW")
    kinds = {"income": "INCOME_STATEMENT", "balance": "BALANCE_SHEET",
             "cashflow": "CASH_FLOW", "earnings": "EARNINGS", "overview": "OVERVIEW"}
    live, ok = {}, True
    for kind, fn in kinds.items():
        try:
            payload = _fetch(fn, symbol)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            ok = False
            break
        if _provider_error(payload) == "invalid_symbol":
            return {"error": f"Invalid stock code '{symbol}': Alpha Vantage has no such symbol.", "symbol": symbol}
        if _provider_error(payload) is not None:
            ok = False
            break
        live[kind] = payload
    if ok and live.get("income", {}).get("quarterlyReports"):
        return parse_company(symbol, live["income"], live["balance"], live["cashflow"],
                             live["earnings"], live["overview"], source)
    saved = {kind: _saved(symbol, name) for kind, name in
             [("income", "income_statement"), ("balance", "balance_sheet"),
              ("cashflow", "cash_flow"), ("earnings", "earnings"), ("overview", "overview")]}
    if saved["income"] and saved["overview"]:
        return parse_company(symbol, saved["income"] or {}, saved["balance"] or {},
                             saved["cashflow"] or {}, saved["earnings"] or {},
                             saved["overview"] or {},
                             source + " (saved copy — live provider unavailable)")
    if _api_key() == "demo" and symbol != "IBM":
        return {"error": DEMO_KEY_MSG, "symbol": symbol}
    return {"error": f"Provider error: company data for '{symbol}' unavailable and no saved copy exists.",
            "symbol": symbol}
