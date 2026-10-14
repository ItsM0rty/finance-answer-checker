"""Minimal stdio JSON-RPC MCP-style server with assumed tool names.

ASSUMPTION: this schema and these tool names are a stand-in built from public
product descriptions. Seapoint's real MCP tool names and schemas are not public
(no docs, no public repo, not in the MCP registry). No Seapoint endpoint is called.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mock_mcp import data

TOOLS = [
    {
        "name": "list_transactions",
        "description": "List cash transactions (mock)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_invoices",
        "description": "List AR invoices (mock)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_balances",
        "description": "Cash balances by source (mock)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_runway_summary",
        "description": "Metadata only in mock",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_fx_rates",
        "description": "Dated FX rates to reporting currency (mock)",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _mode() -> str:
    return os.environ.get("MOCK_MCP_MODE", "provenanced")


def call_tool(name: str, args: dict | None = None) -> dict[str, Any]:
    """Pure-Python entry used by tests and case generator."""
    args = args or {}
    mode = args.get("mode") or _mode()
    if name == "list_transactions":
        return {"transactions": data.get_transactions(mode)}
    if name == "list_invoices":
        return {"invoices": data.get_invoices()}
    if name == "get_balances":
        return {"balances": data.get_balances(mode)}
    if name == "get_runway_summary":
        return data.get_runway_summary(mode)
    if name == "get_fx_rates":
        return data.get_fx_rates()
    raise ValueError(f"Unknown tool: {name}")


def _respond(req_id: Any, result: Any) -> None:
    sys.stdout.write(
        json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}) + "\n"
    )
    sys.stdout.flush()


def _error(req_id: Any, code: int, message: str) -> None:
    sys.stdout.write(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": code, "message": message},
            }
        )
        + "\n"
    )
    sys.stdout.flush()


def handle_request(msg: dict) -> None:
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        _respond(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-finance-mcp", "version": "0.1.0"},
            },
        )
        return

    if method == "tools/list":
        _respond(req_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            content = call_tool(name, arguments)
            _respond(
                req_id,
                {"content": [{"type": "text", "text": json.dumps(content)}]},
            )
        except Exception as e:
            _error(req_id, -32000, str(e))
        return

    if req_id is not None:
        _error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle_request(msg)


if __name__ == "__main__":
    main()
