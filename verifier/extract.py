from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from verifier.models import ExtractedClaim

_CURRENCY_SYMBOL = {"\u00a3": "GBP", "$": "USD", "\u20ac": "EUR"}


def _parse_money_minor(text: str, currency_hint: str | None = None) -> tuple[int | None, str | None]:
    text = text.strip()
    cur = currency_hint
    for sym, code in _CURRENCY_SYMBOL.items():
        if sym in text:
            cur = code
            text = text.replace(sym, "")
    m = re.search(r"([\d,]+(?:\.\d{1,2})?)\s*(k|K|m|M|million|months?)?", text)
    if not m:
        return None, cur
    num = Decimal(m.group(1).replace(",", ""))
    suffix = (m.group(2) or "").lower()
    if suffix in ("k",):
        num *= 1000
    elif suffix in ("m", "million"):
        num *= 1_000_000
    minor = int((num * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return minor, cur


def parse_scenario_hire_minor(text: str) -> int | None:
    """Parse a stated monthly hire cost from the answer (minor units)."""
    m = re.search(
        r"hire[^.\n]{0,80}?((?:GBP\s*)?[\d,]+(?:\.\d{2})?|\$\s*[\d,]+(?:\.\d{2})?)\s*/?\s*month",
        text,
        re.I,
    )
    if not m:
        m = re.search(
            r"((?:GBP\s*)?[\d,]+(?:\.\d{2})?|\$\s*[\d,]+(?:\.\d{2})?)\s*/?\s*month[^.\n]{0,40}?hire",
            text,
            re.I,
        )
    if not m:
        return None
    minor, _ = _parse_money_minor(m.group(1))
    return minor


def extract_claims(final_answer: str) -> list[ExtractedClaim]:
    text = final_answer
    claims: list[ExtractedClaim] = []

    patterns: list[tuple[str, str]] = [
        (r"net\s+burn[^\d$]*(?:GBP\s*)?([\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s*k?)", "net_burn"),
        (r"gross\s+burn[^\d$]*(?:GBP\s*)?([\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s*k?)", "gross_burn"),
        (r"runway[^0-9]*([\d]+(?:\.\d+)?)\s*months?", "runway_months"),
        (r"overdue[^\d$]*(?:GBP\s*)?([\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s*k?)", "overdue_total"),
        (r"VAT[^\d$]*(?:GBP\s*)?([\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s*k?)", "vat_estimate"),
        (r"cash\s+balance[^\d$]*(?:GBP\s*)?([\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s*k?)", "cash_balance"),
    ]

    default_cur = None
    cm = re.search(r"\b(GBP|EUR|USD|\$)\b", text)
    if cm:
        tok = cm.group(1)
        default_cur = _CURRENCY_SYMBOL.get(tok, tok if len(tok) == 3 else None)

    for pat, metric in patterns:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        raw = m.group(0)
        frag = m.group(1)
        if metric == "runway_months":
            months = float(re.search(r"([\d.]+)", frag).group(1))
            claims.append(
                ExtractedClaim(
                    metric=metric,
                    value_months=months,
                    currency=default_cur,
                    raw_text=raw,
                )
            )
        else:
            minor, cur = _parse_money_minor(frag, default_cur)
            claims.append(
                ExtractedClaim(
                    metric=metric,
                    value_minor=minor,
                    currency=cur or default_cur or "GBP",
                    raw_text=raw,
                )
            )

    return claims
