from pathlib import Path

from verifier.adapter import apply_adapter, load_adapter
from verifier.attribute import attribute_claim
from verifier.extract import extract_claims
from verifier.transcript import load_transcript, tool_outputs_from_transcript

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = load_adapter(ROOT / "adapters" / "mock.yaml")


def _attr(case_name: str):
    t = load_transcript(ROOT / "cases" / case_name)
    ds = apply_adapter(ADAPTER, tool_outputs_from_transcript(t))
    as_of = t.as_of_date or __import__("mock_mcp.data", fromlist=["AS_OF"]).AS_OF
    claim = extract_claims(t.final_answer)[0]
    return attribute_claim(claim, ds, as_of, t.stated_definition, t.scenario_hire_cost_minor or 0)


def test_arithmetic_slip_explanation():
    a = _attr("13_arithmetic_slip.json")
    assert a["verdict"] == "MATCHES_NO_DEFINITION"
    assert "Arithmetic slip" in a["explanation"]


def test_fabricated_explanation():
    a = _attr("14_fabricated.json")
    assert a["verdict"] == "MATCHES_NO_DEFINITION"
    assert "fabrication" in a["explanation"].lower()
