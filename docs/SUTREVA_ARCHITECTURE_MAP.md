# Sutreva — Architecture / Dependency Map

**Baseline:** Session 59  
**Purpose:** stable mental model of the codebase so future fixes can target the correct layer.

## Top-level dependency graph

```text
                         ┌─────────────────────┐
                         │       app.py        │
                         │ workflow/state      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    results_ui.py    │
                         │ result presentation │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼─────────────────────────┐
             │                      │                         │
             ▼                      ▼                         ▼
        ┌──────────┐         ┌──────────────┐          ┌──────────────┐
        │  core.py │         │ review_queue │          │ pilot_*.py   │
        │ audit    │         │ review flow  │          │ pilot flow   │
        └────┬─────┘         └──────┬───────┘          └──────┬───────┘
             │                      │                         │
      ┌──────┼───────┐              ▼                         ▼
      │      │       │        ┌──────────────┐        ┌──────────────┐
      ▼      ▼       ▼        │review_store  │        │pilot_report  │
   PDF/evid  Model  Rules     └──────┬───────┘        └──────────────┘
                                     ▼
                               governance.py

 app.py ───────────────────────────────────────────────► exports.py
 app.py ───────────────────────────────────────────────► lifecycle.py
 core.py ──────────────────────────────────────────────► units.py
 core.py ──────────────────────────────────────────────► extraction_contract.py
```

## Layer responsibilities

### Presentation / orchestration

**`app.py`**

Owns:
- Streamlit widgets
- workspace navigation
- session state
- form handling
- invoking application services
- audit workflow routing

**`results_ui.py`**

Owns:
- shared audit-result rendering
- file-centric comparison presentation
- field/evidence review presentation
- engineering/historical intelligence presentation
- Nemotron reasoning and raw-output presentation
- cached Excel/PDF/CSV export artifacts across Streamlit reruns

Should not own:
- PDF parsing algorithms
- model protocol details
- engineering rule logic
- persistence implementation

### Audit engine

**`core.py`**

Owns:
- template loading/validation
- PDF text/evidence extraction
- checkbox/radio analysis
- deterministic overrides
- extraction prompt construction
- model request/response parsing
- engineering rule comparison
- single, batch, and bulk audit orchestration


### Engineering intelligence

**`domain_rules.py` + `engineering_intelligence.py`**

Owns:
- deterministic translation of authoritative audit statuses into engineering exceptions
- severity/category classification
- engineering impact and recommended review action
- optional enrichment from Nemotron assessment/risk without changing audit status

It must not:
- change the authoritative status in `core.py`
- approve or reject equipment
- invent evidence

### Session 48 route

```text
Audit rows
   ↓
engineering_intelligence.analyze_engineering_rows()
   ├── exception category
   ├── severity
   ├── engineering impact
   ├── recommended action
   └── optional Nemotron assessment/risk

Authoritative status remains the `core.py` result.
```

### Contracts / evidence

**`extraction_contract.py`**

Owns structured evidence/extraction records and validation.

**`conflict_detection.py`** owns conflict identification between result sources.

### Persistence / governance

**`review_queue.py`** owns review-domain objects and queue transformations.

**`review_store.py`** owns SQLite persistence.

**`governance.py`** owns approval-event data structures.

**`lifecycle.py`** owns audit-run identity and lifecycle context.

### Reporting

**`exports.py`** owns CSV/Excel/PDF result serialization and filenames.
`results_ui.py` owns the Streamlit download controls and caches serialized
artifacts so normal UI reruns do not regenerate completed reports.

### Pilot

`pilot_dashboard.py`, `pilot_metrics.py`, `pilot_benchmark.py`, `pilot_validation.py`, and `pilot_report.py` form the controlled-pilot subsystem.

### Product identity

**`product_brand.py`** centralizes product name/tagline/version/page title. Use it as the branding migration boundary rather than scattering hard-coded names through UI code.

## Important architectural boundaries

### 1. AI extraction ≠ engineering approval

The model produces extraction data. Deterministic rules and human review remain separate controls.

### 2. Evidence is first-class

A field result can carry evidence and should remain traceable to its source location.

### 3. Bulk audit bypasses the model

Structured spreadsheet data is checked directly through the same comparison engine rather than being unnecessarily sent to the LLM.

### 4. UI reruns are normal

Streamlit reruns the script after widget interaction. State keys and deliberate `st.rerun()` calls are therefore part of the UI architecture and should be considered when debugging perceived lag. Result-derived engineering intelligence and generated report artifacts are cached in `results_ui.py` so reruns do not repeat the same deterministic analysis/serialization work.

### 5. Branding should be centralized

The repository is in transition from `OEM Audit Copilot` to `Sutreva`. Product identity belongs in `product_brand.py`; implementation modules should not accumulate independent product-name constants.

## AI provider / NeMo-Nemotron integration boundary

The current architecture currently concentrates the model call in:

```text
core.call_model()
    ↓
get_client()
    ↓
_build_client()
```

This is the transitional boundary for the next Architecture 2.0 step. The next refactor should place a provider/service interface around this call. The following layers should remain stable unless an integration explicitly requires otherwise:

```text
PDF parsing
Evidence construction
Deterministic overrides
Engineering rule comparison
Review / governance
Exports
```

That separation allows the model-serving/orchestration layer to evolve without turning Sutreva into an AI-only application.

### Session 46 — intelligence route

`run_pdf_audit_with_evidence(..., include_intelligence=True)` now routes through:

`core.run_pdf_audit_with_evidence → ai_orchestration.run_engineering_reasoning → ai_provider.get_model_provider → NebiusNemotronProvider`

The deterministic `compare_against_schema()` result remains authoritative.

### Session 50 — Historical Pattern Intelligence

`pattern_intelligence.py` is an advisory layer over closed `ReviewItem` history. It is reached from the Audit Outcome UI after engineering exception analysis and never feeds back into the authoritative audit status.

### Session 51 — Human Feedback Learning Loop

`feedback_loop.py` sits beside review persistence as an append-only learning-signal layer:

```text
Review Queue
   ↓
review_queue.update_review_item()
   ↓
feedback_loop.build_feedback_record()
   ↓
feedback_loop.record_feedback()
   ↓
feedback_events (append-only)
   ↓
feedback_loop.export_feedback_jsonl()
   ↓
Curated evaluation dataset
```

The feedback layer never mutates deterministic audit status and never auto-trains or changes the
running model. Reviewer identity is retained for auditability but is removed from evaluation exports
by default.


## Evaluation flywheel

`feedback_loop.py` captures append-only reviewer signals. `evaluation_flywheel.py` turns explicitly curated closed reviews into persistent gold cases, evaluates recorded Nemotron outputs, and applies a regression gate. Neither module retrains models or changes authoritative audit status.


## Session 53 — deployment boundary

```text
Sutreva UI / audit services
        ↓
runtime_config.py
        ↓
ModelProvider
        ↓
Nebius Token Factory
        ↓
NVIDIA Nemotron
```

The deployment image contains the application only. The API key is injected at runtime; it is never copied into the image. `NEBIUS_MODEL_NAME`, `NEBIUS_API_BASE_URL`, and timeout settings are deployment configuration, while the default values preserve local development behavior.
