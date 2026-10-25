from pilot_casepack import CASE_PACK, validate_pilot_record


def test_case_pack_has_distinct_industrial_scenarios():
    assert len(CASE_PACK) == 3
    assert len({case["case_id"] for case in CASE_PACK}) == 3


def test_nonmatched_without_evidence_is_rejected():
    issues = validate_pilot_record({"project_id": "P1", "run_id": "R1", "field_name": "pressure", "status": "MISMATCHED"})
    assert "missing:evidence_or_review" in issues


def test_unverified_approval_is_rejected():
    issues = validate_pilot_record({"project_id": "P1", "run_id": "R1", "field_name": "temp", "status": "CONFLICT", "evidence": {"page": 2}, "approved": True})
    assert "unsafe:unverified_approval" in issues
