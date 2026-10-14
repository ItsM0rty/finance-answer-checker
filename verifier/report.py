from __future__ import annotations

import textwrap

import json
import sys
from typing import Any


def _ensure_stdout() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except (OSError, ValueError):
        pass


def format_money(minor: int | None, currency: str = "GBP") -> str:
    if minor is None:
        return "n/a"
    code = currency or "GBP"
    return f"{code} {minor / 100:,.2f}"


def _metric_label(metric: str) -> str:
    return {
        "net_burn": "net_burn",
        "gross_burn": "gross_burn",
        "runway_months": "runway",
        "overdue_total": "overdue",
        "vat_estimate": "vat",
        "cash_balance": "cash",
    }.get(metric, metric[:12])


def render_table(rows: list[dict[str, Any]], header: str = "") -> str:
    _ensure_stdout()
    lines: list[str] = []
    if header:
        lines.append(header)
        lines.append("")
    cols = (
        ("Case", 28),
        ("Metric", 11),
        ("Agent answer", 15),
        ("Recomputed", 15),
        ("Verdict", 26),
        ("Likely cause", 48),
    )
    header_line = "".join(f"{name:<{w}}" for name, w in cols)
    lines.append(header_line)
    lines.append("-" * len(header_line))
    for r in rows:
        case_id = str(r.get("case_id", ""))
        metric = _metric_label(str(r.get("metric", "")))
        claimed = str(r.get("claimed_display", r.get("claimed", "")))
        rec = str(r.get("recomputed_display", r.get("recomputed_stated", "n/a")))
        verdict = str(r.get("verdict", ""))
        cause = str(r.get("likely_cause", r.get("explanation", "")))
        wrapped = textwrap.wrap(cause, width=48) or [""]
        lines.append(
            f"{case_id:<28}{metric:<11}{claimed:<15}{rec:<15}{verdict:<26}{wrapped[0]}"
        )
        for extra in wrapped[1:]:
            lines.append(" " * 95 + extra)
    return "\n".join(lines)


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, default=str)
