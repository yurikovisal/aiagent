from datetime import date

from meza.rules.production import StageNode, propagate_delay, remaining_duration_days


def _stages():
    return [
        StageNode(1, "CNC", "CNC_METAL", 1, 2, date(2026, 9, 1), date(2026, 9, 3)),
        StageNode(2, "Welding", "WELDING", 2, 2, date(2026, 9, 3), date(2026, 9, 5)),
        StageNode(3, "Powder", "POWDER_COATING", 3, 1, date(2026, 9, 5), date(2026, 9, 6),
                  slot_based=True, slot_interval_days=3),
        StageNode(4, "Assembly", "ASSEMBLY", 4, 2, date(2026, 9, 6), date(2026, 9, 8)),
    ]


def test_scenario_3_master_prompt():
    """§54: CNC +2 days -> downstream impact including slot-based powder coating batch miss."""
    result = propagate_delay(_stages(), origin_stage_id=1, delay_days=2, deadline=date(2026, 9, 9))
    assert result.chain[0].delay_days == 2
    assert result.chain[1].delay_days == 2  # welding inherits
    assert result.chain[2].delay_days == 3  # powder coating: missed slot, +1 extra day
    assert result.new_completion == date(2026, 9, 11)
    assert result.deadline_missed_by_days == 2


def test_no_delay_is_noop():
    result = propagate_delay(_stages(), origin_stage_id=1, delay_days=0)
    assert result.final_delay_days == 0


def test_linear_fallback_without_explicit_dependencies():
    stages = [StageNode(i, f"S{i}", "WC", i, 1) for i in range(1, 4)]
    result = propagate_delay(stages, origin_stage_id=1, delay_days=1)
    assert {s.stage_id: s.delay_days for s in result.chain} == {1: 1, 2: 1, 3: 1}


def test_remaining_duration_skips_done_stages():
    stages = _stages()
    stages[0].status = "DONE"
    assert remaining_duration_days(stages) == 2 + 1 + 2  # welding + powder + assembly
