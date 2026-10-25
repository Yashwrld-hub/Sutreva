# Sutreva Session 52 — Evaluation Flywheel

## Objective
Turn explicit human-review corrections into a persistent, versioned evaluation set and reproducible regression report.

## Flow
Review disposition → feedback event → explicit gold labels → curated evaluation case → recorded Nemotron output scoring → regression gate.

## Metrics
- Assessment accuracy
- Risk accuracy
- Evidence grounding rate
- Status preservation rate
- Overall accuracy

## Safety boundary
The flywheel never retrains or mutates the production model automatically. The deterministic audit status remains authoritative. A regression failure blocks model/prompt promotion but does not alter live audit output.

## Persistence
Curated cases are stored in the existing SQLite database in `curated_evaluation_cases`. Reviewer identity is not required in exported evaluation artifacts.
