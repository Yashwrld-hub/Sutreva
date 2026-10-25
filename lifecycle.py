"""Audit lifecycle helpers linking projects, runs, documents and review items."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class AuditRun:
    run_id: str
    project_id: str
    document_revision: str
    created_by: str
    created_at: str


def make_run_id(project_id: str, document_revision: str, created_by: str, nonce: Optional[str] = None) -> str:
    """Create a deterministic, non-sensitive run identifier."""
    raw = "|".join([project_id.strip(), document_revision.strip(), created_by.strip(), nonce or datetime.now(timezone.utc).isoformat()])
    return "run-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def create_audit_run(project_id: str, document_revision: str, created_by: str, nonce: Optional[str] = None) -> AuditRun:
    for name, value in (("project_id", project_id), ("document_revision", document_revision), ("created_by", created_by)):
        if not value or not value.strip():
            raise ValueError(f"{name} is required")
    return AuditRun(make_run_id(project_id, document_revision, created_by, nonce), project_id.strip(), document_revision.strip(), created_by.strip(), datetime.now(timezone.utc).isoformat())


def attach_run_context(item: dict, run: AuditRun) -> dict:
    """Return a copy with lifecycle context; never overwrite existing identifiers."""
    enriched = dict(item)
    enriched.setdefault("project_id", run.project_id)
    enriched.setdefault("run_id", run.run_id)
    enriched.setdefault("document_revision", run.document_revision)
    return enriched
