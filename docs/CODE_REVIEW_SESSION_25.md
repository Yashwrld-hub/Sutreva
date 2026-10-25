# Code Review — Session 25

## Scope

This pass focuses on low-risk packaging and test-discovery hygiene. It does not claim that every line has been manually proven redundant or that production performance has been benchmarked.

## Changes

- Added `pytest.ini` so the supported test suite is explicitly limited to `tests/`; the optional root-level API smoke test is not collected accidentally.
- Added a Ruff configuration for repeatable linting in development/CI environments.
- Excluded generated caches from the deployment archive.
- Preserved application behavior and existing public module interfaces.

## Follow-up required

1. Run Ruff and resolve findings in CI.
2. Add type checking with mypy or pyright.
3. Profile PDF/XLSX extraction on representative documents.
4. Add security tests for upload size, file type, secrets, and prompt injection.
5. Perform human usability validation before an industrial pilot.
