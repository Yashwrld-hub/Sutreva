"""Controlled evaluation flywheel for Sutreva.

This module turns explicitly curated human-review records into reproducible
model/prompt evaluation cases. It does not retrain models or change production
behavior. The current audit status remains authoritative.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


ASSESSMENTS = {"SUPPORTED", "AMBIGUOUS", "UNSUPPORTED", "MISSING"}
RISKS = {"LOW", "MEDIUM", "HIGH"}
EVAL_SCHEMA = "sutreva.evaluation.v1"


class _ClosingConnection(sqlite3.Connection):
    """SQLite connection that closes when used as a context manager."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    feedback_id: str
    item_id: str
    gold_status: str
    gold_assessment: str
    gold_risk: str
    gold_evidence_refs: list[dict[str, Any]]
    source_evidence: dict[str, Any] | None
    original_ai_context: dict[str, Any] | None
    schema_version: str = EVAL_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    assessment_correct: bool
    risk_correct: bool
    evidence_grounded: bool
    status_preserved: bool
    overall_correct: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationReport:
    evaluation_version: str
    model_version: str
    prompt_version: str
    case_count: int
    assessment_accuracy: float
    risk_accuracy: float
    evidence_grounding_rate: float
    status_preservation_rate: float
    overall_accuracy: float
    regression_passed: bool
    scores: list[dict[str, Any]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_refs(refs: Any) -> list[dict[str, Any]]:
    if not isinstance(refs, list):
        return []
    normalized: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        page = ref.get("page")
        line = ref.get("line")
        quote = str(ref.get("quote") or ref.get("text") or "").strip()
        if page is None or line is None or not quote:
            continue
        normalized.append({"page": page, "line": line, "quote": quote})
    return normalized


def _case_id(feedback_id: str, gold_status: str, assessment: str, risk: str, refs: list[dict[str, Any]]) -> str:
    material = json.dumps(
        [feedback_id, gold_status, assessment, risk, refs],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:16]


CURATED_SCHEMA = """
CREATE TABLE IF NOT EXISTS curated_evaluation_cases (
    case_id TEXT PRIMARY KEY,
    feedback_id TEXT NOT NULL,
    case_json TEXT NOT NULL,
    curated_at TEXT NOT NULL
)
"""


def _evaluation_db(db_path: str = "oem_audit_reviews.sqlite3") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, factory=_ClosingConnection)
    conn.execute(CURATED_SCHEMA)
    return conn


def record_curated_case(case: EvaluationCase, db_path: str = "oem_audit_reviews.sqlite3") -> None:
    with _evaluation_db(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO curated_evaluation_cases (case_id, feedback_id, case_json, curated_at) VALUES (?, ?, ?, ?)",
            (case.case_id, case.feedback_id, json.dumps(case.to_dict(), ensure_ascii=False, sort_keys=True), _utc_now()),
        )


def load_curated_cases(db_path: str = "oem_audit_reviews.sqlite3") -> list[EvaluationCase]:
    with _evaluation_db(db_path) as conn:
        rows = conn.execute(
            "SELECT case_json FROM curated_evaluation_cases ORDER BY curated_at, case_id"
        ).fetchall()
    cases = []
    for (payload,) in rows:
        data = json.loads(payload)
        cases.append(EvaluationCase(**data))
    return cases


def predictions_from_cases(cases: Iterable[EvaluationCase]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for case in cases:
        context = case.original_ai_context or {}
        predictions[case.case_id] = {
            "assessment": context.get("assessment", ""),
            "risk": context.get("risk", ""),
            "status": case.gold_status,
            "evidence_refs": context.get("evidence_refs") or [],
        }
    return predictions


def curate_feedback_record(
    record: Any,
    *,
    gold_status: str,
    gold_assessment: str,
    gold_risk: str,
    gold_evidence_refs: list[dict[str, Any]] | None = None,
) -> EvaluationCase:
    """Create an explicit gold-standard evaluation case from reviewer input."""
    if not getattr(record, "evaluation_ready", False):
        raise ValueError("Only closed feedback records can be curated for evaluation.")
    status = str(gold_status or "").strip().upper()
    assessment = str(gold_assessment or "").strip().upper()
    risk = str(gold_risk or "").strip().upper()
    if not status:
        raise ValueError("gold_status is required")
    if assessment not in ASSESSMENTS:
        raise ValueError(f"Unsupported gold assessment: {gold_assessment}")
    if risk not in RISKS:
        raise ValueError(f"Unsupported gold risk: {gold_risk}")
    refs = _normalize_refs(gold_evidence_refs)
    source_evidence = record.source_evidence if isinstance(record.source_evidence, dict) else None
    return EvaluationCase(
        case_id=_case_id(record.feedback_id, status, assessment, risk, refs),
        feedback_id=record.feedback_id,
        item_id=record.item_id,
        gold_status=status,
        gold_assessment=assessment,
        gold_risk=risk,
        gold_evidence_refs=refs,
        source_evidence=source_evidence,
        original_ai_context=record.ai_context if isinstance(record.ai_context, dict) else None,
    )


def export_cases_jsonl(cases: Iterable[EvaluationCase]) -> bytes:
    lines = [json.dumps(case.to_dict(), ensure_ascii=False, sort_keys=True) for case in cases]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def _refs_grounded(pred_refs: Any, source_evidence: Mapping[str, Any] | None) -> bool:
    refs = _normalize_refs(pred_refs)
    if not isinstance(source_evidence, Mapping) or not source_evidence:
        return len(refs) == 0
    if not refs:
        return False
    page = source_evidence.get("page")
    line = source_evidence.get("line")
    quote = str(source_evidence.get("text") or source_evidence.get("quote") or "").strip()
    if page is None or line is None or not quote:
        return False
    return any(
        ref.get("page") == page and ref.get("line") == line and ref.get("quote") == quote
        for ref in refs
    )


def score_case(case: EvaluationCase, prediction: Mapping[str, Any]) -> CaseScore:
    assessment = str(prediction.get("assessment") or "").upper()
    risk = str(prediction.get("risk") or "").upper()
    pred_status = str(prediction.get("status") or case.gold_status).upper()
    assessment_correct = assessment == case.gold_assessment
    risk_correct = risk == case.gold_risk
    evidence_grounded = _refs_grounded(prediction.get("evidence_refs"), case.source_evidence)
    status_preserved = pred_status == case.gold_status
    return CaseScore(
        case_id=case.case_id,
        assessment_correct=assessment_correct,
        risk_correct=risk_correct,
        evidence_grounded=evidence_grounded,
        status_preserved=status_preserved,
        overall_correct=assessment_correct and risk_correct and evidence_grounded and status_preserved,
    )


def evaluate_snapshot(
    cases: Iterable[EvaluationCase],
    predictions: Mapping[str, Mapping[str, Any]],
    *,
    model_version: str,
    prompt_version: str,
    evaluation_version: str = EVAL_SCHEMA,
) -> EvaluationReport:
    case_list = list(cases)
    scores = [score_case(case, predictions.get(case.case_id, {})) for case in case_list]
    count = len(scores)
    denom = count or 1
    assessment_accuracy = sum(s.assessment_correct for s in scores) / denom
    risk_accuracy = sum(s.risk_correct for s in scores) / denom
    evidence_rate = sum(s.evidence_grounded for s in scores) / denom
    status_rate = sum(s.status_preserved for s in scores) / denom
    overall_accuracy = sum(s.overall_correct for s in scores) / denom
    regression_passed = bool(count) and assessment_accuracy >= 0.90 and evidence_rate >= 0.90 and status_rate == 1.0
    return EvaluationReport(
        evaluation_version=evaluation_version,
        model_version=model_version,
        prompt_version=prompt_version,
        case_count=count,
        assessment_accuracy=assessment_accuracy,
        risk_accuracy=risk_accuracy,
        evidence_grounding_rate=evidence_rate,
        status_preservation_rate=status_rate,
        overall_accuracy=overall_accuracy,
        regression_passed=regression_passed,
        scores=[s.to_dict() for s in scores],
        generated_at=_utc_now(),
    )
