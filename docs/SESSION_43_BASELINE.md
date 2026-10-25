# Sutreva — Session 43 Foundation Baseline

**Baseline:** Session 43
**Purpose:** define the known-good reference point before Architecture 2.0 and NeMo/Nemotron work.

## Validation state

- Full test suite: **233 passed**
- Python compilation: passed
- Offline deployment sanity check: passed
- Theme architecture: Streamlit `config.toml` owns Light/Dark palettes
- Landing navigation: callback-based workspace routing
- Product identity: **Sutreva**
- Legacy product name retained only where historical traceability requires it

## Stable product capabilities

1. Single-document PDF/text audit
2. Deterministic PDF evidence extraction
3. Checkbox/radio detection and deterministic overrides
4. Model-assisted structured extraction
5. Schema-driven engineering comparison
6. Batch audit
7. Bulk structured-data audit without an LLM call
8. Evidence-backed review queue
9. Lifecycle/run context
10. Governance/approval events
11. CSV/XLSX/PDF exports
12. Controlled human-vs-tool pilot workflow
13. Configurable audit templates
14. Sutreva light/dark product UI

## Current primary execution path

```text
Streamlit UI (app.py)
        |
        +--> Audit / Batch / Bulk / Review / Pilot / Templates
        |
        +--> core.py
        |      +--> PDF/text extraction
        |      +--> deterministic overrides
        |      +--> evidence construction
        |      +--> model call + JSON parsing
        |      +--> engineering comparison
        |
        +--> lifecycle / review / governance
        |
        +--> exports / pilot reporting
```

## Current AI boundary

The model boundary is currently concentrated in `core.py`:

```text
call_model()
    -> get_client()
    -> _build_client()
    -> OpenAI-compatible Nebius endpoint
    -> Nemotron
```

This remains intentionally unchanged in the Session 43 baseline.

## Freeze rule

Future changes should preserve these invariants unless the change explicitly targets them:

- deterministic evidence remains available independently of the model
- engineering comparison remains separate from model output
- bulk audit remains deterministic/no-LLM
- review/governance remains human-controlled
- exports remain downstream of validated audit results
- UI navigation/state remains in `app.py`
- product identity remains centralized in `product_brand.py`

## Change discipline

Every future functional change should:

1. identify the feature-map route;
2. change the smallest responsible layer;
3. add or update a regression test;
4. run the full test suite;
5. update the architecture/feature map when an execution path changes.
