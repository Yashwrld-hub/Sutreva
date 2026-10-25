from pilot_report import build_pilot_report, report_json_bytes, report_summary_csv_bytes


def test_report_contains_provenance_and_no_approval():
    report = build_pilot_report(
        [{"equipment_type": "Pump", "value_accuracy": 1.0, "status_accuracy": 0.5}],
        [{"manual_minutes": 100, "assisted_minutes": 40}],
        [{"disposition": "REVIEW_REQUIRED"}],
        data_classification="SYNTHETIC_DEVELOPMENT_DATA",
    )
    assert report["report_metadata"]["engineering_approval"] is False
    assert report["report_metadata"]["data_classification"] == "SYNTHETIC_DEVELOPMENT_DATA"
    assert report["metrics"]["minutes_saved"] == 60


def test_report_exports_are_nonempty_and_machine_readable():
    report = build_pilot_report()
    assert b"report_metadata" in report_json_bytes(report)
    csv_bytes = report_summary_csv_bytes(report)
    assert csv_bytes.startswith(b"metric,value")
    assert b"time_reduction_rate" in csv_bytes


def test_report_traceability_summary_and_index():
    report = build_pilot_report(
        [{"case_id": "P-01", "source_document": "pump.pdf", "evidence_refs": ["p1"]}],
        review_records=[{"case_id": "P-01", "reviewer": "R-01"}],
        data_classification="SYNTHETIC_DEVELOPMENT_DATA",
    )
    trace = report["traceability"]
    assert trace["source_coverage_rate"] == 1.0
    assert trace["evidence_coverage_rate"] == 1.0
    assert trace["review_records_with_reviewer"] == 1
    assert len(report["traceability_index"]) == 2
    assert report["traceability_index"][0]["source_document"] == "pump.pdf"
