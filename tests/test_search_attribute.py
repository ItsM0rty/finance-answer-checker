from datetime import date

from verifier.definitions import Definition
from verifier.models import StatedDefinitionSpec
from verifier.search import find_matching_definitions, within_tolerance


def test_within_tolerance():
    assert within_tolerance(1000, 1004)
    assert not within_tolerance(1000, 1020)


def test_find_some_definition_for_net_burn():
    from mock_mcp.server import call_tool
    from verifier.adapter import apply_adapter, load_adapter

    adapter = load_adapter(__import__("pathlib").Path(__file__).resolve().parent.parent / "adapters" / "mock.yaml")
    ds = apply_adapter(
        adapter,
        [{"tool_name": "list_transactions", "output": call_tool("list_transactions", {"mode": "provenanced"})},
         {"tool_name": "get_fx_rates", "output": call_tool("get_fx_rates", {})}],
    )
    d = Definition.from_stated(StatedDefinitionSpec(window_months=3, source="bank"))
    from verifier.metrics import monthly_burn_minor

    val = monthly_burn_minor(ds, d, date(2026, 10, 1), basis="net")
    matches = find_matching_definitions("net_burn", val, ds, date(2026, 10, 1))
    assert len(matches) >= 1
