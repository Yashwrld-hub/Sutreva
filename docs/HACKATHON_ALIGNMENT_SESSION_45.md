# Sutreva — Session 45: Hackathon Architecture Alignment

## Purpose

Session 45 aligns the Sutreva product architecture with the Nebius x NVIDIA Global AI Hackathon requirements without changing the runtime audit behavior.

The official rules require a working software application that runs on Nebius Token Factory or Nebius AI Cloud and uses at least one NVIDIA open-source model. For Sutreva, the intended track is **Best Apps and Agents**. The rules also require a working demo/test build, a public source repository with an open-source license, README/setup instructions, a public demonstration video under three minutes, technology-usage disclosure, tool/model feedback, and an explanation of significant updates when the project existed before the submission period.

Source: https://nebiusglobalaihackathon.devpost.com/rules

## Current implementation baseline

- Sutreva runs a Streamlit application with a deterministic engineering-audit pipeline.
- The model integration is behind `ai_provider.py`.
- The current provider is `NebiusNemotronProvider`.
- The configured model is `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- `core.py` retains `call_model()` as a compatibility entry point while delegating provider networking.
- Evidence extraction, deterministic overrides, engineering comparison, review, governance, lifecycle, and export logic remain separate from the model-provider boundary.

## Hackathon-aligned target architecture

```text
                    Sutreva UI
                        |
                 Application Services
                        |
             Engineering Audit Engine
                  /           \\
          Evidence Layer      Rule/Template Layer
                  \\           /
                   AI Orchestration
                         |
                   ModelProvider
                         |
              Nebius / Nemotron
                         |
               Structured response
                         |
             Validation + Evidence
                         |
                Human Review / Audit
```

The target is deliberately not `PDF -> LLM -> pass/fail`.

The model should contribute to specific engineering-document understanding tasks while Sutreva remains responsible for evidence normalization, deterministic overrides, engineering-rule comparison, traceability, and human disposition.

## Hackathon workflow to demonstrate

```text
OEM datasheet
    -> document parsing
    -> evidence construction
    -> Nemotron-assisted extraction/reasoning
    -> schema validation
    -> engineering-standard comparison
    -> exception / missing-value detection
    -> evidence-backed review
    -> exportable audit record
```

This demonstrates a multi-step workflow rather than an isolated model call.

## Architecture gates before public submission

### Gate 1 — Runtime

Prove the submitted build makes a runtime call to Nebius Token Factory or is deployed on Nebius AI Cloud.

### Gate 2 — NVIDIA model usage

Make the Nemotron usage visible in code, README, application flow, and demonstration material.

### Gate 3 — Material model role

Demonstrate what Nemotron materially contributes to the audit workflow and why that contribution is useful.

### Gate 4 — Reproducibility

Record model, provider, prompt, template/schema, and document-revision context needed to explain an AI-assisted audit result.

### Gate 5 — Human engineering control

Do not represent an AI-generated result as final engineering approval. Preserve review/disposition controls.

### Gate 6 — Submission package

Complete public repository, open-source license, setup instructions, working demo, demonstration video, project description, technology disclosure, and required feedback.

## Existing-project update record

Sutreva existed before the current hackathon submission period. The project-update explanation should therefore focus on substantive changes made during the submission period, including:

- hardening PDF/evidence extraction and deterministic checkbox handling;
- engineering-audit lifecycle, governance, review, pilot, and traceability capabilities;
- UI and navigation hardening;
- the Sutreva product rename and brand consolidation;
- Architecture 2.0 separation work;
- AI Provider abstraction;
- the upcoming material Nemotron/NeMo intelligence layer and its evaluation.

This list is a working record and must be updated as additional substantial changes are completed.

## What not to do

- Do not add AI features solely to create a longer feature list.
- Do not replace deterministic engineering checks with an opaque model response.
- Do not expose or commit API keys.
- Do not claim hackathon readiness before the runtime/demo/submission gates are actually verified.
- Do not fabricate benchmark results; record measured results only.

## Session 45 status

**Status: architecture alignment complete; runtime changes deferred.**

Session 46 should focus on the NeMo/Nemotron intelligence pipeline behind the existing `ModelProvider` boundary.
