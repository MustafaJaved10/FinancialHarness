"""Direct-call test for Yasir's MCP data tools — for Mustafa / any teammate.

Run from the repo root:
    python tools/test_connector.py          (defaults to IBM)
    python tools/test_connector.py AAPL     (needs ALPHAVANTAGE_API_KEY for non-IBM)

Prints exactly what the two MCP tools return, so the connector can be
verified without starting the AI harness.
"""
import asyncio
import json
import sys

sys.path.insert(0, ".")
from stock_assistant.mcp_server import mcp  # noqa: E402


async def main(symbol: str):
    tools = await mcp.list_tools()
    print("Available MCP tools:", [t.name for t in tools])
    r = await mcp.call_tool("get_daily_candles", {"symbol": symbol, "limit": 5})
    print(f"\n=== get_daily_candles({symbol!r}, limit=5) ===")
    print(json.dumps(json.loads(r[0].text), indent=1)[:1500])
    r = await mcp.call_tool("get_company_data", {"symbol": symbol})
    print(f"\n=== get_company_data({symbol!r}) ===")
    print(json.dumps(json.loads(r[0].text), indent=1)[:2000])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "IBM"))
