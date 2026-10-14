import json
from pathlib import Path

import pytest

from verifier.__main__ import check_transcript
from verifier.transcript import TranscriptError, load_transcript

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "minimal_transcript.json"
ADAPTER = ROOT / "adapters" / "mock.yaml"


def test_check_example_transcript():
    out = check_transcript(EXAMPLE, ADAPTER, as_json=True)
    data = json.loads(out)
    assert data["case_id"] == "example"
    assert data["claims"]


def test_malformed_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(TranscriptError, match="Invalid JSON"):
        load_transcript(bad)


def test_missing_final_answer(tmp_path: Path):
    bad = tmp_path / "nofinal.json"
    bad.write_text('{"tool_calls": []}', encoding="utf-8")
    with pytest.raises(TranscriptError, match="final_answer"):
        load_transcript(bad)


def test_invalid_stated_definition(tmp_path: Path):
    bad = tmp_path / "baddef.json"
    bad.write_text(
        json.dumps({"final_answer": "x", "stated_definition": {"window_months": "three"}}),
        encoding="utf-8",
    )
    with pytest.raises(TranscriptError, match="stated_definition"):
        load_transcript(bad)
