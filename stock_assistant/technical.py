"""Technical analysis: indicators, trend, volume, support/resistance.

Pure pandas/numpy so every number is reproducible and unit-testable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]
    df["SMA20"] = close.rolling(20).mean()
    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()
    df["EMA12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA26"] = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    mid = df["SMA20"]
    std = close.rolling(20).std()
    df["BB_upper"] = mid + 2 * std
    df["BB_mid"] = mid
    df["BB_lower"] = mid - 2 * std
    df["Volume_SMA20"] = df["Volume"].rolling(20).mean()
    df["Daily_Return"] = close.pct_change()
    return df


def summarise(df: pd.DataFrame) -> dict:
    """One-row summary of the latest state + plain-language signals."""
    df = add_indicators(df)
    last = df.iloc[-1]
    price = float(last["Close"])
    if price > last["SMA50"] > last["SMA200"]:
        trend = "Uptrend (price > SMA50 > SMA200)"
    elif price < last["SMA50"] < last["SMA200"]:
        trend = "Downtrend (price < SMA50 < SMA200)"
    else:
        trend = "Sideways / mixed (moving averages not aligned)"
    rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else None
    rsi_note = ("overbought (>70)" if rsi and rsi > 70 else
                "oversold (<30)" if rsi and rsi < 30 else "neutral (30-70)")
    recent = df.tail(60)
    vol_ratio = float(last["Volume"] / last["Volume_SMA20"]) if last["Volume_SMA20"] else None
    return {
        "price": round(price, 2),
        "trend": trend,
        "sma20": _r(last["SMA20"]), "sma50": _r(last["SMA50"]), "sma200": _r(last["SMA200"]),
        "rsi": _r(rsi), "rsi_note": rsi_note,
        "macd": _r(last["MACD"]), "macd_signal": _r(last["MACD_signal"]),
        "macd_note": "bullish momentum" if last["MACD"] > last["MACD_signal"] else "bearish momentum",
        "bollinger": {"upper": _r(last["BB_upper"]), "mid": _r(last["BB_mid"]), "lower": _r(last["BB_lower"])},
        "support_60d": round(float(recent["Low"].min()), 2),
        "resistance_60d": round(float(recent["High"].max()), 2),
        "volume": int(last["Volume"]), "volume_vs_20d_avg": _r(vol_ratio),
        "volatility_30d_annualised_pct": _r(float(df["Daily_Return"].tail(30).std() * np.sqrt(252) * 100)),
        "return_1m_pct": _pct(df, 21), "return_3m_pct": _pct(df, 63), "return_1y_pct": _pct(df, 252),
    }


def _r(x):
    return round(float(x), 2) if x is not None and pd.notna(x) else None


def _pct(df, n):
    if len(df) <= n:
        return None
    return round(float((df["Close"].iloc[-1] / df["Close"].iloc[-n - 1] - 1) * 100), 2)
