"""Benchmark execution helpers for human-reviewed pilot comparisons.

This module is deliberately model-agnostic: it compares normalized prediction
records with a reviewer-maintained reference set and reports measurement data.
It does not approve engineering values or declare production readiness.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def _key(row: Mapping[str, Any]) -> str:
    return str(row.get("field_name") or "").strip().lower()


def compare_reference_set(
    predictions: Iterable[Mapping[str, Any]],
    reference: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare field-level predictions against a human-reviewed reference set."""
    pred = {_key(row): row for row in predictions if _key(row)}
    gold = {_key(row): row for row in reference if _key(row)}
    keys = sorted(set(pred) | set(gold))

    exact = 0
    status_matches = 0
    mismatches: list[dict[str, Any]] = []
    for field in keys:
        p, g = pred.get(field), gold.get(field)
        if p is None or g is None:
            mismatches.append({"field_name": field, "reason": "missing_prediction_or_reference"})
            continue
        if p.get("value") == g.get("value"):
            exact += 1
        if str(p.get("status", "")).upper() == str(g.get("status", "")).upper():
            status_matches += 1
        if p.get("value") != g.get("value") or str(p.get("status", "")).upper() != str(g.get("status", "")).upper():
            mismatches.append({"field_name": field, "reason": "value_or_status_difference"})

    return {
        "prediction_fields": len(pred),
        "reference_fields": len(gold),
        "comparable_fields": len(set(pred) & set(gold)),
        "exact_value_matches": exact,
        "status_matches": status_matches,
        "value_accuracy": exact / len(set(pred) & set(gold)) if set(pred) & set(gold) else 0.0,
        "status_accuracy": status_matches / len(set(pred) & set(gold)) if set(pred) & set(gold) else 0.0,
        "missing_prediction": sorted(set(gold) - set(pred)),
        "prediction_only": sorted(set(pred) - set(gold)),
        "mismatches": mismatches,
    }


def summarize_review_dispositions(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize reviewer dispositions without treating them as approvals."""
    dispositions = Counter(str(row.get("disposition", "UNSET")).upper() for row in records)
    return {"total_reviewed": sum(dispositions.values()), "dispositions": dict(sorted(dispositions.items()))}
