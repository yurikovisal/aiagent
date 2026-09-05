from datetime import date

from meza.rules.inventory import IncomingShipment, check_availability, days_of_cover, is_slow_moving


def test_scenario_1_master_prompt():
    """§52: required 1800kg, stock 700kg, incoming 500kg in 5 days (too late vs 3-day deadline)."""
    result = check_availability(
        material="Труба 40x40x2",
        required=1800,
        on_hand=700,
        needed_by=date(2026, 9, 8),
        incoming=[IncomingShipment(quantity=500, expected_at=date(2026, 9, 10), reference="PO-1")],
    )
    assert result.shortage == 1100
    assert result.status == "SHORTAGE"
    assert result.shortage_after_incoming == 1100
    assert result.notes  # explains why the incoming shipment doesn't help


def test_incoming_in_time_covers_shortage():
    result = check_availability(
        material="X", required=1000, on_hand=700, needed_by=date(2026, 9, 10),
        incoming=[IncomingShipment(quantity=500, expected_at=date(2026, 9, 9))],
    )
    assert result.status == "COVERED_BY_INCOMING"
    assert result.shortage_after_incoming == 0


def test_no_shortage_when_stock_sufficient():
    result = check_availability(material="X", required=100, on_hand=700)
    assert result.status == "OK"
    assert result.shortage == 0


def test_reserved_reduces_availability():
    result = check_availability(material="X", required=100, on_hand=200, reserved_by_others=150)
    assert result.available == 50
    assert result.shortage == 50


def test_days_of_cover():
    assert days_of_cover(100, 10) == 10.0
    assert days_of_cover(100, 0) is None


def test_slow_moving():
    assert is_slow_moving(120, threshold_days=90, quantity=5) is True
    assert is_slow_moving(30, threshold_days=90, quantity=5) is False
    assert is_slow_moving(None, threshold_days=90, quantity=5) is True
    assert is_slow_moving(120, threshold_days=90, quantity=0) is False
