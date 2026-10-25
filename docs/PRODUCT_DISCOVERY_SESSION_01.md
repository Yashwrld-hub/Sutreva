# OEM Audit Copilot — Product Discovery Session 01

## Product direction

Build an all-in-one industrial engineering copilot, beginning with evidence-first OEM document auditing and structured equipment-register compliance.

## Decisions

- Evaluate architecture before committing to a frontend/backend rewrite.
- Treat the current application as a modular-monolith candidate.
- Prioritize audit correctness, source traceability, and review workflow over adding more AI features.
- Preserve the existing deterministic comparison engine for structured bulk data.
- Keep AI extraction isolated behind a replaceable provider boundary.

## Cross-functional findings

### Mechanical/reliability engineering
- Every extracted value needs source evidence and unit context.
- A mismatch should be distinguishable from missing data, invalid data, and a rule requiring human review.
- Engineering sign-off must remain a human-controlled decision.

### Software architecture
- Offline comparison logic must not require an AI SDK to be installed.
- Results should have stable field identifiers and machine-readable rule metadata.
- Future work should separate ingestion, extraction, normalization, comparison, review, and export responsibilities.

### UX
- The primary workflow should be project → equipment type → upload → extract → review → disposition → export.
- Reviewers should be able to filter by status and inspect evidence without opening raw model output.

### Enterprise
- Future versions need tenant/project boundaries, role-based access, versioned templates, audit history, and document retention controls.

## Implemented in Session 01

- Made the OpenAI SDK import optional for offline logic and test execution.
- Added rule metadata and review reasons to comparison rows.
- Added an evidence placeholder to establish the future result contract.
- Added a regression test for traceability-ready metadata.
- Verified 63 tests pass when the standalone network connection test is excluded.

## Next sprint

1. Define an evidence object: source file, page, text span, extraction confidence, and verification state.
2. Add a normalization layer for numeric values and units.
3. Add explicit `NEEDS REVIEW` handling for ambiguous or invalid extraction results.
4. Add a review-focused UI with filters and evidence panels.
5. Add provider abstraction and mocked extraction tests.
