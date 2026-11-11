import os
import unittest
from unittest.mock import patch

from stock_assistant import approved_analysis, market_data, sec_data


def observation(value, end, start=None, *, accession="quarter"):
    result = {"val": value, "end": end, "form": "10-Q", "filed": "2026-10-22", "accn": accession}
    if start:
        result["start"] = start
    return result


def facts():
    end, start = "2026-09-30", "2026-07-01"
    return {"entityName": "IBM", "facts": {"us-gaap": {
        sec_data.REVENUE[0]: {"units": {"USD": [
            observation(17_103_000_000, end, start),
            observation(50_000_000_000, end, "2026-01-01"),
        ]}},
        "NetIncomeLoss": {"units": {"USD": [observation(2_189_000_000, end, start)]}},
        "Assets": {"units": {"USD": [observation(100, end), observation(50, "2026-06-30")]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            observation(2.95, end, start),
            observation(9, "2025-12-31", "2025-01-01", accession="annual"),
            observation(7, end, "2026-01-01"),
            observation(6, "2025-09-30", "2025-01-01"),
        ]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            observation(5, end, "2026-01-01"),
            observation(3, "2026-06-30", "2026-01-01"),
        ]}},
    }}}


class SecCompanyDataTest(unittest.TestCase):
    def test_parse_quarter_not_year_to_date(self):
        result = sec_data.parse_company_facts(facts(), "IBM")
        self.assertEqual(result["reporting_period"], "2026-09-30")
        self.assertEqual(result["quarterly"]["sales_revenue"], 17_103_000_000)
        self.assertEqual(result["quarterly"]["eps_reported"], 2.95)
        self.assertEqual(result["quarterly"]["operating_cashflow"], 2)
        self.assertEqual(result["quarterly"]["total_assets"], 100)
        self.assertEqual(result["valuation"]["eps_ttm"], 10)

    def test_sec_earnings_without_alpha_vantage_request(self):
        result = sec_data.parse_company_facts(facts(), "IBM")
        with patch.dict(os.environ, {"SEC_CONTACT_EMAIL": "test@example.com", "STOCK_DATA_MODE": "auto"}), \
             patch.object(sec_data, "get_company_data", return_value=result), \
             patch.object(market_data, "_fetch") as fetch:
            self.assertIn("SEC EDGAR", market_data.get_company_data("IBM", include_valuation=False)["source"])
            fetch.assert_not_called()

    def test_valuation_labels_price_source_and_leaves_cached_facts_unchanged(self):
        result = sec_data.parse_company_facts(facts(), "IBM")
        with patch.dict(os.environ, {"SEC_CONTACT_EMAIL": "test@example.com", "STOCK_DATA_MODE": "auto"}), \
             patch.object(sec_data, "get_company_data", return_value=result), \
             patch.object(market_data, "_valuation_quote", return_value={
                 "source": "Alpha Vantage (saved copy)",
                 "candles": [{"date": "2026-11-10", "close": 244.53}],
             }):
            answer = approved_analysis.fundamental(market_data.get_company_data("IBM"))
            self.assertIn("saved copy", answer["sources"][1])
            self.assertIn(["Price-to-earnings ratio", 24.45, "ratio", "2026-11-10"], answer["table"]["rows"])
            self.assertIsNone(result["valuation"]["pe_ratio"])

    def test_saved_mode_never_calls_sec(self):
        with patch.dict(os.environ, {"SEC_CONTACT_EMAIL": "test@example.com", "STOCK_DATA_MODE": "saved"}), \
             patch.object(sec_data, "get_company_data") as sec:
            self.assertIn("saved copy", market_data.get_company_data("IBM")["source"])
            sec.assert_not_called()

    def test_sec_failure_uses_saved_fallback(self):
        with patch.dict(os.environ, {"SEC_CONTACT_EMAIL": "test@example.com", "STOCK_DATA_MODE": "auto"}), \
             patch.object(sec_data, "get_company_data", side_effect=TimeoutError), \
             patch.object(market_data, "_fetch", side_effect=TimeoutError):
            self.assertIn("saved copy", market_data.get_company_data("IBM")["source"])
