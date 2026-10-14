"""Generate 18 synthetic agent transcripts from mock MCP data.

ASSUMPTION: mock schema, not Seapoint's real tool surface.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mock_mcp import data
from mock_mcp.server import call_tool
from verifier.adapter import apply_adapter, load_adapter
from verifier.definitions import Definition
from verifier.metrics import (
    cash_balance_minor,
    monthly_burn_minor,
    overdue_total_minor,
    runway_months,
    vat_estimate_minor,
)
from verifier.models import StatedDefinitionSpec

OUT = Path(__file__).resolve().parent
ADAPTER = load_adapter(ROOT / "adapters" / "mock.yaml")
AS_OF = data.AS_OF

STATED = StatedDefinitionSpec(
    window_months=3,
    include_pending=False,
    burn_basis="net",
    fx_policy="transaction_date",
    include_uncategorised=True,
    source="bank",
    exclude_one_offs=False,
)


def provenanced_tool_calls() -> list[dict]:
    return [
        {
            "tool_call": {"name": "list_transactions", "args": {"mode": "provenanced"}},
            "tool_output": call_tool("list_transactions", {"mode": "provenanced"}),
        },
        {
            "tool_call": {"name": "list_invoices", "args": {}},
            "tool_output": call_tool("list_invoices", {}),
        },
        {
            "tool_call": {"name": "get_balances", "args": {"mode": "provenanced"}},
            "tool_output": call_tool("get_balances", {"mode": "provenanced"}),
        },
        {
            "tool_call": {"name": "get_fx_rates", "args": {}},
            "tool_output": call_tool("get_fx_rates", {}),
        },
    ]


def raw_tool_calls() -> list[dict]:
    return [
        {
            "tool_call": {"name": "list_transactions", "args": {"mode": "raw"}},
            "tool_output": call_tool("list_transactions", {"mode": "raw"}),
        },
        {
            "tool_call": {"name": "get_balances", "args": {"mode": "raw"}},
            "tool_output": call_tool("get_balances", {"mode": "raw"}),
        },
    ]


def dataset(mode: str = "provenanced"):
    tcs = provenanced_tool_calls() if mode == "provenanced" else raw_tool_calls()
    outputs = [{"tool_name": e["tool_call"]["name"], "output": e["tool_output"]} for e in tcs]
    if mode == "provenanced":
        return apply_adapter(ADAPTER, outputs)
    # raw: still need invoices for overdue cases; skip for raw-only case
    return apply_adapter(ADAPTER, outputs)


def d(spec: StatedDefinitionSpec | None = None) -> Definition:
    return Definition.from_stated(spec or STATED)


def money_gbp(minor: int) -> str:
    return f"GBP {minor / 100:,.2f}"


def write_case(name: str, payload: dict) -> None:
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    ds = dataset("provenanced")
    stated_def = d(STATED)
    net3 = monthly_burn_minor(ds, stated_def, AS_OF, basis="net")
    gross3 = monthly_burn_minor(ds, stated_def, AS_OF, basis="gross")
    rw = runway_months(ds, stated_def, AS_OF)
    od = overdue_total_minor(ds, AS_OF)
    vat = vat_estimate_minor(ds, stated_def, AS_OF)
    cash = cash_balance_minor(ds, stated_def, AS_OF)

    def1 = Definition.from_stated(
        StatedDefinitionSpec(window_months=1, include_pending=False, source="bank")
    )
    net1 = monthly_burn_minor(ds, def1, AS_OF, basis="net")

    def_pending = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=True,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
        )
    )
    net_pending = monthly_burn_minor(ds, def_pending, AS_OF, basis="net")

    def_fx_latest = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="latest",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
        )
    )
    net_fx_latest = monthly_burn_minor(ds, def_fx_latest, AS_OF, basis="net")
    def_fx_none = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="none_mixed",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
        )
    )
    net_fx_none = monthly_burn_minor(ds, def_fx_none, AS_OF, basis="net")
    def_fx_latest_pending = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=True,
            burn_basis="net",
            fx_policy="latest",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
        )
    )
    net_fx_agent = monthly_burn_minor(ds, def_fx_latest_pending, AS_OF, basis="net")

    def_no_uncat = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=False,
            source="bank",
            exclude_one_offs=False,
        )
    )
    net_no_uncat = monthly_burn_minor(ds, def_no_uncat, AS_OF, basis="net")

    def_union = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="gross",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="union",
            exclude_one_offs=False,
        )
    )
    def_union_nodedupe = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="gross",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="union",
            exclude_one_offs=False,
            union_dedupe=False,
        )
    )
    gross_double = monthly_burn_minor(ds, def_union_nodedupe, AS_OF, basis="gross")

    def_ledger = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="ledger",
            exclude_one_offs=False,
        )
    )
    rw_ledger = runway_months(
        ds,
        Definition.from_stated(
            StatedDefinitionSpec(
                window_months=3,
                include_pending=False,
                burn_basis="net",
                source="ledger",
            )
        ),
        AS_OF,
    )

    def_excl_oo = Definition.from_stated(
        StatedDefinitionSpec(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=True,
        )
    )
    net_excl = monthly_burn_minor(ds, def_excl_oo, AS_OF, basis="net")

    hire_minor = 600_000  # GBP 6,000/mo
    rw_hire = runway_months(ds, stated_def, AS_OF, hire_minor)
    rw_scenario_ignore_hire = runway_months(
        ds,
        Definition(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
            scenario_hire_applied=False,
        ),
        AS_OF,
        hire_minor,
    )

    od_future_def = Definition(
        window_months=3,
        include_pending=False,
        burn_basis="net",
        fx_policy="transaction_date",
        include_uncategorised=True,
        source="bank",
        exclude_one_offs=False,
        overdue_include_not_yet_due=True,
    )
    od_future = overdue_total_minor(ds, AS_OF, definition=od_future_def)
    od_old_asof = overdue_total_minor(ds, date(2026, 8, 15))

    vat_gross_def = Definition(
        window_months=3,
        include_pending=False,
        burn_basis="net",
        fx_policy="transaction_date",
        include_uncategorised=True,
        source="bank",
        exclude_one_offs=False,
        vat_on_gross=True,
    )
    vat_gross_basis = vat_estimate_minor(ds, vat_gross_def, AS_OF)

    base = {
        "as_of_date": AS_OF.isoformat(),
        "stated_definition": STATED.model_dump(),
    }
    tc = provenanced_tool_calls()

    cases = [
        (
            "01_correct_stated",
            {
                **base,
                "case_id": "01_correct_stated",
                "tool_calls": tc,
                "final_answer": (
                    f"Net burn is {money_gbp(net3)} per month over the last 3 months. "
                    f"Cash balance is {money_gbp(cash)}; runway about {rw} months."
                ),
                "expected_verdict": {
                    "net_burn": "MATCHES_STATED_DEFINITION",
                    "runway_months": "MATCHES_STATED_DEFINITION",
                },
            },
        ),
        (
            "02_trailing_window_1mo",
            {
                **base,
                "case_id": "02_trailing_window_1mo",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net1)} per month (agent used 1-month window).",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "03_gross_vs_net",
            {
                **base,
                "case_id": "03_gross_vs_net",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(gross3)} per month.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "04_pending_included",
            {
                **base,
                "case_id": "04_pending_included",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net_pending)} including pending SaaS charge.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "05_fx_latest_rate",
            {
                **base,
                "case_id": "05_fx_latest_rate",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net_fx_agent)} at month-end FX.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "06_fx_not_converted",
            {
                **base,
                "case_id": "06_fx_not_converted",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net_fx_none)} (EUR summed as GBP).",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "07_uncategorised_dropped",
            {
                **base,
                "case_id": "07_uncategorised_dropped",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net_no_uncat)} after dropping uncategorised.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "08_union_double_count",
            {
                **base,
                "case_id": "08_union_double_count",
                "tool_calls": tc,
                "final_answer": f"Gross burn is {money_gbp(gross_double)} merging bank and ledger without dedupe.",
                "expected_verdict": {"gross_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "09_ledger_stale_runway",
            {
                **base,
                "case_id": "09_ledger_stale_runway",
                "tool_calls": tc,
                "final_answer": f"Runway is {rw_ledger} months using ledger cash and net burn.",
                "expected_verdict": {"runway_months": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "10_overdue_includes_future",
            {
                **base,
                "case_id": "10_overdue_includes_future",
                "tool_calls": tc,
                "final_answer": f"Total overdue receivables are {money_gbp(od_future)}.",
                "expected_verdict": {"overdue_total": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "11_overdue_wrong_asof",
            {
                **base,
                "case_id": "11_overdue_wrong_asof",
                "tool_calls": tc,
                "final_answer": f"Overdue total as of mid-August is {money_gbp(od_old_asof)}.",
                "expected_verdict": {"overdue_total": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "12_vat_on_gross",
            {
                **base,
                "case_id": "12_vat_on_gross",
                "tool_calls": tc,
                "final_answer": f"Estimated VAT on spend is {money_gbp(vat_gross_basis)}.",
                "expected_verdict": {"vat_estimate": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "13_arithmetic_slip",
            {
                **base,
                "case_id": "13_arithmetic_slip",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net3 + 4_500 if net3 else 999999)} per month.",
                "expected_verdict": {"net_burn": "MATCHES_NO_DEFINITION"},
            },
        ),
        (
            "14_fabricated",
            {
                **base,
                "case_id": "14_fabricated",
                "tool_calls": tc,
                "final_answer": "Net burn is GBP 99,999.99 per month.",
                "expected_verdict": {"net_burn": "MATCHES_NO_DEFINITION"},
            },
        ),
        (
            "15_one_off_excluded",
            {
                **base,
                "case_id": "15_one_off_excluded",
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net_excl)} excluding one-off equipment.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "16_scenario_hire",
            {
                **base,
                "case_id": "16_scenario_hire",
                "tool_calls": tc,
                "scenario_hire_cost_minor": hire_minor,
                "final_answer": (
                    f"If we hire at GBP 6,000/month from next quarter, runway is "
                    f"{rw_scenario_ignore_hire} months."
                ),
                "expected_verdict": {"runway_months": "MATCHES_OTHER_DEFINITION"},
            },
        ),
        (
            "17_raw_no_provenance",
            {
                "case_id": "17_raw_no_provenance",
                "as_of_date": AS_OF.isoformat(),
                "stated_definition": STATED.model_dump(),
                "tool_calls": raw_tool_calls(),
                "final_answer": f"Net burn is {money_gbp(net3)}; cash balance {money_gbp(cash)}.",
                "expected_verdict": {
                    "net_burn": "UNCHECKABLE",
                    "cash_balance": "UNCHECKABLE",
                },
            },
        ),
        (
            "18_no_definition_stated",
            {
                "case_id": "18_no_definition_stated",
                "as_of_date": AS_OF.isoformat(),
                "stated_definition": None,
                "tool_calls": tc,
                "final_answer": f"Net burn is {money_gbp(net3)} per month.",
                "expected_verdict": {"net_burn": "MATCHES_OTHER_DEFINITION"},
            },
        ),
    ]

    for name, payload in cases:
        if payload.get("stated_definition") is None:
            payload.pop("stated_definition", None)
        write_case(name, payload)

    print(f"Wrote {len(cases)} cases to {OUT}")


if __name__ == "__main__":
    main()
