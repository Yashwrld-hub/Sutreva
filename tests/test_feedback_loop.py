from feedback_loop import (
    build_feedback_record,
    export_feedback_jsonl,
    feedback_summary,
    load_feedback,
    record_feedback,
)
from review_queue import ReviewItem


def _item():
    return ReviewItem(
        item_id="P-101:1:Driver Type",
        equipment_id="P-101",
        field="Driver Type",
        status="NEEDS_REVIEW",
        reason="Checkbox evidence needs verification",
        evidence={"page": 2, "line": 18, "text": "Induction Motor"},
        project_id="PRJ-1",
        run_id="RUN-1",
        document_revision="R03",
        ai_context={
            "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
            "prompt_version": "sutreva.reasoning.v2",
            "assessment": "AMBIGUOUS",
            "risk": "MEDIUM",
        },
    )


def test_feedback_record_defaults_and_evaluation_state():
    record = build_feedback_record(_item(), disposition="ACCEPTED", reviewer_id="u1", reviewer_role="REVIEWER")
    assert record.feedback_label == "CONFIRMED_FINDING"
    assert record.evaluation_ready is True
    assert record.ai_context["assessment"] == "AMBIGUOUS"


def test_feedback_is_append_only(tmp_path):
    db = str(tmp_path / "feedback.sqlite3")
    first = build_feedback_record(_item(), disposition="ACCEPTED", reviewer_id="u1")
    second = build_feedback_record(_item(), disposition="REJECTED", feedback_label="OVERRIDDEN_FINDING", reviewer_id="u1")
    record_feedback(first, db)
    record_feedback(second, db)
    rows = load_feedback(db)
    assert [r.feedback_id for r in rows] == [first.feedback_id, second.feedback_id]
    assert rows[0].disposition == "ACCEPTED"
    assert rows[1].disposition == "REJECTED"


def test_feedback_export_excludes_identity_by_default(tmp_path):
    db = str(tmp_path / "feedback.sqlite3")
    closed = build_feedback_record(_item(), disposition="ACCEPTED", reviewer_id="secret-user", reviewer_name="Secret User")
    open_record = build_feedback_record(_item(), disposition="OPEN", reviewer_id="secret-user")
    record_feedback(closed, db)
    record_feedback(open_record, db)
    payload = export_feedback_jsonl(load_feedback(db), include_identity=False).decode("utf-8")
    assert "secret-user" not in payload
    assert "Secret User" not in payload
    assert "evaluation_ready" in payload
    assert "CONFIRMED_FINDING" in payload
    assert "OPEN" not in payload


def test_feedback_summary_counts_learning_signals(tmp_path):
    db = str(tmp_path / "feedback.sqlite3")
    records = [
        build_feedback_record(_item(), disposition="ACCEPTED"),
        build_feedback_record(_item(), disposition="REJECTED", feedback_label="OVERRIDDEN_FINDING"),
        build_feedback_record(_item(), disposition="REQUIRES_ACTION", feedback_label="RULE_UPDATE_SIGNAL"),
    ]
    for record in records:
        record_feedback(record, db)
    summary = feedback_summary(load_feedback(db))
    assert summary == {
        "total_feedback_events": 3,
        "evaluation_ready": 3,
        "confirmed": 1,
        "overridden": 1,
        "rule_update_signals": 1,
    }
