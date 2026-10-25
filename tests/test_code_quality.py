from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CORE = ROOT / "core.py"


def test_deployment_has_no_backup_source_file():
    assert not (ROOT / "app.py.bak").exists()


def test_bulk_mapping_uses_shared_label_normalizer():
    source = CORE.read_text(encoding="utf-8")
    assert "def _normalize(" not in source
    assert "_NORM_RE" not in source
    assert "_norm_label(col)" in source


def test_pdf_batch_upload_uses_evidence_aware_audit_path():
    source = APP.read_text(encoding="utf-8")
    assert "run_pdf_audit_with_evidence(" in source
    assert "run_batch_pdf_audit(" in source
    # PDFs must remain as bytes until the audit worker so page/evidence context
    # is not discarded during multi-file processing.
    assert "extract_text_from_pdf(" not in source


def test_pdf_page_extraction_has_single_shared_implementation():
    source = CORE.read_text(encoding="utf-8")
    assert "def _extract_pdf_page_texts(" in source
    assert "def extract_pdf_pages_with_evidence(" in source
    assert "return pages\n    return pages" not in source
