from meza.rules.scoring import dedupe, impact_from_amount, risk_score, severity_from_score, urgency_from_days


def test_risk_score_bounds():
    assert 0 <= risk_score("LOW", 0, 0) <= 100
    assert risk_score("CRITICAL", 1, 1) > risk_score("LOW", 0, 0)


def test_severity_thresholds():
    assert severity_from_score(90) == "CRITICAL"
    assert severity_from_score(60) == "HIGH"
    assert severity_from_score(40) == "MEDIUM"
    assert severity_from_score(10) == "LOW"


def test_urgency_from_days():
    assert urgency_from_days(0) == 1.0
    assert urgency_from_days(-5) == 1.0
    assert urgency_from_days(None) == 0.3
    assert 0 < urgency_from_days(7, horizon_days=14) < 1


def test_impact_from_amount_caps_at_one():
    assert impact_from_amount(1_000_000_000, reference=10_000_000) == 1.0
    assert impact_from_amount(0) == 0.0


def test_dedupe_keeps_highest_score():
    items = [
        {"entity_type": "order", "entity_id": 1, "rule_key": "x", "score": 10},
        {"entity_type": "order", "entity_id": 1, "rule_key": "x", "score": 90},
    ]
    out = dedupe(items)
    assert len(out) == 1
    assert out[0]["score"] == 90
