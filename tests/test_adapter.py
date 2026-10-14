from mock_mcp.server import call_tool
from verifier.adapter import apply_adapter, load_adapter


def test_adapter_maps_transactions():
    adapter = load_adapter(__import__("pathlib").Path(__file__).resolve().parent.parent / "adapters" / "mock.yaml")
    out = apply_adapter(
        adapter,
        [{"tool_name": "list_transactions", "output": call_tool("list_transactions", {"mode": "provenanced"})}],
    )
    assert len(out.transactions) > 5
    assert out.transactions[0].amount_minor != 0
