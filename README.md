# Sutreva — Evidence-Backed Engineering Document Intelligence

**Sutreva turns engineering documents into reviewable, evidence-backed audit findings.** It uses NVIDIA Nemotron through Nebius Token Factory to extract technical data and, when enabled, perform a second evidence-grounded reasoning pass. A deterministic rules engine then checks extracted values against configurable engineering requirements. Engineers can investigate exceptions, inspect available evidence, record review dispositions, and export audit reports.

Sutreva is designed for **engineering, procurement, and construction (EPC) workflows across multiple engineering disciplines**. It helps teams extract and validate technical specifications, review vendor documentation, identify discrepancies against project requirements, and maintain traceable engineering audit records. Its configurable template architecture is intended to support different equipment types, engineering specifications, and structured registers rather than being limited to rotating equipment.

> **Engineering boundary:** Sutreva supports engineering review; it does not approve equipment or replace a qualified engineer. Model-generated values and explanations must be verified against the source documents and applicable project requirements before sign-off.

## Why this is more than PDF extraction

A generic extractor answers: **“What does this document say?”** Sutreva adds a configurable engineering question: **“Does the extracted value meet the selected requirement, and what evidence supports the finding?”**

Each engineering template defines checks such as acceptable-value lists, expected values, and numerical minimums or maximums. The audit engine applies those rules, distinguishes findings such as missing, mismatched, and out-of-range values, and keeps the result available for human review.

## NVIDIA Nemotron + Nebius Token Factory: how they power Sutreva

Nemotron is part of Sutreva's runtime workflow, not just a chatbot or a name in the technology stack.

- **Structured document extraction:** Sutreva sends the document text and a prompt scoped to the selected audit template to the configured Nemotron model. The model returns candidate field values in JSON form for the application to validate and compare.
- **Evidence-grounded reasoning:** When the reasoning pass is enabled, Sutreva sends the extracted values, deterministic rule outcomes, and available source evidence through a second Nemotron call. It can add assessments such as `SUPPORTED`, `AMBIGUOUS`, `UNSUPPORTED`, or `MISSING`, along with a risk label, concise rationale, and supplied evidence references.
- **Engineering-field enrichment:** The application can use Nemotron to help enrich field metadata in the field-ontology workflow.
- **Hosted inference through Token Factory:** `ai_provider.py` calls Nebius Token Factory through its OpenAI-compatible API. This lets the app use the configured hosted model without requiring the project to serve the model itself. The model, endpoint, and timeout are configurable at runtime.
- **Evaluation and reviewer feedback:** Sutreva records review feedback and supports curated evaluation cases so model or prompt changes can be assessed against engineering-specific examples rather than judged only by generic model benchmarks.

### The important separation of responsibilities

Nemotron supplies extraction and advisory reasoning. It does **not** own the final engineering status. `core.py` remains the authoritative comparison engine: configurable template rules, normalized values, deterministic checks, and conflict handling govern audit statuses. The second reasoning pass can explain uncertainty and surface ambiguity, but it must not silently override the configured rule result. Final dispositions remain with a human reviewer.

The current default model identifier is `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, configured in `runtime_config.py` and overridable with `NEBIUS_MODEL_NAME`. See [NVIDIA Nemotron](https://developer.nvidia.com/topics/ai/Nemotron) and [Nebius Token Factory's Nemotron overview](https://nebius.com/services/token-factory/nemotron) for model/provider information.

## Key capabilities

- **Template-driven engineering checks:** Separate JSON templates for supported engineering audits; add or adjust checks without changing the core comparison engine.
- **PDF and text audits:** Extract candidate fields from supported engineering and vendor documents, including a scanned-document OCR fallback. OCR and model outputs can be imperfect; verify critical values against the original page.
- **Batch auditing:** Process multiple documents with concurrency controls and per-file error isolation.
- **Bulk register auditing:** Map columns from `.xlsx` or `.csv` equipment and engineering registers to template fields. This path uses already-structured data and does not make an AI call for the row-by-row rule comparison.
- **Evidence and conflict review:** Preserve available source evidence and surface model/deterministic disagreements for inspection.
- **Engineering-intelligence context:** Add deterministic exception categories, severity, impact, suggested action, domain context, and advisory historical-pattern context where available.
- **Human review and evaluation workflow:** Record reviewer dispositions and feedback; explicitly curate closed cases into evaluation data. Feedback does not automatically retrain or silently change the model.
- **Exportable reports:** Export audit results to PDF, Excel (`.xlsx`) and CSV.
- **Demo and offline regression workflow:** Rehearse the main audit path with a clearly labelled synthetic pump PDF and deterministic fixtures, without consuming API credits.

**Scope note:** Sutreva's architecture is designed around configurable engineering templates. The current demonstration and example templates are narrower than the intended EPC-wide application scope; broader discipline coverage requires appropriate templates, requirements, test cases, and validation for each use case.

## How a typical audit works

1. **Choose a template.** Select the engineering requirement profile for the equipment, document, or audit type.
2. **Load the source.** Upload a vendor PDF or use supported text input. For bulk mode, upload an engineering spreadsheet and map its columns.
3. **Extract candidate fields.** The configured Nemotron model returns structured candidate values for document audits.
4. **Apply engineering rules.** Sutreva normalizes supported units and compares the data against the selected template using the deterministic audit engine.
5. **Review exceptions.** Inspect field statuses, available evidence, conflict information, rationale, and suggested next steps. The optional Nemotron reasoning pass is advisory.
6. **Record the disposition and export.** A qualified reviewer decides what to accept, clarify, or escalate, then exports the report.

## Quick start

### Requirements

- A supported Python installation.
- A Nebius Token Factory API key for live Nemotron inference.
- Internet access for live inference. The deterministic tests and offline demo rehearsal do not require an API key.

### Windows PowerShell

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
