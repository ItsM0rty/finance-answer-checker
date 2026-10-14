from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from verifier.models import StatedDefinitionSpec


@dataclass(frozen=True)
class Definition:
    window_months: int
    include_pending: bool
    burn_basis: Literal["gross", "net"]
    fx_policy: Literal["transaction_date", "latest", "none_mixed"]
    include_uncategorised: bool
    source: Literal["bank", "ledger", "union"]
    exclude_one_offs: bool
    union_dedupe: bool = True
    overdue_include_paid: bool = False
    overdue_include_not_yet_due: bool = False
    vat_on_gross: bool = False
    scenario_hire_applied: bool = True

    def label(self) -> str:
        parts = [
            f"trailing {self.window_months}mo",
            f"source={self.source}",
            f"burn={self.burn_basis}",
            f"pending={'in' if self.include_pending else 'ex'}",
            f"fx={self.fx_policy}",
            f"uncat={'in' if self.include_uncategorised else 'ex'}",
            f"one_offs={'ex' if self.exclude_one_offs else 'in'}",
        ]
        if self.source == "union":
            parts.append(f"union_dedupe={'yes' if self.union_dedupe else 'no'}")
        if self.overdue_include_paid or self.overdue_include_not_yet_due:
            ob = []
            if self.overdue_include_paid:
                ob.append("include_paid")
            if self.overdue_include_not_yet_due:
                ob.append("include_not_yet_due")
            parts.append(f"overdue={'+'.join(ob) or 'strict'}")
        if self.vat_on_gross:
            parts.append("vat_on_gross")
        if not self.scenario_hire_applied:
            parts.append("scenario_hire=ignored")
        return "; ".join(parts)

    def diff_axes(self, other: Definition) -> list[str]:
        axes: list[str] = []
        if self.window_months != other.window_months:
            axes.append(
                f"trailing {self.window_months} month instead of {other.window_months}"
            )
        if self.include_pending != other.include_pending:
            axes.append(
                "pending included" if self.include_pending else "pending excluded"
            )
        if self.burn_basis != other.burn_basis:
            axes.append(f"{self.burn_basis} burn instead of {other.burn_basis}")
        if self.fx_policy != other.fx_policy:
            axes.append(f"FX policy {self.fx_policy} instead of {other.fx_policy}")
        if self.include_uncategorised != other.include_uncategorised:
            axes.append(
                "uncategorised included"
                if self.include_uncategorised
                else "uncategorised excluded"
            )
        if self.source != other.source:
            axes.append(f"source {self.source} instead of {other.source}")
        if self.exclude_one_offs != other.exclude_one_offs:
            axes.append(
                "one-offs excluded"
                if self.exclude_one_offs
                else "one-offs included"
            )
        if self.union_dedupe != other.union_dedupe:
            axes.append(
                "bank+ledger union without dedupe"
                if not self.union_dedupe
                else "bank+ledger union with dedupe"
            )
        if self.overdue_include_paid != other.overdue_include_paid:
            axes.append(
                "overdue includes paid invoices"
                if self.overdue_include_paid
                else "overdue excludes paid invoices"
            )
        if self.overdue_include_not_yet_due != other.overdue_include_not_yet_due:
            axes.append(
                "overdue includes not-yet-due invoices"
                if self.overdue_include_not_yet_due
                else "overdue strict by due date"
            )
        if self.vat_on_gross != other.vat_on_gross:
            axes.append(
                "VAT on gross spend" if self.vat_on_gross else "VAT net of VAT in spend"
            )
        if self.scenario_hire_applied != other.scenario_hire_applied:
            axes.append(
                "scenario hire cost omitted from runway"
                if not self.scenario_hire_applied
                else "scenario hire cost included in runway"
            )
        return axes

    @classmethod
    def from_stated(cls, spec: StatedDefinitionSpec) -> Definition:
        return cls(
            window_months=spec.window_months,
            include_pending=spec.include_pending,
            burn_basis=spec.burn_basis,
            fx_policy=spec.fx_policy,
            include_uncategorised=spec.include_uncategorised,
            source=spec.source,
            exclude_one_offs=spec.exclude_one_offs,
            union_dedupe=spec.union_dedupe,
        )


def burn_definition_variants() -> list[Definition]:
    windows = (1, 3, 6)
    pending_opts = (False, True)
    burn_opts: tuple[Literal["gross", "net"], ...] = ("gross", "net")
    fx_opts: tuple[Literal["transaction_date", "latest", "none_mixed"], ...] = (
        "transaction_date",
        "latest",
        "none_mixed",
    )
    uncat_opts = (True, False)
    source_opts: tuple[Literal["bank", "ledger", "union"], ...] = (
        "bank",
        "ledger",
        "union",
    )
    one_off_opts = (False, True)
    union_dedupe_opts = (True, False)
    out: list[Definition] = []
    for w in windows:
        for ip in pending_opts:
            for bb in burn_opts:
                for fx in fx_opts:
                    for iu in uncat_opts:
                        for src in source_opts:
                            for eo in one_off_opts:
                                dedupe_opts = (
                                    union_dedupe_opts if src == "union" else (True,)
                                )
                                for ud in dedupe_opts:
                                    out.append(
                                        Definition(
                                            window_months=w,
                                            include_pending=ip,
                                            burn_basis=bb,
                                            fx_policy=fx,
                                            include_uncategorised=iu,
                                            source=src,
                                            exclude_one_offs=eo,
                                            union_dedupe=ud,
                                        )
                                    )
    return out


def overdue_definition_variants() -> list[Definition]:
    bases = [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ]
    return [
        Definition(
            window_months=3,
            include_pending=False,
            burn_basis="net",
            fx_policy="transaction_date",
            include_uncategorised=True,
            source="bank",
            exclude_one_offs=False,
            overdue_include_paid=paid,
            overdue_include_not_yet_due=future,
        )
        for paid, future in bases
    ]


def vat_definition_variants() -> list[Definition]:
    out: list[Definition] = []
    for vat_gross in (False, True):
        for fx in ("transaction_date", "latest", "none_mixed"):
            for w in (1, 3, 6):
                out.append(
                    Definition(
                        window_months=w,
                        include_pending=False,
                        burn_basis="net",
                        fx_policy=fx,
                        include_uncategorised=True,
                        source="bank",
                        exclude_one_offs=False,
                        vat_on_gross=vat_gross,
                    )
                )
    return out


def runway_definition_variants() -> list[Definition]:
    out = burn_definition_variants()
    extra: list[Definition] = []
    for d in out:
        if d.burn_basis == "net":
            extra.append(
                Definition(
                    window_months=d.window_months,
                    include_pending=d.include_pending,
                    burn_basis=d.burn_basis,
                    fx_policy=d.fx_policy,
                    include_uncategorised=d.include_uncategorised,
                    source=d.source,
                    exclude_one_offs=d.exclude_one_offs,
                    union_dedupe=d.union_dedupe,
                    scenario_hire_applied=False,
                )
            )
    return out + extra


def all_definition_variants() -> list[Definition]:
    return burn_definition_variants()


def reduced_search_variants() -> list[Definition]:
    return burn_definition_variants()
