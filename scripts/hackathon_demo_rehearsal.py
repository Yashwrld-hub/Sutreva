"""Offline end-to-end rehearsal for the Sutreva hackathon demo path.

This script uses the real synthetic PDF fixture, evidence extractor, deterministic
engineering comparison, reasoning contract, review queue, feedback capture, and
evaluation flywheel. Model calls are replaced with deterministic fixtures, so the
script never spends API credits and never presents a simulated run as live inference.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai_orchestration
import core
from evaluation_flywheel import curate_feedback_record, evaluate_snapshot, predictions_from_cases, record_curated_case
from feedback_loop import build_feedback_record, record_feedback
from engineering_intelligence import analyze_engineering_rows
from review_queue import build_review_queue, update_review_item

PDF = ROOT / "sample_data" / "hackathon_pump_demo.pdf"
TEMPLATE = ROOT / "templates" / "centrifugal_pump_audit.json"

EXTRACTED = {
    "rated_power_kw": 720,
    "npsha_available_m": 6.2,
    "casing_material": "A216WCB",
    "shaft_material": "A479-316",
    "driver_type": "Induction Motor",
}


class _FakeProvider:
    name = "nebius_nemotron_fixture"

    def __init__(self, reasoning_payload: str):
        self.reasoning_payload = reasoning_payload

    def generate(self, prompt: str, model_name: str = "fixture-model") -> str:
        return self.reasoning_payload


def main() -> int:
    schema = core.load_schema(str(TEMPLATE))
    pdf_bytes = PDF.read_bytes()

    pages = core.extract_pdf_pages_with_evidence(pdf_bytes, schema=schema)
    evidence_map = core.build_evidence_map(pages, schema)

    reasoning_payload = json.dumps({
        "overall_flag": "REVIEW",
        "document_flags": [
            "Rated power exceeds the configured maximum.",
            "Shaft material does not match the configured expected value.",
        ],
        "field_assessments": [
            {
                "field_name": field_name,
                "assessment": "SUPPORTED",
                "risk": "HIGH" if field_name in {"rated_power_kw", "shaft_material"} else "LOW",
                "reason": f"Fixture-backed reasoning for {field_name}.",
                "evidence_refs": [
                    {
                        "page": evidence_map[field_name]["page"],
                        "line": evidence_map[field_name]["line"],
                        "quote": evidence_map[field_name]["text"],
                    }
                ] if evidence_map.get(field_name) else [],
            }
            for field_name in EXTRACTED
        ],
    })

    original_call_model = core.call_model
    original_provider = ai_orchestration.get_model_provider
    core.call_model = lambda prompt, model_name=None: json.dumps(EXTRACTED)
    ai_orchestration.get_model_provider = lambda: _FakeProvider(reasoning_payload)

    try:
        rows, raw, extracted, pages, intelligence = core.run_pdf_audit_with_evidence(
            pdf_bytes, schema, include_intelligence=True
        )
    finally:
        core.call_model = original_call_model
        ai_orchestration.get_model_provider = original_provider

    assert extracted == EXTRACTED, extracted
    status_by_field = {row["field_name"]: row["status"] for row in rows}
    assert status_by_field["rated_power_kw"] == "OUT OF RANGE"
    assert status_by_field["shaft_material"] == "MISMATCHED"
    assert status_by_field["npsha_available_m"] == "MATCHED"
    assert intelligence.status == "COMPLETED"
    assert all(a["evidence_refs"] for a in intelligence.field_assessments)

    group = {
        "identifier": PDF.name,
        "rows": rows,
        "raw_output": raw,
        "summary": core.audit_summary(rows),
        "error": None,
        "intelligence": intelligence.to_dict(),
    }
    reports = analyze_engineering_rows(rows, schema, ai_assessments=intelligence.field_assessments)
    assert reports.exception_count >= 2

    ai_by_field = {a["field_name"]: a for a in intelligence.field_assessments}
    for row in group["rows"]:
        if row["field_name"] in ai_by_field:
            row["ai_context"] = {
                "provider": intelligence.provider,
                "model": intelligence.model,
                "prompt_version": intelligence.prompt_version,
                "assessment": ai_by_field[row["field_name"]]["assessment"],
                "risk": ai_by_field[row["field_name"]]["risk"],
                "reason": ai_by_field[row["field_name"]]["reason"],
                "evidence_refs": ai_by_field[row["field_name"]]["evidence_refs"],
            }

    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "demo_reviews.sqlite3")
        queue = build_review_queue([group], {"project_id": "DEMO-PROJECT", "run_id": "DEMO-RUN", "document_revision": "DEMO-REV-1"})
        assert queue, "Demo fixture should create review findings."
        closed = update_review_item(queue[0], assignee="demo-reviewer", disposition="ACCEPTED", comment="Confirmed against the synthetic demo evidence.")
        feedback = build_feedback_record(
            closed,
            disposition="ACCEPTED",
            reviewer_comment=closed.reviewer_comment,
            feedback_label="CONFIRMED_FINDING",
            reviewer_id="demo-reviewer",
            reviewer_name="demo-reviewer",
            reviewer_role="REVIEWER",
        )
        record_feedback(feedback, db_path=db_path)
        case = curate_feedback_record(
            feedback,
            gold_status=closed.status,
            gold_assessment="SUPPORTED",
            gold_risk="HIGH",
            gold_evidence_refs=[closed.evidence] if closed.evidence else [],
        )
        record_curated_case(case, db_path=db_path)
        report = evaluate_snapshot(
            [case],
            predictions_from_cases([case]),
            model_version="fixture-model",
            prompt_version="fixture-prompt",
        )
        assert report.regression_passed

    result = {
        "fixture": PDF.name,
        "pages": len(pages),
        "authoritative_statuses": status_by_field,
        "exception_count": reports.exception_count,
        "nemotron_reasoning_status": intelligence.status,
        "evidence_refs": sum(bool(a.get("evidence_refs")) for a in intelligence.field_assessments),
        "review_findings": len(queue),
        "evaluation_gate_passed": report.regression_passed,
        "live_provider": False,
        "note": "Offline rehearsal only; model calls are deterministic fixtures and no API credits are used.",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
