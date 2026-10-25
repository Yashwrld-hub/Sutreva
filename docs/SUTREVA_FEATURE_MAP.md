# Sutreva — Feature → Code Map

**Baseline:** Session 59 code-health/performance build  
**Purpose:** fast code navigation when a user-visible feature is broken, slow, incorrect, or visually inconsistent.  
**Scope:** stable navigation reference for the current Sutreva demo/development build; update alongside execution-path changes.

> **How to use this file:** Start from the user-visible symptom, jump to the listed entry point, then follow the downstream path. Line numbers are a Session 41 reference; function names are the stable navigation anchor when line numbers move.

## 1. Master product flow

```text
User input
  │
  ├─ Sidebar / workspace navigation ────────────── app.py
  │
  ├─ Single / batch PDF audit ─────────────────── app.py
  │                                                   │
  │                                                   └─ core.py
  │                                                       ├─ PDF extraction + evidence
  │                                                       ├─ deterministic overrides
  │                                                       ├─ Nemotron model call
  │                                                       ├─ JSON parsing
  │                                                       └─ engineering rule comparison
  │
  ├─ Bulk spreadsheet audit ───────────────────── app.py → core.py
  │
  ├─ Review Queue ──────────────────────────────── app.py → review_queue.py → review_store.py
  │                                                     └→ governance.py
  │
  ├─ Templates ─────────────────────────────────── app.py → core.py (template CRUD/validation)
  │
  ├─ Pilot Dashboard ───────────────────────────── app.py → pilot_*.py
  │
  └─ Results / exports ─────────────────────────── app.py → results_ui.py → results_view.py / exports.py
```

## 2. User-interface navigation index

| User-visible area / control | UI location | First file | Entry point / handler | Main downstream path | Relevant tests |
|---|---:|---|---|---|---|
| Sidebar brand / product identity | `app.py:349-354` | `app.py` | `PRODUCT_*` imports | `product_brand.py` | `tests/test_app_branding.py` |
| Go to audit workspace | `app.py` → `_navigate_to("Audit")` callback | `app.py` | sidebar button | `session_state.active_view = "Audit"` → rerun | `tests/test_app_dashboard_integration.py` |
| + New audit | `app.py:358-363` | `app.py` | sidebar button | clears audit/lifecycle state → Audit view → rerun | `tests/test_app_dashboard_integration.py`, `tests/test_lifecycle.py` |
| Audit type selector | `app.py:366-378` | `app.py` | `list_templates()` / `load_schema()` | `core.list_templates()` → `core.load_schema()` | `tests/test_core.py`, template-related tests |
| Project ID / revision / operator ID | `app.py:372-375` | `app.py` | Streamlit inputs | session/context used by audit lifecycle/review | `tests/test_lifecycle.py`, `tests/test_traceability_integrity.py` |
| Edit this template | `app.py:395-398` | `app.py` | sidebar button | copies schema fields → template editor state | `tests/test_core.py` |
| New blank template | `app.py:400-403` | `app.py` | sidebar button | clears editor state → rerun | `tests/test_core.py` |
| Workspace navigation | `app.py` → `workspace_nav` radio + `_sync_workspace_navigation()` | `app.py` | `st.radio("Workspace")` | dispatches Overview / Audit / Bulk Audit / Pilot / Review / Templates | `tests/test_app_dashboard_integration.py`, `tests/test_ui_launch_design.py` |
| Overview → Open audit workspace | `app.py:436-443` | `app.py` | button | sets active view → rerun | `tests/test_app_dashboard_integration.py` |
| Landing → Start hackathon demo | `app.py` → Overview / sidebar | `app.py` | `_start_hackathon_demo()` | sets pump template + demo state → Audit | `tests/test_hackathon_demo_flow.py`, `tests/test_ui_launch_design.py` |
| Audit → Load demo PDF | `app.py` → Audit | `app.py` | `demo_pdf_loaded` state | `sample_data/hackathon_pump_demo.pdf` → `run_pdf_audit_with_evidence()` | `tests/test_hackathon_demo_flow.py` |
| Hackathon demo rehearsal | CLI | `scripts/hackathon_demo_rehearsal.py` | `main()` | PDF evidence → audit → reasoning → engineering intelligence → review → feedback → evaluation | `tests/test_hackathon_demo_flow.py` |
| Audit PDF/TXT uploader | `app.py:500-504` | `app.py` | `st.file_uploader` | prepares pending files / PDF bytes | `tests/test_app_dashboard_integration.py`, `tests/test_batch.py` |
| Audit → Use sample | `app.py:508-512` | `app.py` | sample button | loads template sample input | `tests/test_app_dashboard_integration.py` |
| Audit → Run audit | `app.py:561+` | `app.py` | primary button | `run_pdf_audit_with_evidence()` / `run_batch_audit()` | `tests/test_core.py`, `tests/test_batch.py`, `tests/test_evidence.py` |
| Result file selector / debug view | `app.py:338-342` | `app.py` | `st.selectbox` | reads stored raw output/result | `tests/test_app_dashboard_integration.py` |
| Result exports | `app.py:307-327` | `app.py` | Excel / PDF / CSV download buttons | `exports.py` | `tests/test_exports.py` |
| Bulk spreadsheet uploader | `app.py:629+` | `app.py` | `st.file_uploader` | spreadsheet → dataframe | `tests/test_bulk.py` |
| Bulk sample equipment list | `app.py:635+` | `app.py` | button | loads sample workbook/list | `tests/test_bulk.py` |
| Bulk identifier-column selector | `app.py:661+` | `app.py` | `st.selectbox` | `guess_identifier_column()` | `tests/test_bulk.py` |
| Bulk field-to-column mapping | `app.py:675+` | `app.py` | dynamic `st.selectbox` | `guess_column_mapping()` | `tests/test_bulk.py` |
| Run bulk audit | `app.py:681+` | `app.py` | primary button | `run_bulk_audit()` | `tests/test_bulk.py` |
| Pilot benchmark inputs | `app.py:711+` | `app.py` | Pilot UI controls | `pilot_dashboard.py`, `pilot_metrics.py` | `tests/test_pilot_dashboard.py`, `tests/test_pilot_metrics.py` |
| Pilot report exports | `app.py:749-772` | `app.py` | download buttons | `build_pilot_report()` → report serializers | `tests/test_pilot_report.py` |
| Review Queue | `app.py:776+` | `app.py` | queue renderer | `build_review_queue()` | `tests/test_review_queue.py`, `tests/test_governance.py` |
| Assignee / disposition / reviewer comment | `app.py:813-817` | `app.py` | review form | `update_review_item()` → `upsert_items()` / governance event | `tests/test_review_queue.py`, `tests/test_governance.py` |
| Template editor form | `app.py:828+` | `app.py` | form + controls | `save_template()` / schema validation | `tests/test_core.py` |
| Add field | `app.py:858` | `app.py` | form submit | updates editor state | `tests/test_core.py` |
| Remove field | `app.py:842+` | `app.py` | per-row button | removes field from editor state → rerun | `tests/test_core.py` |
| Save template | `app.py:881+` | `app.py` | primary button | `core.save_template()` | `tests/test_core.py` |
| Clear editor | `app.py:893+` | `app.py` | button | clears editor state → rerun | `tests/test_core.py` |
| Theme behavior | `app.py` theme CSS + `.streamlit/config.toml` | `app.py` / `.streamlit/config.toml` | native Streamlit theme + inherited custom CSS | theme-safe custom surfaces | `tests/test_theme.py` |

## 3. Audit engine map

### 3.1 PDF → evidence → audit

```text
app.py
  Run audit
    │
    ├─ single / ordinary PDF
    │    └─ core.run_pdf_audit_with_evidence()
    │         ├─ extract_pdf_pages_with_evidence()        [core.py:204-207]
    │         │    └─ _extract_pdf_page_texts()            [178-196]
    │         │         └─ _extract_checkbox_markers()    [480-537]
    │         │              ├─ _filled_checkbox_markers()
    │         │              ├─ _rendered_checkbox_selected()
    │         │              └─ geometry helpers
    │         ├─ build_evidence_index()                   [210-215]
    │         ├─ build_evidence_map()                     [657-662]
    │         │    └─ find_field_evidence()               [615-654]
    │         └─ run_audit()                              [868-901]
    │              ├─ build_extraction_prompt()            [664-714]
    │              ├─ call_model()                         [core.py]
    │              │    └─ ai_provider.get_model_provider()
    │              │         └─ NebiusNemotronProvider.generate()
    │              ├─ parse_json_safely()                  [751-783]
    │              ├─ _deterministic_overrides()           [608-612]
    │              └─ compare_against_schema()             [817-865]
    │                   ├─ _rule_for_result()
    │                   └─ _evidence_supports_value()
    │
    └─ multiple files
         └─ core.run_batch_audit()                         [1058-1088]
              └─ _run_one_for_batch()                      [1044-1055]
                   └─ run_audit()
```

### 3.2 Deterministic extraction / checkbox path

Use this branch first when a PDF visibly contains a value but Sutreva reports `MISSING`, an incorrect option, or an incorrect driver type.

```text
PDF geometry/text
  ↓
_filled_checkbox_markers()                  core.py:296-361
  ↓
_rendered_checkbox_selected()               core.py:403-448
  ↓
_extract_checkbox_markers()                 core.py:480-537
  ↓
_checkbox_overrides()                       core.py:540-551
  ↓
_deterministic_overrides()                  core.py:608-612
  ↓
run_audit()                                  core.py:868-901
```

For ordinary text-derived values:

```text
PDF text
  ↓
_deterministic_text_overrides()             core.py:554-606
  ↓
_deterministic_overrides()
  ↓
run_audit()
```

### 3.3 Model/API path

```text
run_audit()
  ↓
build_extraction_prompt()
  ↓
call_model()
  ↓
get_client() / _build_client()
  ↓
Nebius OpenAI-compatible endpoint
  ↓
Nemotron model
  ↓
parse_json_safely()
```

The current model/API configuration lives in `core.py`; the environment contract is documented in `README.md` / `.env.example`.

## 4. Comparison / rules map

| Problem | First function | Supporting path |
|---|---|---|
| Expected/actual mismatch | `core.compare_against_schema()` | `_rule_for_result()` |
| Min/max out-of-range | `core.compare_against_schema()` | `normalize_numeric_value()` |
| Unit normalization | `core.normalize_numeric_value()` | `units.canonical_unit()` / `units.convert_value()` |
| Evidence does not support value | `core._evidence_supports_value()` | evidence map / source quote |
| Template malformed | `core._validate_schema()` | `load_schema()` / `save_template()` |
| Template cannot be selected | `core.list_templates()` / `load_schema()` | `templates/*.json` |

## 5. Review / governance map

```text
app.py Review Queue
  ↓
review_queue.build_review_queue()                 review_queue.py:29-52
  ↓
ReviewItem
  ↓
review_queue.update_review_item()                 review_queue.py:54-63
  ↓
review_store.upsert_items()                       review_store.py:26-50
  ↓
review_store.connect()                             review_store.py:16-24

Governance events
  ↓
review_store.record_approval_event()              review_store.py:88-95
  ↓
governance.ApprovalEvent                           governance.py:25-38
```

Use `lifecycle.py` whenever the defect concerns audit identity/context rather than a field value:

```text
create_audit_run() → make_run_id() → attach_run_context()
```

## 6. Evaluation flywheel map

```text
Review Queue
  ↓
feedback_loop.build_feedback_record()
  ↓
Explicit gold assessment / risk / status
  ↓
evaluation_flywheel.curate_feedback_record()
  ↓
evaluation_flywheel.record_curated_case()
  ↓
Curated evaluation cases (SQLite)
  ↓
evaluation_flywheel.evaluate_snapshot()
  ├─ assessment accuracy
  ├─ risk accuracy
  ├─ evidence grounding
  └─ status preservation

Run evaluation on recorded Nemotron outputs
  ↓
predictions_from_cases()
  ↓
regression gate
```

Use `evaluation_flywheel.py` first for defects involving curated evaluation, metric calculation, evidence grounding, persistence, or regression gates.

## 6. Pilot map

```text
Pilot Dashboard UI
  ↓
pilot_dashboard.build_pilot_dashboard()            pilot_dashboard.py:12-60
  ↓
pilot_metrics.summarize_results()                  pilot_metrics.py:8-26
  ↓
pilot_metrics.compare_cycle_times()                pilot_metrics.py:29-36

Pilot comparison / validation
  ├─ pilot_benchmark.compare_reference_set()        pilot_benchmark.py:17-52
  ├─ pilot_validation.benchmark_accuracy()           pilot_validation.py:15-38
  └─ pilot_validation.coverage_report()             pilot_validation.py:41-50

Pilot reporting
  └─ pilot_report.build_pilot_report()               pilot_report.py:17-47
       ├─ build_traceability_index()
       ├─ report_json_bytes()
       └─ report_summary_csv_bytes()
```

## 7. Export map

| Output | Entry point | Supporting functions | Tests |
|---|---|---|---|
| Single/batch CSV | `exports.to_csv_bytes()` | `_row_values()` | `tests/test_exports.py` |
| Single/batch Excel | `exports.to_excel_bytes()` | `_row_values()` | `tests/test_exports.py` |
| Single/batch PDF | `exports.to_pdf_bytes()` | `_build_pdf_table_data()`, `_pdf_safe_text()`, `_pdf_paragraph()` | `tests/test_exports.py` |
| Bulk Excel | `exports.to_excel_bytes_bulk()` | `_flatten_bulk()` | `tests/test_exports.py`, `tests/test_bulk.py` |
| Bulk PDF | `exports.to_pdf_bytes_bulk()` | `_flatten_bulk()` | `tests/test_exports.py`, `tests/test_bulk.py` |
| Bulk CSV | `exports.to_csv_bytes_bulk()` | `_flatten_bulk()` | `tests/test_exports.py`, `tests/test_bulk.py` |
| Filename generation | `exports.suggested_filename()` | — | `tests/test_exports.py` |

## 8. Contract / integrity layer

| Concern | File | Entry point |
|---|---|---|
| Evidence object | `extraction_contract.py` | `EvidenceRef` |
| Extraction result object | `extraction_contract.py` | `ExtractionRecord` |
| Contract validation | `extraction_contract.py` | `validate_record()` |
| Model output → records | `extraction_contract.py` | `records_from_extracted()` |
| Conflict detection | `conflict_detection.py` | `detect_conflicts()` |
| Audit traceability | `lifecycle.py` | `AuditRun`, `create_audit_run()` |

## 9. Test routing index

When a defect is reproduced, run the narrow test family first, then the broader suite.

| Symptom | First tests | Broader regression tests |
|---|---|---|
| Sidebar / navigation | `test_app_dashboard_integration.py`, `test_ui_launch_design.py` | `test_code_quality.py`, full suite |
| Theme / rendering | `test_theme.py` | `test_ui_launch_design.py`, full suite |
| Run audit / extraction | `test_core.py`, `test_batch.py` | `test_evidence.py`, `test_contract.py` |
| Checkbox / Driver Type | `test_checkbox_extraction.py`, `test_deterministic_text_overrides.py` | `test_actual_oem_material_flow.py`, `test_evidence.py` |
| Evidence / traceability | `test_evidence.py`, `test_traceability_integrity.py` | `test_core.py`, full suite |
| Bulk audit | `test_bulk.py` | `test_batch.py`, `test_exports.py` |
| Exports / filename | `test_exports.py` | `test_bulk.py`, `test_pilot_report.py` |
| Review queue | `test_review_queue.py` | `test_governance.py`, `test_traceability_integrity.py` |
| Governance | `test_governance.py` | `test_review_queue.py`, `test_traceability_integrity.py` |
| Lifecycle | `test_lifecycle.py` | `test_traceability_integrity.py` |
| Pilot | `test_pilot_*` | app integration / full suite |
| Units | `test_units.py` | `test_core.py`, `test_bulk.py` |

## 10. Change-impact rule

When fixing a defect, use this order:

1. **Start from the symptom entry point** in this map.
2. Inspect the named function and its immediate dependencies.
3. Inspect the narrow test family before modifying shared infrastructure.
4. If the change crosses a module boundary, inspect the downstream tests listed in the map.
5. Do not rewrite unrelated files just because they are in the same feature area.
6. After a fix, add or update a regression test if the defect can be reproduced deterministically.
7. If a new feature/button is added, add it to this map in the same change.

## 11. Session 41 stability anchors

The following areas were specifically hardened before this map was created and should be treated as regression-sensitive:

- single-PDF audit path should parse the document once in the normal Streamlit flow;
- deterministic checkbox/radio evidence should remain conservative under ambiguity;
- material and other deterministic text overrides should remain separate from model extraction;
- review/governance persistence should remain explicit and traceable;
- light/dark theme selection should continue to be owned by `.streamlit/config.toml`; custom HTML should inherit the active native palette;
- exports should preserve source/result separation and avoid contaminating extracted data with filenames.

## 12. Branding note

The product direction is now **Sutreva**. This Session 41 codebase still contains legacy `OEM Audit Copilot` naming in repository documentation and some implementation-facing text. This feature map does **not** perform the branding migration; it only establishes the navigation baseline needed to make that migration safely later.


## Session 42 repair notes

- **Theme switching:** custom UI colors now inherit the native Streamlit theme via `currentColor`/theme-neutral tints. Global `--st-*` variables are not used outside component-scoped styling.
- **Landing-page navigation:** `Open audit workspace` now invokes `_navigate_to("Audit")` as a widget callback. This avoids mutating the radio widget's state after the widget has already been instantiated.
- **Brand:** visible product identity is **Sutreva**. The legacy name **OEM Audit Copilot** is retained in `product_brand.py` as a historical code comment.


### Session 46 — Nemotron intelligence

| User-visible feature | First file | Primary path | Notes |
|---|---|---|---|
| Nemotron engineering reasoning | `app.py` | `run_pdf_audit_with_evidence(..., include_intelligence=True)` → `ai_orchestration.run_engineering_reasoning()` | Advisory only; deterministic audit rows remain authoritative |
| Reasoning prompt/normalization | `ai_orchestration.py` | `_build_reasoning_prompt()` / `_normalize_result()` | Evidence-grounded JSON output |

Session 49: domain-aware context is implemented in `domain_rules.py`; exception presentation remains in `engineering_intelligence.py`.

### Human feedback / learning signals

| User action | First place to inspect | Supporting code | Tests |
|---|---|---|---|
| Save review decision | `app.py` → Review Queue form | `feedback_loop.py`, `review_store.py` | `tests/test_feedback_loop.py`, `tests/test_review_queue.py` |
| Learning signal incorrect | `feedback_loop.build_feedback_record()` | `FEEDBACK_LABELS`, `ReviewItem.ai_context` | `tests/test_feedback_loop.py` |
| Feedback export wrong | `feedback_loop.export_feedback_jsonl()` | identity-redaction / evaluation-ready filtering | `tests/test_feedback_loop.py` |
| Feedback persistence wrong | `feedback_loop.record_feedback()` | `feedback_events` SQLite table | `tests/test_feedback_loop.py` |
| AI context missing from feedback | `review_queue.build_review_queue()` | `ai_context` propagation from result row | `tests/test_review_queue.py` |

## 7. Deployment / hackathon runtime map

```text
Streamlit app
  ↓
runtime_config.get_runtime_config()
  ↓
ai_provider.NebiusNemotronProvider
  ↓
Nebius Token Factory OpenAI-compatible API
  ↓
NVIDIA Nemotron
```

| Problem | First place to inspect | Supporting path |
|---|---|---|
| Wrong deployed model | `runtime_config.py` | `NEBIUS_MODEL_NAME` → `ai_provider.py` |
| Wrong Nebius endpoint | `runtime_config.py` | `NEBIUS_API_BASE_URL` → provider client |
| Deployment preflight fails | `scripts/nebius_preflight.py` | provider configuration / live model catalog |
| Container won't start | `deploy/nebius/Dockerfile` | Streamlit command / environment |
| Hackathon demo sequence issue | `docs/HACKATHON_DEMO_RUNBOOK.md` | sample document + Audit + Review Queue + evaluation flywheel |
| Runtime/provider labeling wrong | `app.py` | `get_runtime_config()` |

Use `scripts/nebius_preflight.py` first for deployment configuration errors before inspecting model-call code.


## Session 55 — live-path corrections

- **Unit-aware comparison** → `core.py:compare_against_schema()` → `units.py` → numeric normalization metadata.
- **Extraction contract** → `core.py:run_audit()` → `extraction_contract.records_from_extracted()` → `row["extraction_record"]`.
- **Conflict gate** → `core.py:run_audit()` → `conflict_detection.detect_conflicts()` → `NEEDS_REVIEW`.
- **Governance event** → `app.py` Review Queue save → `governance.ApprovalEvent` → `review_store.record_approval_event()`.


## Session 59 — Results presentation and performance path

The shared audit-result rendering boundary now lives in `results_ui.py`.
`app.py` remains responsible for workflow/state and calls
`render_group_results()`. The results module owns the file-centric comparison
table, evidence/detail presentation, engineering/historical intelligence,
Nemotron reasoning display, raw-output debug view, and download controls.

Performance-sensitive result work is cached across normal Streamlit reruns:
- `analyze_engineering_rows()` is cached by its result/schema/AI-assessment inputs.
- Excel/PDF/CSV report bytes are cached by result/template/identifier inputs.

The PDF-engine benchmark/hybrid extraction proposal is intentionally **deferred**;
no PDF extraction engine was replaced in Session 59.
