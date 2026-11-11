"""Market data provider.

Primary source: Yahoo Finance via yfinance (free, no API key).
Fallback: deterministic synthetic data so the app, tests and demo still run
offline or when a ticker/source is unavailable. Fallback data is ALWAYS
labelled ``source="synthetic-fallback"`` in the result so it is never
mistaken for real market data.
"""
from __future__ import annotations

import hashlib
import numpy as np
import pandas as pd


def _synthetic_history(symbol: str, days: int = 365) -> pd.DataFrame:
    seed = int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    returns = rng.normal(0.0006, 0.018, size=days)
    close = 100 * np.exp(np.cumsum(returns))
    open_ = close * (1 + rng.normal(0, 0.004, size=days))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, size=days)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, size=days)))
    volume = rng.integers(500_000, 8_000_000, size=days)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )


def get_history(symbol: str, period: str = "1y") -> dict:
    """Return OHLCV history for a ticker.

    Result: {"symbol", "source", "history": DataFrame}
    """
    symbol = symbol.upper().strip()
    try:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        if df is not None and not df.empty:
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            return {"symbol": symbol, "source": "yahoo-finance (yfinance)", "history": df}
    except Exception:
        pass  # fall through to the clearly-labelled synthetic fallback
    return {"symbol": symbol, "source": "synthetic-fallback (offline demo data)",
            "history": _synthetic_history(symbol)}


def get_info(symbol: str) -> dict:
    """Company profile + headline fundamentals (best effort)."""
    symbol = symbol.upper().strip()
    try:
        import yfinance as yf

        info = yf.Ticker(symbol).info or {}
        if info.get("longName") or info.get("shortName"):
            keys = ["longName", "sector", "industry", "marketCap", "trailingPE",
                    "forwardPE", "priceToBook", "dividendYield", "beta",
                    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "profitMargins",
                    "returnOnEquity", "debtToEquity", "revenueGrowth",
                    "earningsGrowth", "currentPrice"]
            return {"symbol": symbol, "source": "yahoo-finance (yfinance)",
                    "info": {k: info.get(k) for k in keys}}
    except Exception:
        pass
    return {"symbol": symbol, "source": "synthetic-fallback (offline demo data)",
            "info": {"longName": f"{symbol} (demo profile)", "sector": "Unknown",
                     "industry": "Unknown", "marketCap": None, "trailingPE": None,
                     "forwardPE": None, "priceToBook": None, "dividendYield": None,
                     "beta": None, "fiftyTwoWeekHigh": None, "fiftyTwoWeekLow": None,
                     "profitMargins": None, "returnOnEquity": None,
                     "debtToEquity": None, "revenueGrowth": None,
                     "earningsGrowth": None, "currentPrice": None}}


def get_financials(symbol: str) -> dict:
    """Income statement / balance sheet / cash flow summaries (best effort)."""
    symbol = symbol.upper().strip()
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        out = {}
        for name, frame in [("income_statement", t.income_stmt),
                            ("balance_sheet", t.balance_sheet),
                            ("cash_flow", t.cashflow)]:
            if frame is not None and not frame.empty:
                out[name] = frame.iloc[:, :4]  # latest 4 periods
        if out:
            return {"symbol": symbol, "source": "yahoo-finance (yfinance)", "statements": out}
    except Exception:
        pass
    return {"symbol": symbol, "source": "synthetic-fallback (offline demo data)", "statements": {}}
