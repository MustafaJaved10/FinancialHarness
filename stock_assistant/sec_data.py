"""Read quarterly company fundamentals from the SEC Company Facts API."""
import json
import urllib.request
from datetime import date
from functools import lru_cache
from time import monotonic

CIKS = {"IBM": "0000051143", "AAPL": "0000320193", "MSFT": "0000789019"}
BASE = "https://data.sec.gov/api/xbrl/companyfacts"
FORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A"}
REVENUE = ("RevenueFromContractWithCustomerExcludingAssessedTax",
           "RevenueFromContractWithCustomerIncludingAssessedTax",
           "Revenues", "SalesRevenueNet")
INCOME = ("NetIncomeLoss", "ProfitLoss")
EPS = ("EarningsPerShareDiluted",)
DURATION_METRICS = {
    "sales_revenue": REVENUE,
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_profit": INCOME,
}
BALANCE_METRICS = {
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "total_equity": ("StockholdersEquity",),
    "cash_and_equivalents": ("CashAndCashEquivalentsAtCarryingValue",),
}
CASH_METRICS = {
    "operating_cashflow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment",),
}


def observations(facts, names, unit):
    for name in names:
        yield from (row for row in facts.get(name, {}).get("units", {}).get(unit, [])
                    if row.get("form") in FORMS and isinstance(row.get("val"), (int, float)))


def duration(row):
    if not row.get("start"):
        return 0
    return (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1


def period_value(facts, names, unit, end, start=None):
    rows = [row for row in observations(facts, names, unit)
            if row["end"] == end and row.get("start") == start]
    if not rows:
        return None
    return max(rows, key=lambda row: row.get("filed", ""))["val"]


def cash_for_quarter(facts, names, start, end):
    value = period_value(facts, names, "USD", end, start)
    if value is not None:
        return value
    cumulative = [row for row in observations(facts, names, "USD")
                  if row["end"] == end and row.get("start", end) < start]
    if not cumulative:
        return None
    latest = max(cumulative, key=lambda row: (row.get("filed", ""), duration(row)))
    previous_end = date.fromordinal(date.fromisoformat(start).toordinal() - 1).isoformat()
    previous = period_value(facts, names, "USD", previous_end, latest["start"])
    return latest["val"] - previous if previous is not None else None


def parse_company_facts(payload, symbol):
    if not isinstance(payload, dict):
        return None
    facts = payload.get("facts", {}).get("us-gaap", {})
    revenue = sorted(
        (row for row in observations(facts, REVENUE, "USD") if 70 <= duration(row) <= 110),
        key=lambda row: (row["end"], row.get("filed", "")), reverse=True,
    )
    for row in revenue:
        start, end = row["start"], row["end"]
        if period_value(facts, INCOME, "USD", end, start) is not None:
            break
    else:
        return None

    quarter = {metric: period_value(facts, tags, "USD", end, start)
               for metric, tags in DURATION_METRICS.items()}
    quarter.update({metric: period_value(facts, tags, "USD", end)
                    for metric, tags in BALANCE_METRICS.items()})
    quarter.update({metric: cash_for_quarter(facts, tags, start, end)
                    for metric, tags in CASH_METRICS.items()})
    quarter["ebitda"] = None
    quarter["eps_reported"] = period_value(facts, EPS, "USD/shares", end, start)
    if quarter["eps_reported"] is None:
        quarter["eps_reported"] = period_value(facts, ("EarningsPerShareBasic",), "USD/shares", end, start)

    # Use the most recent annual diluted EPS plus current YTD minus the matching
    # prior-year YTD when those periods are available in the same filing.
    eps_rows = list(observations(facts, EPS, "USD/shares"))
    annual = [fact for fact in eps_rows if fact["end"] <= end and 350 <= duration(fact) <= 380]
    ttm = None
    if annual:
        last_annual = max(annual, key=lambda fact: (fact["end"], fact.get("filed", "")))
        if last_annual["end"] == end:
            ttm = last_annual["val"]
        else:
            after_year = date.fromordinal(date.fromisoformat(last_annual["end"]).toordinal() + 1).isoformat()
            current = [fact for fact in eps_rows if fact["end"] == end and fact.get("start") == after_year]
            if current:
                current_ytd = max(current, key=lambda fact: fact.get("filed", ""))
                prior = [
                    fact for fact in eps_rows if fact.get("accn") == current_ytd.get("accn")
                    and fact["end"] < last_annual["end"]
                    and 350 <= (date.fromisoformat(end) - date.fromisoformat(fact["end"])).days <= 380
                    and abs(duration(fact) - duration(current_ytd)) <= 7 and fact.get("start")
                ]
                if prior:
                    previous_ytd = max(prior, key=lambda fact: fact["end"])
                    ttm = round(last_annual["val"] + current_ytd["val"] - previous_ytd["val"], 4)

    return {
        "symbol": symbol,
        "company_name": payload.get("entityName"),
        "source": f"SEC EDGAR · {row['form']} company filing data",
        "reporting_period": end,
        "period_label": None,
        "reported_date": row.get("filed"),
        "currency": "USD",
        "quarterly": quarter,
        "valuation": dict.fromkeys(("market_cap", "pe_ratio", "forward_pe", "price_to_book",
                                    "dividend_yield", "beta", "week52_high", "week52_low"))
                     | {"eps_ttm": ttm},
    }


@lru_cache(maxsize=16)
def _cached_company(symbol, user_agent, window):
    request = urllib.request.Request(
        f"{BASE}/CIK{CIKS[symbol]}.json",
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return parse_company_facts(json.load(response), symbol)


def get_company_data(symbol, contact_email):
    return _cached_company(symbol, f"Financial Harness {contact_email}", int(monotonic() // 900))
