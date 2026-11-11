"""Tests for Yasir's data connector (Alpha Vantage) — offline, saved copies.

Run: python -m pytest tests/test_market_data.py -q
"""
import json

import pytest

from stock_assistant import market_data


def test_parse_daily_first_rows_match_alphavantage_ibm():
    payload = json.loads((market_data.SAMPLES / "IBM_daily.json").read_text())
    out = market_data.parse_daily(payload, "IBM", "test")
    assert out["latest_date"] == "2026-11-10"
    first5 = out["candles"][:5]
    assert [c["date"] for c in first5] == ["2026-11-10", "2026-11-09", "2026-11-06",
                                           "2026-11-05", "2026-11-04"]
    assert first5[0] == {"date": "2026-11-10", "open": 244.38, "high": 246.0,
                         "low": 242.7, "close": 244.53, "volume": 2971839}
    for c in first5:
        assert c["high"] >= c["low"] and c["volume"] > 0


def test_saved_copy_fallback_when_provider_down(monkeypatch):
    def boom(fn, symbol):
        raise market_data.urllib.error.URLError("blocked")
    monkeypatch.setattr(market_data, "_fetch", boom)
    out = market_data.get_daily_candles("IBM", limit=5)
    assert "saved copy" in out["source"] and len(out["candles"]) == 5
    comp = market_data.get_company_data("IBM")
    assert comp["quarterly"]["sales_revenue"] == 17103000000
    assert comp["quarterly"]["eps_reported"] == 2.95
    assert comp["currency"] == "USD" and comp["period_label"] == "Q3 2026"


def test_parse_company_missing_values_become_null():
    out = market_data.parse_company("IBM", {}, {}, {}, {}, {}, "test")
    assert out["quarterly"]["sales_revenue"] is None
    assert out["valuation"]["pe_ratio"] is None


def test_invalid_code_format_message():
    out = market_data.get_daily_candles("!!!")
    assert "Invalid stock code" in out["error"]
