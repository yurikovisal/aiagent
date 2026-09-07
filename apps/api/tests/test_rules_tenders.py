from datetime import date

from meza.rules.tenders import analyze_fit


def test_full_coverage_and_time_is_go_candidate():
    result = analyze_fit(
        required_work_centers=["CNC_METAL", "WELDING"],
        available_work_centers=["CNC_METAL", "WELDING", "POWDER_COATING"],
        submission_deadline=date(2026, 9, 20), today=date(2026, 9, 1),
    )
    assert result.capability_coverage == 1.0
    assert result.missing_work_centers == []
    assert result.verdict == "GO_CANDIDATE"


def test_missing_capability_lowers_fit():
    result = analyze_fit(
        required_work_centers=["CNC_METAL", "CNC_WOOD"],
        available_work_centers=["CNC_METAL"],
        submission_deadline=date(2026, 9, 20), today=date(2026, 9, 1),
    )
    assert result.missing_work_centers == ["CNC_WOOD"]
    assert result.capability_coverage == 0.5
    assert result.verdict in ("MARGINAL", "NO_GO_CANDIDATE")


def test_deadline_already_passed_is_no_go():
    result = analyze_fit(
        required_work_centers=["CNC_METAL"], available_work_centers=["CNC_METAL"],
        submission_deadline=date(2026, 8, 1), today=date(2026, 9, 1),
    )
    assert result.fit_score == 0.0
    assert result.verdict == "NO_GO_CANDIDATE"
    assert any("прошёл" in r for r in result.reasons)


def test_no_deadline_given_only_capability_matters():
    result = analyze_fit(required_work_centers=["CNC_METAL"], available_work_centers=["CNC_METAL"], submission_deadline=None, today=date(2026, 9, 1))
    assert result.lead_time_ok is True
    assert result.fit_score == 1.0
