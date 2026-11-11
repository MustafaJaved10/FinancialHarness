# Handoff for Mustafa — Data Connector (from Yasir)

My part is complete. This pack contains everything you need to connect your
AI harness to my data tools and test them yourself. Full details are also on
the Jira ticket (copy in `docs/JIRA_TICKET_DATA_CONNECTOR.md`).

## The 2 MCP tools
| Tool | Input | Gives you |
|---|---|---|
| `get_daily_candles` | `symbol` (e.g. "IBM"), optional `limit` (default 100) | Shared candles format: `{symbol, source, latest_date, candles: [{date, open, high, low, close, volume}]}` — newest first |
| `get_company_data` | `symbol` (e.g. "IBM") | `{symbol, company_name, source, reporting_period, period_label, currency, quarterly: {sales_revenue, net_profit, eps_reported, ...}, valuation: {pe_ratio, market_cap, ...}}` — missing values are null |

Source for both: **Alpha Vantage** (prices: TIME_SERIES_DAILY; company:
INCOME_STATEMENT / BALANCE_SHEET / CASH_FLOW / EARNINGS / OVERVIEW).

## Connect (MCP, stdio)
```json
{
  "mcpServers": {
    "stock-data": {
      "command": "python",
      "args": ["-m", "stock_assistant.mcp_server"],
      "cwd": "<repo root>"
    }
  }
}
```
Setup once: `pip install -r requirements.txt` (note: `mcp` is pinned `<2`).

## Test it yourself (no harness needed)
```bash
python tools/test_connector.py IBM
```
Expected (real, verified): candles with latest_date **2026-11-10**
(close 244.53, volume 2,971,839) and company data for **Q3 2026** —
revenue 17,103,000,000 USD, net profit 2,189,000,000, EPS 2.95.

## One limit to know
The public demo API key works for **IBM only**. For any other symbol set
`ALPHAVANTAGE_API_KEY` (free key from alphavantage.co) — the tools return a
clear message saying this instead of failing silently. If the provider is
ever blocked, the tools automatically answer from the saved copies in
`data/samples/` and the `source` field says "saved copy".

— Yasir
