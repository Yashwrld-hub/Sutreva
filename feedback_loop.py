"""Human-feedback learning loop for Sutreva.

Reviewer decisions are captured as append-only feedback events. Feedback can be
exported as evaluation candidates, but this module never retrains or mutates a
model automatically.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CLOSED_DISPOSITIONS = {"ACCEPTED", "REJECTED", "WAIVED", "REQUIRES_ACTION"}
FEEDBACK_LABELS = {
    "CONFIRMED_FINDING",
    "OVERRIDDEN_FINDING",
    "INSUFFICIENT_EVIDENCE",
    "RULE_UPDATE_SIGNAL",
    "WAIVED_BY_REVIEW",
    "ACTION_REQUIRED",
    "OTHER",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback_events (
    feedback_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    feedback_label TEXT NOT NULL,
    original_status TEXT NOT NULL,
    disposition TEXT NOT NULL,
    reviewer_comment TEXT,
    corrected_value TEXT,
    source_evidence_json TEXT,
    ai_context_json TEXT,
    project_id TEXT,
    run_id TEXT,
    document_revision TEXT,
    reviewer_id TEXT,
    reviewer_name TEXT,
    reviewer_role TEXT,
    occurred_at TEXT NOT NULL,
    schema_version TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    item_id: str
    feedback_label: str
    original_status: str
    disposition: str
    reviewer_comment: str
    corrected_value: str | None
    source_evidence: dict[str, Any] | None
    ai_context: dict[str, Any] | None
    project_id: str | None
    run_id: str | None
    document_revision: str | None
    reviewer_id: str | None
    reviewer_name: str | None
    reviewer_role: str | None
    occurred_at: str
    schema_version: str = "sutreva.feedback.v1"

    @property
    def evaluation_ready(self) -> bool:
        return self.disposition.upper() in CLOSED_DISPOSITIONS

    def to_dict(self, *, include_identity: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        payload["evaluation_ready"] = self.evaluation_ready
        if not include_identity:
            payload.pop("reviewer_id", None)
            payload.pop("reviewer_name", None)
        return payload


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db_path: str = "oem_audit_reviews.sqlite3") -> sqlite3.Connection:
    conn = sqlite3.connect(str(Path(db_path)), factory=_ClosingConnection)
    conn.execute(SCHEMA)
    return conn


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _default_label(disposition: str) -> str:
    mapping = {
        "ACCEPTED": "CONFIRMED_FINDING",
        "REJECTED": "OVERRIDDEN_FINDING",
        "WAIVED": "WAIVED_BY_REVIEW",
        "REQUIRES_ACTION": "ACTION_REQUIRED",
    }
    return mapping.get(disposition.upper(), "OTHER")


def build_feedback_record(
    item: Any,
    *,
    disposition: str,
    reviewer_comment: str = "",
    corrected_value: str | None = None,
    feedback_label: str | None = None,
    reviewer_id: str | None = None,
    reviewer_name: str | None = None,
    reviewer_role: str | None = None,
    feedback_id: str | None = None,
    occurred_at: str | None = None,
) -> FeedbackRecord:
    final_disposition = _clean(disposition).upper() or "OPEN"
    label = _clean(feedback_label).upper() or _default_label(final_disposition)
    if label not in FEEDBACK_LABELS:
        raise ValueError(f"Unsupported feedback label: {feedback_label}")
    try:
        source_evidence = item.evidence if isinstance(item.evidence, dict) else None
    except AttributeError:
        source_evidence = None
    ai_context = getattr(item, "ai_context", None)
    if not isinstance(ai_context, dict):
        ai_context = None
    return FeedbackRecord(
        feedback_id=feedback_id or str(uuid.uuid4()),
        item_id=_clean(item.item_id),
        feedback_label=label,
        original_status=_clean(item.status).upper(),
        disposition=final_disposition,
        reviewer_comment=_clean(reviewer_comment),
        corrected_value=None if corrected_value is None or not _clean(corrected_value) else _clean(corrected_value),
        source_evidence=source_evidence,
        ai_context=ai_context,
        project_id=getattr(item, "project_id", None),
        run_id=getattr(item, "run_id", None),
        document_revision=getattr(item, "document_revision", None),
        reviewer_id=_clean(reviewer_id) or None,
        reviewer_name=_clean(reviewer_name) or None,
        reviewer_role=_clean(reviewer_role).upper() or None,
        occurred_at=occurred_at or _utc_now(),
    )


def record_feedback(record: FeedbackRecord, db_path: str = "oem_audit_reviews.sqlite3") -> None:
    if not record.item_id:
        raise ValueError("item_id is required for feedback")
    if record.feedback_label not in FEEDBACK_LABELS:
        raise ValueError(f"Unsupported feedback label: {record.feedback_label}")
    with connect(db_path) as conn:
        conn.execute(
            """INSERT INTO feedback_events
            (feedback_id,item_id,feedback_label,original_status,disposition,reviewer_comment,corrected_value,
             source_evidence_json,ai_context_json,project_id,run_id,document_revision,reviewer_id,reviewer_name,
             reviewer_role,occurred_at,schema_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.feedback_id,
                record.item_id,
                record.feedback_label,
                record.original_status,
                record.disposition,
                record.reviewer_comment,
                record.corrected_value,
                json.dumps(record.source_evidence, ensure_ascii=False) if record.source_evidence is not None else None,
                json.dumps(record.ai_context, ensure_ascii=False) if record.ai_context is not None else None,
                record.project_id,
                record.run_id,
                record.document_revision,
                record.reviewer_id,
                record.reviewer_name,
                record.reviewer_role,
                record.occurred_at,
                record.schema_version,
            ),
        )


def _json_or_none(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Stored feedback JSON is invalid.") from exc


def load_feedback(db_path: str = "oem_audit_reviews.sqlite3") -> list[FeedbackRecord]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT feedback_id,item_id,feedback_label,original_status,disposition,reviewer_comment,
               corrected_value,source_evidence_json,ai_context_json,project_id,run_id,document_revision,
               reviewer_id,reviewer_name,reviewer_role,occurred_at,schema_version
               FROM feedback_events ORDER BY occurred_at, feedback_id"""
        ).fetchall()
    return [
        FeedbackRecord(
            feedback_id=row[0],
            item_id=row[1],
            feedback_label=row[2],
            original_status=row[3],
            disposition=row[4],
            reviewer_comment=row[5] or "",
            corrected_value=row[6],
            source_evidence=_json_or_none(row[7]),
            ai_context=_json_or_none(row[8]),
            project_id=row[9],
            run_id=row[10],
            document_revision=row[11],
            reviewer_id=row[12],
            reviewer_name=row[13],
            reviewer_role=row[14],
            occurred_at=row[15],
            schema_version=row[16] or "sutreva.feedback.v1",
        )
        for row in rows
    ]


def feedback_summary(records: Iterable[FeedbackRecord]) -> dict[str, int]:
    values = list(records)
    return {
        "total_feedback_events": len(values),
        "evaluation_ready": sum(r.evaluation_ready for r in values),
        "confirmed": sum(r.feedback_label == "CONFIRMED_FINDING" for r in values),
        "overridden": sum(r.feedback_label == "OVERRIDDEN_FINDING" for r in values),
        "rule_update_signals": sum(r.feedback_label == "RULE_UPDATE_SIGNAL" for r in values),
    }


def export_feedback_jsonl(
    records: Iterable[FeedbackRecord], *, include_identity: bool = False
) -> bytes:
    lines = [
        json.dumps(record.to_dict(include_identity=include_identity), ensure_ascii=False, sort_keys=True)
        for record in records
        if record.evaluation_ready
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
