# probe_tools.py - Step 6 probe: what do Yasir's 7 MCP tools accept and return?
import asyncio
import json
import sys

sys.path.insert(0, ".")
from stock_assistant.mcp_server import mcp


async def show(name, args):
    try:
        r = await mcp.call_tool(name, args)
        print(f"\n=== {name}({args}) ===")
        print(r[0].text[:1200])
    except Exception as e:
        print(f"\n=== {name} === ERROR: {e}")


async def main():
    tools = await mcp.list_tools()
    print("=== TOOL SCHEMAS ===")
    for t in tools:
        print(t.name, "->", json.dumps(t.inputSchema))

    await show("get_quote", {"symbol": "IBM"})
    await show("technical_analysis", {"symbol": "IBM"})
    await show("fundamental_analysis", {"symbol": "IBM"})
    await show("projection", {"symbol": "IBM"})
    await show("compare_stocks", {"symbols": ["IBM", "MSFT"]})


asyncio.run(main())
