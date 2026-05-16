import asyncio

from ghostfetch.mcp_server import MCPServer


def test_call_tool_rejects_non_positive_timeout():
    async def _run():
        server = MCPServer()
        result = await server.call_tool(
            "ghostfetch",
            {"url": "https://example.com", "timeout": 0},
        )
        assert result.get("isError") is True
        assert "timeout must be positive" in result["content"][0]["text"]

    asyncio.run(_run())
