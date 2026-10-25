# Product Launch Design Review — Session 35

## Objective

Turn the engineering prototype into a product-like workspace without changing the proven extraction/comparison logic used by the controlled pilot.

## Design decisions

- Keep **OEM Audit Copilot** as the pilot product name.
- Make the first interaction explain the workflow through layout rather than promotional copy.
- Add an Overview workspace with Source → Check → Review → Record flow.
- Put the current audit context close to the primary workflow.
- Use outcome states that answer “what should I do next?” without overstating engineering certainty.
- Make evidence a first-class review surface for PDF audits.
- Keep templates, pilot analytics, and administration available without competing with the primary Audit workflow.
- Remove decorative AI/emoji styling from the product identity.

## Functional improvements in this sprint

- PDF audits use the evidence-aware audit pipeline in the single-document flow.
- Source evidence is surfaced in the field-level review panel when available.
- Audit sessions are summarized in the Overview workspace.
- A small in-session audit history is recorded to help users return to the previous run.
- The sidebar now has a clear New audit action and a more restrained product mark.

## Pilot protection

The following were intentionally left unchanged:

- Extraction rules and deterministic overrides.
- Checkbox handling.
- Material-field recovery.
- Comparison rules.
- Benchmark methodology.
- Governance/approval semantics.

## Validation

- Full test suite: passing.
- Python compilation: passing.
- Deployment sanity check: passing.
- UI source checks cover the Overview, evidence panel, and evidence-aware PDF pipeline.
- Streamlit live browser rendering was not available in the current execution environment; final visual QA should therefore be done after installing `requirements.txt` and launching the app locally.
