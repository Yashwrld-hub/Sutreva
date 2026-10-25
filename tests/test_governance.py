import pytest

from governance import ApprovalEvent, UserIdentity
from review_store import load_review_events, record_approval_event


def test_identity_rejects_unknown_role():
    with pytest.raises(ValueError):
        UserIdentity("u1", "Engineer", "ROOT")

def test_approval_event_is_append_only(tmp_path):
    actor = UserIdentity("u1", "Engineer", "APPROVER")
    event = ApprovalEvent("pump:1:pressure", actor, "ACCEPTED", "Reviewed against approved datasheet")
    db = str(tmp_path / "review.sqlite3")
    record_approval_event(event, db)
    record_approval_event(event, db)
    rows = load_review_events(event.item_id, db)
    assert len(rows) == 2
    assert rows[0][1:5] == ("u1", "Engineer", "APPROVER", "ACCEPTED")


def test_governance_records_are_compatible_with_review_dispositions(tmp_path):
    from governance import ApprovalEvent, UserIdentity
    from review_store import load_review_events, record_approval_event
    db = tmp_path / "review.sqlite3"
    actor = UserIdentity("tester", "Tester", "REVIEWER")
    record_approval_event(ApprovalEvent("item-1", actor, "REQUIRES_ACTION", "verify source"), str(db))
    rows = load_review_events("item-1", str(db))
    assert rows[0][1:5] == ("tester", "Tester", "REVIEWER", "REQUIRES_ACTION")
