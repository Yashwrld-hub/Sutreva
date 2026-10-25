"""SQLite persistence for Sutreva review decisions."""

# Legacy product name retained for historical traceability: OEM Audit Copilot.
import json
import sqlite3
from pathlib import Path
from typing import Iterable

from review_queue import ReviewItem


class _ClosingConnection(sqlite3.Connection):
    """SQLite connection that closes when used as a context manager."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS review_items (
 item_id TEXT PRIMARY KEY, equipment_id TEXT NOT NULL, field TEXT NOT NULL,
 status TEXT NOT NULL, reason TEXT, evidence_json TEXT, project_id TEXT, run_id TEXT, document_revision TEXT, assignee TEXT,
 disposition TEXT, reviewer_comment TEXT, ai_context_json TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


def connect(db_path="oem_audit_reviews.sqlite3"):
    conn = sqlite3.connect(str(Path(db_path)), factory=_ClosingConnection)
    conn.execute(SCHEMA)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(review_items)")}
    for column in ("project_id", "run_id", "document_revision", "ai_context_json"):
        if column not in existing:
            conn.execute(f"ALTER TABLE review_items ADD COLUMN {column} TEXT")
    return conn


def _json_or_none(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Stored AI context is invalid JSON.") from exc


def upsert_items(items: Iterable[ReviewItem], db_path="oem_audit_reviews.sqlite3"):
    values = [
        (
            item.item_id, item.equipment_id, item.field, item.status, item.reason,
            json.dumps(item.evidence) if item.evidence is not None else None,
            getattr(item, "project_id", None), getattr(item, "run_id", None),
            getattr(item, "document_revision", None), item.assignee, item.disposition,
            item.reviewer_comment,
            json.dumps(getattr(item, "ai_context", None), ensure_ascii=False)
            if getattr(item, "ai_context", None) is not None else None,
        )
        for item in items
    ]
    if not values:
        return
    with connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO review_items
            (item_id,equipment_id,field,status,reason,evidence_json,project_id,run_id,document_revision,assignee,disposition,reviewer_comment,ai_context_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET
            equipment_id=excluded.equipment_id,
            field=excluded.field,
            status=excluded.status,
            reason=excluded.reason,
            evidence_json=COALESCE(excluded.evidence_json, review_items.evidence_json),
            project_id=COALESCE(excluded.project_id, review_items.project_id),
            run_id=COALESCE(excluded.run_id, review_items.run_id),
            document_revision=COALESCE(excluded.document_revision, review_items.document_revision),
            assignee=excluded.assignee,
            disposition=excluded.disposition,
            reviewer_comment=excluded.reviewer_comment,
            ai_context_json=COALESCE(excluded.ai_context_json, review_items.ai_context_json),
            updated_at=CURRENT_TIMESTAMP""",
            values,
        )


def load_items(db_path="oem_audit_reviews.sqlite3") -> list[ReviewItem]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT item_id,equipment_id,field,status,reason,evidence_json,project_id,run_id,document_revision,assignee,disposition,reviewer_comment,ai_context_json FROM review_items ORDER BY item_id"
        ).fetchall()
    items = []
    for r in rows:
        try:
            evidence = json.loads(r[5]) if r[5] else None
        except json.JSONDecodeError as exc:
            raise ValueError(f"Stored evidence is invalid JSON for review item {r[0]!r}.") from exc
        items.append(ReviewItem(
            item_id=r[0], equipment_id=r[1], field=r[2], status=r[3], reason=r[4] or "",
            evidence=evidence, assignee=r[9], disposition=r[10],
            reviewer_comment=r[11] or "", project_id=r[6], run_id=r[7], document_revision=r[8],
            ai_context=_json_or_none(r[12]),
        ))
    return items


GOVERNANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
 project_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_runs (
 run_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, document_revision TEXT,
 created_by TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(project_id) REFERENCES projects(project_id)
);
CREATE TABLE IF NOT EXISTS review_events (
 event_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL,
 actor_id TEXT NOT NULL, actor_name TEXT NOT NULL, actor_role TEXT NOT NULL,
 disposition TEXT NOT NULL, comment TEXT, occurred_at TEXT NOT NULL
);
"""


def initialize_governance(db_path="oem_audit_reviews.sqlite3"):
    with connect(db_path) as conn:
        conn.executescript(GOVERNANCE_SCHEMA)


def record_approval_event(event, db_path="oem_audit_reviews.sqlite3"):
    with connect(db_path) as conn:
        conn.executescript(GOVERNANCE_SCHEMA)
        conn.execute(
            """INSERT INTO review_events
            (item_id, actor_id, actor_name, actor_role, disposition, comment, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.item_id, event.actor.user_id, event.actor.display_name,
                event.actor.role.upper(), event.disposition.upper(), event.comment, event.occurred_at,
            ),
        )


def load_review_events(item_id, db_path="oem_audit_reviews.sqlite3"):
    initialize_governance(db_path)
    with connect(db_path) as conn:
        return conn.execute(
            """SELECT item_id,actor_id,actor_name,actor_role,disposition,comment,occurred_at
            FROM review_events WHERE item_id=? ORDER BY event_id""",
            (item_id,),
        ).fetchall()
