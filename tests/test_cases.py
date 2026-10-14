from pathlib import Path

import pytest

from verifier.adapter import apply_adapter, load_adapter
from verifier.attribute import attribute_claim
from verifier.extract import extract_claims
from verifier.transcript import load_transcript, tool_outputs_from_transcript

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
ADAPTER = load_adapter(ROOT / "adapters" / "mock.yaml")


@pytest.mark.parametrize("path", sorted(CASES.glob("*.json")))
def test_case_expected_verdict(path: Path):
    t = load_transcript(path)
    if not t.expected_verdict:
        pytest.skip("no expected_verdict")
    ds = apply_adapter(ADAPTER, tool_outputs_from_transcript(t))
    as_of = t.as_of_date or __import__("mock_mcp.data", fromlist=["AS_OF"]).AS_OF
    hire = t.scenario_hire_cost_minor or 0
    for claim in extract_claims(t.final_answer):
        exp = t.expected_verdict.get(claim.metric)
        if exp is None:
            continue
        got = attribute_claim(claim, ds, as_of, t.stated_definition, hire)["verdict"]
        assert got == exp, f"{path.name} {claim.metric}: {got} != {exp}"
