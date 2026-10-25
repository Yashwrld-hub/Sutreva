Sutreva — Evidence-Backed Engineering Document Intelligence
Sutreva turns OEM equipment documents into reviewable engineering audit findings. It uses NVIDIA Nemotron through Nebius Token Factory to extract technical data and, when enabled, perform a second evidence-grounded reasoning pass. A deterministic rules engine then checks extracted values against configurable, equipment-specific requirements. Engineers can investigate exceptions, inspect available evidence, record review dispositions, and export audit reports.

Sutreva is designed for rotating-equipment and maintenance workflows, including centrifugal pumps, mechanical seals, lubrication lists, and structured equipment registers.
Engineering boundary: Sutreva supports engineering review; it does not approve equipment or replace a qualified engineer. Model-generated values and explanations must be verified against the source documents and applicable project requirements before sign-off.

Why this is more than PDF extraction
A generic extractor answers: “What does this document say?” Sutreva adds a configurable engineering question: “Does the extracted value meet the selected requirement, and what evidence supports the finding?”

Each equipment template defines checks such as acceptable-value lists, expected values, and numerical minimums or maximums. The audit engine applies those rules, distinguishes findings such as missing, mismatched, and out-of-range values, and keeps the result available for human review.
NVIDIA Nemotron + Nebius Token Factory: how they power Sutreva
Nemotron is part of Sutreva's runtime workflow, not just a chatbot or a name in the technology stack.
- Structured document extraction: Sutreva sends the document text and a prompt scoped to the selected audit template to the configured Nemotron model. The model returns candidate field values in JSON form for the application to validate and compare.
- Evidence-grounded reasoning: When the reasoning pass is enabled, Sutreva sends the extracted values, deterministic rule outcomes, and available source evidence through a second Nemotron call. It can add assessments such as SUPPORTED, AMBIGUOUS, UNSUPPORTED, or MISSING, along with a risk label, concise rationale, and supplied evidence references.
- Equipment-field enrichment: The application can use Nemotron to help enrich field metadata in the field-ontology workflow.
- Hosted inference through Token Factory: ai_provider.py calls Nebius Token Factory through its OpenAI-compatible API. This lets the app use the configured hosted model without requiring the project to serve the model itself. The model, endpoint, and timeout are configurable at runtime.
- Evaluation and reviewer feedback: Sutreva records review feedback and supports curated evaluation cases so model or prompt changes can be assessed against engineering-specific examples rather than judged only by generic model benchmarks.
The important separation of responsibilities
Nemotron supplies extraction and advisory reasoning. It does not own the final engineering status. core.py remains the authoritative comparison engine: configurable template rules, normalized values, deterministic checks, and conflict handling govern audit statuses. The second reasoning pass can explain uncertainty and surface ambiguity, but it must not silently override the configured rule result. Final dispositions remain with a human reviewer.

The current default model identifier is nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B, configured in runtime_config.py and overridable with NEBIUS_MODEL_NAME. See NVIDIA Nemotron and Nebius Token Factory's Nemotron overview for model/provider information.
Key capabilities
- Template-driven engineering checks: Separate JSON templates for supported equipment/audit types; add or adjust checks without changing the core comparison engine.
- PDF and text audits: Extract candidate fields from supported OEM documents, including a scanned-document OCR fallback. OCR and model outputs can be imperfect; verify critical values against the original page.
- Batch auditing: Process multiple datasheets with concurrency controls and per-file error isolation.
- Bulk register auditing: Map columns from .xlsx or .csv equipment/lubrication registers to template fields. This path uses already-structured data and does not make an AI call for the row-by-row rule comparison.
- Evidence and conflict review: Preserve available source evidence and surface model/deterministic disagreements for inspection.
- Engineering-intelligence context: Add deterministic exception categories, severity, impact, suggested action, domain context, and advisory historical-pattern context where available.
- Human review and evaluation flywheel: Record reviewer dispositions and feedback; explicitly curate closed cases into evaluation data. Feedback does not automatically retrain or silently change the model.
- Exportable reports: Export audit results to PDF, Excel (.xlsx) and CSV.
- Demo and offline regression workflow: Rehearse the main audit path with a clearly labelled synthetic pump PDF and deterministic fixtures, without consuming API credits.
How a typical audit works
1. Choose a template. Select the engineering requirement profile for the equipment/audit type.
2. Load the source. Upload an OEM PDF or use supported text input. For bulk mode, upload an equipment spreadsheet and map its columns.
3. Extract candidate fields. The configured Nemotron model returns structured candidate values for document audits.
4. Apply engineering rules. Sutreva normalizes supported units and compares the data against the selected template using the deterministic audit engine.
5. Review exceptions. Inspect field statuses, available evidence, conflict information, rationale, and suggested next steps. The optional Nemotron reasoning pass is advisory.
6. Record the disposition and export. A qualified reviewer decides what to accept, clarify, or escalate, then exports the report.
Quick start
Requirements
- A supported Python installation.
- A Nebius Token Factory API key for live Nemotron inference.
- Internet access for live inference. The deterministic tests and offline demo rehearsal do not require an API key.
Windows PowerShell
From the project root:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Edit .env and set your authorized key:
NEBIUS_API_KEY=your-real-key-here
Do not commit .env or expose the key in logs, screenshots, issue reports, or public repositories. Then run:
python test_connection.py
python deployment_check.py
python -m streamlit run app.py
macOS / Linux
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env and set NEBIUS_API_KEY
python test_connection.py
python deployment_check.py
python -m streamlit run app.py
Runtime configuration
Variable	Purpose	Default / behavior
NEBIUS_API_KEY	Authorizes live Token Factory API calls	Required for live model inference; keep secret
NEBIUS_MODEL_NAME	Selects the model ID	nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
NEBIUS_API_BASE_URL	Token Factory-compatible API endpoint	https://api.tokenfactory.nebius.com/v1/
NEBIUS_REQUEST_TIMEOUT_S	Model-request timeout	90 seconds
SUTREVA_MODEL_PROVIDER	Selects the configured provider	nebius_nemotron
SUTREVA_ENV	Runtime environment label	development
SUTREVA_REVIEW_DB_PATH	Optional path for persisted review records	Defaults to oem_audit_reviews.sqlite3 in the working directory; use an appropriately protected persistent location in deployments


The configuration values are implemented in runtime_config.py; the provider integration is in ai_provider.py.
Run an audit
Streamlit application
python -m streamlit run app.py
Choose an audit template, upload a document, run the audit, inspect flagged fields, and export the results. The landing page also provides the guided hackathon demo path. The Use sample workflow loads a project sample into the audit flow for a repeatable first run.
Command line
# Basic text/datasheet audit
python extract.py sample_data/vendor_datasheet_1.txt

# Specify the centrifugal-pump template
python extract.py sample_data/pump_datasheet_1.txt templates/centrifugal_pump_audit.json

# Export a result
python extract.py sample_data/pump_datasheet_1.txt templates/centrifugal_pump_audit.json --export pdf
python extract.py sample_data/vendor_datasheet_1.txt --export xlsx
Bulk auditing of a spreadsheet
1. Open Bulk audit in the application.
2. Upload an .xlsx or .csv equipment/lubrication register.
3. Select the equipment identifier column and map template fields to spreadsheet columns.
4. Run the comparison and export the results.
The bulk path uses deterministic rules on structured values; it does not send the register rows through the LLM for extraction.
Demo and offline rehearsal
The repository includes sample_data/hackathon_pump_demo.pdf, a clearly labelled synthetic centrifugal-pump document designed to trigger two review findings. It is not real vendor data and its rules are not approved engineering requirements.

For a rehearsed end-to-end path without API credits:
python scripts/hackathon_demo_rehearsal.py
Important: the offline rehearsal uses deterministic model fixtures. It validates the application workflow and evaluation gate; it does not demonstrate a live Nemotron response or establish live-provider accuracy. For live inference, configure NEBIUS_API_KEY and use python scripts/nebius_preflight.py --live.

The rehearsal checklist is in docs/HACKATHON_DEMO_SESSION_54.md; the deployment path is documented in docs/NEBIUS_DEPLOYMENT_SESSION_53.md.
Evaluation and testing
Run the offline test suite:
python -m pip install -r requirements-dev.txt
python -m pytest --override-ini addopts='' -q -ra
Compile and run the other local checks:
python -m compileall -q .
python deployment_check.py
python scripts/hackathon_demo_rehearsal.py
The suite covers deterministic rule comparisons, evidence verification, unit normalization, conflict handling, template validation, exporters, batch processing and concurrency, bulk-audit mapping, feedback persistence, evaluation scoring, and related workflows. Latest local validation recorded for this project copy on 25 October 2026: 229 tests passed, Python compilation passed, deployment sanity check passed, and the offline demo evaluation gate passed. The rehearsal used deterministic fixtures (live_provider: false); a live provider call and representative real-vendor benchmark must be validated separately.

Sutreva also provides a controlled pilot workflow under docs/PILOT_EXECUTION_GUIDE.md. The claimed accuracy should be based on manually verified field-level ground truth, with false passes, missed discrepancies, evidence grounding, and unnecessary review flags tracked separately. A preliminary manual estimate is not a formal benchmark.
Architecture and developer guide
Component	Responsibility
app.py	Streamlit interface and audit/review workflow
core.py	Extraction orchestration and authoritative deterministic rule comparison
ai_provider.py	Provider abstraction and Nemotron calls through Nebius Token Factory
runtime_config.py	Model, endpoint, timeout, provider, and review-database configuration
ai_orchestration.py	Non-authoritative, evidence-grounded Nemotron reasoning pass
field_ontology.py	Engineering-field ontology and optional Nemotron-assisted field enrichment
domain_rules.py / engineering_intelligence.py	Equipment-domain context and deterministic exception explanations
review_queue.py / review_store.py / governance.py	Review workflows, persistence, and disposition events
feedback_loop.py / evaluation_flywheel.py / evals/	Reviewer feedback, curated evaluation cases, and regression scoring
exports.py / results_ui.py	Audit outputs and report presentation
templates/	Configurable engineering rules by equipment/audit type


For deeper navigation, start with docs/SUTREVA_FEATURE_MAP.md, docs/SUTREVA_DEBUG_MAP.md, docs/SUTREVA_ARCHITECTURE_MAP.md, and docs/SUTREVA_ENGINEERING_LOG.md. If a feature's execution path changes, update the relevant navigation document in the same change.
Hackathon alignment — Nebius × NVIDIA Global AI Hackathon
Track: Best Apps and Agents
Core technology: NVIDIA Nemotron through Nebius Token Factory

Sutreva is an industrial engineering application rather than a general-purpose chatbot. Its multi-step workflow uses Nemotron for technical extraction and optional evidence-grounded reasoning, then applies deterministic engineering rules and preserves human review as the final decision point. Nebius Token Factory provides the hosted inference path through an OpenAI-compatible API, while Sutreva's application code handles template selection, comparison logic, evidence/review presentation, feedback capture, and evaluation.
Why Nemotron is material to the application
- Removing the model call would remove the AI-assisted extraction of raw OEM document content and the optional model-based evidence assessment; those are meaningful runtime stages.
- The model is not asked to invent engineering limits. Rules stay in the selected template and the deterministic comparison engine.
- The second reasoning pass is evidence-constrained and advisory; model failure or ambiguity must not silently change the authoritative status.
- The evaluation workflow is intended to measure evidence grounding, assessment/risk quality, and status preservation on curated engineering examples.
Hackathon-period development to explain in the submission
The current project history includes work on the Nebius/Nemotron provider integration, evidence-grounded reasoning, unit-aware deterministic comparison and conflict review, clearer field-level audit diagnostics, domain-specific engineering intelligence, historical review patterns, reviewer feedback and evaluation workflows, and a synthetic end-to-end pump demo with an offline rehearsal path. Use the repository's actual commits and engineering log to describe which of these changes were made during the official submission period; do not claim pre-existing work as new.
Submission checklist
Before submitting, verify the current official rules and complete the required items. The rules include a working demo/test build, public code repository with an open-source license, clear setup instructions, an under-three-minute public YouTube demo, identification of the track, explanation of NVIDIA model and Nebius technology usage, feedback on the tools used, and an explanation of significant updates if the project existed before the submission period.

This README describes the implemented architecture and local validation; it does not by itself claim that a public deployment, public demo video, open-source license, or completed Devpost submission is already available. Confirm each item in the live submission before representing it as complete.

Relevant official links:
- Hackathon rules
- Hackathon overview
- How judging works
- Tips for a stronger submission
- Nebius Token Factory — Nemotron
- NVIDIA Nemotron models
Security, privacy, and limitations
- API credentials: keep the real key in .env or a secret manager; never commit secrets or paste them into logs or screenshots.
- Sensitive engineering records: persisted review decisions and evidence may include confidential vendor/project context. Keep the SQLite database out of source control and release archives. Configure SUTREVA_REVIEW_DB_PATH and suitable storage/access controls for a deployed environment.
- Prompt injection: uploaded document text is untrusted input and is included in model prompts. The model output is treated as data, not executable code, but prompt-injection and source-confusion risks remain. Do not use the prototype as an autonomous approval system.
- OCR and source alignment: scanned PDFs may introduce recognition errors, and an extracted value can be associated with the wrong line/field. Verify important values against the source page and approved requirements.
- Single-user prototype boundary: template JSON files are trusted local configuration, not a multi-tenant permission system. Authentication, tenant isolation, and production-grade access controls require further work before broader deployment.
- Engineering sign-off: template mismatch is not by itself proof that equipment is unsafe; acceptance depends on approved project requirements and qualified engineering judgment.
Roadmap
Priorities informed by user-workflow research:
1. Evidence Inspector with page/region grounding and field-level confidence validated against human-checked data.
2. Vendor package completeness tracking across datasheets, GA drawings, motor/driver sheets, ITPs, certificates, and test reports.
3. Revision comparison and change-impact reports for vendor revisions and approved requirements.
4. Cross-document consistency checks and a formal technical-deviation register with ownership and closure evidence.
5. Improved OCR confidence and evidence-to-field alignment for scanned documents.
6. Carefully scoped document-management/CMMS/EAM integrations after a controlled pilot establishes value and data-governance requirements.
These are planned directions, not claims that all capabilities are already implemented.
Adding a new audit template
Add a JSON file to templates/ following the existing schema, including template_name, sample_file, and a fields list. Field rules may use acceptable_values, expected_value, min_value, or max_value. Validate the new template and add regression tests before using it for real engineering review.
Sample data and licensing
All sample datasheets in sample_data/ are synthetic demonstration fixtures, not real vendor or company records. Synthetic examples and configured limits are not approved engineering standards.

Before publishing the repository, include an appropriate open-source LICENSE file and review dependency/model licensing and third-party terms. Confirm the model and API usage are permitted for the intended hackathon/project use.
