# Jira Ticket — Data Connector (MCP) — Yasir

**Title:** Market + company data connector: two MCP tools (Alpha Vantage)
**Status:** ✅ Done — both tools direct-call tested with real IBM data (below).
**For:** Mustafa — your harness can connect and test with the commands at the end.

## What was built
Code: `stock_assistant/market_data.py` (stdlib only, no extra installs) +
tools registered in `stock_assistant/mcp_server.py`. Saved provider copies in
`data/samples/` are used automatically if the live provider is blocked or
rate-limited; the `source` field then says "saved copy".

## Tool 1 — prices & volume
- **Name:** `get_daily_candles`
- **Inputs:** `symbol` (string, e.g. "IBM"), `limit` (int, optional, default 100)
- **Output:** shared candles format —
  `{symbol, source, latest_date, candles: [{date, open, high, low, close, volume}]}`
  (newest first; volume = number of shares traded that day)
- **Source:** Alpha Vantage — TIME_SERIES_DAILY

**Real example — `get_daily_candles("IBM", limit=5)`, source live, latest date 2026-11-10:**
| date | open | high | low | close | volume |
|---|---|---|---|---|---|
| 2026-11-10 | 244.38 | 246.00 | 242.70 | 244.53 | 2,971,839 |
| 2026-11-09 | 246.00 | 248.81 | 245.20 | 246.11 | 4,629,816 |
| 2026-11-06 | 242.92 | 246.34 | 240.35 | 245.00 | 3,494,073 |
| 2026-11-05 | 255.92 | 256.18 | 245.72 | 247.11 | 5,339,546 |
| 2026-11-04 | 255.00 | 258.59 | 253.51 | 254.32 | 3,762,287 |

## Tool 2 — company data
- **Name:** `get_company_data`
- **Input:** `symbol` (string, e.g. "IBM")
- **Output:** `{symbol, company_name, source, reporting_period, period_label,
  reported_date, currency, quarterly: {sales_revenue, gross_profit,
  operating_income, net_profit, ebitda, eps_reported, total_assets,
  total_liabilities, total_equity, cash_and_equivalents, operating_cashflow,
  capital_expenditures}, valuation: {market_cap, pe_ratio, forward_pe,
  price_to_book, eps_ttm, dividend_yield, beta, week52_high, week52_low}}`
  Any value the source does not report is **null** — never guessed.
- **Source:** Alpha Vantage — INCOME_STATEMENT / BALANCE_SHEET / CASH_FLOW /
  EARNINGS / OVERVIEW (company-reported figures; cross-checked against IBM's
  official quarterly reporting page: ibm.com/investor/financial-reporting)

**Real example — `get_company_data("IBM")`:**
Q3 2026 (period ending 2026-09-30, reported 2026-10-21), currency USD —
sales_revenue **17,103,000,000**, net_profit **2,189,000,000**,
eps_reported **2.95** (EPS = profit per share), gross_profit 9,714,000,000,
operating_income 2,880,000,000, total_assets 155,010,000,000,
total_liabilities 118,806,000,000, operating_cashflow 4,025,000,000.
Valuation — market_cap 231,110,394,000, pe_ratio 20.86, price_to_book 6.55,
eps_ttm 11.72, dividend_yield 0.0276, beta 0.764.

## Company-data source — options considered
1. **Alpha Vantage fundamentals (CHOSEN — easiest):** same provider and key
   as the price tool; statements + earnings + valuation in one place; demo
   key works for IBM.
2. SEC EDGAR companyfacts: official and free with no key, but US companies
   only and the field mapping is harder.
3. yfinance (already in the repo): easy, but unofficial and sometimes blocked.

## Errors — clear messages, no guessing
- Wrong code format → "Invalid stock code '...': use letters only, e.g. IBM, AAPL."
- Unknown symbol (with a real key) → "Invalid stock code '...': Alpha Vantage has no such symbol."
- Rate limit / provider block → saved copy is returned and the source says so;
  if there is no saved copy, a clear provider-error message is returned.
- **Known limit:** the public **demo key works for IBM only**. Any other
  symbol returns: "The free demo key only works for IBM… set
  ALPHAVANTAGE_API_KEY" (free key, 20 seconds to claim).

## Source-block status
- Blocked sources: **none.** Alpha Vantage live worked for prices and all
  five company endpoints. Saved copies of every IBM response are committed in
  `data/samples/` so the format and connector stay testable if it ever blocks.

## How Mustafa can connect & test
```bash
pip install -r requirements.txt          # note: mcp is pinned <2 (FastMCP API)
# start the MCP server (stdio):
python -m stock_assistant.mcp_server
# or direct-call test both tools without the harness:
python tools/test_connector.py IBM
```
MCP client config (stdio): command `python`, args `["-m", "stock_assistant.mcp_server"]`,
working directory = repo root. Optional env: `ALPHAVANTAGE_API_KEY=<free key>` for non-IBM symbols.

## Tests
`tests/test_market_data.py` — 4 offline tests (first-5-rows values match the
live IBM response, saved-copy fallback, missing values → null, invalid code
message). Full suite: `python -m pytest -q`.
