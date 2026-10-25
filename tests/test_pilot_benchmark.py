from pilot_benchmark import compare_reference_set, summarize_review_dispositions


def test_reference_comparison_reports_accuracy_and_gaps():
    result = compare_reference_set(
        [{"field_name": "pressure", "value": 10, "status": "MATCHED"}, {"field_name": "temp", "value": 90, "status": "MISMATCHED"}],
        [{"field_name": "pressure", "value": 10, "status": "MATCHED"}, {"field_name": "temp", "value": 95, "status": "MATCHED"}, {"field_name": "oil", "value": "ISO 68", "status": "MATCHED"}],
    )
    assert result["comparable_fields"] == 2
    assert result["exact_value_matches"] == 1
    assert result["missing_prediction"] == ["oil"]
    assert result["prediction_only"] == []
    assert result["value_accuracy"] == 0.5


def test_review_dispositions_are_counted():
    result = summarize_review_dispositions([
        {"disposition": "accepted"}, {"disposition": "needs_review"}, {"disposition": "accepted"}
    ])
    assert result == {"total_reviewed": 3, "dispositions": {"ACCEPTED": 2, "NEEDS_REVIEW": 1}}
