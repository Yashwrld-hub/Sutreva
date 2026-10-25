from pattern_intelligence import build_historical_pattern_matches, history_summary
from review_queue import ReviewItem


def _item(item_id, field, status, disposition, project_id, run_id):
    return ReviewItem(
        item_id=item_id,
        equipment_id="P-101",
        field=field,
        status=status,
        disposition=disposition,
        project_id=project_id,
        run_id=run_id,
    )


def test_historical_matches_use_closed_reviewed_cases_only():
    current = [{
        "field_name": "driver_type",
        "field": "Driver Type",
        "status": "NEEDS_REVIEW",
        "category": "EVIDENCE_GAP",
    }]
    history = [
        _item("1", "Driver Type", "NEEDS_REVIEW", "ACCEPTED", "P1", "R1"),
        _item("2", "Driver Type", "NEEDS_REVIEW", "ACCEPTED", "P2", "R2"),
        _item("3", "Driver Type", "NEEDS_REVIEW", "REJECTED", "P3", "R3"),
        _item("4", "Driver Type", "NEEDS_REVIEW", "OPEN", "P4", "R4"),
    ]
    matches = build_historical_pattern_matches(current, history)
    assert len(matches) == 1
    match = matches[0]
    assert match.similar_case_count == 3
    assert match.common_disposition == "ACCEPTED"
    assert match.disposition_counts == {"ACCEPTED": 2, "REJECTED": 1}
    assert match.prior_projects == 3
    assert match.prior_runs == 3
    assert match.pattern_strength == "MEDIUM"


def test_historical_matching_does_not_cross_status_or_field():
    current = [{
        "field_name": "driver_type",
        "field": "Driver Type",
        "status": "MISSING",
        "category": "MISSING_REQUIRED_DATA",
    }]
    history = [
        _item("1", "Driver Type", "MISMATCHED", "ACCEPTED", "P1", "R1"),
        _item("2", "Seal Plan", "MISSING", "ACCEPTED", "P2", "R2"),
    ]
    assert build_historical_pattern_matches(current, history) == []


def test_history_summary_is_aggregate_only():
    current = [{"field_name": "driver_type", "field": "Driver Type", "status": "MISSING"}]
    history = [_item(str(i), "Driver Type", "MISSING", "ACCEPTED", f"P{i}", f"R{i}") for i in range(1, 6)]
    matches = build_historical_pattern_matches(current, history)
    assert history_summary(matches) == {"fields_with_history": 1, "similar_cases": 5, "high_strength": 1}
