# Product Discovery Session 04 — Engineering Unit Safety

## Decision
Add a conservative unit-normalization layer as a reusable domain module. It must never guess unsupported conversions.

## Implemented
- Canonical aliases for common temperature, pressure, dimensional and speed units.
- Explicit conversions for selected safe pairs.
- Rejection of unsupported conversions.
- Conversion metadata for traceability.
- Regression tests for temperature, pressure, rejection, and metadata.

## Not yet claimed
This is not a complete dimensional-analysis engine. Gauge/absolute pressure semantics, compound units, and source-unit extraction still require domain-specific validation.

## Next review
Design a structured extraction contract containing value, source unit, target unit, evidence reference, and verification state.
