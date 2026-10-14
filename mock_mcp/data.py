"""Seeded dummy company Nimbus SaaS Ltd (deterministic fake data).

ASSUMPTION: this schema and these tool names are a stand-in built from public
product descriptions. Seapoint's real MCP tool names and schemas are not public
(no docs, no public repo, not in the MCP registry).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Literal

Mode = Literal["raw", "provenanced"]

AS_OF = date(2026, 10, 1)
REPORTING = "GBP"

FX_RATES = {
    "EUR": {
        "2026-07-15": 0.86,
        "2026-09-01": 0.88,
        "2026-10-01": 0.87,
    },
    "USD": {
        "2026-08-01": 0.78,
        "2026-10-01": 0.79,
    },
}

# amount_minor: negative = outflow, positive = inflow (canonical sign in mock payloads)


def _bank_tx(
    tid: str,
    txn_date: str,
    amount_minor: int,
    currency: str = "GBP",
    category: str | None = "opex",
    status: str = "posted",
    matched: bool = False,
    one_off: bool = False,
    description: str = "",
) -> dict:
    return {
        "id": f"bank:{tid}",
        "txn_date": txn_date,
        "amount_minor": amount_minor,
        "currency": currency,
        "category": category,
        "status": status,
        "source": "bank",
        "as_of": AS_OF.isoformat(),
        "matched": matched,
        "description": description,
        "one_off": one_off,
    }


def _ledger_tx(
    tid: str,
    txn_date: str,
    amount_minor: int,
    currency: str = "GBP",
    category: str | None = "opex",
    status: str = "posted",
    matched: bool = False,
    one_off: bool = False,
    description: str = "",
) -> dict:
    return {
        "id": f"ledger:{tid}",
        "txn_date": txn_date,
        "amount_minor": amount_minor,
        "currency": currency,
        "category": category,
        "status": status,
        "source": "ledger",
        "as_of": AS_OF.isoformat(),
        "matched": matched,
        "description": description,
        "one_off": one_off,
    }


def seed_transactions_provenanced() -> list[dict]:
    """Jul-Sep 2026 window; deliberate bank vs ledger timing differences."""
    txs = [
        # Matched pair (same economic event, different dates)
        _bank_tx("m1", "2026-09-28", -120_000, category="payroll", matched=True),
        _ledger_tx("m1", "2026-09-25", -120_000, category="payroll", matched=True),
        # Pending bank only
        _bank_tx("p1", "2026-09-30", -45_000, category="saas", status="pending"),
        # Posted opex
        _bank_tx("b1", "2026-08-15", -80_000, category="rent"),
        _ledger_tx("l1", "2026-08-14", -80_000, category="rent"),
        _bank_tx("b2", "2026-07-20", -60_000, category="marketing"),
        _ledger_tx("l2", "2026-07-22", -60_000, category="marketing"),
        # Uncategorised
        _bank_tx("u1", "2026-09-10", -15_000, category=None),
        _ledger_tx("u2", "2026-09-05", -12_000, category=""),
        # EUR spend (needs FX)
        _bank_tx("fx1", "2026-07-15", -50_000, currency="EUR", category="contractors"),
        # USD inflow
        _bank_tx("rev1", "2026-08-01", 200_000, currency="USD", category="revenue"),
        _ledger_tx("rev2", "2026-09-01", 150_000, category="revenue"),
        # One-off
        _bank_tx("oo1", "2026-09-01", -500_000, category="equipment", one_off=True),
        # Extra months for 6mo window
        _bank_tx("b3", "2026-05-10", -55_000, category="opex"),
        _bank_tx("b4", "2026-04-12", -58_000, category="opex"),
    ]
    return txs


def seed_invoices() -> list[dict]:
    return [
        {
            "invoice_id": "inv-101",
            "due_date": "2026-09-15",
            "amount_minor": 80_000,
            "currency": "GBP",
            "paid": False,
            "vatable": True,
        },
        {
            "invoice_id": "inv-102",
            "due_date": "2026-10-20",
            "amount_minor": 40_000,
            "currency": "GBP",
            "paid": False,
            "vatable": True,
        },
        {
            "invoice_id": "inv-103",
            "due_date": "2026-08-01",
            "amount_minor": 25_000,
            "currency": "GBP",
            "paid": True,
            "vatable": True,
        },
        {
            "invoice_id": "inv-104",
            "due_date": "2026-09-01",
            "amount_minor": 30_000,
            "currency": "EUR",
            "paid": False,
            "vatable": True,
        },
    ]


def seed_balances() -> list[dict]:
    return [
        {
            "as_of": "2026-10-01",
            "amount_minor": 1_200_000,
            "currency": "GBP",
            "source": "bank",
        },
        {
            "as_of": "2026-09-28",
            "amount_minor": 1_050_000,
            "currency": "GBP",
            "source": "ledger",
        },
    ]


def strip_provenance(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        o = deepcopy(r)
        for k in ("source", "as_of", "status", "matched", "fx_rate", "fx_date"):
            o.pop(k, None)
        out.append(o)
    return out


def get_transactions(mode: Mode = "provenanced") -> list[dict]:
    rows = seed_transactions_provenanced()
    if mode == "raw":
        return strip_provenance(rows)
    return rows


def get_invoices() -> list[dict]:
    return seed_invoices()


def get_balances(mode: Mode = "provenanced") -> list[dict]:
    rows = seed_balances()
    if mode == "raw":
        return [{k: v for k, v in b.items() if k != "source"} for b in rows]
    return rows


def get_fx_rates() -> dict:
    return {"rates": FX_RATES}


def get_runway_summary(mode: Mode = "provenanced") -> dict:
    return {
        "as_of": AS_OF.isoformat(),
        "reporting_currency": REPORTING,
        "note": "ASSUMPTION: mock schema, not Seapoint's real tool surface.",
    }
