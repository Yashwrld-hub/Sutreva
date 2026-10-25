import pytest

from evaluation_flywheel import (
    curate_feedback_record,
    evaluate_snapshot,
    export_cases_jsonl,
    load_curated_cases,
    predictions_from_cases,
    record_curated_case,
    score_case,
)
from feedback_loop import build_feedback_record
from review_queue import ReviewItem


def _feedback():
    item = ReviewItem(
        item_id="P-101:1:Driver Type",
        equipment_id="P-101",
        field="Driver Type",
        status="NEEDS_REVIEW",
        reason="Checkbox evidence needs verification",
        evidence={"page": 2, "line": 18, "text": "Induction Motor"},
        project_id="PRJ-1",
        run_id="RUN-1",
        document_revision="R03",
        ai_context={"assessment": "AMBIGUOUS", "risk": "MEDIUM"},
    )
    return build_feedback_record(item, disposition="ACCEPTED", reviewer_id="u1")


def _case():
    return curate_feedback_record(
        _feedback(),
        gold_status="NEEDS_REVIEW",
        gold_assessment="SUPPORTED",
        gold_risk="LOW",
        gold_evidence_refs=[{"page": 2, "line": 18, "quote": "Induction Motor"}],
    )


def test_curate_requires_closed_feedback():
    item = ReviewItem(item_id="x", equipment_id="P", field="f", status="NEEDS_REVIEW")
    record = build_feedback_record(item, disposition="OPEN")
    with pytest.raises(ValueError):
        curate_feedback_record(record, gold_status="NEEDS_REVIEW", gold_assessment="SUPPORTED", gold_risk="LOW")


def test_score_case_checks_all_dimensions():
    case = _case()
    score = score_case(case, {
        "status": "NEEDS_REVIEW",
        "assessment": "SUPPORTED",
        "risk": "LOW",
        "evidence_refs": [{"page": 2, "line": 18, "quote": "Induction Motor"}],
    })
    assert score.overall_correct is True
    assert score.evidence_grounded is True


def test_evidence_grounding_fails_for_untrusted_quote():
    case = _case()
    score = score_case(case, {
        "status": "NEEDS_REVIEW",
        "assessment": "SUPPORTED",
        "risk": "LOW",
        "evidence_refs": [{"page": 2, "line": 18, "quote": "invented quote"}],
    })
    assert score.evidence_grounded is False
    assert score.overall_correct is False


def test_evaluate_snapshot_regression_gate():
    case = _case()
    report = evaluate_snapshot(
        [case],
        {case.case_id: {"status": "NEEDS_REVIEW", "assessment": "SUPPORTED", "risk": "LOW", "evidence_refs": [{"page": 2, "line": 18, "quote": "Induction Motor"}]}},
        model_version="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        prompt_version="sutreva.reasoning.v2",
        evaluation_version="sutreva.evaluation.v1",
    )
    assert report.regression_passed is True
    assert report.overall_accuracy == 1.0


def test_evaluate_snapshot_preserves_status_as_hard_gate():
    case = _case()
    report = evaluate_snapshot(
        [case],
        {case.case_id: {"status": "MATCHED", "assessment": "SUPPORTED", "risk": "LOW", "evidence_refs": [{"page": 2, "line": 18, "quote": "Induction Motor"}]}},
        model_version="m",
        prompt_version="p",
    )
    assert report.status_preservation_rate == 0.0
    assert report.regression_passed is False


def test_export_cases_jsonl_is_stable_and_versioned():
    payload = export_cases_jsonl([_case()]).decode()
    assert '"schema_version": "sutreva.evaluation.v1"' in payload
    assert payload.endswith("\n")


def test_curated_cases_persist_and_reload(tmp_path):
    db = str(tmp_path / "eval.sqlite3")
    case = _case()
    record_curated_case(case, db)
    loaded = load_curated_cases(db)
    assert loaded[0].case_id == case.case_id
    assert loaded[0].gold_evidence_refs == case.gold_evidence_refs


def test_predictions_from_cases_preserve_recorded_ai_context():
    case = _case()
    predictions = predictions_from_cases([case])
    assert predictions[case.case_id]["assessment"] == "AMBIGUOUS"
    assert predictions[case.case_id]["risk"] == "MEDIUM"
    assert predictions[case.case_id]["status"] == "NEEDS_REVIEW"
