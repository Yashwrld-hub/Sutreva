# Session 26 — PDF Table Overflow Fix

## Issue

The bulk PDF audit report allowed raw strings to be placed directly into ReportLab table cells. Long uploaded filenames therefore exceeded the identifier column width and visually overlapped the Field, Unit, Extracted Value, and Status columns.

## Root cause

`Table(...)` was receiving plain Python strings. ReportLab can wrap `Paragraph` objects reliably, but a long unbroken filename has no guaranteed wrapping point when kept as a raw string.

## Fix

- Convert PDF table headers and body cells to `Paragraph` objects.
- Add controlled line wrapping for unusually long tokens using explicit `<br/>` breaks.
- HTML-escape user/document text before passing it to ReportLab.
- Give the File/identifier column more width in the bulk report.
- Apply status text styling through Paragraph styles and keep status background styling in the table.
- Apply the same safe text handling to the single-document PDF source-document line.

## Validation

The exact long filename shape from the reported issue was rendered to PDF and visually checked. The filename stays inside its own column; Field, Unit, Extracted Value, and Status remain aligned.

The automated test suite contains 102 tests, all passing, and the project compiles successfully.

## Scope

This is a presentation-layer fix only. It does not change extraction, comparison, audit rules, evidence, or engineering decisions.
