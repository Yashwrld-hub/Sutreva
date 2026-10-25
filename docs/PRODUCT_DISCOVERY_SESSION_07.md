# Product Discovery Session 07 — Conflict Detection

## Objective
Detect multiple distinct extracted values for the same engineering parameter before an audit result is treated as reliable.

## Implemented
- Added deterministic `detect_conflicts()` helper.
- Groups non-empty values by `field_name`.
- Ignores duplicate values and missing values.
- Preserves record indexes and distinct values in a structured `Conflict` object.
- Added regression tests.

## Safety boundaries
- This is a conflict signal, not an automatic engineering rejection.
- Numeric equivalence across units is not inferred here; normalization must occur before comparison.
- Context such as document revision, operating case, and section priority should be added in a later iteration.

## Next sprint
Build a review queue that combines conflicts, missing evidence, unit-conversion warnings, and rule mismatches into prioritized engineer actions.
