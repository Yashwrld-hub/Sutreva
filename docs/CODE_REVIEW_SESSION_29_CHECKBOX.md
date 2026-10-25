# Session 29 — Driver Type checkbox extraction hardening

## User-reported defect

A centrifugal-pump audit PDF visibly showed **Driver Type → Induction Motor** selected, while the audit result reported `MISSING`.

## Root cause

The previous implementation handled two common encodings:

1. filled vector circles in `page.objects['curve']`
2. bullet-like text glyphs in `page.objects['char']`

That was incomplete. PDF forms can encode radio/check boxes as **AcroForm widget annotations**, where the selected state is stored in the annotation `/AS` field and the visible selection does not appear as a curve or text glyph.

The parser also needed a fallback for checkbox artwork embedded in an image/XObject.

## Implemented changes

- Detect selected `Btn` annotations through `page.annots`.
- Normalize pdfplumber PDF Name representations such as `/'Btn'` and `/'Induction_Motor'`.
- Use the annotation selection state when it exactly matches a configured acceptable option.
- Add a rasterized-page fallback for embedded checkbox graphics when no vector/glyph/annotation marker is available.
- Render each page at most once for the raster fallback, avoiding repeated page rasterization for every enum option.
- Keep ambiguous/multiple selections unresolved rather than guessing.
- Preserve the deterministic checkbox marker so the value can flow through extraction, comparison, and evidence reporting.

## Test coverage

Added tests for:

- vector checkbox selection
- AcroForm radio-widget selection
- non-first AcroForm option selection
- full-audit propagation from AcroForm state
- raster checkbox artwork fallback
- existing ambiguity behavior

## Validation

- `116 passed`
- Python compilation passed
- deployment sanity check passed
- Ruff/mypy were not available in the current environment, so no claim of a Ruff or mypy clean run is made.

## Remaining validation requirement

The original OEM PDF that produced the user screenshot is not currently available in the project package. The implementation therefore covers the main PDF encodings, but the exact OEM file must still be run through the application before declaring the specific source document fixed.
