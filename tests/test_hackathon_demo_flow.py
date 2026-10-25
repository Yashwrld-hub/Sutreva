import json
from pathlib import Path

import core
from engineering_intelligence import analyze_engineering_rows
from evaluation_flywheel import (
    curate_feedback_record,
    evaluate_snapshot,
    predictions_from_cases,
    record_curated_case,
)
from feedback_loop import build_feedback_record, record_feedback
from review_queue import build_review_queue, update_review_item


ROOT = Path(__file__).resolve().parents[1]
DEMO_PDF = ROOT / "sample_data" / "hackathon_pump_demo.pdf"
TEMPLATE = ROOT / "templates" / "centrifugal_pump_audit.json"


def test_demo_fixture_and_template_are_present_and_explicit():
    schema = core.load_schema(str(TEMPLATE))
    assert DEMO_PDF.is_file()
    assert schema["demo_file"] == "sample_data/hackathon_pump_demo.pdf"
    assert DEMO_PDF.stat().st_size > 1000


def test_demo_pdf_exposes_expected_review_triggers():
    schema = core.load_schema(str(TEMPLATE))
    pages = core.extract_pdf_pages_with_evidence(DEMO_PDF.read_bytes(), schema=schema)
    evidence = core.build_evidence_map(pages, schema)
    assert evidence["rated_power_kw"]["text"] == "Rated Power: 720 kW"
    assert evidence["shaft_material"]["text"] == "Shaft Material: A479-316"

    original_call = core.call_model
    core.call_model = lambda prompt, model_name=None: json.dumps({
        "rated_power_kw": 720,
        "npsha_available_m": 6.2,
        "casing_material": "A216WCB",
        "shaft_material": "A479-316",
        "driver_type": "Induction Motor",
    })
    try:
        rows, _, extracted, _ = core.run_pdf_audit_with_evidence(
            DEMO_PDF.read_bytes(), schema, include_intelligence=False
        )
    finally:
        core.call_model = original_call
    assert extracted["rated_power_kw"] == 720
    statuses = {row["field_name"]: row["status"] for row in rows}
    assert statuses["rated_power_kw"] == "OUT OF RANGE"
    assert statuses["shaft_material"] == "MISMATCHED"


def test_demo_rehearsal_engineering_review_and_evaluation_loop(tmp_path):
    schema = core.load_schema(str(TEMPLATE))
    result = {
        "identifier": DEMO_PDF.name,
        "rows": [
            {
                "field": "Rated Power",
                "field_name": "rated_power_kw",
                "status": "OUT OF RANGE",
                "review_reason": "Numeric value is outside the configured limit.",
                "extracted_value": 720,
                "evidence": {"page": 1, "line": 8, "text": "Rated Power: 720 kW"},
                "rule": "max 700",
                "ai_context": {
                    "provider": "nebius_nemotron_fixture",
                    "model": "fixture-model",
                    "prompt_version": "sutreva.reasoning.v2",
                    "assessment": "SUPPORTED",
                    "risk": "HIGH",
                    "reason": "Fixture-backed evidence supports the extracted value.",
                    "evidence_refs": [{"page": 1, "line": 8, "quote": "Rated Power: 720 kW"}],
                },
            },
        ],
        "summary": {"MATCHED": 0, "MISSING": 0, "MISMATCHED": 0, "OUT OF RANGE": 1, "TOTAL": 1},
        "error": None,
        "intelligence": {
            "provider": "nebius_nemotron_fixture",
            "model": "fixture-model",
            "prompt_version": "sutreva.reasoning.v2",
            "field_assessments": [{
                "field_name": "rated_power_kw",
                "assessment": "SUPPORTED",
                "risk": "HIGH",
                "reason": "Fixture-backed evidence supports the extracted value.",
                "evidence_refs": [{"page": 1, "line": 8, "quote": "Rated Power: 720 kW"}],
            }],
        },
    }
    rows = result["rows"]
    report = analyze_engineering_rows(rows, schema, ai_assessments=result["intelligence"]["field_assessments"])
    assert report.exception_count == 1

    queue = build_review_queue([result], {"project_id": "DEMO", "run_id": "RUN-54", "document_revision": "DEMO-1"})
    assert queue
    closed = update_review_item(queue[0], disposition="ACCEPTED", comment="Confirmed against the cited demo evidence.")
    feedback = build_feedback_record(
        closed,
        disposition="ACCEPTED",
        reviewer_comment=closed.reviewer_comment,
        feedback_label="CONFIRMED_FINDING",
        reviewer_id="demo-reviewer",
        reviewer_name="demo-reviewer",
        reviewer_role="REVIEWER",
    )
    db = tmp_path / "demo.sqlite3"
    record_feedback(feedback, db_path=str(db))
    case = curate_feedback_record(
        feedback,
        gold_status=closed.status,
        gold_assessment="SUPPORTED",
        gold_risk="HIGH",
        gold_evidence_refs=[closed.evidence],
    )
    record_curated_case(case, db_path=str(db))
    evaluation = evaluate_snapshot(
        [case],
        predictions_from_cases([case]),
        model_version="fixture-model",
        prompt_version="fixture-prompt",
    )
    assert evaluation.regression_passed
