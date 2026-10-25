from results_view import build_file_centric_results, filter_file_centric_results


def _schema():
    return {
        "fields": [
            {"field_name": "power", "label": "Rated Power", "unit": "kW"},
            {"field_name": "casing", "label": "Casing / Barrel Material", "unit": ""},
        ]
    }


def test_build_file_centric_results_places_fields_in_columns():
    records, statuses, columns = build_file_centric_results(
        [
            {
                "identifier": "pump-a.pdf",
                "rows": [
                    {"field_name": "power", "extracted_value": 7.5, "status": "MATCHED"},
                    {"field_name": "casing", "extracted_value": "Cast Iron", "status": "MISMATCHED"},
                ],
                "error": None,
            },
            {
                "identifier": "pump-b.pdf",
                "rows": [
                    {"field_name": "power", "extracted_value": None, "status": "MISSING"},
                    {"field_name": "casing", "extracted_value": "Cast Iron", "status": "MATCHED"},
                ],
                "error": None,
            },
        ],
        _schema(),
        row_label="file",
    )

    assert columns == ["File", "Rated Power", "Casing / Barrel Material", "Overall Status", "Review Fields"]
    assert records[0]["File"] == "pump-a.pdf"
    assert records[0]["Rated Power"] == "7.5"
    assert records[0]["Casing / Barrel Material"] == "Cast Iron"
    assert records[0]["Overall Status"] == "REVIEW"
    assert "Casing / Barrel Material" in records[0]["Review Fields"]
    assert statuses[1]["Rated Power"] == "MISSING"


def test_file_centric_filters_can_target_overall_and_field_status():
    records, statuses, _ = build_file_centric_results(
        [
            {"identifier": "a.pdf", "rows": [{"field_name": "power", "extracted_value": 7, "status": "MATCHED"}], "error": None},
            {"identifier": "b.pdf", "rows": [{"field_name": "power", "extracted_value": None, "status": "MISSING"}], "error": None},
            {"identifier": "c.pdf", "rows": [{"field_name": "power", "extracted_value": 9, "status": "MISMATCHED"}], "error": None},
        ],
        {"fields": [{"field_name": "power", "label": "Rated Power"}]},
        row_label="file",
    )

    assert filter_file_centric_results(records, statuses, overall_filter="REVIEW") == [1, 2]
    assert filter_file_centric_results(records, statuses, selected_field="Rated Power", status_filter="MISSING") == [1]
