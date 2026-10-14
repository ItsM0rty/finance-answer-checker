"""CLI for finance-answer-checker (definition checker).

ASSUMPTION: this schema and these tool names are a stand-in built from public
product descriptions. Seapoint's real MCP tool names and schemas are not public
(no docs, no public repo, not in the MCP registry).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path

from mock_mcp import data
from mock_mcp.server import call_tool
from verifier.adapter import apply_adapter, load_adapter
from verifier.attribute import attribute_claim
from verifier.extract import extract_claims, parse_scenario_hire_minor
from verifier.models import StatedDefinitionSpec
from verifier.report import format_money, render_table, to_json
from verifier.transcript import TranscriptError, load_transcript, tool_outputs_from_transcript

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ADAPTER = ROOT / "adapters" / "mock.yaml"
CASES_DIR = ROOT / "cases"
EXAMPLE_TRANSCRIPT = ROOT / "examples" / "minimal_transcript.json"


def _default_as_of(t) -> date:
    if t.as_of_date:
        return date.fromisoformat(t.as_of_date) if isinstance(t.as_of_date, str) else t.as_of_date
    return data.AS_OF


def _stated_from_args(args: argparse.Namespace, transcript_stated) -> StatedDefinitionSpec | None:
    if getattr(args, "definition_file", None):
        path = Path(args.definition_file)
        data_obj = json.loads(path.read_text(encoding="utf-8"))
        return StatedDefinitionSpec(**data_obj)
    flags_set = any(
        getattr(args, k, None) is not None
        for k in (
            "window",
            "net",
            "gross",
            "include_pending",
            "exclude_pending",
            "fx",
            "source",
            "exclude_one_offs",
            "exclude_uncategorised",
            "union_no_dedupe",
        )
    )
    if not flags_set:
        return transcript_stated
    basis = "net"
    if args.gross:
        basis = "gross"
    if args.net:
        basis = "net"
    include_pending = transcript_stated.include_pending if transcript_stated else False
    if args.include_pending:
        include_pending = True
    if args.exclude_pending:
        include_pending = False
    fx = (transcript_stated.fx_policy if transcript_stated else "transaction_date")
    if args.fx:
        fx = args.fx
    source = (transcript_stated.source if transcript_stated else "bank")
    if args.source:
        source = args.source
    window = args.window if args.window is not None else (
        transcript_stated.window_months if transcript_stated else 3
    )
    include_uncat = True
    if transcript_stated:
        include_uncat = transcript_stated.include_uncategorised
    if args.exclude_uncategorised:
        include_uncat = False
    exclude_oo = False
    if transcript_stated:
        exclude_oo = transcript_stated.exclude_one_offs
    if args.exclude_one_offs:
        exclude_oo = True
    union_dedupe = True
    if transcript_stated:
        union_dedupe = transcript_stated.union_dedupe
    if args.union_no_dedupe:
        union_dedupe = False
    return StatedDefinitionSpec(
        window_months=window,
        include_pending=include_pending,
        burn_basis=basis,
        fx_policy=fx,
        include_uncategorised=include_uncat,
        source=source,
        exclude_one_offs=exclude_oo,
        union_dedupe=union_dedupe,
    )


def check_transcript(
    path: Path,
    adapter_path: Path,
    as_json: bool = False,
    stated_override: StatedDefinitionSpec | None = None,
) -> str:
    transcript = load_transcript(path)
    adapter = load_adapter(adapter_path)
    outputs = tool_outputs_from_transcript(transcript)
    dataset = apply_adapter(adapter, outputs)
    as_of = _default_as_of(transcript)
    stated = stated_override if stated_override is not None else transcript.stated_definition
    hire = transcript.scenario_hire_cost_minor
    if hire is None:
        hire = parse_scenario_hire_minor(transcript.final_answer)
    hire = hire or 0
    claims = extract_claims(transcript.final_answer)

    results = []
    for claim in claims:
        attr = attribute_claim(
            claim,
            dataset,
            as_of,
            stated,
            hire,
        )
        attr["case_id"] = transcript.case_id or path.stem
        if claim.metric == "runway_months":
            attr["claimed_display"] = f"{claim.value_months} mo"
            if attr.get("recomputed_stated") is not None:
                attr["recomputed_display"] = f"{attr['recomputed_stated']} mo"
            else:
                attr["recomputed_display"] = "n/a"
        else:
            cur = claim.currency or dataset.reporting_currency
            attr["claimed_display"] = format_money(
                int(claim.value_minor) if claim.value_minor is not None else None, cur
            )
            rec = attr.get("recomputed_stated")
            attr["recomputed_display"] = (
                format_money(int(rec), cur) if rec is not None else "n/a"
            )
        results.append(attr)

    report = {
        "case_id": transcript.case_id or path.stem,
        "as_of": as_of.isoformat(),
        "claims": results,
    }
    if as_json:
        return to_json(report)
    lines = [f"Case: {report['case_id']} (as-of {as_of})"]
    for r in results:
        lines.append(
            f"  {r['metric']}: {r['verdict']} - {r['explanation']} "
            f"(claimed {r.get('claimed_display')}, stated recompute {r.get('recomputed_display')})"
        )
    return "\n".join(lines)


def cmd_demo() -> int:
    header = (
        "finance-answer-checker demo (ASSUMPTION: mock MCP schema is a stand-in; "
        "Seapoint's real tool names and schemas are not public; no Seapoint endpoint called)\n"
    )
    adapter = load_adapter(DEFAULT_ADAPTER)
    rows = []
    t0 = time.perf_counter()
    for case_path in sorted(CASES_DIR.glob("*.json")):
        transcript = load_transcript(case_path)
        outputs = tool_outputs_from_transcript(transcript)
        dataset = apply_adapter(adapter, outputs)
        as_of = _default_as_of(transcript)
        hire = transcript.scenario_hire_cost_minor
        if hire is None:
            hire = parse_scenario_hire_minor(transcript.final_answer)
        hire = hire or 0
        for claim in extract_claims(transcript.final_answer):
            attr = attribute_claim(
                claim,
                dataset,
                as_of,
                transcript.stated_definition,
                hire,
            )
            cid = transcript.case_id or case_path.stem
            if claim.metric == "runway_months":
                claimed_d = f"{claim.value_months} mo"
                rec_d = (
                    f"{attr.get('recomputed_stated')} mo"
                    if attr.get("recomputed_stated") is not None
                    else "n/a"
                )
            else:
                cur = claim.currency or "GBP"
                claimed_d = format_money(claim.value_minor, cur)
                rec = attr.get("recomputed_stated")
                rec_d = format_money(int(rec), cur) if rec is not None else "n/a"
            rows.append(
                {
                    "case_id": cid,
                    "metric": claim.metric,
                    "claimed_display": claimed_d,
                    "recomputed_display": rec_d,
                    "verdict": attr["verdict"],
                    "likely_cause": attr.get("likely_cause", ""),
                    "explanation": attr.get("explanation", ""),
                }
            )
    elapsed = time.perf_counter() - t0
    table = render_table(rows, header)
    print(table)
    print(f"\nDemo completed in {elapsed:.2f}s ({len(rows)} claims)")
    return 0


def cmd_list_cases() -> int:
    for p in sorted(CASES_DIR.glob("*.json")):
        t = load_transcript(p)
        print(f"{p.name}\t{t.case_id or p.stem}")
    return 0


def cmd_init_example() -> int:
    EXAMPLE_TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    if EXAMPLE_TRANSCRIPT.exists():
        print(f"Example already exists: {EXAMPLE_TRANSCRIPT}")
        return 0
    payload = {
        "case_id": "example",
        "as_of_date": data.AS_OF.isoformat(),
        "stated_definition": {
            "window_months": 3,
            "include_pending": False,
            "burn_basis": "net",
            "fx_policy": "transaction_date",
            "source": "bank",
        },
        "tool_calls": [
            {
                "tool_call": {"name": "list_transactions", "args": {"mode": "provenanced"}},
                "tool_output": call_tool("list_transactions", {"mode": "provenanced"}),
            },
            {
                "tool_call": {"name": "get_fx_rates", "args": {}},
                "tool_output": call_tool("get_fx_rates", {}),
            },
        ],
        "final_answer": "Net burn is GBP 2,206.66 per month over the last 3 months.",
    }
    EXAMPLE_TRANSCRIPT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {EXAMPLE_TRANSCRIPT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independent definition checker for finance agent answers"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="Run all cases and print summary table")
    sub.add_parser("list-cases", help="List case transcript files")
    sub.add_parser("init-example", help="Write examples/minimal_transcript.json")

    p_check = sub.add_parser("check", help="Check one transcript JSON")
    p_check.add_argument("transcript")
    p_check.add_argument("--adapter", default=str(DEFAULT_ADAPTER))
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--definition-file", help="JSON file with StatedDefinitionSpec fields")
    p_check.add_argument("--window", type=int)
    p_check.add_argument("--net", action="store_true")
    p_check.add_argument("--gross", action="store_true")
    p_check.add_argument("--include-pending", action="store_true")
    p_check.add_argument("--exclude-pending", action="store_true")
    p_check.add_argument("--fx", choices=["transaction_date", "latest", "none_mixed"])
    p_check.add_argument("--source", choices=["bank", "ledger", "union"])
    p_check.add_argument("--exclude-one-offs", action="store_true")
    p_check.add_argument("--exclude-uncategorised", action="store_true")
    p_check.add_argument("--union-no-dedupe", action="store_true")

    args = parser.parse_args()
    if args.cmd == "demo":
        return cmd_demo()
    if args.cmd == "list-cases":
        return cmd_list_cases()
    if args.cmd == "init-example":
        return cmd_init_example()
    if args.cmd == "check":
        try:
            transcript = load_transcript(Path(args.transcript))
            stated = _stated_from_args(args, transcript.stated_definition)
            out = check_transcript(
                Path(args.transcript),
                Path(args.adapter),
                as_json=args.json,
                stated_override=stated,
            )
        except TranscriptError as exc:
            print(f"Error: {exc}")
            return 2
        except FileNotFoundError as exc:
            print(f"Error: {exc}")
            return 2
        print(out)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
