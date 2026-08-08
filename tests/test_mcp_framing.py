import asyncio
import json

import pytest

from ghostfetch.mcp_server import MCPServer, MAX_MCP_MESSAGE_SIZE


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


def test_read_framed_message_rejects_too_large():
    async def _run():
        reader = asyncio.StreamReader()
        headers = (
            f"Content-Length: {MAX_MCP_MESSAGE_SIZE + 1}\r\n"
            "Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
        reader.feed_data(headers)
        reader.feed_eof()
        with pytest.raises(ValueError, match="Message too large"):
            await MCPServer._read_framed_message(reader)

    asyncio.run(_run())


def test_encode_newline_message():
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
    encoded = MCPServer._encode_newline_message(payload)
    assert encoded.endswith(b"\n")
    assert json.loads(encoded) == payload


def test_read_newline_message_roundtrip():
    async def _run():
        payload = {"jsonrpc": "2.0", "id": 7, "method": "initialize"}
        encoded = MCPServer._encode_newline_message(payload)
        reader = asyncio.StreamReader()
        reader.feed_data(encoded)
        reader.feed_eof()
        decoded = await MCPServer._read_newline_message(reader)
        assert decoded == payload

    asyncio.run(_run())


def test_read_newline_message_multiline_json():
    async def _run():
        payload = {"jsonrpc": "2.0", "id": 7, "method": "initialize"}
        pretty = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        reader = asyncio.StreamReader()
        reader.feed_data(pretty)
        reader.feed_eof()
        decoded = await MCPServer._read_newline_message(reader)
        assert decoded == payload

    asyncio.run(_run())


def test_read_newline_message_rejects_too_large():
    async def _run():
        # many small lines (like pretty-printed JSON) whose TOTAL exceeds
        # MAX_MCP_MESSAGE_SIZE before the JSON value completes
        reader = asyncio.StreamReader()
        chunk = b'{"a": "' + b"x" * 1000 + b"\n"
        lines = (MAX_MCP_MESSAGE_SIZE // 1000) + 2
        reader.feed_data(chunk * lines + b'"}')
        reader.feed_eof()
        with pytest.raises(ValueError, match="Message too large"):
            await MCPServer._read_newline_message(reader)

    asyncio.run(_run())


def test_read_framed_message_accepts_buffered_first_line():
    async def _run():
        payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        body = json.dumps(payload).encode("utf-8")
        framed = (
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: application/json\r\n\r\n"
        ).encode("utf-8") + body
        # run_stdio reads the first line itself and passes it back in
        first_line, rest = framed.split(b"\r\n", 1)
        reader = asyncio.StreamReader()
        reader.feed_data(rest)
        reader.feed_eof()
        decoded = await MCPServer._read_framed_message(reader, first_line=first_line + b"\r\n")
        assert decoded == payload

    asyncio.run(_run())
