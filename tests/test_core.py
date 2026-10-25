import json

import pytest

from core import (
    compare_against_schema,
    list_templates,
    load_schema,
    parse_json_safely,
    save_template,
    slugify,
)


# ---------- slugify ----------

def test_slugify_basic():
    assert slugify("Lube Oil List Audit") == "lube_oil_list_audit"


def test_slugify_strips_punctuation():
    assert slugify("Viscosity Grade!!") == "viscosity_grade"


def test_slugify_collapses_whitespace():
    assert slugify("  weird   spacing  ") == "weird_spacing"


def test_slugify_never_returns_empty():
    assert slugify("???") == "template"


# ---------- parse_json_safely ----------

def test_parse_json_plain():
    assert parse_json_safely('{"a": 1}') == {"a": 1}


def test_parse_json_strips_markdown_fences():
    text = '```json\n{"a": 1}\n```'
    assert parse_json_safely(text) == {"a": 1}


def test_parse_json_handles_short_preamble():
    text = 'Here is the requested JSON:\n{"a": 1}'
    assert parse_json_safely(text) == {"a": 1}


def test_parse_json_rejects_empty_model_output_with_actionable_error():
    with pytest.raises(ValueError, match="empty response"):
        parse_json_safely("   ")


def test_parse_json_rejects_non_object_at_audit_boundary(monkeypatch):
    from core import run_audit
    monkeypatch.setattr("core.call_model", lambda prompt: '[{"a": 1}]')
    with pytest.raises(ValueError, match="JSON object"):
        run_audit("text", SIMPLE_SCHEMA)


def test_run_audit_retries_once_after_malformed_json(monkeypatch):
    import core
    responses = iter([
        "This is not JSON",
        '{"material": "Steel", "grade": "A276-410", "max_temp": 180, '
        '"min_pressure": 5, "notes": "ok"}',
    ])
    prompts = []

    def fake_call(prompt):
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(core, "call_model", fake_call)
    rows, _, extracted = core.run_audit("text", SIMPLE_SCHEMA)

    assert len(prompts) == 2
    assert "previous response could not be parsed" in prompts[1]
    assert extracted["material"] == "Steel"
    assert next(row for row in rows if row["field_name"] == "material")["status"] == "MATCHED"


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_json_safely("not json at all")


# ---------- compare_against_schema ----------

SIMPLE_SCHEMA = {
    "template_name": "Test Template",
    "fields": [
        {"field_name": "material", "label": "Material", "required": True,
         "acceptable_values": ["Steel", "Aluminum"]},
        {"field_name": "grade", "label": "Grade", "required": True,
         "expected_value": "A276-410"},
        {"field_name": "max_temp", "label": "Max Temp", "required": True,
         "max_value": 200},
        {"field_name": "min_pressure", "label": "Min Pressure", "required": True,
         "min_value": 5},
        {"field_name": "notes", "label": "Notes", "required": False},
    ],
}


def test_missing_field_is_flagged():
    rows = compare_against_schema({}, SIMPLE_SCHEMA)
    assert all(r["status"] == "MISSING" for r in rows)


def test_acceptable_values_substring_match():
    # Real-world case: "Steel vs Steel" should still match "Steel"
    rows = compare_against_schema({"material": "Steel vs Steel"}, SIMPLE_SCHEMA)
    material_row = next(r for r in rows if r["field"] == "Material")
    assert material_row["status"] == "MATCHED"


def test_acceptable_values_no_match():
    rows = compare_against_schema({"material": "Ceramic"}, SIMPLE_SCHEMA)
    material_row = next(r for r in rows if r["field"] == "Material")
    assert material_row["status"] == "MISMATCHED"


def test_expected_value_match_and_mismatch():
    rows_ok = compare_against_schema({"grade": "A276-410"}, SIMPLE_SCHEMA)
    rows_bad = compare_against_schema({"grade": "Wrong Grade"}, SIMPLE_SCHEMA)
    assert next(r for r in rows_ok if r["field"] == "Grade")["status"] == "MATCHED"
    assert next(r for r in rows_bad if r["field"] == "Grade")["status"] == "MISMATCHED"


def test_max_value_boundary():
    rows_ok = compare_against_schema({"max_temp": 200}, SIMPLE_SCHEMA)
    rows_over = compare_against_schema({"max_temp": 201}, SIMPLE_SCHEMA)
    assert next(r for r in rows_ok if r["field"] == "Max Temp")["status"] == "MATCHED"
    assert next(r for r in rows_over if r["field"] == "Max Temp")["status"] == "OUT OF RANGE"


def test_min_value_boundary():
    rows_ok = compare_against_schema({"min_pressure": 5}, SIMPLE_SCHEMA)
    rows_under = compare_against_schema({"min_pressure": 4.9}, SIMPLE_SCHEMA)
    assert next(r for r in rows_ok if r["field"] == "Min Pressure")["status"] == "MATCHED"
    assert next(r for r in rows_under if r["field"] == "Min Pressure")["status"] == "OUT OF RANGE"


def test_non_numeric_value_on_numeric_field_is_mismatched_not_crashed():
    rows = compare_against_schema({"max_temp": "not a number"}, SIMPLE_SCHEMA)
    assert next(r for r in rows if r["field"] == "Max Temp")["status"] == "MISMATCHED"


def test_field_with_no_rule_defaults_to_matched_when_present():
    rows = compare_against_schema({"notes": "anything at all"}, SIMPLE_SCHEMA)
    assert next(r for r in rows if r["field"] == "Notes")["status"] == "MATCHED"


# ---------- load_schema validation ----------

def test_load_schema_valid_file(tmp_path):
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(SIMPLE_SCHEMA))
    loaded = load_schema(str(path))
    assert loaded["template_name"] == "Test Template"
    assert len(loaded["fields"]) == 5


def test_load_schema_broken_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError):
        load_schema(str(path))


def test_load_schema_missing_fields_key_raises(tmp_path):
    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps({"template_name": "No Fields"}))
    with pytest.raises(ValueError):
        load_schema(str(path))


def test_load_schema_field_missing_label_raises(tmp_path):
    path = tmp_path / "badfield.json"
    path.write_text(json.dumps({"template_name": "Bad Field", "fields": [{"unit": "kg"}]}))
    with pytest.raises(ValueError):
        load_schema(str(path))


# ---------- save_template + list_templates round trip ----------

def test_save_and_discover_template(tmp_path):
    fields = [{"field_name": "x", "label": "X", "required": True}]
    path = save_template("My New Template", fields, folder=str(tmp_path))

    assert path.endswith("my_new_template.json")

    found = list_templates(str(tmp_path))
    assert "My New Template" in found
    assert found["My New Template"] == path


def test_save_template_overwrites_on_same_name(tmp_path):
    fields_v1 = [{"field_name": "x", "label": "X"}]
    fields_v2 = [{"field_name": "x", "label": "X"}, {"field_name": "y", "label": "Y"}]

    path1 = save_template("Same Name", fields_v1, folder=str(tmp_path))
    path2 = save_template("Same Name", fields_v2, folder=str(tmp_path))

    assert path1 == path2  # same file, i.e. a real edit, not a duplicate
    reloaded = load_schema(path2)
    assert len(reloaded["fields"]) == 2


def test_save_template_rejects_empty_name(tmp_path):
    with pytest.raises(ValueError):
        save_template("", [{"field_name": "x", "label": "X"}], folder=str(tmp_path))


def test_save_template_rejects_no_fields(tmp_path):
    with pytest.raises(ValueError):
        save_template("Valid Name", [], folder=str(tmp_path))


def test_list_templates_skips_malformed_files(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"template_name": "Good One", "fields": []}))
    bad = tmp_path / "bad.json"
    bad.write_text("not json")

    found = list_templates(str(tmp_path))
    assert "Good One" in found
    assert len(found) == 1  # the broken file was silently skipped, not crashed on

def test_result_contains_traceability_ready_metadata():
    rows = compare_against_schema({"max_temp": 201}, SIMPLE_SCHEMA)
    row = next(r for r in rows if r["field"] == "Max Temp")
    assert row["field_name"] == "max_temp"
    assert row["rule"] == {"type": "max_value", "value": 200}
    assert row["evidence"] is None
    assert "review_reason" in row


def test_compare_against_schema_normalizes_inline_units():
    schema = {
        "template_name": "Unit Test",
        "fields": [{"field_name": "pressure", "label": "Pressure", "unit": "bar", "max_value": 10, "required": True}],
    }
    rows = compare_against_schema({"pressure": "1000 kPa"}, schema)
    row = rows[0]
    assert row["status"] == "MATCHED"
    assert row["normalized_value"] == pytest.approx(10.0)
    assert row["unit_normalization"]["converted"] is True


def test_compare_against_schema_normalizes_evidence_units():
    schema = {
        "template_name": "Unit Test",
        "fields": [{"field_name": "flow", "label": "Flow", "unit": "m3/h", "max_value": 60, "required": True}],
    }
    rows = compare_against_schema(
        {"flow": 1000},
        schema,
        evidence={"flow": {"text": "Flow: 1000 L/min", "page": 1, "line": 2}},
        verify_evidence=True,
    )
    row = rows[0]
    assert row["status"] == "MATCHED"
    assert row["normalized_value"] == pytest.approx(60.0)
    assert row["source_unit"] == "L/min"


def test_conflict_between_model_and_deterministic_override_requires_review(monkeypatch):
    schema = {
        "template_name": "Conflict Test",
        "fields": [{
            "field_name": "material", "label": "Material", "required": True,
            "acceptable_values": ["A276-410", "A479-316"], "extraction_aliases": ["SHAFT"],
        }],
    }
    monkeypatch.setattr("core.call_model", lambda prompt: '{"material": "A479-316"}')
    rows, _, extracted = __import__("core").run_audit("SHAFT A276-410", schema)
    assert extracted["material"] == "A276-410"
    assert rows[0]["status"] == "NEEDS_REVIEW"
    assert rows[0]["conflict"] is not None
    assert rows[0]["extraction_record"]["field_name"] == "material"


def test_live_compare_path_calls_normalize_numeric_value(monkeypatch):
    import core
    calls = []
    original = core.normalize_numeric_value

    def wrapped(value, source_unit, target_unit):
        calls.append((value, source_unit, target_unit))
        return original(value, source_unit, target_unit)

    monkeypatch.setattr(core, "normalize_numeric_value", wrapped)
    schema = {
        "template_name": "Unit Test",
        "fields": [{"field_name": "pressure", "label": "Pressure", "unit": "bar", "max_value": 10, "required": True}],
    }
    rows = core.compare_against_schema({"pressure": "1000 kPa"}, schema)
    assert rows[0]["status"] == "MATCHED"
    assert calls


def test_run_audit_attaches_live_extraction_contract(monkeypatch):
    import core
    schema = {
        "template_name": "Contract Integration",
        "fields": [{"field_name": "pressure", "label": "Pressure", "unit": "bar", "max_value": 10, "required": True}],
    }
    monkeypatch.setattr(core, "call_model", lambda prompt: '{"pressure": "1000 kPa"}')
    rows, _, _ = core.run_audit("Pressure: 1000 kPa", schema)
    record = rows[0]["extraction_record"]
    assert record["field_name"] == "pressure"
    assert record["target_unit"] == "bar"
    assert record["normalized_value"] == pytest.approx(10.0)
