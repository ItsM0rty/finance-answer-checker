from datetime import date

from mock_mcp.server import call_tool
from verifier.adapter import apply_adapter, load_adapter
from verifier.definitions import Definition
from verifier.metrics import (
    filter_transactions,
    monthly_burn_minor,
    overdue_total_minor,
    runway_months,
    vat_estimate_minor,
    window_start,
)
from verifier.models import StatedDefinitionSpec

ROOT_ADAPTER = __import__("pathlib").Path(__file__).resolve().parent.parent / "adapters" / "mock.yaml"
AS_OF = date(2026, 10, 1)


def _ds():
    adapter = load_adapter(ROOT_ADAPTER)
    outputs = [
        {"tool_name": "list_transactions", "output": call_tool("list_transactions", {"mode": "provenanced"})},
        {"tool_name": "get_fx_rates", "output": call_tool("get_fx_rates", {})},
        {"tool_name": "get_balances", "output": call_tool("get_balances", {"mode": "provenanced"})},
        {"tool_name": "list_invoices", "output": call_tool("list_invoices", {})},
    ]
    return apply_adapter(adapter, outputs)


def test_window_start_trailing_3mo():
    assert window_start(AS_OF, 3) == date(2026, 7, 1)


def test_pending_excluded_from_burn():
    ds = _ds()
    base = Definition.from_stated(StatedDefinitionSpec(window_months=3, source="bank"))
    pending = Definition.from_stated(
        StatedDefinitionSpec(window_months=3, include_pending=True, source="bank")
    )
    assert monthly_burn_minor(ds, pending, AS_OF) > monthly_burn_minor(ds, base, AS_OF)


def test_union_dedupe_lowers_gross_burn():
    ds = _ds()
    deduped = Definition.from_stated(
        StatedDefinitionSpec(window_months=3, burn_basis="gross", source="union", union_dedupe=True)
    )
    double = Definition.from_stated(
        StatedDefinitionSpec(window_months=3, burn_basis="gross", source="union", union_dedupe=False)
    )
    assert monthly_burn_minor(ds, double, AS_OF, basis="gross") > monthly_burn_minor(
        ds, deduped, AS_OF, basis="gross"
    )


def test_fx_none_mixed_differs_from_transaction_date():
    ds = _ds()
    td = Definition.from_stated(StatedDefinitionSpec(fx_policy="transaction_date", source="bank"))
    nm = Definition.from_stated(StatedDefinitionSpec(fx_policy="none_mixed", source="bank"))
    assert monthly_burn_minor(ds, nm, AS_OF) != monthly_burn_minor(ds, td, AS_OF)


def test_overdue_strict_vs_include_future():
    ds = _ds()
    strict = Definition(
        3, False, "net", "transaction_date", True, "bank", False, overdue_include_not_yet_due=False
    )
    future = Definition(
        3, False, "net", "transaction_date", True, "bank", False, overdue_include_not_yet_due=True
    )
    assert overdue_total_minor(ds, AS_OF, definition=future) > overdue_total_minor(
        ds, AS_OF, definition=strict
    )


def test_vat_gross_exceeds_net_basis():
    ds = _ds()
    net_vat = Definition(
        3, False, "net", "transaction_date", True, "bank", False, vat_on_gross=False
    )
    gross_vat = Definition(
        3, False, "net", "transaction_date", True, "bank", False, vat_on_gross=True
    )
    assert vat_estimate_minor(ds, gross_vat, AS_OF) > vat_estimate_minor(ds, net_vat, AS_OF)


def test_runway_scenario_hire_reduces_runway():
    ds = _ds()
    stated = Definition.from_stated(StatedDefinitionSpec(window_months=3, source="bank"))
    with_hire = runway_months(ds, stated, AS_OF, extra_monthly_cost_minor=600_000)
    without = runway_months(
        ds,
        Definition(
            3, False, "net", "transaction_date", True, "bank", False, scenario_hire_applied=False
        ),
        AS_OF,
        600_000,
    )
    assert with_hire is not None and without is not None
    assert with_hire < without


def test_filter_respects_one_off_exclusion():
    ds = _ds()
    all_tx = filter_transactions(
        ds, Definition.from_stated(StatedDefinitionSpec(exclude_one_offs=False)), AS_OF
    )
    excl = filter_transactions(
        ds, Definition.from_stated(StatedDefinitionSpec(exclude_one_offs=True)), AS_OF
    )
    assert len(all_tx) >= len(excl)
