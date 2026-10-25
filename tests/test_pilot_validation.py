from pilot_validation import benchmark_accuracy, coverage_report


def test_benchmark_accuracy_reports_disagreement_and_missing_rows():
    result = benchmark_accuracy(
        [{"field_name": "pressure", "status": "MATCHED"}, {"field_name": "temp", "status": "MISMATCHED"}, {"field_name": "viscosity", "status": "MATCHED"}],
        [{"field_name": "pressure", "status": "MATCHED"}, {"field_name": "temp", "status": "MATCHED"}, {"field_name": "oil", "status": "MISSING"}],
    )
    assert result["compared"] == 2
    assert result["correct"] == 1
    assert result["accuracy"] == 0.5
    assert result["missing_prediction"] == ["oil"]
    assert result["missing_benchmark"] == ["viscosity"]
    assert result["disagreements"][0]["key"] == "temp"


def test_coverage_report_is_deterministic():
    result = coverage_report([{"evidence": {"page": 1}}, {"evidence": None}, {}])
    assert result == {"total": 3, "with_evidence": 1, "without_evidence": 2, "coverage_rate": 1 / 3}
