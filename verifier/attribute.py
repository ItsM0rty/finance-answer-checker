from __future__ import annotations

from datetime import date, timedelta

from verifier.definitions import Definition
from verifier.metrics import overdue_total_minor
from verifier.models import CanonicalDataset, ExtractedClaim, StatedDefinitionSpec
from verifier.search import (
    find_matching_definitions,
    nearest_stated_delta,
    recompute_under_stated,
    within_tolerance,
)

Verdict = str

NEAR_STATED_SLIP = 0.005
NEAR_STATED_SLIP_MAX = 0.03


def _has_provenance(data: CanonicalDataset) -> bool:
    for tx in data.transactions:
        if tx.source is not None:
            return True
    return False


def _short_cause(explanation: str, max_len: int = 42) -> str:
    text = explanation.strip()
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 3].rsplit(" ", 1)[0]
    return cut + "..."


def _classify_no_match(
    metric: str,
    claimed_val: int | float,
    data: CanonicalDataset,
    as_of: date,
    stated_def: Definition | None,
    recomputed: int | float | None,
    extra_hire_minor: int,
) -> str:
    if stated_def and recomputed is not None:
        _, rel = nearest_stated_delta(
            metric, claimed_val, data, stated_def, as_of, extra_hire_minor
        )
        if NEAR_STATED_SLIP < rel <= NEAR_STATED_SLIP_MAX:
            return (
                "Arithmetic slip: close to the stated-definition recompute "
                "but outside tolerance."
            )
    return (
        "No tested definition reproduces this figure within tolerance; "
        "likely fabrication or an unstated definition outside the grid."
    )


def attribute_claim(
    claim: ExtractedClaim,
    data: CanonicalDataset,
    as_of: date,
    stated: StatedDefinitionSpec | None,
    extra_hire_minor: int = 0,
) -> dict:
    metric = claim.metric
    if metric == "runway_months":
        claimed_val = claim.value_months
    else:
        claimed_val = claim.value_minor

    if claimed_val is None:
        return {
            "metric": metric,
            "verdict": "UNCHECKABLE",
            "explanation": "Could not parse a numeric claim from the answer.",
            "likely_cause": "Unparseable claim",
            "claimed": None,
            "recomputed_stated": None,
            "matching_definitions": [],
        }

    needs_provenance = metric in ("net_burn", "gross_burn", "runway_months", "cash_balance")
    if needs_provenance and not _has_provenance(data) and metric != "overdue_total":
        return {
            "metric": metric,
            "verdict": "UNCHECKABLE",
            "explanation": "Tool output lacks provenance (source/status); cannot test pending or source axes.",
            "likely_cause": "Missing provenance in tool output",
            "claimed": claimed_val,
            "recomputed_stated": None,
            "matching_definitions": [],
        }

    stated_def = Definition.from_stated(stated) if stated else None
    recomputed = None
    if stated_def:
        recomputed = recompute_under_stated(
            metric, data, stated_def, as_of, extra_hire_minor
        )

    matches = find_matching_definitions(
        metric, claimed_val, data, as_of, extra_hire_minor
    )

    if metric in ("net_burn", "gross_burn") and matches:
        want = "net" if metric == "net_burn" else "gross"
        same_basis = [m for m in matches if m.burn_basis == want]
        if same_basis:
            matches = same_basis

    if stated_def and recomputed is not None and not matches:
        _, rel = nearest_stated_delta(
            metric, claimed_val, data, stated_def, as_of, extra_hire_minor
        )
        if NEAR_STATED_SLIP < rel <= NEAR_STATED_SLIP_MAX:
            expl = (
                "Arithmetic slip: close to the stated-definition recompute "
                "but outside tolerance."
            )
            return {
                "metric": metric,
                "verdict": "MATCHES_NO_DEFINITION",
                "explanation": expl,
                "likely_cause": _short_cause(expl),
                "claimed": claimed_val,
                "recomputed_stated": recomputed,
                "matching_definitions": [],
            }

    if stated_def and recomputed is not None:
        if metric == "runway_months":
            ok = within_tolerance(claimed_val, recomputed)
        else:
            ok = within_tolerance(int(claimed_val), int(recomputed))
        if ok:
            expl = f"Matches stated definition ({stated_def.label()})."
            return {
                "metric": metric,
                "verdict": "MATCHES_STATED_DEFINITION",
                "explanation": expl,
                "likely_cause": "Stated definition",
                "claimed": claimed_val,
                "recomputed_stated": recomputed,
                "matching_definitions": [stated_def.label()],
            }
        if metric == "net_burn":
            from verifier.metrics import monthly_burn_minor

            gross_stated = monthly_burn_minor(
                data, stated_def, as_of, basis="gross"
            )
            if gross_stated is not None and within_tolerance(
                int(claimed_val), int(gross_stated)
            ):
                expl = "Figure matches gross burn under the stated window, not net burn."
                return {
                    "metric": metric,
                    "verdict": "MATCHES_OTHER_DEFINITION",
                    "explanation": expl,
                    "likely_cause": _short_cause(expl),
                    "claimed": claimed_val,
                    "recomputed_stated": recomputed,
                    "matching_definitions": [stated_def.label()],
                    "other_definition_axes": ["gross burn instead of net"],
                }

    if metric == "overdue_total" and not matches:
        for delta in range(-90, 91):
            alt = as_of + timedelta(days=delta)
            if alt == as_of:
                continue
            alt_val = overdue_total_minor(data, alt)
            if within_tolerance(int(claimed_val), alt_val):
                expl = (
                    f"Overdue total matches as-of {alt.isoformat()} "
                    f"rather than {as_of.isoformat()}."
                )
                return {
                    "metric": metric,
                    "verdict": "MATCHES_OTHER_DEFINITION",
                    "explanation": expl,
                    "likely_cause": _short_cause(expl),
                    "claimed": claimed_val,
                    "recomputed_stated": recomputed,
                    "matching_definitions": [f"as_of={alt.isoformat()}"],
                }

    if matches:
        if stated_def:
            other = [m for m in matches if m != stated_def]
            if metric == "gross_burn":
                union_no = [m for m in other if m.source == "union" and not m.union_dedupe]
                if union_no:
                    other = union_no
            if metric == "runway_months":
                hire_omit = [m for m in other if not m.scenario_hire_applied]
                if hire_omit:
                    other = hire_omit
                ledger = [m for m in other if m.source == "ledger"]
                if ledger:
                    other = ledger
            if other:
                best = other[0]
                compare_stated = stated_def
                if metric == "gross_burn":
                    compare_stated = Definition(
                        window_months=stated_def.window_months,
                        include_pending=stated_def.include_pending,
                        burn_basis="gross",
                        fx_policy=stated_def.fx_policy,
                        include_uncategorised=stated_def.include_uncategorised,
                        source=stated_def.source,
                        exclude_one_offs=stated_def.exclude_one_offs,
                        union_dedupe=stated_def.union_dedupe,
                    )
                axes = best.diff_axes(compare_stated)
                expl = "Agent figure matches a different definition: " + "; ".join(
                    axes[:3]
                )
                return {
                    "metric": metric,
                    "verdict": "MATCHES_OTHER_DEFINITION",
                    "explanation": expl,
                    "likely_cause": _short_cause(axes[0] if axes else expl),
                    "claimed": claimed_val,
                    "recomputed_stated": recomputed,
                    "matching_definitions": [m.label() for m in matches[:5]],
                    "other_definition_axes": axes,
                }
        if not stated_def:
            expl = (
                "No definition stated; figure matches at least one tested definition "
                "(ambiguous which applies)."
            )
            return {
                "metric": metric,
                "verdict": "MATCHES_OTHER_DEFINITION",
                "explanation": expl,
                "likely_cause": "Unstated definition (ambiguous)",
                "claimed": claimed_val,
                "recomputed_stated": None,
                "matching_definitions": [m.label() for m in matches[:8]],
            }

    expl = _classify_no_match(
        metric, claimed_val, data, as_of, stated_def, recomputed, extra_hire_minor
    )
    return {
        "metric": metric,
        "verdict": "MATCHES_NO_DEFINITION",
        "explanation": expl,
        "likely_cause": _short_cause(expl),
        "claimed": claimed_val,
        "recomputed_stated": recomputed,
        "matching_definitions": [],
    }
