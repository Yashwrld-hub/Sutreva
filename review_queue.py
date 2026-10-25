"""Actionable review queue utilities for engineering audit findings."""
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

OPEN_STATUSES = {"MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW", "CONFLICT", "UNVERIFIED"}

@dataclass
class ReviewItem:
    item_id: str
    equipment_id: str
    field: str
    status: str
    reason: str = ""
    evidence: Optional[dict] = None
    assignee: Optional[str] = None
    disposition: Optional[str] = None
    reviewer_comment: str = ""
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    document_revision: Optional[str] = None
    ai_context: Optional[dict] = None

    @property
    def is_open(self) -> bool:
        return self.disposition in (None, "OPEN", "REOPENED")

    def to_dict(self):
        return asdict(self)

def build_review_queue(results: Iterable[dict], lifecycle_context: Optional[dict] = None) -> list[ReviewItem]:
    """Convert audit result groups into actionable items; matched rows are omitted."""
    queue = []
    for group in results:
        equipment_id = str(group.get("identifier", "Unknown"))
        for index, row in enumerate(group.get("rows", [])):
            status = str(row.get("status", "")).upper()
            if status in {"MATCHED", "OK", "PASS"}:
                continue
            field = str(row.get("field", row.get("field_name", "Unknown")))
            evidence = row.get("evidence") or row.get("evidence_ref")
            reason = row.get("review_reason") or row.get("reason") or status
            queue.append(ReviewItem(
                item_id=f"{equipment_id}:{index}:{field}",
                equipment_id=equipment_id,
                field=field,
                status=status or "NEEDS_REVIEW",
                reason=str(reason),
                evidence=evidence,
                project_id=(lifecycle_context or {}).get("project_id"),
                run_id=(lifecycle_context or {}).get("run_id"),
                document_revision=(lifecycle_context or {}).get("document_revision"),
                ai_context=row.get("ai_context"),
            ))
    return queue

def update_review_item(item: ReviewItem, *, assignee=None, disposition=None, comment=None) -> ReviewItem:
    """Apply review metadata without mutating the original item."""
    updated = ReviewItem(**item.to_dict())
    if assignee is not None:
        updated.assignee = assignee.strip() or None
    if disposition is not None:
        updated.disposition = disposition.strip().upper() or None
    if comment is not None:
        updated.reviewer_comment = comment.strip()
    return updated
