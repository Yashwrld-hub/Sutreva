from engineering_intelligence import analyze_engineering_rows


SCHEMA = {
    "fields": [
        {"field_name": "power_kw", "label": "Power", "required": True, "max_value": 700},
        {"field_name": "driver_type", "label": "Driver Type", "required": True, "acceptable_values": ["Induction Motor"]},
        {"field_name": "seal_plan", "label": "Seal Plan", "required": True, "expected_value": "Plan 53B"},
    ]
}


def test_engineering_report_classifies_exceptions_without_changing_status():
    rows = [
        {"field_name": "power_kw", "field": "Power", "status": "OUT OF RANGE", "extracted_value": 900, "evidence": {"page": 2}},
        {"field_name": "driver_type", "field": "Driver Type", "status": "NEEDS_REVIEW", "extracted_value": "Induction Motor", "evidence": {"page": 3}},
        {"field_name": "seal_plan", "field": "Seal Plan", "status": "MISSING", "extracted_value": None, "evidence": {}},
    ]
    report = analyze_engineering_rows(rows, SCHEMA)
    assert report.exception_count == 3
    assert report.critical_count == 1
    assert report.high_count == 1
    assert report.medium_count == 1
    assert report.blocking is True
    assert {e["category"] for e in report.exceptions} == {
        "LIMIT_EXCEEDED", "EVIDENCE_GAP", "MISSING_REQUIRED_DATA"
    }
    assert [r["status"] for r in rows] == ["OUT OF RANGE", "NEEDS_REVIEW", "MISSING"]


def test_ai_high_risk_can_raise_exception_severity_but_not_status():
    rows = [
        {"field_name": "driver_type", "field": "Driver Type", "status": "NEEDS_REVIEW", "extracted_value": "Induction Motor", "evidence": {"page": 4}},
    ]
    report = analyze_engineering_rows(rows, SCHEMA, ai_assessments=[{
        "field_name": "driver_type",
        "assessment": "AMBIGUOUS",
        "risk": "HIGH",
    }])
    exc = report.exceptions[0]
    assert exc["severity"] == "HIGH"
    assert exc["ai_assessment"] == "AMBIGUOUS"
    assert exc["ai_risk"] == "HIGH"
    assert exc["status"] == "NEEDS_REVIEW"
