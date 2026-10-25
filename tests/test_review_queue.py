from review_queue import build_review_queue, update_review_item


def test_queue_omits_matched_and_keeps_findings():
    queue = build_review_queue([{"identifier": "P-101", "rows": [
        {"field": "flow", "status": "MATCHED"},
        {"field": "pressure", "status": "MISMATCHED", "reason": "Above limit"},
    ]}])
    assert len(queue) == 1
    assert queue[0].item_id == "P-101:1:pressure"
    assert queue[0].reason == "Above limit"

def test_review_update_is_non_mutating():
    item = build_review_queue([{"identifier": "C-1", "rows": [{"field": "temp", "status": "NEEDS_REVIEW"}]}])[0]
    updated = update_review_item(item, assignee="Engineer A", disposition="approved", comment="Checked source")
    assert item.assignee is None
    assert updated.assignee == "Engineer A"
    assert updated.disposition == "APPROVED"
    assert updated.reviewer_comment == "Checked source"


def test_review_queue_carries_ai_context():
    queue = build_review_queue([{
        "identifier": "P-101",
        "rows": [{
            "field_name": "driver_type",
            "field": "Driver Type",
            "status": "NEEDS_REVIEW",
            "ai_context": {"assessment": "AMBIGUOUS", "risk": "HIGH"},
        }],
    }])
    assert queue[0].ai_context["assessment"] == "AMBIGUOUS"
    assert queue[0].ai_context["risk"] == "HIGH"
