# Sutreva — Debug Map

**Baseline:** Session 41  
**Purpose:** turn a local screenshot/console report into the smallest relevant code path.

## Fast routing table

| What you report | Start here | Then inspect | Do not start by rereading |
|---|---|---|---|
| Sidebar is lagging / buttons respond late | `app.py:349-403` | `list_templates()`, `load_schema()`, Streamlit reruns | PDF extraction, Nemotron |
| Sidebar/landing navigation does nothing | `app.py` → `_navigate_to()` / `workspace_nav` | callback-driven `active_view` routing | `core.run_audit()` |
| Workspace tab doesn't switch | `app.py:427-434` | `active_view` state | model/API code |
| Run audit crashes | `app.py:561+` | `run_pdf_audit_with_evidence()` / `run_batch_audit()` | exports first |
| PDF uploads but fields are missing | `core.run_pdf_audit_with_evidence()` | extraction/evidence → deterministic overrides | UI CSS |
| Driver Type is MISSING/wrong | `core._extract_checkbox_markers()` | `_checkbox_overrides()` → `_deterministic_overrides()` | model prompt first |
| Visible PDF value differs from result | `core._deterministic_text_overrides()` | `build_evidence_map()` | export code |
| `Expecting value: line 1 column 1` | `core.parse_json_safely()` | raw model output → `call_model()` | checkbox code |
| Nemotron call fails | `core.call_model()` | `ai_provider.get_model_provider()` → `NebiusNemotronProvider` / env config | Streamlit rendering |
| Result status is wrong | `core.compare_against_schema()` | rule + unit normalization + evidence | PDF checkbox geometry |
| Unit conversion wrong | `core.normalize_numeric_value()` | `units.py` | model/API |
| Bulk audit is wrong | `app.py:623+` | `guess_identifier_column()`, `guess_column_mapping()`, `run_bulk_audit()` | PDF parser |
| Review Queue doesn't save | `app.py:813-817` | `review_queue.update_review_item()` → `review_store.upsert_items()` | pilot modules |
| Approval history missing | `review_store.py:88-101` | `governance.py` | exports |
| Template save fails | `app.py:881+` | `core.save_template()` → `_validate_schema()` | audit execution |
| Template not appearing | `core.list_templates()` | cache invalidation / `templates/` files | review queue |
| Export filename/data looks wrong | `exports.suggested_filename()` + `exports.*` | result construction in `core.py` | Streamlit navigation |
| Excel/PDF/CSV download errors | `exports.py` | specific serializer path | model extraction |
| Results page reruns feel slow | `results_ui.py` → `render_group_results()` | cached engineering analysis / cached export artifacts | PDF parser first |
| Export generation repeats on every rerun | `results_ui.py` → `_cached_*_export()` | Streamlit cache key inputs / serializer | model extraction |
| Pilot metric wrong | `pilot_metrics.py` | dashboard/report consumers | core extraction |
| Dark/light UI is broken | `app.py` theme CSS + `.streamlit/config.toml` | native Streamlit theme + custom HTML inheritance | audit engine |
| App won't import/start | `app.py` imports | `deployment_check.py`, `requirements.txt` | business logic |

## Error-text routing

### `Expecting value: line 1 column 1 (char 0)`

Start at:

```text
core.parse_json_safely()
    ↓
core.call_model()
    ↓
ai_provider.get_model_provider()
    ↓
NebiusNemotronProvider.generate()
    ↓
raw model output
```

Questions to answer before changing code:

- Was the API response empty?
- Was the API response an error object instead of JSON extraction output?
- Did the provider return markdown/code fences?
- Did the model return a truncated response?
- Did the prompt ask for a schema the parser cannot accept?

Do not change the PDF extraction path until the raw output path is verified.

### `KeyError`, `TypeError`, or missing result field

Start at:

```text
extraction_contract.py
    ↓
validate_record() / records_from_extracted()
    ↓
core.run_audit()
    ↓
app render path
```

### PDF-specific mismatch

Separate the problem into these categories:

1. **Text extraction problem** → `_extract_pdf_page_texts()`
2. **Checkbox geometry problem** → `_extract_checkbox_markers()` and helpers
3. **Evidence association problem** → `find_field_evidence()` / `build_evidence_map()`
4. **Deterministic override problem** → `_deterministic_text_overrides()` / `_checkbox_overrides()`
5. **Model extraction problem** → `call_model()` / `parse_json_safely()`
6. **Engineering comparison problem** → `compare_against_schema()`

### UI screenshot with no console error

Route in this order:

```text
app.py
  ↓
widget declaration
  ↓
button/input state key
  ↓
session_state mutation
  ↓
st.rerun()
  ↓
conditional view branch
```

This is usually a UI-state issue before it is an engine issue.

## Lag triage

When a user reports "the sidebar is lagging":

1. Start in `app.py:349-403`.
2. Check functions executed on every Streamlit rerun:
   - `list_templates()`
   - `load_schema()`
3. Check whether a button causes unnecessary `st.rerun()` cycles.
4. Check whether an expensive audit function is accidentally executed outside a guarded button branch.
5. Only then inspect PDF/model work.

The current design intentionally keeps PDF extraction behind the audit action rather than parsing every time a user changes UI state.

## Fix workflow

```text
Screenshot / console error
        ↓
Identify symptom
        ↓
Use routing table
        ↓
Inspect entry point + immediate dependency chain
        ↓
Check narrow regression tests
        ↓
Make smallest fix
        ↓
Run narrow tests
        ↓
Run broader regression tests
        ↓
Update this map only if the execution path changed
```


### Theme switching failure

Start in `app.py` theme CSS and `.streamlit/config.toml`. Confirm that the custom UI does **not** pin global colors through `--st-*` variables or a Python theme snapshot. Native Streamlit owns the Light/Dark palette; Sutreva custom HTML should inherit `currentColor` and use theme-neutral tints.

Also confirm the runtime uses `streamlit>=1.52.1` so the confirmed 1.51–1.52.0 custom-theme persistence regression is excluded.

| Nemotron reasoning warning/failure | `ai_orchestration.py` | `run_engineering_reasoning()` | deterministic audit rows |
| Reasoning JSON invalid | `ai_orchestration.py` | `_parse_json_object()` | provider networking |
| Reasoning flags look wrong | `ai_orchestration.py` | `_normalize_result()` + reasoning prompt | `compare_against_schema()` |

Session 49: domain-aware context is implemented in `domain_rules.py`; exception presentation remains in `engineering_intelligence.py`.

### Historical pattern intelligence

Symptom: `Historical pattern intelligence` is missing or inconsistent.

Start at `app.py` → `build_historical_pattern_matches()` → `pattern_intelligence.py` → `review_store.py` / `ReviewItem.disposition`.

Remember: an empty history store is a valid state and should not be treated as a product error.


## Session 55 symptom routes

| Symptom | First inspection | Supporting layer |
|---|---|---|
| Correct numbers marked out of range due to units | `core.py:compare_against_schema()` | `units.py`, numeric normalization metadata |
| Conflicting model/source values | `core.py:run_audit()` | `conflict_detection.py`, `extraction_contract.py` |
| Review saved but no audit event | `app.py` Review Queue save | `governance.py`, `review_store.py` |
| Extraction record missing | `core.py:run_audit()` | `extraction_contract.py` |


## Session 59 — current results-performance boundary

For result-page performance issues, inspect `results_ui.py` before changing
`core.py`. The result renderer now caches deterministic engineering reports
and completed Excel/PDF/CSV serialization across Streamlit reruns. The PDF
extraction engine was deliberately left unchanged in this session; benchmark
and hybrid-engine work is deferred to a later corpus-driven phase.
