# Product Discovery Session 18 — Pilot Benchmark Execution

## Objective
Create a repeatable, model-agnostic comparison between copilot predictions and a human-reviewed reference set.

## Acceptance criteria
- Field names are normalized before comparison.
- Value and status accuracy are reported separately.
- Missing predictions and prediction-only fields are surfaced.
- Mismatches remain review findings; the benchmark does not approve engineering data.
- Reviewer dispositions are summarized without conflating disposition with technical approval.

## Pilot governance
Reference data must be created or approved by an authorized subject-matter reviewer. Synthetic fixtures are for software testing only and must not be represented as plant-approved requirements.

## Next decision gate
Run the benchmark against a small, permissioned document set with documented reviewer adjudication, then assess accuracy, traceability, review effort, and unresolved failure modes.
