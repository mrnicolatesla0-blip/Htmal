"""Read-only client for the official NSE-hosted MCP endpoints."""
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

NSE_SERVERS = {
    "live": "https://mcp.nseindia.in/cmmkt/mcp",
    "history": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
}


def _plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


async def list_nse_tools(server):
    if server not in NSE_SERVERS:
        raise ValueError("Unknown NSE data server.")
    async with streamablehttp_client(NSE_SERVERS[server], timeout=30, sse_read_timeout=30) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": _plain(tool.inputSchema),
                }
                for tool in response.tools
            ]


async def call_nse_tool(server, name, arguments):
    tools = await list_nse_tools(server)
    if not any(tool["name"] == name for tool in tools):
        raise ValueError("That tool is not published by the selected NSE server.")
    async with streamablehttp_client(NSE_SERVERS[server], timeout=30, sse_read_timeout=30) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            structured = getattr(result, "structuredContent", None)
            if structured is not None:
                return _plain(structured)
            content = []
            for item in getattr(result, "content", []):
                if hasattr(item, "text"):
                    content.append(item.text)
                else:
                    content.append(_plain(item))
            return {"isError": bool(getattr(result, "isError", False)), "content": content}
