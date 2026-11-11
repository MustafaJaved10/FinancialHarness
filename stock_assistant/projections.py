"""Projections, stock comparison and what-if scenarios (Python-powered)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_provider, technical


def compare(symbols: list[str]) -> list[dict]:
    rows = []
    for s in symbols:
        hist = data_provider.get_history(s)["history"]
        t = technical.summarise(hist)
        rows.append({"symbol": s.upper(), "price": t["price"], "trend": t["trend"],
                     "rsi": t["rsi"], "return_1m_pct": t["return_1m_pct"],
                     "return_3m_pct": t["return_3m_pct"], "return_1y_pct": t["return_1y_pct"],
                     "volatility_pct": t["volatility_30d_annualised_pct"]})
    return rows


def projection(symbol: str, years: int = 3, simulations: int = 1000) -> dict:
    """Monte-Carlo projection from the stock's own historical drift/volatility.

    Assumptions are returned with the result — a projection is a scenario
    model, NOT a prediction.
    """
    hist = data_provider.get_history(symbol, period="2y")["history"]
    log_returns = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
    mu, sigma = float(log_returns.mean()), float(log_returns.std())
    rng = np.random.default_rng(42)
    days = int(years * 252)
    paths = np.exp(np.cumsum(rng.normal(mu, sigma, size=(simulations, days)), axis=1))
    start = float(hist["Close"].iloc[-1])
    final = start * paths[:, -1]
    return {
        "symbol": symbol.upper(), "start_price": round(start, 2), "years": years,
        "simulations": simulations,
        "p10": round(float(np.percentile(final, 10)), 2),
        "median_p50": round(float(np.percentile(final, 50)), 2),
        "p90": round(float(np.percentile(final, 90)), 2),
        "assumptions": [
            f"Daily drift/volatility estimated from the last ~2 years of prices (mu={mu:.5f}, sigma={sigma:.4f})",
            "Returns assumed log-normal; no dividends, splits, fees or taxes included",
            "Past volatility is not a guarantee of future behaviour — scenario model, not a prediction",
        ],
    }


def what_if(symbol: str, investment: float, monthly_add: float = 0.0,
            annual_return_pct: float = 8.0, years: int = 5) -> dict:
    """Deterministic what-if: lump sum + monthly additions at an assumed return."""
    r = annual_return_pct / 100 / 12
    months = int(years * 12)
    value, contributed = float(investment), float(investment)
    for _ in range(months):
        value = value * (1 + r) + monthly_add
        contributed += monthly_add
    return {"symbol": symbol.upper(), "initial": investment, "monthly_add": monthly_add,
            "assumed_annual_return_pct": annual_return_pct, "years": years,
            "total_contributed": round(contributed, 2), "final_value": round(value, 2),
            "gain": round(value - contributed, 2),
            "assumption_note": "Constant assumed return, compounded monthly; real markets vary year to year."}
