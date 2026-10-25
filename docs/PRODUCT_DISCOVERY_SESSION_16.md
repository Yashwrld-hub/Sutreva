# Product Discovery Session 16 — Pilot Validation

## Decision
Introduce a deterministic pilot QA layer before making performance or accuracy claims.

## Added
- Benchmark comparison keyed by a stable field identifier.
- Accuracy and disagreement reporting.
- Missing prediction/benchmark detection.
- Evidence coverage reporting with an explicit limitation: coverage does not prove evidence correctness.

## Acceptance criteria
1. Every pilot case has a human-reviewed benchmark.
2. Status disagreements are surfaced, never silently overwritten.
3. Evidence coverage and extraction accuracy are reported separately.
4. Metrics are reproducible from the same inputs.
5. No metric is presented as engineering approval.

## Next step
Create a pilot case pack using sanitized, representative pump and compressor documents, then have a qualified engineer review the benchmark labels.
