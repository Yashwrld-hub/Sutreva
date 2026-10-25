# Sutreva — Session 48 Engineering Intelligence v1

## Objective
Translate authoritative audit outcomes into engineering-facing exceptions that help reviewers prioritize action without changing the underlying compliance status.

## New module
`engineering_intelligence.py`

The module classifies:

- `MISSING` → `MISSING_REQUIRED_DATA`
- `MISMATCHED` → `SPECIFICATION_MISMATCH`
- `OUT OF RANGE` → `LIMIT_EXCEEDED`
- `NEEDS_REVIEW` → `EVIDENCE_GAP`

Each exception includes:

- severity
- engineering impact
- recommended action
- extracted value
- deterministic source evidence
- optional Nemotron assessment/risk

## Authority boundary

The layer never changes the authoritative `core.py` status. A Nemotron risk of HIGH can raise the presentation severity of an exception, but it cannot convert MATCHED to MISMATCHED or approve/reject an item.

## UI

The shared audit-results view now exposes:

- total engineering exceptions
- critical exceptions
- high-severity exceptions
- files containing blocking exceptions
- field-level exception table

This applies to both PDF/batch and structured bulk results because the layer consumes the common audit-row contract.

## Validation

- 164 tests passed
- deployment sanity check passed
- Python compilation passed

## Next boundary

The next step can use these deterministic exception objects as inputs to richer domain reasoning, equipment-family rules, and eventually historical engineering-pattern analysis without coupling those capabilities to the UI.
