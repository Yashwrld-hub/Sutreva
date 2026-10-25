"""Offline tests for graphical checkbox extraction from PDF forms."""

from io import BytesIO

import pdfplumber
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from core import (
    _checkbox_overrides,
    _extract_checkbox_markers,
    _field_anchor_top,
    extract_text_from_pdf,
    load_schema,
)


def _checkbox_pdf(selected=("Induction Motor",)):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 700, "DRIVER TYPE")
    options = [
        (105, "Induction Motor"),
        (260, "Steam Turbine"),
        (440, "Gear"),
    ]
    c.setFont("Helvetica", 10)
    for x, option in options:
        is_selected = option in selected
        c.circle(x, 678, 6, stroke=1, fill=int(is_selected))
        c.drawString(x + 15, 675, option.upper())
    c.save()
    return buf.getvalue()


def _acroform_radio_pdf(selected="Induction Motor"):
    """Build a PDF whose radio buttons are AcroForm widgets, not page curves."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 700, "DRIVER TYPE")
    options = [
        (105, "Induction Motor"),
        (260, "Steam Turbine"),
        (440, "Gear"),
    ]
    c.setFont("Helvetica", 10)
    for x, option in options:
        c.acroForm.radio(
            name="driver_type",
            value=option.replace(" ", "_"),
            selected=(option == selected),
            x=x - 6, y=672, size=12, buttonStyle="circle", borderStyle="solid",
        )
        c.drawString(x + 15, 675, option.upper())
    c.save()
    return buf.getvalue()


def test_extracts_selected_acroform_radio_widget():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    pdf_bytes = _acroform_radio_pdf("Induction Motor")
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        markers = _extract_checkbox_markers(pdf.pages[0], schema)
    assert markers == ["[CHECKBOX SELECTED] Driver Type: Induction Motor"]


def test_extracts_selected_acroform_radio_widget_for_non_first_option():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    pdf_bytes = _acroform_radio_pdf("Gear")
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        markers = _extract_checkbox_markers(pdf.pages[0], schema)
    assert markers == ["[CHECKBOX SELECTED] Driver Type: Gear"]


def test_acroform_checkbox_flows_into_full_audit(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": null, "npsha_available_m": null, '
                        '"casing_material": null, "shaft_material": null, '
                        '"driver_type": null}',
    )
    from core import run_pdf_audit_with_evidence
    rows, _, extracted, _ = run_pdf_audit_with_evidence(_acroform_radio_pdf("Induction Motor"), schema)
    assert extracted["driver_type"] == "Induction Motor"
    driver_row = next(row for row in rows if row["field_name"] == "driver_type")
    assert driver_row["status"] == "MATCHED"
    assert driver_row["evidence"]["source"] == "checkbox_selection"



def _raster_checkbox_pdf(selected="Induction Motor"):
    """Build a PDF with checkbox artwork embedded as a raster image."""
    img = Image.new("RGB", (360, 28), "white")
    draw = ImageDraw.Draw(img)
    options = [(8, "Induction Motor"), (165, "Steam Turbine"), (320, "Gear")]
    for x, option in options:
        cx, cy, r = x, 14, 6
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline="black", width=2)
        if option == selected:
            draw.ellipse((cx-3, cy-3, cx+3, cy+3), fill="black")
    image_buf = BytesIO()
    img.save(image_buf, format="PNG")
    image_buf.seek(0)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 700, "DRIVER TYPE")
    # The image contains only the checkbox graphics. Labels remain PDF text
    # so the fallback can map each detected circle to an option.
    c.drawImage(ImageReader(image_buf), 97, 672, width=360, height=28, mask="auto")
    c.setFont("Helvetica", 10)
    c.drawString(120, 675, "INDUCTION MOTOR")
    c.drawString(277, 675, "STEAM TURBINE")
    c.drawString(432, 675, "GEAR")
    c.save()
    return buf.getvalue()


def test_extracts_raster_checkbox_graphic_when_no_pdf_object_exists():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    pdf_bytes = _raster_checkbox_pdf("Induction Motor")
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[0]
        assert not page.objects.get("curve")
        assert page.objects.get("image")
        markers = _extract_checkbox_markers(page, schema)
    assert markers == ["[CHECKBOX SELECTED] Driver Type: Induction Motor"]

def test_extracts_single_selected_checkbox():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    pdf_bytes = _checkbox_pdf()
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        markers = _extract_checkbox_markers(pdf.pages[0], schema)
    assert markers == ["[CHECKBOX SELECTED] Driver Type: Induction Motor"]


def test_checkbox_selection_is_injected_into_pdf_text():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    text = extract_text_from_pdf(_checkbox_pdf(), schema=schema)
    assert "[CHECKBOX SELECTED] Driver Type: Induction Motor" in text
    assert _checkbox_overrides(text, schema)["driver_type"] == "Induction Motor"


def test_multiple_selected_options_are_left_for_human_review():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    with pdfplumber.open(BytesIO(_checkbox_pdf(selected=("Induction Motor", "Gear")))) as pdf:
        markers = _extract_checkbox_markers(pdf.pages[0], schema)
    assert markers == []


def test_run_audit_prefers_deterministic_checkbox_over_model_null(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    pdf_text = extract_text_from_pdf(_checkbox_pdf(), schema=schema)

    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": null, "npsha_available_m": null, '
                        '"casing_material": null, "shaft_material": null, '
                        '"driver_type": null}',
    )
    from core import run_audit
    rows, _, extracted = run_audit(pdf_text, schema)

    assert extracted["driver_type"] == "Induction Motor"
    driver_row = next(row for row in rows if row["field_name"] == "driver_type")
    assert driver_row["status"] == "MATCHED"


def test_pdf_audit_with_evidence_keeps_checkbox_provenance(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": null, "npsha_available_m": null, '
                        '"casing_material": null, "shaft_material": null, '
                        '"driver_type": null}',
    )
    from core import run_pdf_audit_with_evidence
    rows, _, _, _ = run_pdf_audit_with_evidence(_checkbox_pdf(), schema)
    driver_row = next(row for row in rows if row["field_name"] == "driver_type")
    assert driver_row["status"] == "MATCHED"
    assert driver_row["evidence"]["source"] == "checkbox_selection"
    assert "CHECKBOX SELECTED" in driver_row["evidence"]["text"]


def test_provided_oem_datasheet_extracts_driver_type_checkbox():
    """Regression test using the OEM PDF supplied for the failing case."""
    schema = load_schema("templates/centrifugal_pump_audit.json")
    with open("tests/fixtures/provided_driver_type_case.pdf", "rb") as fh:
        pdf_bytes = fh.read()
    text = extract_text_from_pdf(pdf_bytes, schema=schema)
    assert _checkbox_overrides(text, schema)["driver_type"] == "Induction Motor"


def test_driver_type_anchor_does_not_match_unrelated_drivers_heading():
    """Regression for repeated generic 'driver/drivers' words in the form."""
    with open("tests/fixtures/provided_driver_type_case.pdf", "rb") as fh:
        pdf_bytes = fh.read()
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        anchor = _field_anchor_top(page, "Driver Type", words)
    assert 430 <= anchor <= 440
