from pilot_metrics import compare_cycle_times, summarize_results


def test_summarize_results_counts_statuses_and_failures():
    result = summarize_results([
        {"rows": [{"status": "MATCHED"}, {"status": "MISMATCHED"}]},
        {"rows": [{"status": "NEEDS_REVIEW"}], "error": None},
        {"rows": [], "error": "failed"},
    ])
    assert result["files_processed"] == 3
    assert result["files_failed"] == 1
    assert result["rows_evaluated"] == 3
    assert result["matched_rows"] == 1
    assert result["flagged_rows"] == 2


def test_compare_cycle_times():
    metrics = compare_cycle_times(120, 45)
    assert metrics["minutes_saved"] == 75
    assert metrics["reduction_rate"] == 0.625


def test_compare_cycle_times_rejects_negative_values():
    try:
        compare_cycle_times(-1, 10)
    except ValueError:
        pass
    else:
        raise AssertionError("negative cycle time should be rejected")
