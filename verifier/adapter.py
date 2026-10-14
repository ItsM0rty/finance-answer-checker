"""Map assumed MCP tool JSON to the canonical finance model.

ASSUMPTION: this schema and these tool names are a stand-in built from public
product descriptions. Seapoint's real MCP tool names and schemas are not public
(no docs, no public repo, not in the MCP registry).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from verifier.models import Balance, CanonicalDataset, Invoice, Source, Transaction, TxStatus


def load_adapter(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get(obj: dict, dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _parse_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])


def apply_adapter(
    adapter: dict[str, Any],
    tool_outputs: list[dict[str, Any]],
) -> CanonicalDataset:
    """Map assumed MCP tool outputs to canonical model.

    ASSUMPTION: mock schema, not Seapoint's real tool surface.
    """
    reporting = adapter.get("reporting_currency", "GBP")
    sign = adapter.get("amount_sign", "negative_outflow")
    txs: list[Transaction] = []
    invoices: list[Invoice] = []
    balances: list[Balance] = []
    fx_rates: dict[str, dict[str, float]] = adapter.get("fx_rates", {})

    for block in tool_outputs:
        name = block.get("tool_name", "")
        payload = block.get("output", {})
        if name == adapter["tools"]["transactions"]:
            rows = payload.get(adapter["fields"]["transactions_list"], [])
            for row in rows:
                amt = int(row[adapter["fields"]["amount_minor"]])
                if sign == "positive_outflow":
                    amt = -amt
                src = row.get(adapter["fields"].get("source", "source"))
                status = row.get(adapter["fields"].get("status", "status"))
                txs.append(
                    Transaction(
                        id=str(row[adapter["fields"]["id"]]),
                        txn_date=_parse_date(row[adapter["fields"]["txn_date"]]),
                        amount_minor=amt,
                        currency=row.get(adapter["fields"].get("currency", "currency"), reporting),
                        category=row.get(adapter["fields"].get("category", "category")),
                        description=row.get("description", ""),
                        source=Source(src) if src in ("bank", "ledger") else None,
                        as_of=_parse_date(row.get(adapter["fields"].get("as_of", "as_of"))),
                        status=TxStatus(status) if status in ("pending", "posted") else None,
                        matched=row.get(adapter["fields"].get("matched", "matched")),
                        fx_rate_to_reporting=row.get("fx_rate"),
                        fx_date=_parse_date(row.get("fx_date")),
                        is_one_off=bool(row.get("one_off", False)),
                    )
                )
        elif name == adapter["tools"]["invoices"]:
            rows = payload.get(adapter["fields"]["invoices_list"], [])
            for row in rows:
                invoices.append(
                    Invoice(
                        id=str(row[adapter["fields"]["invoice_id"]]),
                        due_date=_parse_date(row[adapter["fields"]["due_date"]]),
                        amount_minor=int(row[adapter["fields"]["invoice_amount_minor"]]),
                        currency=row.get("currency", reporting),
                        paid=bool(row.get("paid", False)),
                        vatable=bool(row.get("vatable", True)),
                    )
                )
        elif name == adapter["tools"]["balances"]:
            rows = payload.get(adapter["fields"]["balances_list"], [])
            for row in rows:
                src = row.get("source")
                balances.append(
                    Balance(
                        as_of=_parse_date(row[adapter["fields"]["balance_as_of"]]),
                        amount_minor=int(row[adapter["fields"]["balance_amount_minor"]]),
                        currency=row.get("currency", reporting),
                        source=Source(src) if src in ("bank", "ledger") else None,
                    )
                )
        elif name == adapter["tools"].get("fx_rates"):
            fx_payload = payload.get("rates", {})
            for cur, by_date in fx_payload.items():
                fx_rates.setdefault(cur, {}).update(
                    {str(k): float(v) for k, v in by_date.items()}
                )

    if not fx_rates and "fx_rates" in adapter:
        fx_rates = adapter["fx_rates"]

    return CanonicalDataset(
        transactions=txs,
        invoices=invoices,
        balances=balances,
        reporting_currency=reporting,
        fx_rates=fx_rates,
    )
