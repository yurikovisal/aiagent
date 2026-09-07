from meza.rules.marketing import compute_campaign_performance


def test_cost_per_lead_and_conversion():
    perf = compute_campaign_performance(campaign_id=1, name="Instagram", budget=300_000, spent=120_000, leads_generated=6, leads_converted=2)
    assert perf.cost_per_lead == 20_000
    assert round(perf.conversion_rate, 4) == round(2 / 6, 4)
    assert round(perf.budget_utilization, 4) == 0.4


def test_no_leads_yields_none_not_zero_division():
    perf = compute_campaign_performance(campaign_id=1, name="X", budget=100, spent=50, leads_generated=0, leads_converted=0)
    assert perf.cost_per_lead is None
    assert perf.conversion_rate is None


def test_zero_budget_utilization_is_none():
    perf = compute_campaign_performance(campaign_id=1, name="X", budget=0, spent=50, leads_generated=5, leads_converted=1)
    assert perf.budget_utilization is None
