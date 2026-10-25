"""Read-only dashboard aggregates for industrial pilot reporting.

The functions here produce reporting metrics only; they do not approve or reject
engineering findings and do not infer production readiness.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping


def build_pilot_dashboard(
    benchmark_records: Iterable[Mapping[str, Any]] = (),
    cycle_records: Iterable[Mapping[str, Any]] = (),
    review_records: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Aggregate benchmark, cycle-time, and review data for a dashboard."""
    benchmarks = list(benchmark_records or [])
    cycles = list(cycle_records or [])
    reviews = list(review_records or [])

    by_equipment: dict[str, dict[str, Any]] = defaultdict(lambda: {"cases": 0, "value_accuracy_sum": 0.0, "status_accuracy_sum": 0.0})
    total_value_accuracy = 0.0
    total_status_accuracy = 0.0
    for record in benchmarks:
        value_accuracy = float(record.get("value_accuracy", 0) or 0)
        status_accuracy = float(record.get("status_accuracy", 0) or 0)
        equipment = str(record.get("equipment_type") or "UNKNOWN").strip() or "UNKNOWN"
        bucket = by_equipment[equipment]
        bucket["cases"] += 1
        bucket["value_accuracy_sum"] += value_accuracy
        bucket["status_accuracy_sum"] += status_accuracy
        total_value_accuracy += value_accuracy
        total_status_accuracy += status_accuracy

    equipment_summary = {}
    for equipment, bucket in sorted(by_equipment.items()):
        cases = bucket["cases"]
        equipment_summary[equipment] = {
            "cases": cases,
            "value_accuracy": bucket["value_accuracy_sum"] / cases,
            "status_accuracy": bucket["status_accuracy_sum"] / cases,
        }

    manual = sum(float(item.get("manual_minutes", 0) or 0) for item in cycles)
    assisted = sum(float(item.get("assisted_minutes", 0) or 0) for item in cycles)
    dispositions = Counter(str(item.get("disposition", "UNSET")).upper() for item in reviews)
    return {
        "benchmark_cases": len(benchmarks),
        "cycle_records": len(cycles),
        "review_records": len(reviews),
        "overall_value_accuracy": total_value_accuracy / len(benchmarks) if benchmarks else 0.0,
        "overall_status_accuracy": total_status_accuracy / len(benchmarks) if benchmarks else 0.0,
        "manual_minutes": manual,
        "assisted_minutes": assisted,
        "minutes_saved": manual - assisted,
        "time_reduction_rate": (manual - assisted) / manual if manual else 0.0,
        "review_dispositions": dict(sorted(dispositions.items())),
        "by_equipment": equipment_summary,
    }
