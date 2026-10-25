"""Synthetic industrial pilot case pack and acceptance checks.

The cases are intentionally synthetic and must not be treated as approved
engineering requirements or real vendor data.
"""
from __future__ import annotations

from typing import Any, Mapping

CASE_PACK = [
    {
        "case_id": "PUMP-001",
        "equipment_type": "centrifugal_pump",
        "scenario": "Nominal datasheet with one pressure exception",
        "expected_review_focus": ["pressure", "evidence"],
    },
    {
        "case_id": "COMP-001",
        "equipment_type": "reciprocating_compressor",
        "scenario": "Conflicting lubricant and temperature references",
        "expected_review_focus": ["conflict", "units", "evidence"],
    },
    {
        "case_id": "LUBE-001",
        "equipment_type": "lube_oil_register",
        "scenario": "Bulk register with missing and mismatched fields",
        "expected_review_focus": ["missing", "mismatch", "traceability"],
    },
]

ACCEPTANCE_CRITERIA = {
    "traceability": "Every finding has project, run, source and field context.",
    "evidence": "Every non-matched finding is evidence-linked or marked NEEDS_REVIEW.",
    "reviewability": "Every flagged finding can be assigned and given a disposition.",
    "safety": "No missing, conflicting or unverified value is silently approved.",
}


def validate_pilot_record(record: Mapping[str, Any]) -> list[str]:
    """Return acceptance issues for one normalized finding record."""
    issues: list[str] = []
    for field in ("project_id", "run_id", "field_name"):
        if not str(record.get(field) or "").strip():
            issues.append(f"missing:{field}")
    status = str(record.get("status") or "UNKNOWN").upper().replace(" ", "_")
    if status != "MATCHED" and not record.get("evidence"):
        issues.append("missing:evidence_or_review")
    if status in {"CONFLICT", "NEEDS_REVIEW", "MISSING"} and record.get("approved") is True:
        issues.append("unsafe:unverified_approval")
    return issues
