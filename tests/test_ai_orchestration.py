import json

from ai_orchestration import run_engineering_reasoning


SCHEMA = {
    "template_name": "Test",
    "fields": [
        {"field_name": "material", "label": "Material", "expected_value": "Steel"},
        {"field_name": "pressure", "label": "Pressure", "max_value": 10},
    ],
}

ROWS = [
    {
        "field_name": "material",
        "status": "MATCHED",
        "extracted_value": "Steel",
        "evidence": {"page": 1, "text": "Material: Steel"},
        "rule": {"type": "expected_value", "value": "Steel"},
    },
    {
        "field_name": "pressure",
        "status": "OUT OF RANGE",
        "extracted_value": 15,
        "evidence": {"page": 2, "text": "Pressure: 15 bar"},
        "rule": {"type": "max_value", "value": 10},
    },
]


def test_reasoning_pass_returns_structured_advisory_result():
    payload = {
        "overall_flag": "REVIEW",
        "document_flags": ["Pressure exceeds configured maximum."],
        "field_assessments": [
            {"field_name": "material", "assessment": "SUPPORTED", "risk": "LOW", "reason": "Evidence states Steel.", "evidence_refs": [{"page": 1, "line": 1, "quote": "Material: Steel"}]},
            {"field_name": "pressure", "assessment": "SUPPORTED", "risk": "HIGH", "reason": "Source evidence states 15 bar.", "evidence_refs": [{"page": 2, "line": 1, "quote": "Pressure: 15 bar"}]},
        ],
    }

    class FakeProvider:
        name = "fake_nemotron"

    result = run_engineering_reasoning(
        ROWS,
        SCHEMA,
        {"material": "Steel", "pressure": 15},
        model_name="test-model",
        generate=lambda prompt, model: json.dumps(payload),
    )

    assert result.enabled is True
    assert result.status == "COMPLETED"
    assert result.overall_flag == "REVIEW"
    assert len(result.field_assessments) == 2
    assert result.field_assessments[1]["risk"] == "HIGH"
    assert result.field_assessments[1]["evidence_refs"][0]["page"] == 2


def test_reasoning_failure_is_non_authoritative(monkeypatch):
    class FakeProvider:
        name = "fake_nemotron"

    monkeypatch.setattr("ai_orchestration.get_model_provider", lambda: FakeProvider())
    result = run_engineering_reasoning(
        ROWS,
        SCHEMA,
        {"material": "Steel", "pressure": 15},
        generate=lambda prompt, model: "not json",
    )

    assert result.status == "FAILED"
    assert result.error
    assert result.overall_flag == "NONE"


def test_reasoning_result_does_not_change_authoritative_rows():
    payload = {
        "overall_flag": "NONE",
        "document_flags": [],
        "field_assessments": [
            {"field_name": "pressure", "assessment": "SUPPORTED", "risk": "LOW", "reason": "Evidence supports the value.", "evidence_refs": []},
        ],
    }
    result = run_engineering_reasoning(
        ROWS,
        SCHEMA,
        {"material": "Steel", "pressure": 15},
        generate=lambda prompt, model: json.dumps(payload),
    )
    assert ROWS[1]["status"] == "OUT OF RANGE"
    assert result.overall_flag == "NONE"


def test_pdf_audit_api_keeps_legacy_four_value_contract(monkeypatch):
    import core
    monkeypatch.setattr(core, "extract_pdf_pages_with_evidence", lambda *args, **kwargs: [])
    monkeypatch.setattr(core, "build_evidence_index", lambda pages: "text")
    monkeypatch.setattr(core, "build_evidence_map", lambda pages, schema: {})
    monkeypatch.setattr(
        core,
        "run_audit",
        lambda *args, **kwargs: ([], "{}", {}),
    )
    result = core.run_pdf_audit_with_evidence(b"pdf", SCHEMA)
    assert len(result) == 4


def test_pdf_audit_can_append_intelligence_without_changing_core_rows(monkeypatch):
    import core
    sentinel = object()
    monkeypatch.setattr(core, "extract_pdf_pages_with_evidence", lambda *args, **kwargs: [])
    monkeypatch.setattr(core, "build_evidence_index", lambda pages: "text")
    monkeypatch.setattr(core, "build_evidence_map", lambda pages, schema: {})
    monkeypatch.setattr(core, "run_audit", lambda *args, **kwargs: ([], "{}", {}))
    monkeypatch.setattr(core, "run_engineering_reasoning", lambda *args, **kwargs: sentinel)
    result = core.run_pdf_audit_with_evidence(b"pdf", SCHEMA, include_intelligence=True)
    assert len(result) == 5
    assert result[-1] is sentinel


def test_reasoning_prompt_contains_evidence_reference_contract():
    from ai_orchestration import _build_reasoning_prompt
    prompt = _build_reasoning_prompt(ROWS, SCHEMA, {"material": "Steel", "pressure": 15})
    assert '"evidence_refs"' in prompt
    assert "Never invent page/line numbers" in prompt


def test_malformed_evidence_reference_is_dropped():
    from ai_orchestration import _normalize_result
    overall, flags, assessments = _normalize_result({
        "overall_flag": "REVIEW",
        "document_flags": [],
        "field_assessments": [{
            "field_name": "pressure",
            "assessment": "SUPPORTED",
            "risk": "LOW",
            "reason": "ok",
            "evidence_refs": [
                {"page": 2, "line": 3, "quote": "Pressure: 15 bar"},
                {"page": None, "line": 4, "quote": "bad"},
            ],
        }],
    })
    assert overall == "REVIEW"
    assert assessments[0]["evidence_refs"] == [{"page": 2, "line": 3, "quote": "Pressure: 15 bar"}]
