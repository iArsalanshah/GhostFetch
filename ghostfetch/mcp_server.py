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
        
        await self.ensure_initialized()
        
        url = arguments.get("url")
        context_id = arguments.get("context_id")
        timeout = arguments.get("timeout", 120)
        
        if not url:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Missing required parameter: url"}]
            }
        
        try:
            result = await asyncio.wait_for(
                self.scraper.fetch(url, context_id=context_id),
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
                        "version": "1.0.0"
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
        """Run the MCP server using stdio transport."""
        import sys
        
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())
        
        try:
            while True:
                # Read message length header
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode().strip())
                except json.JSONDecodeError:
                    continue
                
                response = await self.handle_message(message)
                
                if response:
                    response_bytes = (json.dumps(response) + "\n").encode()
                    writer.write(response_bytes)
                    await writer.drain()
        
        finally:
            await self.cleanup()


async def main():
    """Main entry point for MCP server."""
    server = MCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
