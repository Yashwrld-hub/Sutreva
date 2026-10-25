"""Deterministic pilot metrics for audit workflow measurement."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def summarize_results(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return aggregate metrics without making engineering approval decisions."""
    results = list(results or [])
    total_files = len(results)
    failed = sum(1 for item in results if item.get("error"))
    rows = [row for item in results for row in (item.get("rows") or [])]
    statuses = Counter(str(row.get("status", "UNKNOWN")).upper() for row in rows)
    total_rows = len(rows)
    flagged = sum(statuses[s] for s in ("MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW", "CONFLICT"))
    matched = statuses.get("MATCHED", 0)
    return {
        "files_processed": total_files,
        "files_failed": failed,
        "rows_evaluated": total_rows,
        "matched_rows": matched,
        "flagged_rows": flagged,
        "status_counts": dict(sorted(statuses.items())),
        "flag_rate": (flagged / total_rows) if total_rows else 0.0,
    }


def compare_cycle_times(manual_minutes: float, assisted_minutes: float) -> dict[str, float]:
    """Calculate pilot time deltas; rejects invalid negative durations."""
    if manual_minutes < 0 or assisted_minutes < 0:
        raise ValueError("Cycle times cannot be negative")
    saved = manual_minutes - assisted_minutes
    reduction = (saved / manual_minutes) if manual_minutes else 0.0
    return {"manual_minutes": manual_minutes, "assisted_minutes": assisted_minutes,
            "minutes_saved": saved, "reduction_rate": reduction}
