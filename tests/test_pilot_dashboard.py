from pilot_dashboard import build_pilot_dashboard


def test_dashboard_aggregates_accuracy_by_equipment_and_time():
    result = build_pilot_dashboard(
        benchmark_records=[
            {"equipment_type": "Pump", "value_accuracy": 1.0, "status_accuracy": 0.5},
            {"equipment_type": "Pump", "value_accuracy": 0.5, "status_accuracy": 1.0},
            {"equipment_type": "Compressor", "value_accuracy": 0.8, "status_accuracy": 0.9},
        ],
        cycle_records=[{"manual_minutes": 100, "assisted_minutes": 60}, {"manual_minutes": 50, "assisted_minutes": 40}],
        review_records=[{"disposition": "accepted"}, {"disposition": "needs_review"}],
    )
    assert result["benchmark_cases"] == 3
    assert result["by_equipment"]["Pump"]["value_accuracy"] == 0.75
    assert result["manual_minutes"] == 150
    assert result["assisted_minutes"] == 100
    assert result["minutes_saved"] == 50
    assert result["time_reduction_rate"] == 50 / 150
    assert result["review_dispositions"] == {"ACCEPTED": 1, "NEEDS_REVIEW": 1}


def test_dashboard_empty_input_is_safe():
    result = build_pilot_dashboard()
    assert result["benchmark_cases"] == 0
    assert result["overall_value_accuracy"] == 0.0
    assert result["time_reduction_rate"] == 0.0
    assert result["by_equipment"] == {}
