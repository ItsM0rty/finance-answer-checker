from datetime import date

from mock_mcp.server import call_tool
from verifier.adapter import apply_adapter, load_adapter
from verifier.definitions import Definition
from verifier.metrics import monthly_burn_minor, overdue_total_minor
from verifier.models import StatedDefinitionSpec

ROOT_ADAPTER = __import__("pathlib").Path(__file__).resolve().parent.parent / "adapters" / "mock.yaml"


def _ds():
    adapter = load_adapter(ROOT_ADAPTER)
    outputs = [
        {"tool_name": "list_transactions", "output": call_tool("list_transactions", {"mode": "provenanced"})},
        {"tool_name": "get_fx_rates", "output": call_tool("get_fx_rates", {})},
    ]
    return apply_adapter(adapter, outputs)


def test_net_burn_positive():
    ds = _ds()
    d = Definition.from_stated(StatedDefinitionSpec(window_months=3, source="bank"))
    net = monthly_burn_minor(ds, d, date(2026, 10, 1), basis="net")
    assert net is not None and net > 0


def test_overdue_excludes_paid():
    adapter = load_adapter(ROOT_ADAPTER)
    outputs = [
        {"tool_name": "list_invoices", "output": call_tool("list_invoices", {})},
    ]
    ds = apply_adapter(adapter, outputs)
    total = overdue_total_minor(ds, date(2026, 10, 1))
    assert total > 0
