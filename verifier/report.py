from __future__ import annotations

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
        ("Case", 22),
        ("Metric", 10),
        ("Agent answer", 14),
        ("Recomputed", 14),
        ("Verdict", 22),
        ("Likely cause", 42),
    )
    header_line = "".join(f"{name:<{w}}" for name, w in cols)
    lines.append(header_line)
    lines.append("-" * min(140, len(header_line)))
    for r in rows:
        case_id = str(r.get("case_id", ""))[:22]
        metric = _metric_label(str(r.get("metric", "")))[:10]
        claimed = str(r.get("claimed_display", r.get("claimed", "")))[:14]
        rec = str(r.get("recomputed_display", r.get("recomputed_stated", "n/a")))[:14]
        verdict = str(r.get("verdict", ""))[:22]
        cause = str(r.get("likely_cause", r.get("explanation", "")))[:42]
        lines.append(
            f"{case_id:<22} {metric:<10} {claimed:<14} {rec:<14} {verdict:<22} {cause}"
        )
    return "\n".join(lines)


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, default=str)
