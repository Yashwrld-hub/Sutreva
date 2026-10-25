from core import (
    build_evidence_index,
    build_evidence_map,
    compare_against_schema,
    find_field_evidence,
)


def test_build_evidence_index_preserves_page_labels():
    result = build_evidence_index([{"page": 1, "text": "Material: SS316"}, {"page": 2, "text": "Pressure: 10 bar"}])
    assert "[PAGE 1]" in result
    assert "[PAGE 2]" in result


def test_compare_accepts_field_evidence():
    schema = {"fields": [{"field_name": "material", "label": "Material", "acceptable_values": ["SS316"]}]}
    rows = compare_against_schema({"material": "SS316"}, schema, {"material": {"page": 1, "quote": "Material: SS316"}})
    assert rows[0]["evidence"]["page"] == 1



def test_find_field_evidence_returns_page_and_line():
    pages = [{"page": 2, "text": "Material: Stainless Steel\nMax Pressure: 12 bar"}]
    field = {"field_name": "material", "label": "Material"}
    evidence = find_field_evidence(pages, field)
    assert evidence["page"] == 2
    assert evidence["line"] == 1
    assert evidence["source"] == "label_match"


def test_build_evidence_map_keeps_missing_evidence_explicit():
    pages = [{"page": 1, "text": "Material: Stainless Steel"}]
    schema = {"fields": [
        {"field_name": "material", "label": "Material"},
        {"field_name": "pressure", "label": "Max Pressure"},
    ]}
    evidence = build_evidence_map(pages, schema)
    assert evidence["material"]["page"] == 1
    assert evidence["pressure"] is None


def test_unverified_value_requires_review_when_enabled():
    schema = {"fields": [{"field_name": "pressure", "label": "Pressure", "max_value": 12}]}
    rows = compare_against_schema(
        {"pressure": 10}, schema,
        {"pressure": {"page": 1, "text": "Pressure: 8 bar"}},
        verify_evidence=True,
    )
    assert rows[0]["status"] == "NEEDS_REVIEW"


def test_verified_value_remains_matched_when_enabled():
    schema = {"fields": [{"field_name": "pressure", "label": "Pressure", "max_value": 12}]}
    rows = compare_against_schema(
        {"pressure": 10}, schema,
        {"pressure": {"page": 1, "text": "Pressure: 10 bar"}},
        verify_evidence=True,
    )
    assert rows[0]["status"] == "MATCHED"
