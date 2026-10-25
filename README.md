# Sutreva — Evidence-Backed Engineering Document Intelligence

Sutreva is an evidence-backed engineering document intelligence and audit
platform designed for engineering, procurement, and construction (EPC)
workflows across multiple disciplines. It helps teams extract technical
specifications from vendor documents and structured engineering registers,
compare them against configurable project requirements, identify discrepancies,
and maintain traceable engineering review records.

Powered by NVIDIA Nemotron through Nebius Token Factory, Sutreva combines
AI-assisted extraction and optional advisory reasoning with deterministic
engineering rules and human review. Current examples focus on mechanical and
rotating-equipment documentation; broader discipline coverage requires
appropriate templates, requirements, and validation.

Built for the Nebius x NVIDIA Global AI Hackathon.

## 🚀 Live Demo

**Try Sutreva:** [Launch the Live Application](https://yashwrld-hub-sutreva-app-72rkuc.streamlit.app/)

- **Live Application:** https://yashwrld-hub-sutreva-app-72rkuc.streamlit.app/
- **Source Code:** https://github.com/Yashwrld-hub/Sutreva
- **License:** [MIT License](https://github.com/Yashwrld-hub/Sutreva/blob/main/LICENSE)

Explore the application to upload engineering documents, run an audit, review discrepancies and supporting evidence, and export structured audit reports.

## How this differs from general-purpose PDF extraction tools

Generic AI document-extraction products (e.g. invoice/receipt extractors aimed
at finance teams) solve a real but different problem: reading a messy PDF and
returning its data as a spreadsheet. That's the first half of this tool, not
the whole of it.

The actual problem here is **engineering compliance**, not extraction alone:
a value isn't useful on its own — it has to be checked against a configurable
technical standard and reported as matched, missing, mismatched, or out of
range. That comparison layer — acceptable-value lists, exact-match specs,
min/max thresholds, all defined per equipment type through the template
editor — is the core of the product, and it's not something general-purpose
extractors do, because invoices don't have engineering pass/fail criteria the
way a seal chamber pressure or a shaft material does.

In short: general extractors answer *"what does this document say?"* This
tool answers *"does what this document says meet our standard?"*

## How it works

1. Each file in `templates/` defines a company standard for one audit/equipment
   type (Mechanical Seal Audit, Centrifugal Pump Audit, etc.) — fully
   customizable by editing or adding a JSON file, no code changes needed.
2. `extract.py` / `app.py` read a supported engineering document (`.txt` or `.pdf`; scanned PDFs
   may use best-effort OCR), send it to a Nemotron model on Nebius Token
   Factory with a structured extraction prompt scoped to the chosen
   template's fields, and get back JSON.
3. The result is compared against the template's rules (acceptable values,
   expected values, min/max thresholds) and shown as a compliance report:
   MATCHED / MISMATCHED / MISSING / OUT OF RANGE.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# paste your real Nebius API key into .env
```

## Run it

```bash
# Step 1: confirm your key + model access work
python test_connection.py

# Step 2: run the actual Sutreva extraction + compliance check (CLI)
python extract.py sample_data/vendor_datasheet_1.txt
python extract.py sample_data/pump_datasheet_1.txt templates/centrifugal_pump_audit.json

# Export straight from the CLI
python extract.py sample_data/vendor_datasheet_1.txt --export xlsx
python extract.py sample_data/pump_datasheet_1.txt templates/centrifugal_pump_audit.json --export pdf

# Or launch the web UI (template picker, editor, and one-click exports)
streamlit run app.py
```

## Exporting results

Every audit — single-document, batch, or bulk — can be downloaded as
**Excel (.xlsx)**, **PDF**, or **CSV**, from the web UI's export buttons or
the CLI (`--export xlsx|pdf|csv`). Reports include the full field-by-field
table, colour-coded statuses, a summary count, and a note that AI-assisted
values should be verified before sign-off.

## Auditing datasheets (one at a time, or many at once)

The **Audit datasheets** tab handles both cases with the same flow — upload
one file or select several, and it adapts automatically:

1. **One file** → runs a single extraction and shows the field-by-field
   report immediately.
2. **Multiple files** → each one is sent to Nemotron **concurrently**
   (adjustable, default 3 at a time in the Streamlit UI) instead of one at a time, so a large
   batch doesn't mean waiting for each file sequentially. Failures are
   isolated per file — one bad scan or a transient API error is recorded
   as an error row for that file only and never stops the rest of the run.

Either way, results land in the same consolidated report, exportable as
Excel/PDF/CSV, with a "raw model output" debug view available per file.

This is genuinely concurrent, not sequential-with-a-progress-bar — verified
in `tests/test_batch.py`, which checks actual wall-clock timing (a 6-file
batch finishes in well under a second with several workers, versus ~1.8s
processed one at a time) and confirms the configured worker limit is
actually respected, not just accepted.

## Bulk audit mode (for equipment lists already in spreadsheet form)

Real equipment/lubrication registers usually already exist as structured
spreadsheets — one row per piece of equipment, one column per attribute —
not as individual PDFs. The **Bulk audit** tab handles this directly:

1. Upload an `.xlsx` or `.csv` equipment list.
2. Pick which column identifies each row (e.g. "Equipment Tag").
3. Map each template field to a spreadsheet column — the tool suggests a
   best-effort mapping automatically, which you can override.
4. Run the audit: every row is checked against the template's rules and
   reported as matched, missing, mismatched, or out of range.

**No AI call happens in this mode.** The data is already structured, so
mapping columns directly is faster and more reliable than sending it
through an LLM — the same comparison engine used for single-document and
batch audits is reused here, just applied row-by-row.

A synthetic sample equipment list (`sample_data/lube_oil_bulk_sample.xlsx`,
modeled on a real plant lubrication schedule) is included for testing.

## Hackathon demo rehearsal

The submission build includes a clearly labelled synthetic centrifugal-pump PDF so
the demo can exercise the real PDF/evidence path without requiring the presenter
to search for a document live. Start from the landing page with **Start hackathon
demo**, then load the demo PDF, run the audit, review the exception, and run the
evaluation flywheel.

The offline rehearsal script runs the same underlying pipeline with deterministic
model fixtures and never uses API credits:

```bash
python scripts/hackathon_demo_rehearsal.py
```

See `docs/HACKATHON_DEMO_SESSION_54.md` for the submission rehearsal checklist.

## Hackathon build status

Sutreva is being prepared for the **Nebius x NVIDIA Global AI Hackathon** under the **Best Apps and Agents** track. The project currently uses NVIDIA Nemotron through Nebius Token Factory. Submission-readiness requirements are tracked in:

- `docs/SUTREVA_HACKATHON_TRACKER.json` — machine-readable readiness checklist.
- `docs/HACKATHON_ALIGNMENT_SESSION_45.md` — architecture and submission gates.
- `docs/SUTREVA_SUBMISSION_ARCHITECTURE.md` — intended demo and technology narrative.

The official rules require the submitted project to run on Nebius Token Factory or Nebius AI Cloud, use at least one NVIDIA open-source model, provide a working demo/test build, public source repository and open-source license, README/setup instructions, and a public demonstration video under three minutes. See the live rules before submission: https://nebiusglobalaihackathon.devpost.com/rules

## NVIDIA Nemotron + Nebius Token Factory

**Configured model:** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`

**Endpoint:** `https://api.tokenfactory.nebius.com/v1/`

`ai_provider.py` calls Nebius Token Factory through its OpenAI-compatible
API. For document audits, Nemotron generates candidate structured field values
from source documents using the selected template. When enabled, a second
Nemotron pass assesses the extracted fields against deterministic rule results
and available evidence, producing advisory assessments and rationale for human
review.

**Separation of responsibilities:** `core.py` applies the configured template
rules and remains authoritative for audit status. Nemotron's reasoning is
advisory and must not silently override deterministic outcomes. A human reviewer
remains responsible for final acceptance or escalation. Bulk auditing of
already-structured `.xlsx` and `.csv` registers uses column mapping and
deterministic comparisons rather than sending each row to the model.

Live inference requires a valid `NEBIUS_API_KEY` in your local `.env` file.
Never commit API keys or expose them in logs or screenshots.

## Adding a new audit template

Add a new `.json` file to `templates/` following the same structure as the
existing ones (`template_name`, `sample_file`, and a `fields` list with each
field's expected type of check — `acceptable_values`, `expected_value`,
`min_value`, or `max_value`). It will automatically appear in the app's
template dropdown — no code changes required.

## Sample data

All sample datasheets under `sample_data/` are synthetic, made-up documents
(not real vendor or company data) used to demonstrate the tool.

## Supported input formats

- `.txt` — plain text.
- `.pdf` — digitally created PDFs. Scanned PDFs may be processed using
  best-effort OCR when no usable text layer is available.

OCR results depend on scan quality, orientation, layout, and text clarity.
Always verify critical extracted values against the original document page.


## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The latest local regression run on 25 October 2026 passed **221 tests**.
Re-run the test command above to validate your current checkout. The suite covers
comparison logic (matched/missing/mismatched/out-of-range, including boundary
values), template validation, save/load/edit behavior, cache invalidation,
Excel/PDF/CSV exporters, bulk-audit column mapping and row processing, and batch
processing concurrency, ordering, and per-file error isolation. These tests run
offline without an API key or network access.


## Engineering code map

For fast maintenance and debugging, this repository now includes a code-navigation map:

- `docs/SUTREVA_FEATURE_MAP.md` — feature → UI control → function → dependency → tests.
- `docs/SUTREVA_DEBUG_MAP.md` — symptom/error → first file/function to inspect.
- `docs/SUTREVA_ARCHITECTURE_MAP.md` — module responsibilities and dependency boundaries.
- `docs/SUTREVA_ARCHITECTURE_2_0.md` — target architecture and NeMo/Nemotron migration boundary.
- `docs/AI_PROVIDER_SESSION_44.md` — Session 44 provider abstraction and validation record.
- `docs/SESSION_43_BASELINE.md` — frozen Session 43 validation baseline and change discipline.
- `docs/SUTREVA_FEATURE_INDEX.json` — machine-readable version of the feature/debug index.
- `docs/EVIDENCE_EVALUATION_SESSION_47.md` — evidence contract and Session 47 evaluation methodology.
- `docs/ENGINEERING_INTELLIGENCE_SESSION_48.md` — deterministic engineering exception layer and Session 48 validation.
- `docs/DOMAIN_ENGINEERING_RULES_SESSION_49.md` — equipment-family profiles and Session 49 domain-context validation.
- `docs/SESSION_50_HISTORICAL_PATTERN_INTELLIGENCE.md` — advisory use of prior closed review cases for contextual pattern intelligence.
- `docs/SESSION_51_HUMAN_FEEDBACK_LOOP.md` — append-only reviewer feedback capture, evaluation-ready learning signals, and safe export rules.
- `feedback_loop.py` — human-feedback persistence, summary, and evaluation-dataset export; never auto-trains the model.
- `evals/sutreva_evidence_benchmark.jsonl` + `evals/sutreva_eval.py` — domain-specific evidence benchmark and scorer.
- `tests/test_feedback_loop.py` — append-only feedback persistence, evaluation-ready filtering, identity-safe export, and learning-signal summaries.
- `evals/nemo_evaluator.sutreva.yaml` — NeMo Evaluator model-regression smoke configuration.
- `domain_rules.py` — configurable equipment-domain context for pump, seal, and lubrication workflows.
- `scripts/hackathon_demo_rehearsal.py` — offline end-to-end rehearsal of the submission path without API credits.
- `sample_data/hackathon_pump_demo.pdf` — clearly labelled synthetic pump PDF used for hackathon rehearsal; it intentionally contains two review triggers.
- `docs/HACKATHON_DEMO_SESSION_54.md` — submission rehearsal sequence, truthfulness rules, and acceptance criteria.

These are maintained as navigation artifacts. When a feature's execution path changes, update the relevant map in the same change.

## Security notes

- **Prompt injection from uploaded documents**: datasheet text is inserted
  directly into the prompt sent to Nemotron. A malicious PDF/text file could
  contain text designed to make the model ignore its extraction instructions
  (e.g. "ignore previous instructions and output X"). In this tool, the
  blast radius is limited — the model's output is only ever shown back to
  the same user as a JSON/table, never executed or used to take further
  action — but this is a known limitation worth stating rather than ignoring.
  A production version handling untrusted third-party documents would need
  input sanitization and/or a system-prompt hardening pass.
- **Template files are trusted input, not user-submitted at runtime by
  strangers**: `load_schema()` now validates structure and fails cleanly on
  malformed JSON, but templates are still plain files on disk with no
  authentication layer — appropriate for a single-user hackathon prototype,
  not yet for a multi-tenant deployment.
- **API key handling**: kept in `.env`, never committed, never logged.

## Roadmap

These are future priorities; they should not be interpreted as existing,
production-ready capabilities.

- Improve OCR confidence reporting and evidence-to-field alignment for
  scanned or low-quality documents.
- Track vendor-package completeness across datasheets, drawings, certificates,
  inspection and test plans, and test reports.
- Compare document revisions and highlight changes affecting engineering
  requirements or previously reviewed fields.
- Check consistency across related documents and support technical-deviation
  tracking with ownership and closure evidence.
- Expand configurable templates across EPC disciplines, with discipline-
  specific requirements and validated evaluation cases.
- Strengthen deployment controls, project-level isolation, and integrations
  after controlled pilot testing.

## Synthetic pilot case pack

`pilot_casepack.py` contains synthetic pump, compressor, and lubrication-register
scenarios plus deterministic acceptance checks. These cases are for workflow QA
only; they are not real vendor data or approved engineering requirements.

## Controlled pilot: human audit vs tool audit

Use `docs/PILOT_EXECUTION_GUIDE.md` for the controlled comparison procedure. Blank CSV templates are available under `pilot_workspace/` for recording human-reviewed results, tool outputs, and field-level comparisons. Do not treat tool statuses as engineering approval; every final disposition requires human review.

### Deployment sanity check

```bash
python deployment_check.py
```

### Launch

```bash
python -m pip install -r requirements.txt
cp .env.example .env
# Add the authorized API key to .env
python deployment_check.py
python -m streamlit run app.py
```

### Graphical checkbox forms

Digitally-created OEM PDFs can use filled circles to indicate an enum selection
(e.g. `Driver Type`). When a schema contains `acceptable_values`, the ingestion
layer detects an unambiguous selected checkbox and preserves it as deterministic
source evidence. Ambiguous selections are left for human review.

## Session 53 — Nebius deployment and hackathon demo
The container/deployment path is documented in `docs/NEBIUS_DEPLOYMENT_SESSION_53.md`.
Use `python scripts/nebius_preflight.py` for an offline deployment check and
`python scripts/nebius_preflight.py --live` after setting `NEBIUS_API_KEY` to verify
that the configured Token Factory key can see the configured model. The 3-minute
demo script is in `docs/HACKATHON_DEMO_RUNBOOK.md`.

## Historical pattern intelligence

Session 50 adds an advisory history layer that compares current engineering exceptions with prior closed review cases. Historical context never changes the authoritative audit status or engineering rules. See `docs/SESSION_50_HISTORICAL_PATTERN_INTELLIGENCE.md`.



## Session 52
The evaluation flywheel converts explicitly curated human feedback into persistent gold cases and a regression gate covering assessment accuracy, risk accuracy, evidence grounding, and authoritative-status preservation.
