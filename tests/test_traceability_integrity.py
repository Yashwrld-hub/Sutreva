import sqlite3
import tempfile
from pathlib import Path

import pytest

from review_queue import ReviewItem
from review_store import load_items, upsert_items


def test_persistence_preserves_lifecycle_context_and_reviewer_fields():
    with tempfile.TemporaryDirectory() as d:
        db = str(Path(d) / "reviews.sqlite3")
        original = ReviewItem(
            item_id="P-1:0:pressure", equipment_id="P-1", field="pressure",
            status="MISMATCHED", reason="over limit", evidence={"page": 2},
            assignee="engineer-7", disposition="OPEN", reviewer_comment="check gauge",
            project_id="PROJECT-9", run_id="run-abc", document_revision="REV-3",
        )
        upsert_items([original], db)
        loaded = load_items(db)
        assert len(loaded) == 1
        item = loaded[0]
        assert item.project_id == "PROJECT-9"
        assert item.run_id == "run-abc"
        assert item.document_revision == "REV-3"
        assert item.assignee == "engineer-7"
        assert item.disposition == "OPEN"
        assert item.reviewer_comment == "check gauge"


def test_review_store_reports_corrupt_evidence_json():
    with tempfile.TemporaryDirectory() as d:
        db = str(Path(d) / "reviews.sqlite3")
        item = ReviewItem("x", "P-1", "Pressure", "MISSING", evidence={"page": 1})
        upsert_items([item], db)
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "UPDATE review_items SET evidence_json=? WHERE item_id=?",
                ("{bad", "x"),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ValueError, match="invalid JSON"):
            load_items(db)
