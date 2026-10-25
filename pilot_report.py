"""Exportable, evidence-aware pilot reporting helpers.

Reports summarize measurements and preserve their provenance. They do not
approve engineering findings or declare production readiness.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from pilot_dashboard import build_pilot_dashboard


def build_pilot_report(
    benchmark_records=(),
    cycle_records=(),
    review_records=(),
    *,
    project_name: str = "Sutreva",
    data_classification: str = "SYNTHETIC_DEVELOPMENT_DATA",
    reviewer: str = "",
) -> dict[str, Any]:
    """Create a portable report envelope with metrics and provenance."""
    benchmark_records = list(benchmark_records or [])
    cycle_records = list(cycle_records or [])
    review_records = list(review_records or [])
    dashboard = build_pilot_dashboard(benchmark_records, cycle_records, review_records)
    return {
        "report_metadata": {
            "project_name": project_name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_classification": data_classification,
            "reviewer": reviewer,
            "engineering_approval": False,
        },
        "metrics": dashboard,
        "source_counts": {
            "benchmark_records": len(benchmark_records),
            "cycle_records": len(cycle_records),
            "review_records": len(review_records),
        },
        "traceability": _traceability_summary(benchmark_records, review_records),
        "traceability_index": build_traceability_index(benchmark_records, review_records),
    }


def report_json_bytes(report: Mapping[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")


def report_summary_csv_bytes(report: Mapping[str, Any]) -> bytes:
    """Export a compact KPI/value CSV suitable for review or spreadsheet use."""
    metrics = report.get("metrics", {})
    rows = [
        ("benchmark_cases", metrics.get("benchmark_cases", 0)),
        ("overall_value_accuracy", metrics.get("overall_value_accuracy", 0.0)),
        ("overall_status_accuracy", metrics.get("overall_status_accuracy", 0.0)),
        ("manual_minutes", metrics.get("manual_minutes", 0.0)),
        ("assisted_minutes", metrics.get("assisted_minutes", 0.0)),
        ("minutes_saved", metrics.get("minutes_saved", 0.0)),
        ("time_reduction_rate", metrics.get("time_reduction_rate", 0.0)),
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _traceability_summary(benchmark_records, review_records):
    """Summarize record-level provenance without asserting engineering validity."""
    with_source = 0
    with_evidence = 0
    with_reviewer = 0
    for record in benchmark_records:
        if record.get("source_document") or record.get("source_id"):
            with_source += 1
        if record.get("evidence_refs") or record.get("evidence"):
            with_evidence += 1
    for record in review_records:
        if record.get("reviewer") or record.get("reviewer_id"):
            with_reviewer += 1
    total = len(benchmark_records)
    return {
        "benchmark_records_with_source": with_source,
        "benchmark_records_with_evidence": with_evidence,
        "benchmark_records_total": total,
        "source_coverage_rate": (with_source / total) if total else 0.0,
        "evidence_coverage_rate": (with_evidence / total) if total else 0.0,
        "review_records_with_reviewer": with_reviewer,
        "review_records_total": len(review_records),
    }


def build_traceability_index(benchmark_records=(), review_records=()):
    """Return a stable, export-friendly index of benchmark and review provenance."""
    rows = []
    for record_type, records in (("benchmark", benchmark_records or []), ("review", review_records or [])):
        for index, record in enumerate(records, start=1):
            rows.append({
                "record_type": record_type,
                "record_index": index,
                "case_id": record.get("case_id", ""),
                "equipment_tag": record.get("equipment_tag", ""),
                "source_document": record.get("source_document", record.get("source_id", "")),
                "evidence_refs": record.get("evidence_refs", record.get("evidence", [])),
                "reviewer": record.get("reviewer", record.get("reviewer_id", "")),
            })
    return rows
