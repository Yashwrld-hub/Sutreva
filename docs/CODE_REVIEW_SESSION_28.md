# Code Review — Session 28

## Review objective

Audit the current OEM Audit Copilot codebase for the reported runtime error:

`Expecting value: line 1 column 1 (char 0)`

and perform a static, behavior-preserving review for redundant code, avoidable
work, fragile parsing, unsafe patterns, and deployment blockers.

## Scope

- 20 production Python modules were reviewed.
- 19 test modules were reviewed.
- Production Python source: 2,860 lines.
- Test source: 1,108 lines.
- All production and test modules were AST-parsed and compiled.
- Import-use analysis found no unused production imports.
- Search for dynamic execution/unsafe deserialization patterns found no `eval`,
  `exec`, `pickle`, `yaml.load`, `os.system`, or `shell=True` usage.

## Root cause of the reported JSON error

`core.parse_json_safely()` previously called `json.loads()` directly after only
removing markdown fences. An empty model response or a short non-JSON preamble
therefore surfaced the low-level JSON decoder message:

`Expecting value: line 1 column 1 (char 0)`

The error is now handled at the model-output boundary.

## Fixes implemented

### 1. Defensive model response validation — `core.py`

- Empty/whitespace-only model responses now produce an actionable error.
- Markdown JSON fences are removed safely.
- A valid JSON object/array preceded by a short natural-language preamble can
  be recovered using the standard JSON decoder's `raw_decode()`.
- Malformed JSON syntax is not silently rewritten.
- The audit layer explicitly requires a JSON object.
- A single retry is issued only after a JSON parse failure, with a stricter
  JSON-only instruction. Normal successful audits make no extra API call.

### 2. Checkbox extraction remains deterministic — `core.py`

- Checkbox overrides are still applied after model parsing, so a model `null`
  or wrong guess cannot overwrite a deterministic selected checkbox.
- PDF word normalization is now computed once per page during checkbox
  extraction rather than repeatedly for every accepted option.

### 3. Persistence error clarity — `review_store.py`

Corrupt stored evidence JSON no longer exposes a raw `JSONDecodeError`. The
error identifies the affected review item so the database record can be
investigated.

### 4. Small UI performance cleanup — `app.py`

The suggested spreadsheet identifier column is calculated once instead of
calling the same heuristic twice during widget creation.

## Regression coverage added

- Model output with a JSON preamble.
- Empty model output.
- Non-object model output.
- One retry after malformed JSON.
- Corrupt persisted evidence JSON.

## Validation

- 113 automated tests pass.
- Python bytecode compilation passes.
- Deployment sanity check passes.
- All JSON templates were loaded as part of the test/deployment workflow.
- A simulated empty-first-response followed by valid JSON completes the audit
  and preserves deterministic checkbox extraction.

## Non-blocking technical debt

1. Ruff and mypy could not be installed in the isolated environment because
   external package download was unavailable. The repository already contains
   Ruff configuration for the next connected CI run.
2. `app.py` and several export functions are large UI/reporting functions. They
   are candidates for further modularization, but splitting them now would add
   refactoring risk without improving the reported error.
3. Some boundary handlers intentionally use broad exceptions to isolate an
   individual file or API call. These should remain at boundaries but should be
   narrowed where a production deployment provides stable exception classes.
4. Current PDF ingestion is for digital PDFs; scanned documents still require
   OCR.
5. Real industrial accuracy must still be established using an authorized,
   human-reviewed benchmark set.

## Review conclusion

The reported `Expecting value` failure was a brittle model-output parsing issue.
The parser and audit boundary are now defensive, parse failures are actionable,
and malformed responses get one targeted recovery attempt. The changes are
behavior-preserving for valid JSON and ordinary text fields.
