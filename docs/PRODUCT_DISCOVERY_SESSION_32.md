# OEM Audit Copilot — Product / UX Review Session 32

## Objective
Improve the visible product experience without changing the proven extraction/comparison workflow used for the human-vs-tool pilot.

## Decisions

- Keep the product name **OEM Audit Copilot** for the current pilot.
- Position it as **Evidence-backed engineering document intelligence**.
- Centralize product identity in `product_brand.py` so a future rename does not require repository-wide edits.
- Keep the visual language industrial and restrained rather than promotional or chatbot-like.
- Reorganize navigation labels around the engineering workflow: Audit, Bulk Audit, Pilot Dashboard, Review Queue, Templates.
- Make the audit session context visible before a run: template, field count, project, and document revision.
- Keep AI-assisted findings explicitly subject to qualified engineering verification.

## UX changes in this sprint

- Added a compact product hero/header.
- Added a persistent audit-session context block to the Audit view.
- Added workflow guidance: Upload → Analyze → Review evidence → Export.
- Improved result-section hierarchy and reviewer guidance.
- Renamed administration/review labels to make their purpose clearer.
- Added a small centralized branding module and regression tests for product identity/navigation.

## Explicitly not changed

- Extraction algorithms and deterministic OEM overrides.
- Comparison rules and engineering status logic.
- Evidence model and review persistence.
- Pilot benchmark methodology.

The UX sprint therefore does not contaminate the current human-vs-tool benchmark with algorithm changes.

## Remaining UX work

- Clickable evidence-to-source navigation in the result table.
- Dedicated finding detail card with extraction status vs compliance status.
- Reviewer usability test with 2–3 engineers.
- Accessible color/status treatment and keyboard navigation review.
