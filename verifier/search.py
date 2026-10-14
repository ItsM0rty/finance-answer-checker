from __future__ import annotations

from datetime import date

from verifier.definitions import (
    Definition,
    all_definition_variants,
    burn_definition_variants,
    overdue_definition_variants,
    runway_definition_variants,
    vat_definition_variants,
)
from verifier.metrics import (
    cash_balance_minor,
    monthly_burn_minor,
    overdue_total_minor,
    runway_months,
    vat_estimate_minor,
)
from verifier.models import CanonicalDataset


TOLERANCE = 0.005  # 0.5%


def within_tolerance(claimed: int | float, computed: int | float) -> bool:
    if claimed == 0 and computed == 0:
        return True
    base = max(abs(float(claimed)), 1.0)
    return abs(float(claimed) - float(computed)) / base <= TOLERANCE


def variants_for_metric(metric: str) -> list[Definition]:
    if metric == "overdue_total":
        return overdue_definition_variants()
    if metric == "vat_estimate":
        return vat_definition_variants()
    if metric == "runway_months":
        return runway_definition_variants()
    return burn_definition_variants()


def compute_metric(
    metric: str,
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    extra_hire_minor: int = 0,
) -> int | float | None:
    if metric == "gross_burn":
        return monthly_burn_minor(data, definition, as_of, basis="gross")
    if metric == "net_burn":
        return monthly_burn_minor(data, definition, as_of, basis="net")
    if metric == "cash_balance":
        return cash_balance_minor(data, definition, as_of)
    if metric == "runway_months":
        return runway_months(data, definition, as_of, extra_hire_minor)
    if metric == "overdue_total":
        return overdue_total_minor(data, as_of, definition=definition)
    if metric == "vat_estimate":
        return vat_estimate_minor(data, definition, as_of)
    return None


def find_matching_definitions(
    metric: str,
    claimed: int | float,
    data: CanonicalDataset,
    as_of: date,
    extra_hire_minor: int = 0,
    variants: list[Definition] | None = None,
) -> list[Definition]:
    variants = variants or variants_for_metric(metric)
    scored: list[tuple[float, Definition]] = []
    base = max(abs(float(claimed)), 1.0)
    for d in variants:
        val = compute_metric(metric, data, d, as_of, extra_hire_minor)
        if val is not None and within_tolerance(claimed, val):
            scored.append((abs(float(claimed) - float(val)) / base, d))
            continue
        if metric == "net_burn":
            gross_val = monthly_burn_minor(data, d, as_of, basis="gross")
            if gross_val is not None and within_tolerance(claimed, gross_val):
                scored.append((abs(float(claimed) - float(gross_val)) / base, d))
    # Closest reproduction first, so that a definition that reproduces the
    # figure exactly is preferred over one that is merely within tolerance.
    scored.sort(key=lambda pair: pair[0])
    return [d for _, d in scored]


def recompute_under_stated(
    metric: str,
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    extra_hire_minor: int = 0,
) -> int | float | None:
    return compute_metric(metric, data, definition, as_of, extra_hire_minor)


def nearest_stated_delta(
    metric: str,
    claimed: int | float,
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    extra_hire_minor: int = 0,
) -> tuple[int | float | None, float]:
    """Return stated recomputation and relative distance (0 = exact)."""
    recomputed = recompute_under_stated(
        metric, data, definition, as_of, extra_hire_minor
    )
    if recomputed is None:
        return None, float("inf")
    base = max(abs(float(claimed)), 1.0)
    rel = abs(float(claimed) - float(recomputed)) / base
    return recomputed, rel
