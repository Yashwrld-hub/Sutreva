# Product Discovery Session 31 — Actual OEM Material Extraction Fix

## Problem observed

The actual pilot report showed `Casing / Barrel Material` and `Shaft Material` as `MISSING`, while the source OEM PDF visibly contained `A216WCB` and `A276-410`.

## Source evidence

For the supplied API 610 datasheet, the extracted source text contains:

- `BARREL / CASE A216WCB IMPELLER A487CA6NM`
- `SHAFT A276-410`
- `INDUCTION MOTOR STEAM TURBINE GEAR`

The existing AI-only path could return null for the two material fields even when the values were plainly present in the source layout.

## Fix

A conservative deterministic text override layer was added for fields with finite accepted values or an exact expected value. The template supports field-specific `extraction_aliases`, allowing `Casing / Barrel Material` to recognize `BARREL / CASE` and `Shaft Material` to recognize `SHAFT`.

When multiple configured values occur on the same material row, the first configured value occurring after the explicit field alias is selected. This handles the source layout where the casing and impeller materials appear on the same line without treating both as candidates for the same field.

Evidence lookup now uses the same aliases, so the extracted value remains traceable and passes the evidence-support gate.

## Safeguard

This mechanism is intentionally limited to configured textual candidates. It does not infer arbitrary numeric values or use nearest-number heuristics. Ambiguous/unconfigured cases remain available to the model/human review workflow.

## Validation

- Regression suite: 121 tests passing.
- Python compilation: passed.
- Deployment sanity check: passed.
- Offline end-to-end simulation with model returning null for material fields: `A216WCB`, `A276-410`, and `Induction Motor` were recovered deterministically.
