"""Deterministic pilot validation helpers.

These helpers compare copilot outputs with a human-reviewed benchmark without
making an engineering approval decision. They are intended for pilot QA.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping


def normalize_status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper().replace(" ", "_")


def benchmark_accuracy(
    predicted: Iterable[Mapping[str, Any]],
    benchmark: Iterable[Mapping[str, Any]],
    key: str = "field_name",
) -> dict[str, Any]:
    """Compare predicted statuses with a reviewed benchmark by stable key."""
    pred = {str(row.get(key)): normalize_status(row.get("status")) for row in predicted}
    gold = {str(row.get(key)): normalize_status(row.get("status")) for row in benchmark}
    keys = sorted(set(pred) | set(gold))
    missing_prediction = [item for item in keys if item not in pred and item in gold]
    missing_benchmark = [item for item in keys if item not in gold and item in pred]
    compared = [item for item in keys if item in pred and item in gold]
    correct = sum(pred[item] == gold[item] for item in compared)
    return {
        "compared": len(compared),
        "correct": correct,
        "accuracy": correct / len(compared) if compared else 0.0,
        "missing_prediction": missing_prediction,
        "missing_benchmark": missing_benchmark,
        "disagreements": [
            {"key": item, "predicted": pred[item], "benchmark": gold[item]}
            for item in compared if pred[item] != gold[item]
        ],
    }


def coverage_report(predicted: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Report evidence coverage; presence is not proof of correctness."""
    rows = list(predicted or [])
    with_evidence = sum(1 for row in rows if row.get("evidence"))
    return {
        "total": len(rows),
        "with_evidence": with_evidence,
        "without_evidence": len(rows) - with_evidence,
        "coverage_rate": with_evidence / len(rows) if rows else 0.0,
    }
