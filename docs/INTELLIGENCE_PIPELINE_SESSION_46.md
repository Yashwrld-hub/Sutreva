# Sutreva — Intelligence Pipeline Session 46

## Purpose

Session 46 introduces the first evidence-grounded reasoning stage behind the AI provider boundary. The current production inference path remains Nebius Token Factory + NVIDIA Nemotron through the OpenAI-compatible API.

## Runtime path

```text
PDF
  ↓
Evidence extraction
  ↓
Nemotron extraction pass
  ↓
Deterministic overrides
  ↓
Deterministic engineering comparison  ← authoritative
  ↓
Evidence-grounded Nemotron reasoning  ← advisory
  ↓
Human review / disposition
```

The reasoning pass receives only the extracted values, configured rules, deterministic rows, and source evidence. It may report supported values, ambiguity, unsupported values, or document-level flags. It must not alter the deterministic audit status.

## Failure policy

If the advisory reasoning call fails, the engineering audit still completes. The failure is recorded in the result and surfaced in the UI.

## NeMo relationship

NVIDIA NeMo is treated as the evaluation/orchestration ecosystem for the model lifecycle, while the live Sutreva inference path remains the Nebius Token Factory OpenAI-compatible endpoint. NVIDIA's NeMo Evaluator supports API-backed Nemotron services and reproducible benchmark artifacts, which is the next evaluation integration step.

## Hackathon significance

The submitted workflow can now demonstrate two distinct Nemotron contributions: structured extraction and an evidence-grounded second reasoning pass. The reasoning stage is advisory, so a model failure cannot silently turn an engineering mismatch into a match.
