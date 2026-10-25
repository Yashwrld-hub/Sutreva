# Sutreva — Architecture 2.0

**Starting point:** Session 43
**Status:** Architecture target and migration guide

## 1. Objective

Architecture 2.0 separates **presentation**, **application orchestration**, **engineering domain logic**, **evidence**, **AI orchestration**, **model providers**, and **persistence/reporting**.

The purpose is not to rewrite Sutreva. It is to make the existing system easier to evolve, test, and debug while preserving deterministic engineering controls.

## 2. Target architecture

```text
                              SUTREVA
                                 |
                    +------------+------------+
                    |                         |
              Presentation              Application Services
                app.py                 audit / review / pilot
                    |                         |
                    +------------+------------+
                                 |
                         Engineering Domain
                    +------------+------------+
                    |            |             |
                 Audit      Evidence       Templates
                 Rules      Contracts       / Schema
                    |            |             |
                    +------------+------------+
                                 |
                        AI Orchestration
                    +------------+------------+
                    |                          |
             Extraction Tasks          Future AI Tasks
                    |
              Model Provider
             +------+------+
             |             |
          Nemotron      Future model
             |
       Nebius / NeMo / local deployment

                    Downstream controls
             Review -> Governance -> Export
```

## 3. Current-to-target mapping

| Current component | 2.0 responsibility | Migration intent |
|---|---|---|
| `app.py` | Presentation + thin orchestration | keep UI logic, reduce domain logic over time |
| `core.py` | Transitional orchestration + engineering engine | split only where a stable boundary is clear |
| `extraction_contract.py` | Evidence/extraction domain contract | keep stable |
| `conflict_detection.py` | Evidence/conflict domain service | keep stable |
| `templates/*.json` | Engineering schema/rules | keep stable |
| `product_brand.py` | Product identity | keep stable |
| `review_queue.py` | Review domain | keep stable |
| `review_store.py` | Persistence | keep stable |
| `governance.py` | Governance domain | keep stable |
| `lifecycle.py` | Audit lifecycle | keep stable |
| `exports.py` | Reporting adapters | keep stable |
| `pilot_*.py` | Evaluation/pilot subsystem | keep stable |
| `core.call_model()` | Compatibility entry point into AI orchestration | now delegates to `ai_provider.get_model_provider()` |
| `ai_provider.py` | Model-provider boundary | implemented in Session 44; current provider is Nebius/Nemotron |

## 4. Non-negotiable architectural principles

### Evidence before reasoning

Model reasoning should operate on extracted/located evidence where practical. The system should not replace source evidence with an unsupported model assertion.

### AI is advisory, not approval

Model output is an input to the audit pipeline. It is not an engineering sign-off mechanism.

### Deterministic controls remain deterministic

Checkbox detection, known-value overrides, units, schema rules, and evidence validation should not be converted into probabilistic model calls merely for architectural uniformity.

### Provider independence

Sutreva should be able to change model providers without changing its engineering-rule or evidence layers.

### Reproducibility

A future audit record should be able to identify the document revision, template revision, model/provider, prompt version, and final human disposition.

## 5. AI provider boundary

The first concrete Architecture 2.0 refactor is expected to replace the direct model dependency:

```text
core.call_model()
    -> OpenAI client
    -> fixed Nebius endpoint
```

with a provider boundary conceptually equivalent to:

```text
AIExtractionService
        |
   ModelProvider
   /          \
Nemotron      FutureProvider
```

The first implementation should preserve the existing Nebius/Nemotron behavior and tests. NeMo/Nemotron integration should then be introduced behind the same boundary rather than spread through `core.py`.

## 6. Planned extraction of responsibilities from `core.py`

The eventual decomposition is:

```text
core.py (transitional)
  |
  +--> document extraction service
  +--> evidence service
  +--> deterministic override service
  +--> AI extraction service
  +--> engineering comparison service
  +--> audit orchestration service
```

This is a migration map, not a request to split the file blindly. Each extraction happens only when a real dependency boundary and regression coverage exist.

## 7. Debugging consequence

The existing feature/debug map remains the front door:

```text
User symptom
   -> Feature Map
   -> UI / service boundary
   -> responsible module
   -> tests
```

Architecture 2.0 should make that route shorter, not more complicated.

## 8. Next implementation milestone

## 8. Session 44 milestone — AI Provider Abstraction v1

**Status: implemented.**

`ai_provider.py` now owns the provider boundary. The current path is:

```text
run_audit()
  ↓
core.call_model()          # compatibility boundary
  ↓
ai_provider.get_model_provider()
  ↓
ModelProvider protocol
  ↓
NebiusNemotronProvider
  ↓
OpenAI-compatible Nebius endpoint
  ↓
Nemotron
```

The refactor preserves the existing system prompt, model selection, zero-temperature request, reasoning-content fallback, empty-response handling, and one-retry behavior. Provider tests run entirely offline with mocked clients.

The next milestone is **NeMo/Nemotron integration planning and adapter design**, not a provider rewrite. The goal is to determine which NeMo runtime/orchestration capabilities belong behind the same provider boundary while keeping Sutreva's evidence and engineering-rule layers unchanged.
