from domain_rules import domain_context_for_field, get_domain_profile, infer_profile_id
from engineering_intelligence import analyze_engineering_rows


def test_profile_resolution_uses_explicit_template_metadata():
    schema = {"equipment_profile": "centrifugal_pump", "template_name": "Anything Else", "fields": []}
    assert infer_profile_id(schema) == "centrifugal_pump"
    assert get_domain_profile(schema).label == "Centrifugal Pump"


def test_profile_resolution_falls_back_to_template_name():
    schema = {"template_name": "Mechanical Seal Audit", "fields": []}
    assert infer_profile_id(schema) == "mechanical_seal"


def test_domain_context_is_field_specific():
    schema = {"equipment_profile": "centrifugal_pump", "fields": []}
    ctx = domain_context_for_field(schema, "npsha_available_m")
    assert ctx["domain_role"] == "Suction-side margin"
    assert ctx["domain_priority"] == "CRITICAL"


def test_engineering_exception_carries_domain_context_without_changing_status():
    schema = {
        "equipment_profile": "mechanical_seal",
        "fields": [{"field_name": "api_plan", "label": "API Plan", "required": True, "expected_value": "Plan 53B"}],
    }
    rows = [{"field_name": "api_plan", "field": "API Plan", "status": "MISMATCHED", "extracted_value": "Plan 53", "evidence": {"page": 4}}]
    report = analyze_engineering_rows(rows, schema)
    exc = report.exceptions[0]
    assert report.domain_profile_id == "mechanical_seal"
    assert exc["domain_role"] == "Seal support plan"
    assert exc["domain_priority"] == "CRITICAL"
    assert exc["status"] == "MISMATCHED"
