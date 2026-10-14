from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Source(str, Enum):
    BANK = "bank"
    LEDGER = "ledger"


class TxStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"


class Transaction(BaseModel):
    id: str
    txn_date: date
    amount_minor: int  # signed: negative = outflow, positive = inflow
    currency: str
    category: str | None = None
    description: str = ""
    source: Source | None = None
    as_of: date | None = None
    status: TxStatus | None = None
    matched: bool | None = None
    fx_rate_to_reporting: float | None = None
    fx_date: date | None = None
    is_one_off: bool = False


class Invoice(BaseModel):
    id: str
    due_date: date
    amount_minor: int  # positive = owed to company (receivable) or negative for payable; we use positive = customer owes us
    currency: str
    paid: bool = False
    vatable: bool = True


class Balance(BaseModel):
    as_of: date
    amount_minor: int
    currency: str
    source: Source | None = None


class CanonicalDataset(BaseModel):
    transactions: list[Transaction] = Field(default_factory=list)
    invoices: list[Invoice] = Field(default_factory=list)
    balances: list[Balance] = Field(default_factory=list)
    reporting_currency: str = "GBP"
    fx_rates: dict[str, dict[str, float]] = Field(default_factory=dict)
    # fx_rates[currency][iso_date] = rate to reporting currency


class StatedDefinitionSpec(BaseModel):
    window_months: int = 3
    include_pending: bool = False
    burn_basis: Literal["gross", "net"] = "net"
    fx_policy: Literal["transaction_date", "latest", "none_mixed"] = "transaction_date"
    include_uncategorised: bool = True
    source: Literal["bank", "ledger", "union"] = "bank"
    exclude_one_offs: bool = False
    union_dedupe: bool = True


class ExtractedClaim(BaseModel):
    metric: str
    value_minor: int | None = None
    value_months: float | None = None
    currency: str | None = None
    raw_text: str = ""


class Transcript(BaseModel):
    tool_calls: list[dict] = Field(default_factory=list)
    final_answer: str = ""
    stated_definition: StatedDefinitionSpec | None = None
    as_of_date: date | None = None
    expected_verdict: dict[str, str] | None = None
    case_id: str | None = None
    scenario_hire_cost_minor: int | None = None
