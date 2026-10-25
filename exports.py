"""
exports.py — turns an audit result into a downloadable file.

Kept separate from core.py so the extraction/comparison logic stays free of
any formatting concerns. Every function returns raw bytes, so the caller
(Streamlit, CLI, or anything else) decides what to do with them.
"""

import csv
import io
import textwrap
from datetime import datetime
from html import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core import audit_summary, slugify


# Shared status colours, used by both the Excel and PDF exports.
STATUS_COLORS = {
    "MATCHED": ("2E7D32", "E8F5E9"),      # text, fill
    "MISSING": ("C62828", "FFEBEE"),
    "MISMATCHED": ("B8720A", "FFF8E1"),
    "OUT OF RANGE": ("B8720A", "FFF8E1"),
    "NEEDS_REVIEW": ("6D5BD0", "F3E8FF"),
}

HEADERS = ["Field", "Unit", "Extracted Value", "Status"]


def _summary_keys(summary):
    base = ["MATCHED", "MISSING", "MISMATCHED", "OUT OF RANGE"]
    if summary.get("NEEDS_REVIEW", 0):
        base.append("NEEDS_REVIEW")
    base.append("TOTAL")
    return base


def _summary_label(key):
    return key.replace("_", " ").title()


def _flatten_bulk(results):
    return [(r["identifier"], row) for r in results for row in r["rows"]]


def _row_values(row):
    value = row["extracted_value"]
    return [
        row["field"],
        row.get("unit", ""),
        "—" if value is None or value == "" else str(value),
        row["status"],
    ]


def _build_file_centric_bulk_table(results, identifier_label="Equipment"):
    fields = []
    for result in results:
        for row in result.get("rows", []):
            field = row.get("field", "")
            if field and field not in fields:
                fields.append(field)

    headers = [identifier_label, *fields, "Overall Status", "Review Fields"]
    records = []
    status_records = []

    for result in results:
        row_by_field = {row.get("field", ""): row for row in result.get("rows", [])}
        values = [result.get("identifier", "")]
        statuses = {}
        for field in fields:
            row = row_by_field.get(field)
            if row is None:
                values.append("—")
                statuses[field] = "MISSING"
                continue
            value = row.get("extracted_value")
            values.append("—" if value in (None, "") else str(value))
            statuses[field] = row.get("status", "")

        if result.get("error"):
            overall = "ERROR"
        elif any(status in ("MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW")
                 for status in statuses.values()):
            overall = "REVIEW"
        else:
            overall = "MATCHED"

        review_fields = ", ".join(
            field for field, status in statuses.items() if status not in ("MATCHED", "")
        ) or "—"
        values.extend([overall, review_fields])
        records.append(values)
        status_records.append(statuses)

    return headers, records, status_records


def _pdf_safe_text(value):
    text = "" if value is None else str(value)
    if len(text) <= 32:
        return escape(text, quote=False) or " "

    chunks = textwrap.wrap(
        text, width=32, break_long_words=True, break_on_hyphens=True,
        replace_whitespace=False, drop_whitespace=False,
    )
    return "<br/>".join(escape(chunk, quote=False) for chunk in chunks) or " "


def _pdf_paragraph(value, style):
    return Paragraph(_pdf_safe_text(value), style)


def _build_pdf_table_data(headers, rows, body_style, header_style, status_styles=None):
    header_cells = [_pdf_paragraph(header, header_style) for header in headers]
    body_cells = []
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            style = status_styles.get(value, body_style) if status_styles and index == len(row) - 1 else body_style
            cells.append(_pdf_paragraph(value, style))
        body_cells.append(cells)
    return [header_cells] + body_cells


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

def to_csv_bytes(rows, template_name, source_name=""):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"OEM Audit Report — {template_name}"])
    if source_name:
        writer.writerow([f"Source document: {source_name}"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow(_row_values(row))

    summary = audit_summary(rows)
    writer.writerow([])
    writer.writerow(["Summary"])
    for key in _summary_keys(summary):
        writer.writerow([_summary_label(key), summary.get(key, 0)])

    return buf.getvalue().encode("utf-8")


# --------------------------------------------------------------------------
# Excel
# --------------------------------------------------------------------------

def to_excel_bytes(rows, template_name, source_name=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Audit Report"

    thin = Side(style="thin", color="D0D4DC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = f"OEM Audit Report — {template_name}"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="14213D")
    ws.merge_cells("A1:D1")

    ws["A2"] = f"Source document: {source_name or 'n/a'}"
    ws["A3"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    for cell in ("A2", "A3"):
        ws[cell].font = Font(name="Arial", size=9, color="5A6478")
        ws.merge_cells(f"{cell}:D{cell[1:]}")

    header_row = 5
    for col, title in enumerate(HEADERS, start=1):
        c = ws.cell(row=header_row, column=col, value=title)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="14213D")
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border = border
    ws.row_dimensions[header_row].height = 22

    for i, row in enumerate(rows, start=header_row + 1):
        values = _row_values(row)
        for col, value in enumerate(values, start=1):
            c = ws.cell(row=i, column=col, value=value)
            c.font = Font(name="Arial", size=10)
            c.border = border
            c.alignment = Alignment(vertical="center")

        status = row["status"]
        if status in STATUS_COLORS:
            text_color, fill_color = STATUS_COLORS[status]
            sc = ws.cell(row=i, column=4)
            sc.font = Font(name="Arial", size=10, bold=True, color=text_color)
            sc.fill = PatternFill("solid", fgColor=fill_color)

    summary = audit_summary(rows)
    start = header_row + len(rows) + 2
    ws.cell(row=start, column=1, value="Summary").font = Font(
        name="Arial", size=11, bold=True, color="14213D")

    for offset, key in enumerate(_summary_keys(summary), start=1):
        ws.cell(row=start + offset, column=1, value=_summary_label(key)).font = Font(name="Arial", size=10)
        vc = ws.cell(row=start + offset, column=2, value=summary.get(key, 0))
        vc.font = Font(name="Arial", size=10, bold=(key == "TOTAL"))

    for col, width in zip(range(1, 5), (34, 10, 30, 16), strict=True):
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def to_pdf_bytes(rows, template_name, source_name=""):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"OEM Audit Report — {template_name}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleX", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=colors.HexColor("#14213D"), spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "MetaX", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=colors.HexColor("#5A6478"),
    )
    h2_style = ParagraphStyle(
        "H2X", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=colors.HexColor("#14213D"), spaceBefore=16, spaceAfter=6,
    )
    table_header_style = ParagraphStyle(
        "TableHeaderX", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, leading=10, textColor=colors.white,
    )
    table_body_style = ParagraphStyle(
        "TableBodyX", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9.5, wordWrap="LTR",
    )

    story = [
        Paragraph(f"OEM Audit Report — {escape(str(template_name), quote=False)}", title_style),
        _pdf_paragraph(f"Source document: {source_name or 'n/a'}", meta_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Spacer(1, 14),
    ]

    status_styles = {
        status: ParagraphStyle(
            f"TableStatus_{status.replace(' ', '_')}", parent=table_body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(f"#{STATUS_COLORS[status][0]}"),
        )
        for status in STATUS_COLORS
    }
    table_rows = [_row_values(r) for r in rows]
    data = _build_pdf_table_data(HEADERS, table_rows, table_body_style, table_header_style, status_styles)
    table = Table(data, colWidths=[62 * mm, 20 * mm, 56 * mm, 32 * mm], repeatRows=1)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14213D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for i, row in enumerate(rows, start=1):
        if row["status"] in STATUS_COLORS:
            _, fill_color = STATUS_COLORS[row["status"]]
            style.append(("BACKGROUND", (3, i), (3, i), colors.HexColor(f"#{fill_color}")))

    table.setStyle(TableStyle(style))
    story.append(table)

    summary = audit_summary(rows)
    story.append(Paragraph("Summary", h2_style))
    summary_data = [
        [_summary_label(key), str(summary.get(key, 0))]
        for key in _summary_keys(summary)
    ]
    summary_table = Table(summary_data, colWidths=[40 * mm, 20 * mm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DC")),
    ]))
    story.append(summary_table)

    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "Generated by Sutreva. Extracted values are AI-assisted and "
        "should be verified by a qualified engineer before sign-off.",
        meta_style,
    ))

    doc.build(story)
    return buf.getvalue()


def suggested_filename(template_name, extension, source_name=""):
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = slugify(template_name)
    if source_name:
        base = f"{base}_{slugify(source_name.rsplit('.', 1)[0])[:28]}"
    return f"{base}_{stamp}.{extension}"


# --------------------------------------------------------------------------
# Bulk exports
# --------------------------------------------------------------------------

def to_excel_bytes_bulk(results, template_name, identifier_label="Equipment"):
    wb = Workbook()
    thin = Side(style="thin", color="D0D4DC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws1 = wb.active
    ws1.title = "Overview"
    ws1["A1"] = f"Audit Overview — {template_name}"
    ws1["A1"].font = Font(name="Arial", size=14, bold=True, color="14213D")
    ws1["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws1["A2"].font = Font(name="Arial", size=9, color="5A6478")

    headers, file_rows, status_records = _build_file_centric_bulk_table(results, identifier_label)
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(headers)))
    for col, title in enumerate(headers, start=1):
        c = ws1.cell(row=4, column=col, value=title)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="14213D")
        c.border = border
        c.alignment = Alignment(vertical="center", wrap_text=True)

    for i, values in enumerate(file_rows, start=5):
        for col, value in enumerate(values, start=1):
            c = ws1.cell(row=i, column=col, value=value)
            c.font = Font(name="Arial", size=10)
            c.border = border
            c.alignment = Alignment(vertical="top", wrap_text=True)

        overall_col = len(headers) - 1
        overall = values[overall_col]
        if overall == "REVIEW":
            ws1.cell(row=i, column=overall_col + 1).font = Font(
                name="Arial", size=10, bold=True, color="B8720A"
            )
        elif overall == "ERROR":
            ws1.cell(row=i, column=overall_col + 1).font = Font(
                name="Arial", size=10, bold=True, color="C62828"
            )
        elif overall == "MATCHED":
            ws1.cell(row=i, column=overall_col + 1).font = Font(
                name="Arial", size=10, bold=True, color="2E7D32"
            )

    widths = [30] + [24] * (len(headers) - 3) + [16, 34]
    for col, width in zip(range(1, len(headers) + 1), widths, strict=True):
        ws1.column_dimensions[get_column_letter(col)].width = width
    ws1.freeze_panes = "A5"
    ws1.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{max(4, len(file_rows) + 4)}"

    ws2 = wb.create_sheet("Detail")
    detail_headers = [identifier_label, "Field", "Unit", "Extracted Value", "Status"]
    for col, title in enumerate(detail_headers, start=1):
        c = ws2.cell(row=1, column=col, value=title)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="14213D")
        c.border = border

    flat = _flatten_bulk(results)
    for i, (identifier, row) in enumerate(flat, start=2):
        values = [identifier] + _row_values(row)
        for col, value in enumerate(values, start=1):
            c = ws2.cell(row=i, column=col, value=value)
            c.font = Font(name="Arial", size=10)
            c.border = border

        if row["status"] in STATUS_COLORS:
            text_color, fill_color = STATUS_COLORS[row["status"]]
            sc = ws2.cell(row=i, column=5)
            sc.font = Font(name="Arial", size=10, bold=True, color=text_color)
            sc.fill = PatternFill("solid", fgColor=fill_color)

    for col, width in zip(range(1, 6), (26, 26, 10, 24, 16), strict=True):
        ws2.column_dimensions[get_column_letter(col)].width = width
    ws2.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf_bytes_bulk(results, template_name, identifier_label="Equipment"):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Audit Report — {template_name}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleX", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=15, textColor=colors.HexColor("#14213D"), spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "MetaX", parent=styles["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=colors.HexColor("#5A6478"),
    )
    table_header_style = ParagraphStyle(
        "BulkTableHeaderX", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.8, leading=9, textColor=colors.white,
    )
    table_body_style = ParagraphStyle(
        "BulkTableBodyX", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.5, leading=9, wordWrap="LTR",
    )

    n_items = len(results)
    n_flagged = sum(1 for r in results if r["summary"]["MATCHED"] != r["summary"]["TOTAL"])
    used_ai = any(r.get("raw_output") for r in results)

    story = [
        Paragraph(f"Audit Report — {escape(str(template_name), quote=False)}", title_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Paragraph(f"{n_items} {escape(str(identifier_label), quote=False).lower()} record(s) audited · {n_flagged} with at least one issue", meta_style),
        Spacer(1, 12),
    ]

    headers, file_rows, status_records = _build_file_centric_bulk_table(results, identifier_label)
    status_styles = {
        status: ParagraphStyle(
            f"BulkTableStatus_{status.replace(' ', '_')}", parent=table_body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(f"#{STATUS_COLORS.get(status, ('14213D', 'FFFFFF'))[0]}"),
        )
        for status in (*STATUS_COLORS.keys(), "MATCHED", "REVIEW", "ERROR")
    }
    data = _build_pdf_table_data(
        headers, file_rows, table_body_style, table_header_style, status_styles
    )
    n_cols = len(headers)
    identifier_width = 45 * mm
    status_width = 25 * mm
    review_width = 45 * mm
    remaining_width = 269 * mm - identifier_width - status_width - review_width
    field_width = remaining_width / max(1, n_cols - 3)
    col_widths = [identifier_width] + [field_width] * (n_cols - 3) + [status_width, review_width]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14213D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    overall_col = n_cols - 2
    for i, values in enumerate(file_rows, start=1):
        overall = values[overall_col]
        if overall == "REVIEW":
            style.append(("BACKGROUND", (overall_col, i), (overall_col, i), colors.HexColor("#FFF8E1")))
        elif overall == "ERROR":
            style.append(("BACKGROUND", (overall_col, i), (overall_col, i), colors.HexColor("#FFEBEE")))
        elif overall == "MATCHED":
            style.append(("BACKGROUND", (overall_col, i), (overall_col, i), colors.HexColor("#E8F5E9")))

    table.setStyle(TableStyle(style))
    story.append(table)
    story.append(Spacer(1, 16))

    footer_text = (
        "Generated by Sutreva. Extracted values are AI-assisted and "
        "should be verified by a qualified engineer before sign-off."
        if used_ai else
        "Generated by Sutreva. Values were mapped directly from the "
        "uploaded spreadsheet — no AI extraction was used for this report."
    )
    story.append(Paragraph(footer_text, meta_style))

    doc.build(story)
    return buf.getvalue()


def to_csv_bytes_bulk(results, template_name, identifier_label="Equipment"):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"Audit Report — {template_name}"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])

    headers, file_rows, _ = _build_file_centric_bulk_table(results, identifier_label)
    writer.writerow(headers)
    writer.writerows(file_rows)

    writer.writerow([])
    writer.writerow(["Detailed Field Results"])
    writer.writerow([identifier_label, "Field", "Unit", "Extracted Value", "Status"])
    for identifier, row in _flatten_bulk(results):
        writer.writerow([identifier] + _row_values(row))

    writer.writerow([])
    has_needs_review = any(r.get("summary", {}).get("NEEDS_REVIEW", 0) for r in results)
    if has_needs_review:
        writer.writerow([identifier_label, "Matched", "Missing", "Mismatched", "Out of Range", "Needs Review", "Total"])
        for r in results:
            s = r["summary"]
            writer.writerow([r["identifier"], s["MATCHED"], s["MISSING"], s["MISMATCHED"], s["OUT OF RANGE"], s.get("NEEDS_REVIEW", 0), s["TOTAL"]])
    else:
        writer.writerow([identifier_label, "Matched", "Missing", "Mismatched", "Out of Range", "Total"])
        for r in results:
            s = r["summary"]
            writer.writerow([r["identifier"], s["MATCHED"], s["MISSING"], s["MISMATCHED"], s["OUT OF RANGE"], s["TOTAL"]])

    return buf.getvalue().encode("utf-8")



# --------------------------------------------------------------------------
# EPC Technical Query (TQ) / Comments Resolution Sheet (CRS) Exports
# --------------------------------------------------------------------------

TQ_HEADERS = [
    "Sr. No.",
    "Equipment / File",
    "Page / Line Ref",
    "Parameter",
    "Governing Requirement",
    "Vendor Offered Value",
    "Audit Status",
    "Technical Query / Required Action",
    "Vendor Response",
    "Closure Status",
]


def _format_rule_requirement(rule, unit=""):
    if not isinstance(rule, dict):
        return "As per specification"
    rtype = rule.get("type")
    rval = rule.get("value")
    unit_suffix = f" {unit}" if unit else ""
    if rtype == "acceptable_values" and isinstance(rval, list):
        return "One of: " + ", ".join(str(v) for v in rval)
    if rtype == "expected_value":
        return f"Must equal {rval}{unit_suffix}"
    if rtype == "max_value":
        return f"Max {rval}{unit_suffix}"
    if rtype == "min_value":
        return f"Min {rval}{unit_suffix}"
    return "Record required"


def _build_tq_question(row, identifier):
    field = row.get("field") or row.get("field_name") or "Parameter"
    status = row.get("status") or "REVIEW"
    val = row.get("extracted_value")
    unit = row.get("unit") or ""
    req_str = _format_rule_requirement(row.get("rule"), unit)
    if status == "MISSING":
        return (
            f"Vendor to furnish '{field}' ({req_str}). Parameter was omitted or blank in {identifier}; "
            f"please update datasheet and confirm compliance."
        )
    if status == "OUT OF RANGE":
        return (
            f"Offered '{field}' ({val} {unit}) exceeds governing limit ({req_str}). "
            f"Vendor to confirm design basis or revise selection to comply."
        )
    if status == "MISMATCHED":
        return (
            f"Offered '{field}' ({val}) deviates from specified requirement ({req_str}). "
            f"Vendor to confirm compliance with governing specification or submit formal deviation request."
        )
    if any(q in str(val or "").lower() for q in ("ample", "adequate", "standard")):
        return (
            f"Datasheet states qualitative '{val}' for '{field}' ({req_str}). "
            f"Vendor to provide explicit numeric/material specification for engineering sign-off."
        )
    return (
        f"Verify source value '{val}' for '{field}' against governing requirement ({req_str}) "
        f"and confirm on next datasheet revision."
    )


def build_technical_query_rows(results):
    """Build structured EPC Technical Query (TQ) / Comments Resolution Sheet (CRS) records."""
    tq_rows = []
    sr_no = 1
    for result in results:
        identifier = result.get("identifier", "Document")
        if result.get("error"):
            tq_rows.append([
                sr_no,
                identifier,
                "—",
                "Document Ingestion",
                "Readable PDF/Text Datasheet",
                "ERROR",
                "ERROR",
                f"Document could not be processed ({result.get('error')}). Vendor to re-issue clean searchable PDF.",
                "",
                "OPEN",
            ])
            sr_no += 1
            continue
        for row in result.get("rows", []):
            status = row.get("status", "")
            if status in ("MATCHED", ""):
                continue
            ev = row.get("evidence") or {}
            page_line = (
                f"Page {ev.get('page')}, Line {ev.get('line')}"
                if ev.get("page") and ev.get("line")
                else (f"Page {ev.get('page')}" if ev.get("page") else "Not cited")
            )
            val = row.get("extracted_value")
            val_display = "— (Blank)" if val in (None, "") else str(val)
            tq_rows.append([
                sr_no,
                identifier,
                page_line,
                row.get("field", ""),
                _format_rule_requirement(row.get("rule"), row.get("unit", "")),
                val_display,
                status,
                _build_tq_question(row, identifier),
                "",
                "OPEN",
            ])
            sr_no += 1
    return tq_rows


def to_tq_csv_bytes(results, template_name):
    """Export EPC Technical Query (TQ) / Comments Resolution Sheet (CRS) as CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"COMMENTS RESOLUTION SHEET (CRS) / TECHNICAL QUERIES — {template_name}"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    writer.writerow(TQ_HEADERS)
    for r in build_technical_query_rows(results):
        writer.writerow(r)
    return buf.getvalue().encode("utf-8")


def to_tq_excel_bytes(results, template_name):
    """Export EPC Technical Query (TQ) / Comments Resolution Sheet (CRS) as formatted Excel (.xlsx)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments Resolution Sheet"

    thin = Side(style="thin", color="D0D4DC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = f"COMMENTS RESOLUTION SHEET (CRS) & TECHNICAL QUERIES — {template_name}"
    ws["A1"].font = Font(name="Arial", size=13, bold=True, color="14213D")
    ws.merge_cells("A1:J1")

    ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Issue to Vendor / Bidder for Technical Clarification"
    ws["A2"].font = Font(name="Arial", size=9, color="5A6478")
    ws.merge_cells("A2:J2")

    for col, title in enumerate(TQ_HEADERS, start=1):
        c = ws.cell(row=4, column=col, value=title)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="14213D")
        c.border = border
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 24

    tq_rows = build_technical_query_rows(results)
    for i, values in enumerate(tq_rows, start=5):
        for col, value in enumerate(values, start=1):
            c = ws.cell(row=i, column=col, value=value)
            c.font = Font(name="Arial", size=9.5)
            c.border = border
            c.alignment = Alignment(vertical="top", wrap_text=True)
        status = values[6]
        if status in STATUS_COLORS:
            t_col, f_col = STATUS_COLORS[status]
            sc = ws.cell(row=i, column=7)
            sc.font = Font(name="Arial", size=9.5, bold=True, color=t_col)
            sc.fill = PatternFill("solid", fgColor=f_col)

    widths = (8, 28, 16, 22, 24, 20, 15, 48, 28, 14)
    for col, width in zip(range(1, 11), widths, strict=True):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A5"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
