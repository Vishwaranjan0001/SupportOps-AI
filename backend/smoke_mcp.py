"""Run BEFORE Groq to verify MCP server and SQLite tools are connected."""
import asyncio
from pathlib import Path
from langchain.mcp import MCPAdapter
from db import init_db


async def main():
    init_db()
    async with MCPAdapter(Path(__file__).resolve().with_name('mcp_server.py')) as adapter:
        tools = await adapter.list_tools()
        print('MCP tools discovered:', [tool.name for tool in tools])
        order_tool = next(t for t in tools if t.name == 'get_order_status')
        print('MCP tool result:', await order_tool.ainvoke({'order_id': 'ORD-1001'}))


if __name__ == '__main__':
    asyncio.run(main())
