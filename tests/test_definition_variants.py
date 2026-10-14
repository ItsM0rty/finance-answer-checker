from datetime import date

from cases.generate import dataset, AS_OF
from verifier.definitions import Definition
from verifier.models import StatedDefinitionSpec
from verifier.search import compute_metric, find_matching_definitions


def test_case08_union_no_dedupe_matches():
    ds = dataset()
    t = __import__("verifier.extract", fromlist=["extract_claims"]).extract_claims(
        "Gross burn is GBP 3,633.33 merging bank and ledger without dedupe."
    )[0]
    assert t.value_minor == 363_333
    matches = find_matching_definitions("gross_burn", t.value_minor, ds, AS_OF)
    assert any(not m.union_dedupe and m.source == "union" for m in matches)


def test_case06_none_mixed_fx_matches():
    ds = dataset()
    t = __import__("verifier.extract", fromlist=["extract_claims"]).extract_claims(
        "Net burn is GBP 2,083.33 (EUR summed as GBP)."
    )[0]
    d = Definition.from_stated(
        StatedDefinitionSpec(fx_policy="none_mixed", source="bank", window_months=3)
    )
    val = compute_metric("net_burn", ds, d, AS_OF)
    assert val == t.value_minor
