from pathlib import Path


def test_live_modules_integrate_unit_contract_conflict_and_governance():
    root = Path(__file__).resolve().parents[1]
    core = (root / "core.py").read_text(encoding="utf-8")
    app = (root / "app.py").read_text(encoding="utf-8")
    assert "from extraction_contract import" in core
    assert "from conflict_detection import" in core
    assert "records_from_extracted" in core
    assert "detect_conflicts" in core
    assert "from governance import ApprovalEvent, UserIdentity" in app
    assert "record_approval_event" in app
