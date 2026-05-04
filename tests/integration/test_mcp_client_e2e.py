"""Real MCP client smoke test — uses a tiny stdio MCP echo server (built-in)."""
from __future__ import annotations

import asyncio
import sys

import pytest

from ralph.mcp_audit.client import McpStdioClient

# This integration test needs the `mcp` Python SDK to spawn a tiny FastMCP server.
pytestmark = pytest.mark.integration


FASTMCP_INLINE = """
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('test-echo')

@mcp.tool()
def echo(msg: str) -> str:
    \"\"\"Echo back the input.\"\"\"
    return f'echo: {msg}'

if __name__ == '__main__':
    mcp.run()
"""


async def _run_e2e(tmp_path):
    server_file = tmp_path / "echo_server.py"
    server_file.write_text(FASTMCP_INLINE, encoding="utf-8")
    client = McpStdioClient([sys.executable, str(server_file)])
    await client.start()
    try:
        tools = await client.list_tools()
        assert any(t.name == "echo" for t in tools)
        result = await client.call_tool("echo", {"msg": "hello"})
        assert "echo: hello" in str(result)
    finally:
        await client.stop()


def test_mcp_stdio_client_e2e(tmp_path):
    try:
        import mcp  # noqa: F401
    except ImportError:
        pytest.skip("mcp SDK not installed")
    asyncio.run(_run_e2e(tmp_path))
