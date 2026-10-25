# Sutreva --- Engineering & Development Log

> **Historical naming rule:** The product is recorded as **OEM Datasheet
> Audit / OEM Audit Copilot** throughout the historical development
> timeline up to the product-renaming decision. From the explicit rename
> decision onward, the product identity is **Sutreva**. Historical
> entries are not retroactively renamed.

## 1. Project Overview

The project began as an engineering-focused OEM Datasheet Audit / OEM
Audit Copilot intended to reduce manual effort in reviewing OEM
engineering documents, extracting important equipment specifications,
validating them against audit criteria, preserving source evidence, and
producing traceable audit outputs.

It evolved into a broader evidence-backed engineering document
intelligence platform connecting engineering documents, structured data,
unit normalization, validation, evidence, human review, audit runs,
reporting, and planned AI capabilities.

Current product identity: **Sutreva**.

Core principle:

> **UNDERSTAND → INVESTIGATE → DECIDE → IMPLEMENT → TEST → DOCUMENT**

Engineering priorities: accuracy, traceability, reproducibility,
explainability, data integrity, unit consistency, validation, and
auditability.

## 2. Current System Architecture

The current implementation is a Python/Streamlit modular monolith. The Streamlit workflow/state boundary is `app.py`; shared audit-result presentation is isolated in `results_ui.py`, which delegates to `results_view.py`, engineering intelligence, historical patterns, and export serializers.

```text
User
  |
  v
Streamlit UI
  |
  v
Audit Workflow
  |
  +-- PDF / Document Extraction
  +-- Templates / Rules
  +-- Extraction Contract
  +-- Unit Normalization
  +-- Conflict Detection
  +-- Audit Logic
  |
  v
Structured Engineering Fields
  |
  +-- Original Source Value / Unit
  +-- Normalized Value / Target Unit
  +-- Evidence / Traceability
  |
  v
Authoritative Engineering Comparison
  |
  v
Engineering Intelligence
  |
  +-- Domain-aware exception context
  +-- Historical pattern context
  +-- Nemotron reasoning (advisory)
  |
  v
Human Review
  |
  +-- Governance / Approval Event
  +-- Feedback Event
  |
  v
Evaluation Flywheel
  |
  +-- Curated evaluation cases
  +-- Recorded model-output evaluation
  +-- Regression gate
  |
  v
Persistence / Exports / Reporting
```

Important live modules include `app.py`, `results_ui.py`, `results_view.py`, `core.py`, `extract.py`,
`extraction_contract.py`, `units.py`, `conflict_detection.py`,
`exports.py`, `review_queue.py`, `review_store.py`, `governance.py`,
`feedback_loop.py`, `evaluation_flywheel.py`, `engineering_intelligence.py`,
`domain_rules.py`, `pattern_intelligence.py`, `ai_orchestration.py`,
`ai_provider.py`, `runtime_config.py`, `lifecycle.py`, `pilot_metrics.py`,
`pilot_dashboard.py`, `pilot_report.py`, `pilot_casepack.py`,
`product_brand.py`, and `deployment_check.py`.

The extraction boundary now preserves structured extraction information
including source unit, target unit, normalized value, evidence and
verification status. Unit normalization is part of the live engineering
comparison path rather than test-only functionality.

PDF auditing uses the evidence-aware path for both single-file and
multi-file workflows. Multi-file PDF batches retain PDF bytes until the
worker executes `run_pdf_audit_with_evidence()`, preserving page/line
evidence, deterministic source reconciliation and verification behavior.
Per-file failures are isolated into result rows and do not abort the batch.
The Streamlit UI defaults to three parallel AI requests, with a bounded
worker limit, to reduce request bursts and improve batch responsiveness. The
lower-level text batch API now uses the same default of three workers.

The primary audit-results presentation is file-centric: one document/equipment
record occupies one row and each configured audit field occupies a column. A
compact overall-status and review-fields column support batch triage, while
field-status controls and Streamlit's table-level column filtering support
large-batch sorting/filtering. The detailed field-by-field evidence view is
retained separately so the comparison table stays compact as the number of
documents grows. `results_ui.py` now owns this presentation boundary and
caches deterministic engineering reports plus completed report artifacts across
normal Streamlit reruns.

Deterministic extraction also has a conservative label-attached text path for
material/text fields whose source vocabulary is not present in the configured
template. It recovers explicitly labelled source text on the same line; it
does not replace numeric/unit-aware extraction or infer values from unrelated
nearby text.

The audit engine remains authoritative for engineering/compliance status.
AI reasoning, historical patterns and engineering-intelligence context are
advisory and cannot silently change the authoritative audit result.

The current AI/provider path is:

```text
Audit Workflow
     |
     v
AI Orchestration
     |
     v
ModelProvider
     |
     v
Nebius Token Factory / NVIDIA Nemotron
```

The application supports configured provider/model values through
`runtime_config.py`. Offline demo/rehearsal paths do not claim live model
execution.

Persistence currently includes review, governance, feedback and evaluation
state. Human review remains in the control loop.

The current product also contains Nebius deployment scaffolding,
preflight checks and a deterministic hackathon demo workflow.

## 3. Development Timeline

### Session 1 --- Enhanced Foundation

**Type:** Feature / Architecture

Established the initial OEM Datasheet Audit application foundation and
modular engineering-audit workflow.

**Status:** Implemented

### Session 2 --- Evidence Foundation

**Type:** Feature / Architecture

Introduced evidence as a first-class part of extraction and audit
results so outputs could be traced back to source material.

**Status:** Implemented

### Session 3 --- Evidence Review

**Type:** Feature

Added a workflow for reviewing extracted evidence.

**Status:** Implemented

### Session 4 --- Evidence Verification

**Type:** Feature / Improvement

Strengthened verification of evidence rather than automatically trusting
extracted information.

**Status:** Implemented

### Session 5 --- Units Foundation

**Type:** Feature / Engineering Decision

Introduced a dedicated unit conversion/normalization layer. The
engineering principle was to preserve the original source value/unit
while supporting normalized internal values.

**Status:** Implemented

### Session 6 --- Extraction Contract

**Type:** Architecture / Feature

Introduced/strengthened an extraction contract through
`extraction_contract.py` so downstream logic receives structured
extraction results.

**Status:** Implemented

### Session 7 --- Conflict Detection

**Type:** Feature

Added explicit conflict detection for cases where extraction paths or
document representations disagree.

**Status:** Implemented

### Session 8 --- Review Queue

**Type:** Feature

Introduced `review_queue.py` so ambiguous or conflicting findings can be
routed to human review.

**Status:** Implemented

### Session 9 --- Review UI

**Type:** Feature / UX

Added a dedicated review interface for evidence and findings.

**Status:** Implemented

### Session 10 --- Persistence

**Type:** Architecture / Feature

Introduced SQLite-backed persistence and review storage so audit/review
state could survive application reruns.

**Status:** Implemented

### Session 11 --- Governance

**Type:** Architecture / Security

Introduced governance mechanisms through `governance.py`.

**Status:** Implemented

### Session 12 --- Lifecycle

**Type:** Architecture

Introduced lifecycle/state handling through `lifecycle.py`.

**Status:** Implemented

### Session 13 --- End-to-End Traceability

**Type:** Architecture / Feature

Extended traceability across the audit workflow so source documents,
extracted information, findings and outputs remained connected.

**Status:** Implemented

### Session 14 --- Traceability Hardening

**Type:** Improvement / Architecture

Hardened the traceability implementation.

**Status:** Implemented

### Session 15 --- Pilot Dashboard

**Type:** Feature

Introduced/expanded `pilot_dashboard.py` for pilot-level measurement.

**Status:** Implemented

### Session 16 --- Pilot Validation

**Type:** Testing / Validation

Established a pilot-validation framework. A semantic issue was
identified in benchmark accuracy logic: `missing_prediction` and
`missing_benchmark` had been using the same benchmark-only logic.

The intended semantics were:

``` python
missing_prediction = [
    item for item in keys
    if item not in pred and item in gold
]

missing_benchmark = [
    item for item in keys
    if item not in gold and item in pred
]
```

Testing should include a predicted-only key.

**Status:** Corrective work identified; exact final state requires
verification against current code.

### Session 17 --- Pilot Case Pack

**Type:** Feature

Introduced/expanded `pilot_casepack.py` and repeatable pilot case-pack
preparation.

**Status:** Implemented

### Session 18 --- Benchmarking

**Type:** Testing / Feature

Added benchmarking support for comparison against benchmark data.

**Status:** Implemented

### Session 19 --- Pilot Dashboard Refinement

**Type:** Improvement

Refined pilot dashboard behavior and metric visibility.

**Status:** Implemented

### Session 20 --- Interactive Dashboard

**Type:** Feature / UX

Added more interactive dashboard behavior for pilot information.

**Status:** Implemented

### Session 21 --- Pilot Reporting

**Type:** Feature

Introduced/expanded `pilot_report.py` for formal pilot reporting.

**Status:** Implemented

### Session 22 --- Traceability Reporting

**Type:** Feature

Extended reporting to include traceability information rather than only
aggregate results.

**Status:** Implemented

### Session 23 --- Human vs Tool Pilot

**Type:** Testing / Validation

Established an independent human-vs-tool comparison methodology using
the same documents.

Representative fields included Rated Power, NPSHA Available,
Casing/Barrel Material, Shaft Material and Driver Type.

The workflow includes independent human audit, tool audit,
field-by-field comparison, discrepancy/root-cause recording, review-time
comparison and human validation.

**Status:** Implemented

### Session 24 --- Code Review / Optimization

**Type:** Refactoring

Performed a broader code review and optimization pass focused on
redundancy, loops and maintainability.

**Status:** Implemented

### Session 25 --- Code Quality

**Type:** Improvement

Performed additional code-quality and maintainability improvements.

**Status:** Implemented

### Session 26 --- PDF Layout Fix

**Type:** Bug Fix / Investigation

Addressed PDF layout/extraction behavior that caused incomplete or
incorrect audit information.

**Status:** Resolved

### Session 27 --- Checkbox Fix

**Type:** Bug Fix / Investigation

A selected checkbox in an OEM PDF was not correctly interpreted.

Investigation found that the PDF represented checkbox graphics using
vector paths. Unselected and selected circles had different nested
vector construction, while the detector treated filled vector paths too
generically.

The solution recognized nested vector checkbox construction while
retaining AcroForm/glyph/raster fallbacks.

**Status:** Resolved

### Session 28 --- JSON / Code Review Fix

**Type:** Bug Fix / Refactoring

Addressed the runtime error:

``` text
Expecting value: line 1 column 1 (char 0)
```

The affected path was attempting to parse invalid/empty JSON. JSON
handling was hardened.

**Status:** Resolved

### Session 29 --- Driver Type Hardening

**Type:** Bug Fix / Investigation

Driver Type remained missing/ambiguous.

Investigation found that generic `driver` / `drivers` matching could
select the wrong region instead of the complete field label.

The implementation was changed to use the complete field label and
retain the hardened checkbox interpretation.

**Status:** Resolved

### Session 30 --- Actual OEM Driver Fix

**Type:** Bug Fix / Validation

Validated the driver extraction against the actual OEM centrifugal pump
PDF rather than only synthetic fixtures.

Relevant values included:

-   Rated Power: 687.4 kW
-   NPSHA Available: 5.96 m
-   Driver Type: Induction Motor

The actual OEM document was retained as a regression reference.

**Status:** Resolved

### Session 31 --- Actual OEM Material Fix

**Type:** Bug Fix / Investigation

Two material fields were missing:

-   Casing / Barrel Material
-   Shaft Material

The actual OEM source contained:

``` text
BARREL / CASE  A216WCB
SHAFT          A276-410
```

Deterministic source-value recovery was added using field aliases and
row association.

Recovered values:

-   Casing / Barrel Material: `A216WCB`
-   Shaft Material: `A276-410`

**Status:** Resolved

### Session 32 --- UX and Branding

**Type:** Feature / UX / Engineering Decision

Repositioned the interface toward an industrial control-room /
enterprise engineering aesthetic.

Direction included restrained indigo/blue-gray styling, clean panels,
evidence-first results, minimal decorative effects, and workflow:

``` text
Upload → Analyze → Review Evidence → Export
```

Navigation included Audit, Bulk Audit, Pilot Dashboard, Review Queue and
Templates.

**Status:** Implemented

### Session 33 --- Branding NameError Fix

**Type:** Bug Fix

Branding changes caused a `NameError` because `page_title` and
product-brand constants were not imported in `app.py`.

Affected imports included:

-   `PRODUCT_DESCRIPTION`
-   `PRODUCT_NAME`
-   `PRODUCT_TAGLINE`
-   `PRODUCT_VERSION`
-   `page_title`

The branding configuration remained centralized.

**Status:** Resolved

### Session 34 --- Product Launch Design

**Type:** Architecture / UX

Strengthened the overall product around outcome-oriented states,
evidence-first result panels, session context and professional
engineering navigation.

**Status:** Implemented

### Session 35 --- Launch-Grade UX

**Type:** UX / Improvement

Further refined visual hierarchy and workflow while preserving the
industrial engineering identity.

**Status:** Implemented

### Session 36 --- Workspace Navigation/UI Fix

**Type:** Bug Fix / UX

Corrected workspace/navigation behavior and associated UI presentation.

**Status:** Resolved

### Session 37 --- Light Theme

**Type:** UX / Improvement

Introduced a coherent light theme using the indigo engineering visual
system.

**Status:** Implemented

### Session 38 --- Indigo and Dark Mode

**Type:** UX / Feature

Introduced indigo-based dark-mode styling.

**Status:** Implemented

### Session 39 --- Dark Mode Fix

**Type:** Bug Fix / UX

Improved dark-mode behavior where native Streamlit components and custom
CSS were not consistently themed.

**Status:** Resolved; further hardening followed.

### Session 40 --- Code Optimization

**Type:** Refactoring / Performance

Removed redundant work and simplified several production paths.

Key optimizations:

-   removed duplicate PDF extraction in the Streamlit audit path
-   reduced same-PDF processing from twice to once
-   removed duplicate unreachable `return pages`
-   removed duplicate normalization helper and regex
-   cached `_norm_label()`
-   optimized `_field_anchor_top()`
-   reduced repeated normalization and regex work
-   removed unused `extract_number_and_unit()`
-   consolidated UI result passes
-   consolidated error-result construction
-   changed SQLite review persistence to `executemany()` in one
    transaction
-   reduced approval persistence from two DB connections to one
-   combined pilot-dashboard scans
-   consolidated traceability record construction
-   removed `app.py.bak`
-   removed caches/backups from package

The recorded development state reported approximately 2847 → 2766
production-module lines, 81 lines removed, and 141 tests passing.
Ruff/mypy/pyflakes/radon/bandit were not installed, so they were not
claimed as executed.

**Status:** Implemented

### Session 41 --- Dark Mode Hardened

**Type:** Bug Fix / UX / Testing

Dark mode was hardened across native Streamlit widgets and application
containers.

Changes included:

-   `COLOR_SCHEME = THEME_MODE`
-   CSS `color-scheme`
-   app shell selectors including `[data-testid="stApp"]`
-   toolbar/background selectors
-   main block/vertical wrapper styling
-   dataframe/table backgrounds
-   markdown text styling
-   text/number input and text-area styling
-   selectbox/multiselect styling
-   BaseWeb popover/menu/listbox/options styling
-   expander styling
-   alert styling
-   sidebar styling
-   regression tests for theme selectors

Recorded validation reported all tests passing, compile verification,
deployment sanity verification and ZIP integrity verification. The known
limitation is that Streamlit theme context can temporarily be stale
during theme switching, so final visual acceptance benefits from manual
verification.

**Status:** Implemented / Manual visual verification recommended

------------------------------------------------------------------------

### Session 43 — Architecture Foundation

**Type:** Architecture / Documentation

Established a frozen known-good baseline and documented the target
Architecture 2.0 direction before introducing the new AI/provider layers.

The baseline preserved the existing audit behavior while making the future
provider boundary and architecture migration explicit.

**Testing & Verification:** Recorded baseline validation reported 233 tests
passing, deployment sanity verification, Python compilation and ZIP
integrity verification.

**Status:** Implemented

### Session 44 — AI Provider Abstraction

**Type:** Architecture / Refactoring

Introduced a `ModelProvider` boundary so the audit/application layer no
longer needs to know the concrete model-access implementation.

The existing Nebius/Nemotron behavior was retained behind a
`NebiusNemotronProvider`, including the existing model interaction and
response handling.

A compatibility alias was retained for the existing `API_BASE_URL` import
contract after the refactor exposed that dependency.

**Testing & Verification:** Recorded validation reported 240 tests passing,
deployment sanity verification and Python compilation. Ruff could not be
executed because Ruff was not installed in the environment.

**Status:** Implemented

### Session 45 — Hackathon Architecture Alignment

**Type:** Architecture / Engineering Decision

Aligned Sutreva's architecture with the Nebius × NVIDIA Global AI Hackathon
requirements.

The project was treated as a working engineering application that must make
meaningful use of Nebius and an NVIDIA open-source model, while preserving
the deterministic engineering-audit foundation.

Added hackathon tracking/alignment artifacts and tests without changing the
audit runtime.

**Testing & Verification:** Recorded validation reported 152 tests passing,
deployment sanity verification, Python compilation and tracker validation.

**Status:** Implemented

### Session 46 — Nemotron Intelligence Pipeline

**Type:** Feature / AI Architecture

Added an AI orchestration layer between the audit engine and the model
provider.

The live reasoning flow was designed as:

```text
Evidence Extraction
  ↓
Deterministic Overrides
  ↓
Engineering Comparison
  ↓
Nemotron Evidence-Grounded Reasoning
  ↓
Human Review
```

Nemotron reasoning is advisory. It cannot replace the authoritative
engineering status.

An evaluation scaffold was also added for NeMo-based model evaluation.
The application uses the Nebius provider path; NeMo evaluation is kept
separate from the live inference dependency.

Existing four-value audit-call compatibility was preserved unless the new
intelligence output is explicitly requested.

**Testing & Verification:** Recorded validation reported 157 tests passing,
deployment sanity verification and Python compilation.

**Status:** Implemented

### Session 47 — Evidence Intelligence & Evaluation

**Type:** Feature / Testing / AI

Strengthened evidence-grounded Nemotron assessments.

Field assessments can retain evidence references including page, line and
source quotation. The reasoning prompt requires references to come from the
deterministic evidence map rather than inventing locations.

Added an engineering-specific evidence benchmark covering supported values,
missing values, ambiguity, unsupported extraction, rule violations,
checkbox-derived evidence, conflicting evidence and numeric boundaries.

NeMo Evaluator remains the generic model/provider evaluation layer, while
Sutreva's benchmark measures domain-specific engineering evidence quality.

**Testing & Verification:** Recorded validation reported 162 tests passing.
The golden-fixture harness reported 100% assessment accuracy, risk accuracy,
evidence grounding and status preservation; these were harness-integrity
results and not live Nemotron performance measurements.

**Status:** Implemented

### Session 48 — Engineering Intelligence v1

**Type:** Feature / Architecture

Added an engineering exception layer above the authoritative audit engine.

The layer classifies exceptions, assigns context/severity, describes
engineering impact and provides recommended reviewer action.

It does not modify the authoritative audit status.

**Testing & Verification:** Recorded validation reported 164 tests passing,
deployment sanity verification, Python compilation and ZIP integrity.

**Status:** Implemented

### Session 49 — Domain-Aware Engineering Rules

**Type:** Feature / Engineering

Added equipment/domain profiles so engineering exceptions can be interpreted
in equipment context.

Initial domain profiles included centrifugal pump, mechanical seal and
lubrication-register contexts.

The profiles provide context and prioritization rather than silently adding
acceptance limits to the audit engine.

**Testing & Verification:** Recorded validation reported 168 tests passing,
deployment sanity verification and Python compilation.

**Status:** Implemented

### Session 50 — Historical Pattern Intelligence

**Type:** Feature / Architecture

Added contextual use of prior closed/reviewed cases for current engineering
exceptions.

Historical patterns can report similar-case counts, prior dispositions,
projects/audits represented and pattern strength.

Historical information is advisory only and cannot modify current
authoritative status, severity, blocking state, acceptance rules or source
evidence.

**Testing & Verification:** Recorded validation reported 171 tests passing,
deployment sanity verification, compilation and tracker validation.

**Status:** Implemented

### Session 51 — Human Feedback Learning Loop

**Type:** Feature / Architecture

Added an append-only human-feedback layer connecting review decisions to
structured learning signals and future evaluation data.

Feedback signals include confirmation, override, insufficient evidence,
rule-update signal, waiver, action required and other reviewer outcomes.

Reviewer identity is retained for auditability but is excluded by default
from exported evaluation data.

Production feedback does not automatically retrain Nemotron or silently
change prompts or audit rules.

**Testing & Verification:** Recorded validation reported 176 tests passing,
deployment sanity verification and Python compilation.

**Status:** Implemented

### Session 52 — Evaluation Flywheel

**Type:** Feature / Testing / Architecture

Connected reviewer feedback to persistent curated evaluation cases and
recorded model-output evaluation.

The flow is:

```text
Reviewer Feedback
  ↓
Gold Evaluation Case
  ↓
Recorded Model Output
  ↓
Evidence / Assessment / Risk / Status Evaluation
  ↓
Regression Gate
```

Evaluation cases persist across application restarts.

Regression failure blocks promotion/evaluation acceptance but does not change
production audit results.

**Testing & Verification:** Recorded validation reported 184 tests passing,
deployment sanity verification, Python compilation and tracker validation.

**Status:** Implemented

### Session 53 — Nebius Deployment & Hackathon Demo Architecture

**Type:** Architecture / Deployment / Hackathon

Centralized deployment/runtime configuration in `runtime_config.py` and
added Nebius deployment scaffolding.

Supported configuration includes environment, provider, API key,
Token Factory base URL, model name and request timeout.

Added Nebius Docker/deployment files and a preflight script. The preflight
can perform offline configuration checks and an optional live model-availability
check.

The existing synthetic sample workflow was retained, with the distinction
between synthetic/offline demo execution and live model execution documented.

**Testing & Verification:** Recorded validation reported 189 tests passing,
deployment sanity verification, offline Nebius preflight and Python
compilation. Docker image build was not executed because Docker was not
installed in the environment.

**Status:** Implemented / Cloud deployment requires live verification

### Session 54 — Hackathon Demo Hardening

**Type:** Testing / Bug Fix / UX / Hackathon

Added a dedicated hackathon demo entry point using a synthetic centrifugal
pump PDF fixture.

The fixture intentionally contains two review triggers so the complete
workflow can be demonstrated:

```text
PDF
 ↓
Evidence Extraction
 ↓
Audit
 ↓
Engineering Intelligence
 ↓
Review
 ↓
Feedback
 ↓
Evaluation
```

During rehearsal, a deterministic material override edge case was discovered:
narrative text containing words such as "expected" or "configured" could be
mistaken for an authoritative field value.

The material matcher was narrowed to reject candidates preceded by explicit
narrative cues while preserving legitimate material lines.

**Testing & Verification:** Recorded validation reported 193 tests passing.
The offline rehearsal produced two intentional engineering exceptions, five
evidence references, two review findings and a passing evaluation gate, with
zero API credits used.

**Status:** Resolved / Implemented

### Session 55 — Architecture Truth & Unit Normalization

**Type:** Architecture / Refactoring / Feature / Engineering Decision

#### Problem / Requirement

A source-code architecture review identified three important discrepancies:

1. `units.py` existed and was tested but unit normalization did not affect
   the real audit comparison path.
2. `extraction_contract.py`, `conflict_detection.py` and `governance.py`
   existed but were not all connected to the running application path.
3. Passing unit tests could therefore make isolated scaffolding appear to be
   live product functionality.

#### Investigation

The audit path, imports and test usage were traced before modification.

Confirmed findings:

- `normalize_numeric_value()` was not previously exercised by the
  production comparison path.
- Unit coverage was incomplete for engineering units used in realistic
  documents, including volume/flow/power/mass/speed/torque categories.
- `ExtractionRecord` was previously test/scaffolding architecture rather
  than the live audit boundary.
- `conflict_detection.py` was previously test-only scaffolding.
- `governance.py` was previously not connected to the main application path,
  while parallel governance persistence existed in `review_store.py`.

#### Decision

Integrate the useful architecture into the live path rather than deleting
the modules.

The selected approach was:

```text
Source Value + Unit
       ↓
Extraction Contract
       ↓
Safe Unit Normalization
       ↓
Engineering Comparison
       ↓
Conflict Detection
       ↓
Authoritative Audit Status
       ↓
Review / Governance / Feedback
```

Unit conversion must preserve the original source value/unit and expose the
normalized value/unit for traceability.

Gauge/absolute pressure conversion must not be silently inferred without
explicit ambient-pressure context.

#### Implementation

Expanded `units.py` to cover additional engineering dimensions including
temperature, pressure, length, volume, flow, power, mass, speed and torque.

Connected `normalize_numeric_value()` to the real comparison path.

Introduced live use of `ExtractionRecord` at the audit boundary, including
source unit, target unit, normalized value, evidence and verification
status.

Connected conflict detection so disagreement between extraction paths can
surface as `CONFLICT` / `NEEDS_REVIEW` rather than being silently accepted.

Connected governance approval events to the review workflow while retaining
the existing review/feedback persistence model.

Updated architecture/feature/debug mapping to distinguish live runtime
modules from historical scaffolding.

#### Testing & Verification

Recorded Session 55 validation reported:

- 207 tests passing
- deployment sanity verification
- Nebius offline preflight
- hackathon demo rehearsal
- Python compilation

Additional regression coverage specifically verified that
`normalize_numeric_value()` and `ExtractionRecord` are exercised through the
live audit path.

The demo rehearsal continued to produce two intentional engineering
exceptions and a passing evaluation gate.

#### Result

The previously identified unit-normalization and test-only-scaffolding
discrepancies were corrected. Unit conversion, extraction contracts,
conflict detection and governance are now connected to actual application
behavior.

#### Status

**Implemented**

### Session 56 — Real-Document Extraction & Multi-File Batch Hardening

**Type:** Bug Fix / Extraction / Performance / UX / Testing

### Problem / Requirement

Recent validation with a real Gorman-Rupp centrifugal pump PDF exposed two
issues:

1. The document contained explicit `Casing` and `Impeller Shaft` material
   values, but the audit report showed both fields as `MISSING`.
2. Uploading multiple files could make the Streamlit audit workspace appear
   frozen while processing, and the multi-file PDF path discarded the
   evidence-aware PDF pipeline by converting PDFs to plain text before batch
   execution.

The supplied PDF explicitly contains `Casing: ... Ductile Iron 65-45-12` and
`Impeller Shaft: Carbon Steel 1045` on page 1. It does not explicitly provide
`Rated Power`, `NPSHA Available`, or `Driver Type` as configured audit fields.

### Investigation

The existing deterministic material matcher only recovered finite values
listed in the centrifugal-pump template. The Gorman-Rupp document uses a
different material vocabulary, so no deterministic override was produced when
the model returned null for those fields.

The Streamlit multi-file path also extracted every PDF into plain text before
calling `run_batch_audit()`. That meant batch PDFs did not use the same
page/evidence-aware `run_pdf_audit_with_evidence()` path as single PDFs.
Multiple concurrent AI requests were also exposed directly through the UI
with a default of five workers, increasing request-burst/rate-limit pressure.

### Root Cause

- Material/text extraction was too tightly coupled to the configured template
  vocabulary.
- Multi-file PDF processing used a text-only batch path instead of the live
  evidence-aware PDF audit path.
- The default concurrency level was higher than necessary for a stable local
  Nebius API workflow.

### Decision

Add a conservative generic label-attached extraction path for non-numeric
text/material fields, while retaining the existing finite-value matcher as the
more authoritative path when both produce a value.

Introduce a dedicated `run_batch_pdf_audit()` path so multi-file PDFs retain
page/evidence context and receive the same deterministic reconciliation, unit
normalization, conflict detection and verification behavior as single-file
audits. Cap batch workers at six and make three the UI default. A worker/UI
progress callback failure must never discard completed audit results.

### Implementation

Updated `core.py`:

- added `_deterministic_label_overrides()` for explicitly labelled text/material
  values outside the template's finite vocabulary
- kept numeric fields on the existing unit-aware path so values such as
  `720 kW` cannot be converted into raw strings by generic extraction
- added `_result_or_error()` for consistent per-file batch result isolation
- added `_run_one_pdf_for_batch()`
- added `run_batch_pdf_audit()` with bounded concurrency, stable input ordering,
  per-file error isolation and guarded progress callbacks

Updated `app.py`:

- removed pre-audit PDF-to-text conversion from the multi-file path
- routed uploaded PDFs through `run_batch_pdf_audit()`
- retained the text-upload batch path for `.txt` files
- reduced default parallel requests from five to three and bounded the control
  at six
- preserved upload order, including duplicate filename handling
- kept a single progress indicator across the multi-file run

Updated tests:

- added generic material/text extraction coverage
- added PDF batch ordering/failure-isolation coverage
- added progress-callback failure isolation coverage
- updated the architecture/code-quality expectation to reflect the new live
  PDF batch path

### Testing & Verification

Executed:

- 211 automated tests passing
- Python compilation / `compileall`
- Nebius offline preflight
- offline hackathon demo rehearsal
- direct regression against the supplied `pump3.pdf`
- direct multi-file PDF batch regression using two PDFs with two workers

For the supplied Gorman-Rupp PDF, the corrected deterministic path recovered:

- Casing material: `(63E31-B) Ductile Iron 65-45-12` → `MISMATCHED` against
  the configured template values
- Shaft material: `Carbon Steel 1045` → `MISMATCHED` against the configured
  expected `A276-410`
- Rated Power: `MISSING` because the supplied document does not explicitly
  provide that configured field
- NPSHA Available: `MISSING` because the supplied document does not
  explicitly provide that configured field
- Driver Type: `MISSING` because the supplied document does not explicitly
  provide that configured field

The multi-file regression returned two result records in input order and
progress callbacks reached completion without aborting the batch.

### Result

The real-document material extraction defect is resolved for explicitly
labelled text/material fields outside the template vocabulary. Multi-file PDF
processing now follows the same evidence-aware audit architecture as single
PDF processing, with bounded concurrency and per-file failure isolation.

The supplied Gorman-Rupp PDF is correctly treated as a different equipment
source from the configured centrifugal-pump acceptance template: the two
explicit material values are surfaced and compared rather than incorrectly
reported as missing.

### Status

**Implemented / Needs broader corpus verification**


# 4. Feature Development Summary

## Document extraction

The system evolved from basic PDF extraction toward deterministic
handling of text, tables, layout-dependent fields, checkboxes, vector
graphics and engineering material fields.

## Units

A dedicated unit layer is now part of the live engineering comparison path.
The system preserves original source value/unit while producing a normalized
value/unit for comparison. Supported dimensions include temperature, pressure,
length, volume, flow, power, mass, speed and torque.

Gauge/absolute pressure conversion requires explicit context and is not
silently inferred.

## Evidence and traceability

Evidence became a core product principle. Findings should remain
traceable to source documents and relevant source locations.

## Human review

Uncertain or conflicting findings are routed through human review rather
than assuming automated extraction is always correct.

## Audit Runs

The earlier **Bulk Audit** concept is being repositioned as **Audit
Runs**.

An Audit Run represents a controlled collection of documents/equipment
processed under a defined template/ruleset.

``` text
Audit Run
 |
 +-- Documents
 +-- Template
 +-- Findings
 +-- Evidence
 +-- Reviews
 +-- Results
 +-- Export
```

## Pilot validation

The pilot measures human vs tool performance on the same documents,
including field accuracy, missing-value rate, wrong-value rate, evidence
coverage, review time and reviewer correction rate.

------------------------------------------------------------------------

# 5. Bug Investigations & Fixes

## Driver Type extraction

**Confirmed root cause:** vector checkbox representation plus
insufficient field anchoring.

**Resolution:** nested-vector checkbox recognition, complete field-label
anchoring and existing fallback methods.

## Material field recovery

**Confirmed root cause:** OEM row/label structures were not sufficiently
recovered by generic extraction.

**Resolution:** deterministic alias and source-row recovery.

## JSON parsing failure

The affected path attempted to parse invalid/empty JSON, producing
`Expecting value: line 1 column 1 (char 0)`. JSON handling was hardened.

## Benchmark semantic issue

The intended distinction between missing predictions and prediction-only
fields was identified during Session 16. The final implementation should
be verified against the current source before documenting it as fully
resolved.

------------------------------------------------------------------------

# 6. Engineering & Architecture Decisions

## Deterministic extraction remains important

Engineering PDFs can encode the same information through text, tables,
vector shapes and form controls. Critical fields therefore retain
deterministic extraction paths.

## Evidence is first-class

Extracted values should remain connected to their source evidence.

## Human review remains in the control loop

Ambiguous or consequential findings should be reviewable and correctable
by an engineer.

## Modular monolith first

The pilot remains a modular monolith. Distributed services should only
be introduced when actual scale requires them.

## Unit normalization is part of the authoritative comparison path

Source engineering values are preserved with their original units, then
normalized to the target/template unit before numeric comparison.

This prevents equivalent values expressed in different units from being
treated as mismatches and makes the transformation traceable.

The conversion layer deliberately avoids silently converting gauge and
absolute pressure without the required context.

## AI as augmentation

The intended AI architecture is:

``` text
PDF
 |
 +--> Deterministic extraction
 |
 +--> AI/document intelligence
 |
 v
Evidence fusion
 |
Engineering validation
 |
Reasoning
 |
Human review
```

------------------------------------------------------------------------

# 7. Testing & Validation

Testing principles:

-   test the smallest relevant scope first
-   run broader regression where practical
-   use real OEM documents for important regressions
-   keep synthetic fixtures distinct from real pilot results
-   never fabricate test results

The actual OEM centrifugal pump PDF was used during debugging and
regression validation.

Relevant extracted values included:

``` text
Rated Power       = 687.4 kW
NPSHA Available   = 5.96 m
Barrel / Case     = A216WCB
Shaft             = A276-410
Driver Type       = Induction Motor
```

The recorded Session 40/41 development state reported 141 tests passing
and compile/deployment sanity verification.

------------------------------------------------------------------------

# 8. Known Issues & Technical Debt

1.  Final manual visual acceptance of light/dark themes remains useful.
2.  The benchmark missing-prediction/missing-benchmark historical issue
    should still be verified against the current source before being marked
    fully resolved.
3.  Live Nebius cloud deployment and real-model inference require manual/live
    environment verification; the recorded offline checks do not constitute
    a live cloud inference test.
4.  Docker image build has not been executed in the development environment
    because Docker was not installed there.
5.  The larger representative OEM validation corpus has not yet been
    collected; current regression coverage includes real and synthetic
    fixtures but is not a substitute for broad field validation.
6.  Formal Sutreva domain/trademark clearance remains a separate task.

------------------------------------------------------------------------

# 9. Future Improvements

-   Build a larger representative OEM validation corpus covering varied
    equipment, OEM layouts, scanned PDFs, tables, checkboxes, missing fields,
    conflicting values and difficult documents.
-   Establish a formal batch validation benchmark with field accuracy,
    evidence accuracy, false-positive/false-negative rates, review effort
    and runtime measurements.
-   Complete live Nebius deployment and real Nemotron inference verification.
-   Measure model/provider latency, token usage, failure recovery and
    long-document behavior.
-   Continue hardening the hackathon demo path using real documents.
-   Formalize the Audit Run domain model.
-   Create formal system-context, container, component, data-flow and
    deployment diagrams.
-   Expand equipment templates and domain-specific engineering rules.
-   Expand engineering units only when supported by real validation
    requirements.
-   Complete formal brand/domain/trademark clearance.
-   Preserve the engineering log as the single development-history
    source of truth.

------------------------------------------------------------------------

# 10. Product Identity Transition --- OEM Datasheet Audit → Sutreva

**Type:** Engineering Decision / Product Decision

## Context

The original product name described the initial use case but became
restrictive as the system expanded from OEM datasheet auditing into
broader engineering document intelligence.

## Investigation

Several candidate names were explored. Speclytic, SpecDex, Pramana,
Sakshya and Anvesa showed significant existing commercial/product usage
or conflict signals during preliminary searches.

A Sanskrit-inspired coined-name direction was then explored.

## Decision

The product identity is now:

# Sutreva

Sutreva is treated as a coined, Sanskrit-inspired brand. The conceptual
inspiration is **Sūtra**, representing a connecting thread/framework.

The intended product metaphor is:

``` text
Engineering Document
       ↓
Information
       ↓
Evidence
       ↓
Engineering Rule
       ↓
Finding
       ↓
Human Review
       ↓
Decision
```

Sutreva represents the thread connecting these stages.

## Consequences

Benefits:

-   broader than OEM datasheets
-   not tied to a specific AI model/provider
-   not tied to Streamlit
-   supports future engineering-document intelligence
-   supports NeMo/Nemotron integration
-   provides a distinctive product identity

Trade-offs:

-   rename must be propagated consistently
-   formal domain/trademark clearance remains necessary
-   historical entries retain the previous product identity

**Status:** Product-direction decision adopted; formal legal/domain
clearance pending.

------------------------------------------------------------------------

# 11. Current Product Direction

**Sutreva** is intended to become:

> **An evidence-backed engineering intelligence platform that transforms
> engineering documents into structured, traceable and reviewable
> engineering information.**

Current strategic architecture:

``` text
                         SUTREVA
                 Engineering Intelligence
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   Document Intelligence  Engineering      Evidence
                          Intelligence
          |                |                |
          |                +-- Rules       +-- Traceability
          |                +-- Validation  +-- Source
          |                               +-- Review
          |
          +-- Deterministic extraction
          +-- AI-assisted extraction
          +-- Retrieval
          +-- Multimodal understanding
                           |
                           v
                    Human Review
                           |
                           v
                    Audit / Decision
```

------------------------------------------------------------------------

# 12. Documentation Principles

The project uses one master engineering document:

``` text
docs/SUTREVA_ENGINEERING_LOG.md
```

Meaningful work should be documented when it involves significant
features, bugs, root-cause discoveries, architecture changes, extraction
changes, engineering calculations, units, AI integration, schemas, APIs,
performance, security, dependencies, validation findings, technical
discoveries or important decisions.

Trivial formatting, whitespace and routine cleanup should not create
documentation noise.

The objective is to preserve engineering knowledge for future
developers, AI coding agents, debugging, maintenance, architecture
understanding, hackathon evaluation and future feature development.

------------------------------------------------------------------------

# 13. Current Status

**Current product:** Sutreva

**Historical identity:** OEM Datasheet Audit / OEM Audit Copilot

**Current maturity:** pilot-ready engineering audit platform with live
deterministic extraction, evidence and traceability, unit normalization,
conflict detection, domain-aware engineering intelligence, advisory
Nemotron reasoning, human review, governance events, feedback capture,
persistent evaluation cases, exports, professional Streamlit UX,
light/dark themes, Nebius deployment scaffolding and a reproducible
hackathon demo path.

**Latest recorded validation:** 218 tests passing, with deployment sanity,
Nebius offline preflight, compilation, real-document regression, batch-path
regression, file-centric results-view regression and offline hackathon
rehearsal validation recorded through Session 58.

**Immediate strategic direction:**

1.  Treat Session 57 as the current extraction/batch-hardening baseline.
2.  Collect and validate a larger representative OEM document corpus.
3.  Establish formal batch accuracy/evidence/performance benchmarks.
4.  Complete live Nebius deployment and real Nemotron inference verification.
5.  Continue UX/demo hardening based on real-document findings.
6.  Expand equipment/domain coverage based on measured validation needs.
7.  Complete formal brand/domain/trademark clearance.
8.  Maintain this engineering log as the single historical source of truth.


------------------------------------------------------------------------

# 14. Session 57 — Real Pump Datasheet Engineering Logic & Audit Run Safety

## [2026-09-29] — Real Pump Datasheet Engineering Logic & Audit Run Safety

### Type
Bug Investigation / Engineering Logic / UX Reliability / Regression Hardening

### Problem / Requirement

A real centrifugal-pump datasheet (`pump data1.pdf`) was uploaded and the
Streamlit audit failed before producing a result. The UI displayed:

``` text
ERROR
not enough values to unpack (expected 5, got 4)
```

The same testing cycle exposed two additional requirements:

1. The centrifugal-pump extraction logic must handle real OEM terminology such
   as `Motor power : 7.5 kW` when the configured audit field is `Rated Power`.
2. Starting a second audit must not leave the previous run's Excel/PDF/CSV
   controls capable of triggering a Streamlit rerun while the new audit is
   processing.

The engineering requirement is to fix these cases without weakening the
principle that deterministic engineering rules remain authoritative and that
ambiguous mappings are visible rather than silently guessed.

### Investigation

The supplied real document was inspected at source level.

On page 2, the datasheet contains:

- `N.P.S.H available : -`
- `Brake power : 4.9 kW`
- `Motor power : 7.5 kW`
- `Casing : Cast Iron`
- `Shaft : Stainless Steel AISI329`
- `Motor Make/type : CMG or equal /EX-PROOF/132`

The existing single-file UI path always unpacked
`run_pdf_audit_with_evidence()` into five variables:

``` text
rows, raw, _, _pages, intelligence = run_pdf_audit_with_evidence(...)
```

However, the function intentionally returns four values when the advisory
Nemotron reasoning pass is disabled and five values only when
`include_intelligence=True`. This contract mismatch caused the observed
runtime failure.

The batch helper had a related fragile conditional-unpacking expression. The
helper was rewritten to branch explicitly on `include_intelligence`, making the
four-value and five-value contracts explicit and testable.

The real document also demonstrated that the generic deterministic extractor
could already recover the explicit material values, but `Rated Power` had no
transparent mapping to the OEM's `Motor power` label. Blindly treating
`Brake power` and `Motor power` as interchangeable would be unsafe because the
same datasheet contains both values.

### Root Cause

**Primary runtime root cause:** the single-file Streamlit PDF path expected five
return values even when the PDF audit function correctly returned four values
with advisory reasoning disabled.

**Engineering extraction root cause:** the centrifugal-pump schema did not
define a transparent source-label mapping for the `Rated Power` field, while
the OEM document expressed the relevant value as `Motor power` and also
contained a different `Brake power` value.

**UX reliability root cause:** the audit result area rendered download
controls from the previous completed run. Streamlit download-button
interaction could trigger a new rerun while a subsequent audit was still
executing. The export controls therefore needed an explicit no-rerun contract
rather than relying only on the processing spinner.

### Decision

1. Keep the four-value/five-value `run_pdf_audit_with_evidence()` contract
   unchanged for backward compatibility.
2. Make both single-file and batch callers branch explicitly on the
   `include_intelligence` flag.
3. Introduce transparent, schema-configured deterministic source aliases for
   engineering fields whose OEM label differs from the audit field label.
4. For the centrifugal-pump template, configure `Motor power` as the
   deterministic source alias for `Rated Power`. This is a visible template
   mapping, not a fuzzy inference and not a hidden acceptance rule.
5. Preserve `Brake power` as a separate source value in the document; do not
   silently substitute it for `Rated Power`.
6. Add `N.P.S.H available` aliases so the source line containing `-` remains
   traceable when the resulting value is correctly treated as missing.
7. Keep `Driver Type` conservative: the presence of a motor technical
   datasheet does not by itself convert the field into an authoritative
   `Induction Motor` value without explicit supporting evidence.
8. Treat download actions as non-rerun interactions (`on_click="ignore"`) so
   report downloads cannot interrupt an active audit run.
9. Clear stale audit results at the beginning of a new run and track
   `audit_processing` in session state to prevent a second run from being
   layered over the first result set.

### Implementation

#### Core audit contract

`_run_one_pdf_for_batch()` now explicitly handles:

``` text
include_intelligence=False
    -> rows, raw_output, extracted, pages

include_intelligence=True
    -> rows, raw_output, extracted, pages, intelligence
```

This removes the fragile starred-tuple unpacking path.

#### Engineering source mapping

A new deterministic numeric extraction path reads only values attached to
explicitly configured `deterministic_source_aliases`.

The centrifugal-pump template now contains:

``` json
"deterministic_source_aliases": ["Motor power"]
```

for `rated_power_kw`.

The source evidence therefore records the exact OEM line:

``` text
Motor power : 7.5 kW
```

rather than presenting the mapping as an unexplained AI inference.

The NPSHA field now recognizes both:

``` text
N.P.S.H available
NPSH available
```

as source-label aliases.

#### UI run safety

The audit button is disabled while an audit is marked as processing.
Previous results are cleared at the start of a new run. The processing flag is
reset in a `finally` block so exceptions do not permanently leave the session
in a busy state.

Audit export buttons now use Streamlit's non-rerun download behavior so clicking
Excel/PDF/CSV does not start another application execution while processing.

### Testing & Verification

The real `pump data1.pdf` was executed through the evidence-aware audit path
with a deterministic model fixture. The resulting extraction was:

``` text
Rated Power          -> 7.5 kW -> MATCHED
NPSHA Available      -> missing -> MISSING
Casing / Barrel      -> Cast Iron -> MISMATCHED
Shaft Material       -> Stainless Steel AISI329 -> MISMATCHED
Driver Type          -> missing -> MISSING
```

The `Rated Power` result is supported by the page-2 source line `Motor power :
7.5 kW`. The casing and shaft values are supported by their respective page-2
source lines. No unsupported `Driver Type` inference was introduced.

Automated regression suite:

- **216 tests passing**
- New regression tests cover the four-value PDF path.
- New regression tests cover the five-value reasoning path.
- New regression tests cover the real pump source mapping.
- UI regression checks cover `audit_processing` and non-rerun download controls.
- Python compilation passed.
- Nebius offline preflight passed.
- Hackathon offline rehearsal passed with the existing expected two
  engineering exceptions and evaluation gate PASS.

### Result

The observed `expected 5, got 4` runtime failure is removed from both the
single-file and batch PDF calling boundaries.

The real OEM pump datasheet now produces a useful evidence-backed result rather
than failing before the audit table is rendered. The engineering mapping
correctly distinguishes `Motor power` from `Brake power`, while material values
remain directly sourced from their labelled OEM fields.

The export controls no longer need to participate in application reruns, so a
user can download an already-completed report without disturbing the processing
state of a subsequent audit.

### Status

**Implemented and regression-tested.**

Further real-document validation remains required before treating the
centrifugal-pump source mapping as complete across different OEMs and document
layouts.

### Known Issues / Follow-up

- `Driver Type` remains intentionally conservative for documents that only
  imply a motor type through secondary motor data without explicitly naming an
  accepted driver category.
- `Rated Power` source mapping is template-specific and should be reviewed when
  a project defines rated pump power differently from motor power.
- Multi-file validation should continue with mixed layouts, duplicate filenames,
  scanned/image-heavy PDFs, tables, checkbox documents, missing values,
  conflicting values and malformed PDFs.

------------------------------------------------------------------------


# 15. Current Status Update — Session 57

**Current product:** Sutreva

**Latest session:** Session 57 — Real Pump Datasheet Engineering Logic & Audit Run Safety

**Latest automated validation:** 216 tests passing.

**Current validated capabilities:**

- deterministic PDF extraction with source evidence
- explicit OEM terminology mappings through schema configuration
- live unit normalization
- conflict detection
- domain-aware engineering intelligence
- advisory Nemotron reasoning
- human review and governance events
- batch PDF processing with per-file failure isolation
- safe single-file and multi-file PDF audit contracts
- non-rerun report downloads during audit execution
- Nebius deployment configuration and offline preflight
- reproducible hackathon demo rehearsal

**Next validation priority:** expand the real OEM corpus and measure extraction,
evidence, status, batch reliability and review performance across materially
different document layouts before adding further extraction heuristics.

# 16. Development Timeline — Session 58

### Session 58 — File-Centric Results & Scalable Audit Review

### Type
Feature / UX / Reporting Architecture

### Problem / Requirement

The audit results table repeated the same file identifier across one row per
field. This is readable for a single document but becomes cluttered as the
number of OEM datasheets increases. The user requirement was to make the
results easier to sort and filter at batch scale by placing one file on each
row and the audited field values across columns, while retaining detailed
evidence for engineering review.

### Investigation

The existing `render_group_results()` function already had all field rows and
the configured schema available at render time. The existing overview table
was count-oriented and the field-by-field table was long-form. Therefore the
change could be implemented entirely at the presentation boundary without
changing extraction, deterministic comparison, evidence, unit normalization,
engineering intelligence or Nemotron reasoning.

The existing evidence/detail view and report exports were deliberately retained
so the new comparison view would not remove traceability.

### Decision

Adopt a two-level results architecture:

1. **Master comparison table:** one file/equipment per row, one configured
   audit field per column, plus `Overall Status` and `Review Fields`.
2. **Detailed review view:** expandable field-by-field rows with source
   evidence, rules and extracted values.

Add explicit batch filters for overall status and a selected field/status pair,
while preserving Streamlit's native column sorting/filtering on the master
table. Do not put evidence quotes or reasoning into the master cells because
that would recreate the clutter the change is intended to remove.

### Implementation

Updated `app.py` and added `results_view.py`:

- Built a schema-ordered file-centric master results table.
- Converted each configured field into a dedicated column.
- Added `Overall Status` and compact `Review Fields` columns.
- Added overall-status filtering.
- Added selected-field status filtering.
- Kept detailed evidence in the existing expandable review section.
- Kept the count-oriented overview available as a collapsed operational
  summary instead of the primary results table.
- Preserved existing processing, engineering intelligence and export behavior.

Added a UI regression test asserting the file-centric/filterable result
architecture.

### Testing & Verification

- `python -m pytest tests` -> **218 tests collected/passed**.
- `python -m py_compile app.py` and `python -m py_compile results_view.py` -> passed.
- Existing Session 57 real-pump regression coverage remains green.
- No extraction or audit-engine tests were modified to accommodate the UI
  change.

The test suite was executed from the project root; an initial invocation from
outside the project root produced expected relative-template path failures,
then the suite was rerun from the correct project root and passed completely.
No product defect was inferred from the initial incorrect working directory.

### Result

The audit workspace now scales as a comparison grid rather than a repeated
long-form list. Engineers can scan one file per row, sort/filter field values,
filter attention states, and then open the detailed evidence view only for the
records requiring investigation.

### Status

**Implemented and regression-tested.**

### Future Improvements

- Validate the master table with 20, 50 and 100+ real OEM documents.
- Consider equipment-type-specific column grouping when multiple templates are
  eventually shown in a shared portfolio view.
- Keep evidence and detailed reasoning out of the master table unless a compact
  drill-down interaction can be added without sacrificing scanability.



# 17. Current Status Update — Session 59

**Current product:** Sutreva

**Latest session:** Session 59 — Code Health, Performance & Dependency Optimization

**Latest automated validation:** 218 tests passing; Python compilation passed.

**Current validated capabilities:**

- file-centric audit-result presentation with separate detailed evidence review
- cached deterministic engineering intelligence across Streamlit reruns
- cached Excel/PDF/CSV report artifacts across Streamlit reruns
- modular result presentation boundary in `results_ui.py`
- explicit three-worker default for the lower-level text batch API and Streamlit UI
- explicit separation of parse retries from provider/network retries
- unused-import cleanup in the reviewed production modules
- Ruff added to development dependencies for future local/CI lint validation
- existing deterministic audit, evidence, unit-normalization, review, governance, evaluation and demo paths preserved

**Deliberately deferred:**

- PDF extraction-engine benchmark/hybrid extraction replacement was skipped as requested.
- PyMuPDF/pypdfium2 evaluation remains a future corpus-driven phase; no PDF parser was replaced in Session 59.
- Full live Streamlit runtime verification was not executed in this environment because the runtime dependency set is not installed here.

# 18. Development Timeline — Session 59

## [2026-09-30] — Code Health, Performance & Dependency Optimization

### Type
Architecture / Performance / Code Quality / Documentation

### Problem / Requirement

Session 58 review identified avoidable Streamlit rerun work, an oversized shared
result-rendering function, stale worker-count documentation, unused imports,
unclear retry boundaries, and missing development lint tooling. The requested
optimization was to execute the safe Phase 1 and structural Phase 3 work while
explicitly skipping the PDF-engine benchmark/replacement Phase 2.

### Investigation

The result renderer in `app.py` contained the shared comparison, engineering
intelligence, historical pattern, evidence, export, reasoning and debug UI in
one large function. Export serializer calls were evaluated during every render,
so Excel/PDF/CSV bytes could be regenerated on ordinary Streamlit reruns.
Engineering intelligence was also recomputed from unchanged result data on
reruns.

The reviewed production modules also contained imports no longer referenced by
current code. The Streamlit UI already used three workers, while the lower-level
text batch API and README described five as the default. Model-provider retries
and JSON-parse retries were separate mechanisms, but the distinction was not
explicit in the code documentation; with one retry at each layer, the worst
case is four provider requests for one audit extraction.

No PDF extraction engine was replaced or benchmarked in this session.

### Root Cause

The main performance issue was architectural: Streamlit reruns are expected,
but result-derived computations and serialization were not explicitly cached at
the presentation boundary. The maintainability issue was concentration of
multiple presentation responsibilities in `app.py`. Documentation/tooling drift
accounted for the worker-default mismatch and missing lint dependency.

### Decision

1. Move shared result rendering from `app.py` into `results_ui.py` without
   changing audit semantics.
2. Split the former monolithic renderer into focused preparation, outcome,
   comparison, engineering-intelligence, evidence-review, export, AI-reasoning,
   and raw-output rendering helpers.
3. Cache deterministic engineering reports and generated Excel/PDF/CSV bytes
   across Streamlit reruns using `st.cache_data`.
4. Align the lower-level text batch default with the current UI default at three
   workers and document the bounded concurrency choice.
5. Make parse-retry vs provider-retry boundaries explicit while preserving the
   existing retry counts and compatibility constants.
6. Remove verified unused imports and add Ruff to `requirements-dev.txt`.
7. Update the architecture/feature/debug documentation to reflect the live
   result-rendering path.
8. Do not change the PDF extraction engine in this session.

### Implementation

- Added `results_ui.py` as the presentation boundary for shared audit results.
- Reduced `app.py` to workflow/state responsibilities for this result path.
- Added cached engineering-report, historical-pattern and export helper functions in `results_ui.py`.
- Preserved `on_click="ignore"` on download controls.
- Removed unused imports from `core.py` and `ai_provider.py`; removed the now-
  unused result-rendering imports from `app.py`.
- Added `MAX_PROVIDER_RETRIES` as the explicit provider retry name while retaining
  `MAX_RETRIES` as a compatibility alias.
- Set `run_batch_audit()` default `max_workers` to 3 to match the Streamlit UI.
- Added `ruff>=0.6.0` to `requirements-dev.txt`.
- Corrected README worker wording and updated architecture/feature/debug maps.
- Updated `tests/test_ui_launch_design.py` so UI architecture checks cover both
  `app.py` and the new `results_ui.py` module.

### Testing & Verification

- `python -m pytest -q` -> **218 passed**.
- `python -m compileall -q .` -> passed.
- AST-based unused-import review for `app.py`, `core.py`, `ai_provider.py`, and
  `results_ui.py` -> no unused imports detected.
- PDF-engine benchmark/replacement -> intentionally not run.
- Ruff execution -> unavailable in the current environment because the package
  could not be installed without network access; dependency was added for local/CI use.
- Direct `results_ui` runtime import -> not executable in this environment because
  Streamlit is not installed in the current execution image; syntax compilation
  and the full existing test suite passed.

### Result

The result-rendering path is now separated from the main Streamlit workflow,
repeated deterministic analysis and report serialization are cached across normal
reruns, worker-default documentation is aligned with the actual UI behavior, and
retry semantics are explicit. The authoritative extraction, engineering comparison,
evidence, review, governance, evaluation and AI-provider behavior were not
redesigned.

### Status

**Implemented and regression-tested.**

### Known Issues / Follow-up

- The PDF extraction-engine optimization remains intentionally deferred.
- Real corpus validation remains the next evidence-based performance gate.
- Ruff should be executed in the developer/CI environment after dependencies are
  installed.
- Full Streamlit UI smoke testing should be performed in the target runtime image.
- A public open-source `LICENSE` file is still a submission-readiness item and was
  not selected automatically in this session because the project license choice was
  not explicitly specified.

### Future Improvements

- Run the deferred PDF-engine benchmark against the planned varied OEM corpus.
- Measure result-page latency and export-cache effectiveness on 20/50/100+ documents.
- Consider further `core.py` decomposition only after corpus-backed tests protect
  the extraction behavior.

### Session 59 — Ruff Findings Review / Lint Remediation Addendum

#### Type
Code Quality / Static Analysis / Regression Safety

#### Problem / Requirement
Local Windows validation installed Ruff successfully and reported 68 findings. The requirement was to review the findings before applying automated fixes, because Sutreva contains engineering-critical deterministic logic and the lint report included both safe style findings and potentially behavior-sensitive findings.

#### Investigation
The report consisted primarily of import ordering (`I001`), exception chaining (`B904`), explicit `zip(..., strict=...)` (`B905`), unused assignments/imports (`F401`/`F841`), a duplicate test definition (`F811`), inline statements (`E701`), and module-level imports after deliberate `sys.path` bootstrapping (`E402`) in deployment/demo scripts.

A controlled cleanup was performed against the Session 59 package. One attempted removal of `dataclasses.field` based on an `F402` finding immediately exposed a real behavior dependency because `field(default_factory=list)` is required by `IntelligenceResult`. That change was reverted before validation. This confirmed that Ruff's suggested fix must be reviewed rather than blindly applied.

The `E402` findings in the deployment/demo scripts are intentional: those scripts establish the repository root on `sys.path` before importing project modules when executed directly. They are therefore documented as per-file Ruff exceptions rather than being structurally reordered in a way that could break direct execution.

#### Decision
- Apply only reviewed, behavior-preserving lint fixes.
- Do not use Ruff `--unsafe-fixes`.
- Do not remove imports that are required by runtime declarations even when their names shadow local variables.
- Preserve intentional script bootstrap imports and configure explicit per-file Ruff exceptions for those boundaries.
- Keep engineering/audit behavior unchanged.

#### Implementation
Reviewed lint cleanup includes import ordering, exception chaining, explicit `zip(..., strict=True)`, removal of genuinely unused assignments/imports, duplicate-test cleanup, and formatting of the two temperature conversion branches in `units.py`.

The `field` import in `ai_orchestration.py` was retained because it is required at runtime by `dataclasses.field(default_factory=list)`.

Ruff per-file exceptions were added for the intentional repository-root bootstrap imports in `scripts/hackathon_demo_rehearsal.py` and `scripts/nebius_preflight.py`.

#### Testing & Verification
- `python -m compileall -q .` -> passed after remediation.
- `python -m pytest -q` -> **218 passed** after remediation.
- Ruff findings were reviewed from the developer-provided Ruff 0.16.9 report; Ruff itself was not executable in the isolated build environment, so no claim of a zero-finding Ruff run is made here.

#### Result
The lint report has been converted into a controlled cleanup rather than a blind auto-fix. Engineering behavior remains regression-tested at the existing 218-test baseline.

#### Status
**Implemented and regression-tested; final local Ruff verification required.**

### Session 59 — Final Ruff Cleanup / Import Normalization Addendum

#### Type
Code Quality / Static Analysis / Regression Safety

#### Problem / Requirement
The follow-up local Ruff report reduced the remaining findings from the earlier 68 to 25 findings: 24 import-organization findings (`I001`) and one exception-chaining finding (`B904`). The objective was to resolve the remaining findings without changing Sutreva behavior.

#### Investigation
The remaining `I001` findings were confined to import-block organization across production modules and tests. The `B904` finding was in the template-loading boundary in `core.py`, where the original `OSError` should remain available as the explicit exception cause.

The uploaded report confirms the final pre-cleanup count of 25 findings, with 24 marked fixable by Ruff and the `core.py` exception-chaining issue requiring a deliberate fix.

#### Decision
- Normalize the reported import blocks manually and conservatively.
- Apply the `core.py` exception-chain fix explicitly with `raise ... from e`.
- Do not apply broad unsafe or behavior-changing lint transformations.
- Re-run compilation and the complete offline regression suite after the cleanup.

#### Implementation
- Normalized import ordering/grouping in the reported production modules and test modules.
- Corrected the checkbox-test import grouping without changing test behavior.
- Corrected the `core.py` template-load exception to preserve the original `OSError` as the cause.
- No PDF extraction-engine changes were made.
- No audit-rule, evidence, AI, review, governance, or persistence behavior was changed.

#### Testing & Verification
- `python -m compileall -q .` -> passed.
- `python -m pytest -q` -> **218 passed**.
- The isolated build environment still does not have Ruff installed and cannot install packages because external package access is unavailable; therefore this session does not claim a fresh executable `ruff check .` result.
- The developer-provided local Ruff report remains the authoritative source for the findings that were remediated.

#### Result
The 25 findings shown in the follow-up Ruff report were addressed through controlled source edits, and the existing 218-test regression baseline remains intact.

#### Status
**Implemented and regression-tested; local Ruff execution should be the final lint gate.**


## [2026-09-30] — Windows Regression Findings After Ruff Import Cleanup
### Type
Bug Investigation / Regression Fix

### Problem / Requirement
After local Ruff import normalization, the Windows validation run exposed four pytest failures. Two failures came from tests reading UTF-8 source files using the Windows locale encoding. Two failures came from SQLite database files remaining open after persistence operations, causing Windows `WinError 32` cleanup failures.

### Investigation
The source files are valid UTF-8 and contain Unicode glyphs used by the application UI and engineering markers. The affected tests called `Path.read_text()` without an explicit encoding, which defaults to the Windows locale encoding in the reported environment. The persistence failure was traced to `review_store.connect()`: callers used `with connect(db_path) as conn`, but Python's sqlite3 connection context manager commits/rolls back and does not close the connection on context exit. Windows therefore retained a file handle to `reviews.sqlite3` when TemporaryDirectory attempted cleanup.

### Root Cause
1. Test source inspection depended on the Windows locale encoding instead of explicitly declaring UTF-8.
2. `review_store.connect()` returned a normal sqlite3 connection whose context-manager exit did not close the connection, leaving SQLite file handles open.

### Decision
Make UTF-8 explicit in source-inspection tests and make `review_store.connect()` return a connection that closes itself when leaving a context-manager block. This preserves the existing call pattern while correcting resource lifecycle behavior.

### Implementation
- Updated `tests/test_app_dashboard_integration.py` and `tests/test_architecture_truth.py` to use `read_text(encoding="utf-8")`.
- Added a private `_ClosingConnection` subclass in `review_store.py` whose `__exit__` delegates transaction handling and then closes the connection.
- Updated `connect()` to use `_ClosingConnection`.

### Testing & Verification
Local Windows pytest output identified the four failures: two `UnicodeDecodeError` failures and two SQLite `PermissionError: [WinError 32]` cleanup failures. The fixes are targeted to those root causes. Full regression validation must be rerun after applying this package.

### Result
The failures are understood and addressed without changing audit logic, extraction behavior, AI behavior, or PDF processing.

### Status
Fix implemented; awaiting local Ruff and full pytest confirmation.


## [2026-09-30] — Windows SQLite Test Cleanup Finalization
### Type
Bug Investigation / Test Reliability Fix

### Problem / Requirement
After the UTF-8 and persistence fixes, the local Windows suite still reported one failure in `test_review_store_reports_corrupt_evidence_json`: Windows could not remove the temporary `reviews.sqlite3` file because the test's direct `sqlite3.connect()` context left the connection open.

### Investigation
The failing test opens the SQLite database directly with `sqlite3.connect(db)` to corrupt `evidence_json`, commits the update, and then leaves the `with` block. On the reported Python 3.14 Windows environment, the SQLite connection remains an open file handle after context-manager exit. `TemporaryDirectory` subsequently attempts to delete the database and receives `PermissionError: [WinError 32]`.

The production `review_store.connect()` already uses the `_ClosingConnection` resource-lifecycle fix, so the remaining failure was isolated to the test's direct raw SQLite connection.

### Root Cause
The test relied on `sqlite3.Connection.__exit__` to close the connection. That context manager handles transaction semantics but does not guarantee connection closure, leaving a Windows file handle open during temporary-directory cleanup.

### Decision
Make the test's direct SQLite resource lifecycle explicit with `try/finally` and `conn.close()`. Do not add production workarounds solely for a test that intentionally bypasses the production persistence abstraction.

### Implementation
Updated `tests/test_traceability_integrity.py` so the corruption setup uses an explicit connection lifecycle:
- create `sqlite3.connect(db)`
- execute the deliberate corrupt-data update
- commit
- close in `finally`

No application persistence logic was changed by this final fix.

### Testing & Verification
- `python -m compileall -q .` -> passed.
- `python -m pytest -q` -> **218 passed**.
- The previously failing `test_review_store_reports_corrupt_evidence_json` now passes.
- Local Ruff 0.16.9 had already reported **All checks passed** after the import cleanup.

### Result
The Windows-specific regression is resolved at its actual source. The test suite is back to the established **218/218 passing** baseline, with no changes to Sutreva audit, extraction, AI, PDF, governance, or persistence behavior.

### Status
**Resolved and regression-tested.**

## [2026-10-01] — File-Centric Export Parity
### Type
Feature Enhancement / Export Consistency / Regression Validation

### Problem / Requirement
Session 58 introduced the file-centric results view in the application UI: one row per audited file/equipment record and one column per configured/audited field. The bulk PDF export still used the older flattened `(file, field)` table, while CSV also started with the flattened field-level representation and Excel's Overview sheet only summarized counts. The requirement was to make the file-centric representation the primary table in every bulk export format.

### Investigation
`results_view.py` already defined the intended file-centric presentation semantics: one record per result, field values as columns, an overall status, and a review-fields indicator. `exports.py` implemented separate bulk layouts for Excel, PDF, and CSV, so the UI and export representations had drifted. The existing detailed field-level export data remains useful for traceability and was therefore retained below the primary file-centric view rather than removed.

### Root Cause
The Session 58 file-centric presentation was implemented at the Streamlit results-view layer, but the bulk export serializers continued using their pre-existing flat field-row layout independently.

### Decision
Create one shared deterministic file-centric bulk-table builder in `exports.py` and use it as the primary representation for Excel, PDF, and CSV. Preserve the detailed field-level table/data in Excel's Detail sheet and CSV's Detailed Field Results section. Use landscape A4 for bulk PDF output so wider file-centric tables remain usable across multiple audited fields.

### Implementation
- Added `_build_file_centric_bulk_table()` to derive stable field columns from the bulk audit results and generate one row per file/equipment record.
- Added `Overall Status` with `MATCHED`, `REVIEW`, or `ERROR` semantics aligned with the Session 58 results view.
- Added `Review Fields` listing fields whose authoritative status is not `MATCHED`.
- Updated Excel `Overview` to use the file-centric table as its primary sheet while retaining the existing field-level `Detail` sheet.
- Updated PDF bulk export to render the same file-centric table as the primary report table; switched the bulk report to landscape A4 to accommodate field columns.
- Updated CSV bulk export to place the file-centric table first, followed by the detailed field-level section and summary counts.
- Added regression tests for the shared table shape and CSV/Excel file-centric output.
- No extraction, audit-rule, AI, evidence, review, or PDF-ingestion logic was changed.

### Testing & Verification
- `python -m compileall -q .` -> passed.
- `python -m pytest -q` -> **221 passed** (218 existing tests + 3 new export-parity tests).
- `python -m ruff check .` could not be executed in the isolated build environment because Ruff is not installed there; local Windows Ruff 0.16.9 had already reported **All checks passed** before this export-only change.
- Direct PDF validation with `pypdf` confirmed the generated PDF contains the file-centric headers `File`, `Recommended Lubricant`, `Recommended Grade`, `UOM`, `Overall Status`, and `Review Fields`, plus multiple audited identifiers.
- Excel validation with `openpyxl` confirmed the Overview header and one-row-per-file structure.
- CSV validation confirmed the file-centric table is the first data table and detailed field-level output remains available.

### Result
Bulk Excel, PDF, and CSV exports now share the same primary file-centric comparison representation introduced in Session 58, while detailed field-level traceability is preserved.

### Status
**Implemented and regression-tested.**

## [2026-10-04] — Batch Performance Instrumentation After Worker-Scaling Benchmark
### Type
Performance Measurement / Observability Enhancement

### Problem / Requirement
A 15-file heterogeneous centrifugal-pump corpus was benchmarked at approximately 18 minutes with 1 worker, 6 minutes 50 seconds with 3 workers, and 3 minutes 30 seconds with 6 workers. The near-linear scaling indicates that batch concurrency is effective, but the application did not expose per-file processing timing needed to diagnose future performance regressions or distinguish slow documents from slow batches.

### Investigation
The batch PDF path already limits configured concurrency to a maximum of 6 workers and uses `ThreadPoolExecutor`. The observed 1/3/6-worker timings showed strong throughput scaling, so no immediate change to the batch architecture or worker ceiling was justified. The optional Nemotron engineering reasoning toggle had also produced essentially the same 15-file elapsed time when disabled, so the reasoning pass was not identified as the dominant batch bottleneck in this test.

### Root Cause
The application had no lightweight runtime telemetry attached to batch results. Performance analysis therefore depended entirely on manually timing complete runs and could not show the per-file latency distribution after a batch completed.

### Decision
Do not increase the UI worker ceiling beyond 6 or change the default worker setting based solely on this benchmark. Add low-overhead per-file timing telemetry instead. Keep the existing concurrency architecture unchanged until provider limits, corpus behavior, and per-file latency are better understood.

### Implementation
- Added `time.perf_counter()` timing around each batch text/PDF worker execution in `core.py`.
- Added a `performance.total_s` field to successful and isolated-error batch result records.
- Preserved the existing result schema and error-isolation behavior; telemetry is additive only.
- Added a compact processing-telemetry caption to the shared results UI showing file count, average, minimum, and maximum per-file processing time when telemetry is available.
- Added regression coverage confirming timing metadata is present even when one batch item fails.
- No changes to extraction, audit rules, AI prompts/providers, PDF ingestion, worker ceiling, or export semantics.

### Testing & Verification
- `python -m compileall -q .` -> passed.
- `python -m pytest -q` -> **221 passed**.
- Ruff was not available in the isolated build environment; the user's local Ruff 0.16.9 baseline had already reported **All checks passed** before this instrumentation change. The modified code was kept Ruff-compatible by preserving import ordering and line-length conventions.
- Manual benchmark evidence: approximately 18:00 at 1 worker, 6:50 at 3 workers, and 3:30 at 6 workers for the same 15-file corpus.

### Result
Sutreva now exposes lightweight per-file processing telemetry without changing the audit pipeline. The benchmark supports retaining the existing 1–6 worker control while using measured telemetry for the next performance investigation.

### Status
**Implemented and regression-tested.**


---

## [2026-10-25] — Multi-Discipline Plant Equipment Profiles, ASTM/ASME Metallurgical Equivalence, Coupled Physics Checks & EPC Technical Query (TQ/CRS) Generator

### Type
- Feature / Architecture / Engineering Decision

### Problem / Requirement
1. Expand Sutreva beyond rotating pumps/seals so engineers can audit any plant equipment package (Distillation Columns/Towers, Chemical Reactors, Shell & Tube Heat Exchangers, Air-Cooled Fin Fans, Agitators/Mixers, Compressors, and Pressure Vessels).
2. Eliminate false `MISMATCHED` flags when a vendor specifies an equivalent ASTM/ASME metallurgical grade within the same alloy family (e.g., `A 216 Gr. WCC` for `A216WCB`, or `A 479 Type 410 Cl 2` for `A276-410` on Ruhrpumpen) while keeping cross-alloy mismatches (`A479-316` vs `A276-410`) strictly enforced.
3. Add coupled cross-parameter engineering checks (e.g., $\text{NPSH}_A - \text{NPSH}_R \ge 1.0\text{ m}$, $P_{\text{motor}} / P_{\text{rated}} \ge 1.10$, $P_{\text{design}} \ge P_{\text{operating}}$, $T_{\text{design}} \ge T_{\text{operating}}$).
4. Provide a 1-click **Technical Query (TQ) / Comments Resolution Sheet (CRS)** generator so flagged exceptions can be issued directly to vendors with page/line citations.

### Investigation
- Inspected `domain_rules.py`, `field_ontology.py`, `core.py`, `engineering_intelligence.py`, `exports.py`, and `results_ui.py`.
- Verified `tests/test_hackathon_demo_flow.py` and `scripts/hackathon_demo_rehearsal.py` to ensure that `A479-316` (316 Austenitic SS) continues to evaluate as `MISMATCHED` against `expected_value: "A276-410"` (410 Martensitic SS).

### Decision
- Group metallurgical grades into strict alloy-equivalent sets (`_METALLURGICAL_GRADE_FAMILIES` in `field_ontology.py`) so only genuine compositional/standard equivalents (`A216 WCB` $\leftrightarrow$ `A216 WCC`, `A276-410` $\leftrightarrow$ `A479 Type 410`, `AISI 316` $\leftrightarrow$ `CF8M`, `SA-516 Gr 70` $\leftrightarrow$ `A516 Gr 70`) match.
- Implement `evaluate_coupled_engineering_checks()` in `engineering_intelligence.py` as an advisory, deterministic physics layer that attaches `coupled_checks` to `EngineeringIntelligenceReport`.
- Implement `build_technical_query_rows()`, `to_tq_excel_bytes()`, and `to_tq_csv_bytes()` in `exports.py` and expose download buttons in `results_ui.py`.

### Implementation
- Modified `domain_rules.py`, `field_ontology.py`, `core.py`, `engineering_intelligence.py`, `exports.py`, and `results_ui.py`.
- Added `templates/shell_and_tube_heat_exchanger_audit.json`.

### Testing & Verification
- Not tested in chat environment — requires local execution of `python -m pytest` and `python scripts/hackathon_demo_rehearsal.py`.

### Result
- Multi-discipline equipment support, metallurgical equivalence, coupled physics checks, and CRS/TQ exports implemented.

### Status
- Needs Verification
