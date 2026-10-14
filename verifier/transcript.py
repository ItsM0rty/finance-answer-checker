from __future__ import annotations

import json
from pathlib import Path

from datetime import date

from pydantic import ValidationError

from verifier.models import StatedDefinitionSpec, Transcript


class TranscriptError(ValueError):
    pass


def load_transcript(path: Path) -> Transcript:
    if not path.exists():
        raise TranscriptError(f"Transcript file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TranscriptError(f"Could not read transcript: {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TranscriptError(f"Invalid JSON in {path.name}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise TranscriptError("Transcript root must be a JSON object.")
    if "final_answer" not in data:
        raise TranscriptError("Transcript missing required field: final_answer")
    tool_calls = data.get("tool_calls")
    if tool_calls is not None and not isinstance(tool_calls, list):
        raise TranscriptError("tool_calls must be a list when present.")
    stated = data.get("stated_definition")
    spec = None
    if stated is not None:
        if not isinstance(stated, dict):
            raise TranscriptError("stated_definition must be an object when present.")
        try:
            spec = StatedDefinitionSpec(**stated)
        except ValidationError as exc:
            raise TranscriptError(f"Invalid stated_definition: {exc}") from exc
    as_of = data.get("as_of_date")
    if isinstance(as_of, str):
        try:
            as_of = date.fromisoformat(as_of)
        except ValueError as exc:
            raise TranscriptError(f"Invalid as_of_date: {as_of}") from exc
    elif as_of is not None:
        raise TranscriptError("as_of_date must be an ISO date string when present.")
    hire = data.get("scenario_hire_cost_minor")
    if hire is not None and not isinstance(hire, int):
        raise TranscriptError("scenario_hire_cost_minor must be an integer (minor units).")
    return Transcript(
        tool_calls=data.get("tool_calls", []),
        final_answer=data.get("final_answer", ""),
        stated_definition=spec,
        as_of_date=as_of,
        expected_verdict=data.get("expected_verdict"),
        case_id=data.get("case_id"),
        scenario_hire_cost_minor=hire,
    )


def tool_outputs_from_transcript(transcript: Transcript) -> list[dict]:
    out: list[dict] = []
    for entry in transcript.tool_calls:
        if not isinstance(entry, dict):
            raise TranscriptError("Each tool_calls entry must be an object.")
        tc = entry.get("tool_call", {})
        if not isinstance(tc, dict):
            raise TranscriptError("tool_call must be an object in each tool_calls entry.")
        out.append(
            {
                "tool_name": tc.get("name"),
                "output": entry.get("tool_output", {}),
            }
        )
    return out
