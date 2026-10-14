from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from verifier.definitions import Definition
from verifier.models import CanonicalDataset, Transaction, TxStatus


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def window_start(as_of: date, window_months: int) -> date:
    """First day of the earliest month in a trailing window ending on as_of."""
    return _add_months(_month_start(as_of), -window_months)


def filter_transactions(
    data: CanonicalDataset, definition: Definition, as_of: date
) -> list[Transaction]:
    ws = window_start(as_of, definition.window_months)
    out: list[Transaction] = []
    for tx in data.transactions:
        if tx.txn_date < ws or tx.txn_date > as_of:
            continue
        if not definition.include_pending and tx.status == TxStatus.PENDING:
            continue
        if not definition.include_uncategorised and (tx.category is None or tx.category == ""):
            continue
        if definition.exclude_one_offs and tx.is_one_off:
            continue
        if definition.source == "bank":
            if tx.source is not None and tx.source.value != "bank":
                continue
        elif definition.source == "ledger":
            if tx.source is not None and tx.source.value != "ledger":
                continue
        else:
            # union: dedupe matched pairs by id prefix match
            pass
        out.append(tx)
    if definition.source == "union" and definition.union_dedupe:
        out = _dedupe_union(out)
    return out


def _dedupe_union(txs: list[Transaction]) -> list[Transaction]:
    """Keep one leg of matched bank+ledger pairs (prefer bank)."""
    by_match: dict[str, list[Transaction]] = {}
    unmatched: list[Transaction] = []
    for tx in txs:
        key = tx.id.split(":")[-1] if ":" in tx.id else tx.id
        if tx.matched:
            by_match.setdefault(key, []).append(tx)
        else:
            unmatched.append(tx)
    picked: list[Transaction] = []
    for group in by_match.values():
        bank = [t for t in group if t.source and t.source.value == "bank"]
        if bank:
            picked.append(bank[0])
        else:
            picked.append(group[0])
    return unmatched + picked


def _fx_convert(
    amount_minor: int,
    currency: str,
    reporting: str,
    fx_policy: str,
    fx_rates: dict[str, dict[str, float]],
    txn_date: date,
    as_of: date,
) -> int:
    if currency == reporting:
        return amount_minor
    rates = fx_rates.get(currency, {})
    if not rates:
        if fx_policy == "none_mixed":
            return amount_minor
        return amount_minor
    if fx_policy == "none_mixed":
        return amount_minor
    if fx_policy == "latest":
        dkey = max(rates.keys())
    else:
        dkey = txn_date.isoformat()
        if dkey not in rates:
            keys = sorted(rates.keys())
            dkey = keys[-1]
            for k in keys:
                if k <= txn_date.isoformat():
                    dkey = k
    rate = Decimal(str(rates[dkey]))
    return int(Decimal(amount_minor) * rate)


def monthly_burn_minor(
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    basis: str | None = None,
) -> int | None:
    basis = basis or definition.burn_basis
    txs = filter_transactions(data, definition, as_of)
    if not txs and definition.source != "union":
        # may still be empty
        pass
    outflows = 0
    inflows = 0
    reporting = data.reporting_currency
    for tx in txs:
        amt = _fx_convert(
            tx.amount_minor,
            tx.currency,
            reporting,
            definition.fx_policy,
            data.fx_rates,
            tx.txn_date,
            as_of,
        )
        if amt < 0:
            outflows += -amt
        else:
            inflows += amt
    months = definition.window_months
    if basis == "gross":
        return outflows // months if months else None
    net = outflows - inflows
    return net // months if months else None


def cash_balance_minor(
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
) -> int | None:
    candidates = [b for b in data.balances if b.as_of <= as_of]
    if not candidates:
        return None
    if definition.source == "bank":
        candidates = [b for b in candidates if b.source and b.source.value == "bank"]
    elif definition.source == "ledger":
        candidates = [b for b in candidates if b.source and b.source.value == "ledger"]
    if not candidates:
        return None
    best = max(candidates, key=lambda b: b.as_of)
    return best.amount_minor


def runway_months(
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    extra_monthly_cost_minor: int = 0,
) -> float | None:
    cash = cash_balance_minor(data, definition, as_of)
    net = monthly_burn_minor(data, definition, as_of, basis="net")
    if cash is None or net is None or net <= 0:
        return None
    hire = extra_monthly_cost_minor if definition.scenario_hire_applied else 0
    effective_burn = net + hire
    if effective_burn <= 0:
        return None
    return round(cash / effective_burn, 2)


def overdue_total_minor(
    data: CanonicalDataset,
    as_of: date,
    reporting: str | None = None,
    definition: Definition | None = None,
) -> int:
    reporting = reporting or data.reporting_currency
    definition = definition or Definition(
        window_months=3,
        include_pending=False,
        burn_basis="net",
        fx_policy="transaction_date",
        include_uncategorised=True,
        source="bank",
        exclude_one_offs=False,
    )
    total = 0
    for inv in data.invoices:
        if inv.paid and not definition.overdue_include_paid:
            continue
        if inv.due_date >= as_of and not definition.overdue_include_not_yet_due:
            continue
        amt = inv.amount_minor
        if inv.currency != reporting:
            amt = _fx_convert(
                amt,
                inv.currency,
                reporting,
                "transaction_date",
                data.fx_rates,
                inv.due_date,
                as_of,
            )
        total += amt
    return total


def vat_estimate_minor(
    data: CanonicalDataset,
    definition: Definition,
    as_of: date,
    rate: Decimal = Decimal("0.20"),
) -> int:
    """Standard-rate VAT on net vatable outflows in window (simplified)."""
    txs = filter_transactions(data, definition, as_of)
    vatable_spend = 0
    reporting = data.reporting_currency
    for tx in txs:
        if tx.amount_minor >= 0:
            continue
        amt = _fx_convert(
            tx.amount_minor,
            tx.currency,
            reporting,
            definition.fx_policy,
            data.fx_rates,
            tx.txn_date,
            as_of,
        )
        vatable_spend += -amt
    if definition.vat_on_gross:
        return int(Decimal(vatable_spend) * rate)
    return int(Decimal(vatable_spend) * rate / (Decimal("1") + rate))
