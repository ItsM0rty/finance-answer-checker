"""Check that the stated likely cause names the real driver, not only the verdict."""

from pathlib import Path

import pytest

from mock_mcp.data import AS_OF
from verifier.adapter import apply_adapter, load_adapter
from verifier.attribute import attribute_claim
from verifier.extract import extract_claims
from verifier.transcript import load_transcript, tool_outputs_from_transcript

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = load_adapter(ROOT / "adapters" / "mock.yaml")

# case file prefix -> (metric, substrings that must all appear in the cause,
# substrings that must not appear)
EXPECTED = {
    "05_": ("net_burn", ["pending included", "FX policy latest"], []),
    "06_": ("net_burn", ["none_mixed"], ["pending"]),
    "08_": ("gross_burn", ["without dedupe"], []),
    "09_": ("runway_months", ["source ledger"], ["scenario hire"]),
    "10_": ("overdue_total", ["not-yet-due"], []),
    "12_": ("vat_estimate", ["VAT-inclusive"], []),
    "16_": ("runway_months", ["scenario hire cost omitted"], []),
}


def _cause(prefix: str, metric: str) -> str:
    path = next((ROOT / "cases").glob(prefix + "*.json"))
    t = load_transcript(path)
    ds = apply_adapter(ADAPTER, tool_outputs_from_transcript(t))
    hire = t.scenario_hire_cost_minor or 0
    for claim in extract_claims(t.final_answer):
        if claim.metric == metric:
            res = attribute_claim(
                claim, ds, t.as_of_date or AS_OF, t.stated_definition, hire
            )
            return res["likely_cause"]
    raise AssertionError(f"no {metric} claim in {path.name}")


@pytest.mark.parametrize("prefix", sorted(EXPECTED))
def test_likely_cause_names_real_driver(prefix):
    metric, must, must_not = EXPECTED[prefix]
    cause = _cause(prefix, metric)
    for s in must:
        assert s in cause, f"{prefix}: {s!r} missing from {cause!r}"
    for s in must_not:
        assert s not in cause, f"{prefix}: {s!r} unexpectedly in {cause!r}"
