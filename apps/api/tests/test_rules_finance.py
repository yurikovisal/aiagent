from meza.rules.finance import compute_margin, explain_variance


def test_scenario_2_master_prompt():
    """§53: revenue 18,500,000 / planned 9,200,000 / actual 10,570,000."""
    planned = {"MATERIAL": 5_000_000, "LABOR": 2_500_000, "SUBCONTRACTOR": 1_000_000,
               "LOGISTICS": 400_000, "INSTALLATION": 200_000, "OTHER": 100_000}
    actual = {"MATERIAL": 6_100_000, "LABOR": 2_670_000, "SUBCONTRACTOR": 1_000_000,
              "LOGISTICS": 500_000, "INSTALLATION": 200_000, "OTHER": 100_000}
    result = compute_margin(18_500_000, planned, actual)
    assert result.planned_total == 9_200_000
    assert result.actual_total == 10_570_000
    assert result.cost_variance == 1_370_000
    assert round(result.cost_variance_pct, 1) == 14.9
    assert result.planned_gross_profit == 9_300_000
    assert result.actual_gross_profit == 7_930_000
    text = explain_variance(result)
    assert "перерасход" in text.lower()


def test_zero_revenue_margin_is_none():
    result = compute_margin(0, {"MATERIAL": 100}, {"MATERIAL": 150})
    assert result.planned_margin is None
    assert result.actual_margin is None


def test_unknown_category_folds_into_other():
    result = compute_margin(1000, {"WEIRD_CATEGORY": 100}, {})
    other = next(c for c in result.categories if c.category == "OTHER")
    assert other.planned == 100


def test_no_variance_message():
    result = compute_margin(1000, {"MATERIAL": 100}, {"MATERIAL": 100})
    assert result.cost_variance == 0
    assert "соответствуют плану" in explain_variance(result)
