# Product Discovery — Session 03

## Decision
Evidence must be deterministic and reviewable. The model may extract values, but source references are generated independently from page-labelled document text.

## Implemented
- `find_field_evidence(pages, field)` performs conservative label matching.
- `build_evidence_map(pages, schema)` creates a field-to-evidence map.
- `run_audit(..., evidence=...)` accepts evidence metadata.
- `run_pdf_audit_with_evidence(...)` preserves PDF page references through extraction and comparison.
- Added regression tests for page/line evidence and explicit missing evidence.

## Known limitations
- Label matching is intentionally conservative and can miss synonyms or table-based layouts.
- It does not yet prove that the matched line contains the exact extracted value.
- Scanned PDFs/OCR and spreadsheet cell coordinates remain future work.

## Next sprint
Implement value-aware evidence validation: the evidence line must contain a normalized representation of the extracted value, with unit-aware matching and an explicit `NEEDS_REVIEW` outcome when verification fails.
