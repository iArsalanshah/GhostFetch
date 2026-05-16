import asyncio

from ghostfetch.mcp_server import MCPServer


def test_encode_framed_message_contains_content_length():
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
    encoded = MCPServer._encode_framed_message(payload)
    assert b"Content-Length:" in encoded
    assert b"\r\n\r\n" in encoded


def test_read_framed_message_roundtrip():
    async def _run():
        payload = {"jsonrpc": "2.0", "id": 7, "method": "initialize"}
        encoded = MCPServer._encode_framed_message(payload)
        reader = asyncio.StreamReader()
        reader.feed_data(encoded)
        reader.feed_eof()
        decoded = await MCPServer._read_framed_message(reader)
        assert decoded == payload

    asyncio.run(_run())
