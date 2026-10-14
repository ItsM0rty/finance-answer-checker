from verifier.extract import extract_claims, parse_scenario_hire_minor


def test_extract_net_burn_and_runway():
    text = "Net burn is GBP 12,345.67 per month. Runway is 8.5 months."
    claims = extract_claims(text)
    metrics = {c.metric for c in claims}
    assert "net_burn" in metrics
    assert "runway_months" in metrics
    net = next(c for c in claims if c.metric == "net_burn")
    assert net.value_minor == 1_234_567


def test_parse_scenario_hire():
    text = "If we hire at GBP 6,000/month from next quarter, runway is 5 months."
    assert parse_scenario_hire_minor(text) == 600_000
