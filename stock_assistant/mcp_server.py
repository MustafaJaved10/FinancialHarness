"""MCP server — exposes market data & analysis as Model Context Protocol tools.

Any MCP client (Claude Desktop, Cursor, the AI harness in this repo) can
connect and call these tools. Run:  python -m stock_assistant.mcp_server
Transport: stdio (default MCP local transport).
Market-data MCP: get_quote, get_history_summary, technical_analysis
Company MCP:     fundamental_analysis, compare_stocks, projection
"""
from __future__ import annotations

from . import data_provider, harness, market_data

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Install the MCP SDK first: pip install mcp ({exc})")

mcp = FastMCP("stock-market-assistant")


@mcp.tool()
def get_daily_candles(symbol: str, limit: int = 100) -> dict:
    """Real daily price + volume candles in the shared format (Alpha Vantage).

    Input: a stock code, e.g. "IBM". Output keys: symbol, source,
    latest_date, candles[{date, open, high, low, close, volume}].
    On a wrong code / empty data / provider problem, returns {"error": ...}
    with a clear message instead of guessing.
    """
    return market_data.get_daily_candles(symbol, limit=limit)


@mcp.tool()
def get_company_data(symbol: str, include_valuation: bool = True) -> dict:
    """Reported quarterly company data and optional valuation from available providers.

    Input: a stock code, e.g. "IBM". Output keys: symbol, company_name,
    source, reporting_period, period_label, currency,
    quarterly{sales_revenue, net_profit, eps_reported, ...},
    valuation{market_cap, pe_ratio, price_to_book, ...}.
    Values the source does not report are null, never invented.
    """
    return market_data.get_company_data(symbol, include_valuation=include_valuation)


@mcp.tool()
def get_quote(symbol: str) -> dict:
    """Latest price and company profile for a ticker."""
    info = data_provider.get_info(symbol)
    hist = data_provider.get_history(symbol, period="5d")
    last = hist["history"].iloc[-1]
    return {"symbol": symbol.upper(), "price": round(float(last["Close"]), 2),
            "name": info["info"].get("longName"), "source": hist["source"]}


@mcp.tool()
def technical_analysis(symbol: str) -> dict:
    """Indicators, trend, support/resistance and volume for a ticker."""
    return harness.REGISTRY.call(harness.PERMISSIONS, "technical_analysis", symbol=symbol)


@mcp.tool()
def fundamental_analysis(symbol: str) -> dict:
    """Valuation, profitability, leverage and growth for a ticker."""
    return harness.REGISTRY.call(harness.PERMISSIONS, "fundamental_analysis", symbol=symbol)


@mcp.tool()
def compare_stocks(symbols: list[str]) -> dict:
    """Compare 2-5 tickers side by side."""
    return harness.REGISTRY.call(harness.PERMISSIONS, "compare_stocks", symbols=symbols)


@mcp.tool()
def projection(symbol: str, years: int = 3) -> dict:
    """Monte-Carlo projection with stated assumptions."""
    return harness.REGISTRY.call(harness.PERMISSIONS, "projection", symbol=symbol, years=years)


if __name__ == "__main__":
    mcp.run()
