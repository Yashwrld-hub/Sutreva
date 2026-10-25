from lifecycle import attach_run_context, create_audit_run


def test_create_run_and_attach_context():
    run = create_audit_run("P-01", "rev-2", "u-7", nonce="fixed")
    item = attach_run_context({"item_id": "x", "project_id": "existing"}, run)
    assert run.run_id.startswith("run-")
    assert item["project_id"] == "existing"
    assert item["run_id"] == run.run_id
    assert item["document_revision"] == "rev-2"


def test_required_fields():
    try:
        create_audit_run("", "rev-1", "u-1")
    except ValueError as exc:
        assert "project_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
