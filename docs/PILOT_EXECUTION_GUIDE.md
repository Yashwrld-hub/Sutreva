# Human Audit vs Tool Audit — Pilot Execution Guide

## Purpose

Compare an engineer-reviewed audit with the tool-generated audit using the same authorized source document. This guide is for controlled pilot evaluation, not automatic engineering approval.

## Required inputs

1. Authorized OEM datasheet or equipment register.
2. Approved audit template and acceptance criteria.
3. Human reviewer with appropriate engineering responsibility.
4. Tool run identifier and source-document identifier.

## Recommended procedure

1. Assign a unique `case_id` and record the source-document name/version.
2. Have the engineer complete `pilot_workspace/human_audit_template.csv` without using the tool output.
3. Run the same source document through the application.
4. Export the tool result and populate `pilot_workspace/tool_audit_results_template.csv`.
5. Join the human and tool records using `case_id`, equipment tag, and field.
6. Complete `pilot_workspace/comparison_template.csv`.
7. Review every mismatch, missing field, unit discrepancy, and evidence gap.
8. Record the final disposition: `accepted`, `corrected`, `rejected`, or `needs SME review`.

## Measurement definitions

- **Value match:** Human-reviewed value and tool value agree after an explicitly documented unit normalization.
- **Status match:** Human status and tool status agree under the approved audit rule.
- **Evidence present:** The tool result contains a usable source reference that a reviewer can verify.
- **Final disposition:** Human decision after reviewing the source and comparison; never inferred automatically from the model output.

## Controls

- Do not upload confidential documents without authorization.
- Do not put API keys in source files or commit `.env`.
- Treat document text as untrusted input.
- Do not treat a `MATCHED` result as engineering approval.
- Keep document version, reviewer identity, and review date for every case.
- Keep synthetic cases separate from real pilot results.

## Pilot exit criteria

Agree on the following before starting the pilot:

- Target equipment category and sample size.
- Required fields and accepted units.
- Accuracy calculation method.
- Treatment of missing, ambiguous, and conflicting values.
- Minimum evidence coverage.
- Reviewer sign-off requirements.
- Data retention and deletion rules.
