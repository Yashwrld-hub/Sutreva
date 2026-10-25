import time

import pytest

from core import audit_summary, delete_template, list_templates, load_schema, save_template
from exports import (
    suggested_filename,
    to_csv_bytes,
    to_excel_bytes,
    to_pdf_bytes,
)


SAMPLE_ROWS = [
    {"field": "Seal Face Material", "unit": "", "extracted_value": "Silicon Carbide", "status": "MATCHED"},
    {"field": "Max Operating Temp", "unit": "C", "extracted_value": 180, "status": "MATCHED"},
    {"field": "API Plan", "unit": "", "extracted_value": None, "status": "MISSING"},
    {"field": "Seal Chamber Pressure", "unit": "bar", "extracted_value": 9, "status": "OUT OF RANGE"},
]


# ---------- audit_summary ----------

def test_audit_summary_counts():
    s = audit_summary(SAMPLE_ROWS)
    assert s["MATCHED"] == 2
    assert s["MISSING"] == 1
    assert s["OUT OF RANGE"] == 1
    assert s["MISMATCHED"] == 0
    assert s["TOTAL"] == 4


def test_audit_summary_empty():
    s = audit_summary([])
    assert s["TOTAL"] == 0
    assert s["MATCHED"] == 0


# ---------- exports produce valid files ----------

def test_excel_export_is_valid_xlsx():
    data = to_excel_bytes(SAMPLE_ROWS, "Mechanical Seal Audit", "FS-A21.pdf")
    assert data[:2] == b"PK"          # xlsx is a zip archive
    assert len(data) > 3000


def test_pdf_export_is_valid_pdf():
    data = to_pdf_bytes(SAMPLE_ROWS, "Mechanical Seal Audit", "FS-A21.pdf")
    assert data[:4] == b"%PDF"
    assert len(data) > 1000


def test_csv_export_contains_data_and_summary():
    text = to_csv_bytes(SAMPLE_ROWS, "Mechanical Seal Audit", "FS-A21.pdf").decode("utf-8")
    assert "Seal Face Material" in text
    assert "OUT OF RANGE" in text
    assert "Summary" in text
    assert "Total,4" in text


def test_csv_export_renders_none_as_dash():
    text = to_csv_bytes(SAMPLE_ROWS, "T", "").decode("utf-8")
    # The MISSING row's value should not appear as the literal "None"
    assert ",None," not in text


def test_exports_handle_empty_rows():
    # Should not raise even with nothing to report
    assert to_excel_bytes([], "Empty", "")[:2] == b"PK"
    assert to_pdf_bytes([], "Empty", "")[:4] == b"%PDF"
    assert b"Summary" in to_csv_bytes([], "Empty", "")


# ---------- filenames ----------

def test_suggested_filename_shape():
    name = suggested_filename("Mechanical Seal Audit", "xlsx", "FS-A21.pdf")
    assert name.startswith("mechanical_seal_audit_")
    assert name.endswith(".xlsx")
    assert " " not in name


def test_suggested_filename_without_source():
    name = suggested_filename("Pump Audit", "pdf")
    assert name.startswith("pump_audit_")
    assert name.endswith(".pdf")


# ---------- caching correctness ----------

def test_load_schema_cache_busts_on_edit(tmp_path):
    """Caching must not serve stale data after a template is edited."""
    folder = tmp_path / "templates"
    folder.mkdir()

    p1 = save_template("Cache Test", [{"field_name": "a", "label": "A"}], folder=str(folder))
    first = load_schema(p1)
    assert len(first["fields"]) == 1

    # mtime has 1s granularity on some filesystems, so ensure a distinct stamp
    time.sleep(1.1)

    p2 = save_template(
        "Cache Test",
        [{"field_name": "a", "label": "A"}, {"field_name": "b", "label": "B"}],
        folder=str(folder),
    )
    second = load_schema(p2)
    assert len(second["fields"]) == 2, "Cache served stale template after edit"


def test_list_templates_cache_busts_on_new_file(tmp_path):
    folder = tmp_path / "templates"
    folder.mkdir()

    save_template("First", [{"field_name": "a", "label": "A"}], folder=str(folder))
    assert len(list_templates(str(folder))) == 1

    time.sleep(1.1)

    save_template("Second", [{"field_name": "b", "label": "B"}], folder=str(folder))
    found = list_templates(str(folder))
    assert len(found) == 2, "Cache served stale template list after adding a file"
    assert "Second" in found


def test_list_templates_missing_folder_returns_empty(tmp_path):
    assert list_templates(str(tmp_path / "does_not_exist")) == {}


# ---------- save/delete ----------

def test_save_template_rejects_invalid_field(tmp_path):
    """A field missing 'label' must be rejected before it's written to disk."""
    with pytest.raises(ValueError):
        save_template("Bad", [{"field_name": "x"}], folder=str(tmp_path))


def test_delete_template_removes_file(tmp_path):
    path = save_template("To Delete", [{"field_name": "a", "label": "A"}], folder=str(tmp_path))
    delete_template(path)
    with pytest.raises(ValueError):
        load_schema(path)


def test_delete_missing_template_raises(tmp_path):
    with pytest.raises(ValueError):
        delete_template(str(tmp_path / "nope.json"))


def test_bulk_pdf_wraps_long_identifier_without_rendering_overflow():
    """Long uploaded filenames must stay inside the PDF table cell."""
    from exports import to_pdf_bytes_bulk

    long_filename = (
        "ilide.info-api-610-10th-edition-rated-70kw-centrifugal-pump-datasheet-"
        "pr_6392952fd3fe449d7288ed54f06d3516.pdf"
    )
    results = [{
        "identifier": long_filename,
        "rows": [
            {"field": "Rated Power", "unit": "kW", "extracted_value": 70, "status": "MATCHED"},
            {"field": "NPSH Available", "unit": "m", "extracted_value": 3.6, "status": "MATCHED"},
            {"field": "Casing Material", "unit": "", "extracted_value": None, "status": "MISSING"},
            {"field": "Shaft Material", "unit": "", "extracted_value": None, "status": "MISSING"},
            {"field": "Impeller Diameter", "unit": "mm", "extracted_value": 310, "status": "MATCHED"},
        ],
        "summary": {"MATCHED": 3, "MISSING": 2, "MISMATCHED": 0, "OUT OF RANGE": 0, "TOTAL": 5},
    }]
    from exports import _pdf_safe_text

    data = to_pdf_bytes_bulk(results, "Centrifugal Pump Audit", "File")
    assert data[:4] == b"%PDF"
    assert "<br/>" in _pdf_safe_text(long_filename)
