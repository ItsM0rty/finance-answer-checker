import json

from mock_mcp.server import TOOLS, call_tool


def test_call_tool_transactions():
    out = call_tool("list_transactions", {"mode": "provenanced"})
    assert "transactions" in out
    assert out["transactions"][0].get("source") == "bank"


def test_call_tool_raw_strips_provenance():
    out = call_tool("list_transactions", {"mode": "raw"})
    assert "source" not in out["transactions"][0]


def test_tools_list_names():
    names = {t["name"] for t in TOOLS}
    assert "list_transactions" in names
    assert "get_balances" in names
