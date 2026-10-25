# Product Discovery Session 27 — Graphical Checkbox Extraction Fix

## Problem

Some OEM datasheets represent enum fields with a row of graphical checkboxes.
The text layer contains the option labels but not the selected state. The audit
therefore previously reported fields such as `Driver Type` as `MISSING` even
when a checkbox was visibly selected.

## Fix

The PDF ingestion layer now inspects small filled circular PDF vector graphics
and common filled checkbox glyphs. When exactly one accepted option is found
next to the field options, ingestion adds a deterministic source marker:

`[CHECKBOX SELECTED] Driver Type: Induction Motor`

The extractor applies that marker as a deterministic override of the model
output. Ambiguous cases (for example, multiple selected options) are left
unresolved for human review rather than guessed.

## Scope

This fixes digitally-created PDFs whose checkbox state is represented in the PDF
content stream. Scanned/photographed PDFs remain outside the current OCR scope.

## Acceptance criteria

- Single selected accepted checkbox is extracted correctly.
- Model `null` cannot overwrite a deterministic checkbox selection.
- Multiple selected options remain unresolved.
- Evidence contains the checkbox marker and retains page/line provenance.
- Existing audit behavior remains unchanged for ordinary text fields.

## Validation

An offline ReportLab vector-checkbox fixture and end-to-end evidence test were
added. The repository test suite is run from `tests/` to avoid external/root
connection checks.
