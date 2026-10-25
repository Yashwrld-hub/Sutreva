import time

import pytest

import core
from core import bulk_overview, run_batch_audit, run_batch_pdf_audit


SCHEMA = {
    "template_name": "T",
    "fields": [{"field_name": "a", "label": "A", "expected_value": "GOOD"}],
}


def _fake_run_audit_factory(delay=0.0, fail_on=None):
    fail_on = fail_on or set()

    def _fake(text, schema):
        if delay:
            time.sleep(delay)
        if text in fail_on:
            raise RuntimeError(f"simulated failure for {text}")
        rows = core.compare_against_schema({"a": text}, schema)
        return rows, f"raw:{text}", {"a": text}

    return _fake


@pytest.fixture
def mock_run_audit(monkeypatch):
    """Lets each test install its own fake run_audit without touching the network."""
    def _install(delay=0.0, fail_on=None):
        monkeypatch.setattr(core, "run_audit", _fake_run_audit_factory(delay, fail_on))
    return _install


def test_batch_preserves_input_order(mock_run_audit):
    mock_run_audit(delay=0.05)
    named_texts = [("f1", "GOOD"), ("f2", "BAD"), ("f3", "GOOD")]
    results = run_batch_audit(named_texts, SCHEMA, max_workers=3)
    assert [r["identifier"] for r in results] == ["f1", "f2", "f3"]


def test_batch_runs_concurrently_not_sequentially(mock_run_audit):
    mock_run_audit(delay=0.3)
    named_texts = [(f"f{i}", "GOOD") for i in range(6)]

    start = time.time()
    run_batch_audit(named_texts, SCHEMA, max_workers=6)
    elapsed = time.time() - start

    # Sequential would take ~1.8s (6 x 0.3s); concurrent should be well under 1s.
    assert elapsed < 1.0, f"Batch took {elapsed:.2f}s — doesn't look concurrent"


def test_batch_respects_max_workers_limit(mock_run_audit):
    """With only 2 workers, 6 files at 0.2s each should take at least 3 rounds."""
    mock_run_audit(delay=0.2)
    named_texts = [(f"f{i}", "GOOD") for i in range(6)]

    start = time.time()
    run_batch_audit(named_texts, SCHEMA, max_workers=2)
    elapsed = time.time() - start

    # 6 files / 2 workers = 3 sequential rounds of 0.2s = ~0.6s minimum
    assert elapsed >= 0.5, f"Finished in {elapsed:.2f}s — max_workers may not be respected"


def test_batch_one_failure_does_not_affect_others(mock_run_audit):
    mock_run_audit(fail_on={"BROKEN"})
    named_texts = [("good1.pdf", "GOOD"), ("bad.pdf", "BROKEN"), ("good2.pdf", "GOOD")]
    results = run_batch_audit(named_texts, SCHEMA, max_workers=3)

    assert results[0]["error"] is None
    assert results[1]["error"] == "simulated failure for BROKEN"
    assert results[2]["error"] is None
    # the two good files should still have real results
    assert results[0]["summary"]["MATCHED"] == 1
    assert results[2]["summary"]["MATCHED"] == 1
    assert all(r["performance"]["total_s"] >= 0 for r in results)


def test_batch_all_failures_returns_all_error_rows(mock_run_audit):
    mock_run_audit(fail_on={"X", "Y"})
    results = run_batch_audit([("a", "X"), ("b", "Y")], SCHEMA, max_workers=2)
    assert all(r["error"] is not None for r in results)
    assert all(r["summary"]["TOTAL"] == 0 for r in results)


def test_batch_empty_input_returns_empty_list(mock_run_audit):
    mock_run_audit()
    assert run_batch_audit([], SCHEMA) == []


def test_batch_progress_callback_reaches_total(mock_run_audit):
    mock_run_audit()
    named_texts = [(f"f{i}", "GOOD") for i in range(5)]
    calls = []
    run_batch_audit(named_texts, SCHEMA, max_workers=3, progress_callback=lambda d, t: calls.append((d, t)))
    assert len(calls) == 5
    assert calls[-1] == (5, 5)


def test_bulk_overview_marks_errored_file_as_not_matched(mock_run_audit):
    mock_run_audit(fail_on={"BROKEN"})
    results = run_batch_audit([("bad.pdf", "BROKEN")], SCHEMA, max_workers=1)
    overview = bulk_overview(results)
    assert overview[0]["all_matched"] is False
    assert overview[0]["error"] is not None


def test_batch_pdf_failure_isolated_and_ordered(monkeypatch):
    def fake_pdf(pdf_bytes, schema, *, include_intelligence=False):
        if pdf_bytes == b"BROKEN":
            raise RuntimeError("bad pdf")
        rows = core.compare_against_schema({"a": "GOOD"}, schema)
        return rows, "raw", {"a": "GOOD"}, [{"page": 1, "text": "A: GOOD"}]

    monkeypatch.setattr(core, "run_pdf_audit_with_evidence", fake_pdf)
    results = run_batch_pdf_audit([("one.pdf", b"GOOD"), ("bad.pdf", b"BROKEN"), ("two.pdf", b"GOOD")], SCHEMA, max_workers=2)
    assert [r["identifier"] for r in results] == ["one.pdf", "bad.pdf", "two.pdf"]
    assert results[0]["error"] is None
    assert results[1]["error"] == "bad pdf"
    assert results[2]["error"] is None


def test_batch_pdf_progress_callback_cannot_abort_batch(monkeypatch):
    def fake_pdf(pdf_bytes, schema, *, include_intelligence=False):
        rows = core.compare_against_schema({"a": "GOOD"}, schema)
        return rows, "raw", {"a": "GOOD"}, []

    monkeypatch.setattr(core, "run_pdf_audit_with_evidence", fake_pdf)
    calls = []
    def bad_callback(done, total):
        calls.append((done, total))
        raise RuntimeError("UI callback failure")

    results = run_batch_pdf_audit([("one.pdf", b"GOOD"), ("two.pdf", b"GOOD")], SCHEMA, max_workers=2, progress_callback=bad_callback)
    assert len(results) == 2
    assert all(r["error"] is None for r in results)
    assert calls[-1] == (2, 2)


def test_batch_pdf_without_intelligence_accepts_four_value_audit_result(monkeypatch):
    def fake_pdf(pdf_bytes, schema, *, include_intelligence=False):
        rows = core.compare_against_schema({"a": "GOOD"}, schema)
        return rows, "raw", {"a": "GOOD"}, []

    monkeypatch.setattr(core, "run_pdf_audit_with_evidence", fake_pdf)
    result = core._run_one_pdf_for_batch("one.pdf", b"GOOD", SCHEMA, include_intelligence=False)
    assert result["error"] is None
    assert result["summary"]["MATCHED"] == 1


def test_batch_pdf_with_intelligence_accepts_five_value_audit_result(monkeypatch):
    class FakeIntelligence:
        def to_dict(self):
            return {"status": "OK"}

    def fake_pdf(pdf_bytes, schema, *, include_intelligence=False):
        rows = core.compare_against_schema({"a": "GOOD"}, schema)
        return rows, "raw", {"a": "GOOD"}, [], FakeIntelligence()

    monkeypatch.setattr(core, "run_pdf_audit_with_evidence", fake_pdf)
    result = core._run_one_pdf_for_batch("one.pdf", b"GOOD", SCHEMA, include_intelligence=True)
    assert result["error"] is None
    assert result["intelligence"] == {"status": "OK"}
