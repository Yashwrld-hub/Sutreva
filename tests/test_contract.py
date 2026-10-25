from conflict_detection import detect_conflicts
from extraction_contract import (
    EvidenceRef,
    ExtractionRecord,
    records_from_extracted,
    validate_record,
)


def test_valid_record():
    record = ExtractionRecord("pressure", 12, confidence=0.9, evidence=EvidenceRef(page=1, line=2))
    assert validate_record(record) == []

def test_invalid_confidence_and_page():
    record = ExtractionRecord("pressure", 12, confidence=1.2, evidence=EvidenceRef(page=0))
    errors = validate_record(record)
    assert "confidence must be between 0 and 1" in errors
    assert "evidence page must be 1 or greater" in errors

def test_records_follow_schema():
    schema = {"fields": [{"field_name": "pressure", "unit": "bar"}]}
    records = records_from_extracted({"pressure": 12}, schema, {"pressure": {"page": 2, "line": 4}})
    assert records[0].field_name == "pressure"
    assert records[0].target_unit == "bar"
    assert records[0].evidence.page == 2


def test_detects_conflicting_values_for_same_field():
    records = [
        ExtractionRecord("discharge_pressure", 12, evidence=EvidenceRef(page=1)),
        ExtractionRecord("discharge_pressure", 14, evidence=EvidenceRef(page=3)),
    ]
    conflicts = detect_conflicts(records)
    assert len(conflicts) == 1
    assert conflicts[0].field_name == "discharge_pressure"
    assert set(conflicts[0].values) == {12, 14}


def test_ignores_duplicate_values_and_missing_values():
    records = [
        ExtractionRecord("temperature", 180),
        ExtractionRecord("temperature", 180),
        ExtractionRecord("temperature", None),
    ]
    assert detect_conflicts(records) == []
