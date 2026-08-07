#!/usr/bin/env python3
"""
GhostFetch MCP Server

Model Context Protocol (MCP) server that exposes GhostFetch as a tool
for AI agents following the MCP specification.

Usage:
    python -m ghostfetch.mcp_server

Or add to your MCP configuration:
    {
        "mcpServers": {
            "ghostfetch": {
                "command": "python",
                "args": ["-m", "ghostfetch.mcp_server"]
            }
        }
    }
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

# Add parent directory for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.security import validate_target_url, URLValidationError
from src.utils.security import validate_context_id
from ghostfetch.version import __version__

MAX_MCP_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB


class MCPServer:
    """Simple MCP server implementation for GhostFetch."""
    
    def __init__(self):
        self.scraper = None
        self._initialized = False
    
    async def ensure_initialized(self):
        """Lazy initialization of the scraper."""
        if not self._initialized:
            from src.core.scraper import StealthScraper
            self.scraper = StealthScraper()
            await self.scraper.start()
            self._initialized = True
    
    async def cleanup(self):
        """Clean up resources."""
        if self.scraper:
            await self.scraper.stop()
    
    def get_tools(self) -> list:
        """Return available tools in MCP format."""
        return [
            {
                "name": "ghostfetch",
                "description": "Fetch web content from sites that block AI agents. Uses a stealthy headless browser with advanced fingerprinting to bypass anti-bot protections and returns clean Markdown.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch (e.g. https://x.com/user/status/123)"
                        },
                        "context_id": {
                            "type": "string",
                            "description": "Optional session ID for cookie persistence across multiple requests"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Maximum time to wait in seconds (default: 120)",
                            "default": 120
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call."""
        if name != "ghostfetch":
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}]
            }
        
        url = arguments.get("url")
        context_id = arguments.get("context_id")
        timeout = arguments.get("timeout", 120)
        
        if not url:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Missing required parameter: url"}]
            }
        
        try:
            timeout = float(timeout)
            if timeout <= 0:
                raise URLValidationError("timeout must be positive")
            safe_url = validate_target_url(url)
            safe_context_id = validate_context_id(context_id)
            await self.ensure_initialized()
            result = await asyncio.wait_for(
                self.scraper.fetch(safe_url, context_id=safe_context_id),
                timeout=timeout
            )
            
            if not result:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": "No content could be fetched from the URL"}]
                }
            
            # Format response for MCP
            response_text = f"""# {result['metadata'].get('title', 'Fetched Content')}

**Author:** {result['metadata'].get('author', 'Unknown')}
**Date:** {result['metadata'].get('publish_date', 'Unknown')}

---

{result['markdown']}
"""
            
            return {
                "content": [
                    {"type": "text", "text": response_text}
                ],
                "_metadata": result["metadata"]  # Include structured metadata
            }
            
        except URLValidationError as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": str(e)}]
            }
        except asyncio.TimeoutError:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Request timed out after {timeout} seconds"}]
            }
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error fetching URL: {str(e)}"}]
            }
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP message."""
        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        result = None
        error = None
        
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ghostfetch",
                        "version": __version__
                    }
                }
            
            elif method == "tools/list":
                result = {"tools": self.get_tools()}
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.call_tool(tool_name, arguments)
            
            elif method == "notifications/initialized":
                # Acknowledgment, no response needed
                return None
            
            else:
                error = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
        
        except Exception as e:
            error = {
                "code": -32603,
                "message": str(e)
            }
        
        response = {"jsonrpc": "2.0", "id": msg_id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    async def run_stdio(self):
        """Run the MCP server using stdio transport.

        Auto-detects framing from the first line of input:
        - Modern MCP clients (Codex, Cursor, VS Code, GitHub Copilot, etc.)
          use newline-delimited JSON (the MCP stdio spec since 2024-11-05).
        - Legacy clients (Claude Desktop) use Content-Length framed messages.

        The detected framing is used for the whole session.
        """
        reader = asyncio.StreamReader(limit=MAX_MCP_MESSAGE_SIZE + 1)
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

        first_line = await reader.readline()
        if not first_line:
            return
        legacy = first_line.lstrip().lower().startswith(b"content-length:")
        first = True

        async def read_message() -> Optional[Dict[str, Any]]:
            nonlocal first
            buffered = first_line if first else None
            first = False
            if legacy:
                return await self._read_framed_message(reader, buffered)
            return await self._read_newline_message(reader, buffered)

        async def write_message(payload: Dict[str, Any]) -> None:
            if legacy:
                writer.write(self._encode_framed_message(payload))
            else:
                writer.write(self._encode_newline_message(payload))
            await writer.drain()

        while True:
            try:
                message = await read_message()
                if message is None:
                    return
            except Exception:
                continue

            response = await self.handle_message(message)
            if not response:
                continue

            await write_message(response)

    @staticmethod
    def _encode_framed_message(payload: Dict[str, Any]) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        headers = (
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
        return headers + body

    @staticmethod
    def _encode_newline_message(payload: Dict[str, Any]) -> bytes:
        """Encode a message in the modern newline-delimited MCP stdio format."""
        return (json.dumps(payload) + "\n").encode("utf-8")

    @staticmethod
    async def _read_framed_message(
        reader: asyncio.StreamReader,
        first_line: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        headers: Dict[str, str] = {}
        line = first_line
        while True:
            if line is None:
                line = await reader.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            decoded = line.decode("utf-8", errors="replace").strip()
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                headers[key.strip().lower()] = value.strip()
            line = None

        content_length = headers.get("content-length")
        if not content_length:
            raise ValueError("Missing content-length")

        size = int(content_length)
        if size <= 0:
            raise ValueError("Invalid content-length")
        if size > MAX_MCP_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {size} bytes (max {MAX_MCP_MESSAGE_SIZE})")

        body = await reader.readexactly(size)
        return json.loads(body.decode("utf-8"))

    @staticmethod
    async def _read_newline_message(
        reader: asyncio.StreamReader,
        first_line: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read a message in the modern newline-delimited MCP stdio format.

        Tolerates pretty-printed multi-line JSON by accumulating lines until a
        complete JSON value can be parsed.
        """
        decoder = json.JSONDecoder()
        buffer = ""
        line = first_line
        while True:
            if line is None:
                line = await reader.readline()
            if not line:
                return None
            buffer += line.decode("utf-8")
            if len(buffer) > MAX_MCP_MESSAGE_SIZE:
                raise ValueError(f"Message too large: {len(buffer)} bytes (max {MAX_MCP_MESSAGE_SIZE})")
            try:
                obj, _ = decoder.raw_decode(buffer.lstrip())
                return obj
            except json.JSONDecodeError:
                line = None
                continue


async def main():
    """Main entry point for MCP server."""
    import signal
    
    server = MCPServer()
    
    # Handle shutdown signals gracefully
    def handle_shutdown(signum, frame):
        # Raising SystemExit ensures the finally block runs
        raise SystemExit(0)
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        await server.run_stdio()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
