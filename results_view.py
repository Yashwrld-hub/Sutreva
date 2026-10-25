"""Pure helpers for the file-centric audit results presentation.

These helpers deliberately contain no Streamlit dependencies so the shape and
filtering semantics of the batch comparison table can be regression-tested
independently of the browser UI.
"""


def build_file_centric_results(results, schema, row_label="item"):
    """Build one record per result with one column per configured audit field.

    Returns ``(records, statuses)`` where ``statuses`` mirrors the field
    columns and retains the authoritative audit status for filtering/styling.
    """
    field_specs = list((schema or {}).get("fields", []))
    field_labels = [f.get("label") or f.get("field_name") for f in field_specs]
    records = []
    status_records = []

    for result in results:
        row_by_name = {row.get("field_name"): row for row in result.get("rows", [])}
        record = {row_label.capitalize(): result.get("identifier", "")}
        statuses = {}

        for field in field_specs:
            field_name = field.get("field_name")
            label = field.get("label") or field_name
            row = row_by_name.get(field_name)
            if row is None:
                record[label] = "—" if not result.get("error") else "ERROR"
                statuses[label] = "ERROR" if result.get("error") else "MISSING"
                continue
            value = row.get("extracted_value")
            record[label] = "—" if value in (None, "") else str(value)
            statuses[label] = row.get("status", "")

        if result.get("error"):
            record["Overall Status"] = "ERROR"
        elif any(status in ("MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW")
                 for status in statuses.values()):
            record["Overall Status"] = "REVIEW"
        else:
            record["Overall Status"] = "MATCHED"

        record["Review Fields"] = ", ".join(
            label for label, status in statuses.items() if status not in ("MATCHED", "")
        ) or "—"
        records.append(record)
        status_records.append(statuses)

    columns = [row_label.capitalize()] + field_labels + ["Overall Status", "Review Fields"]
    return records, status_records, columns


def filter_file_centric_results(records, status_records, overall_filter="All",
                                selected_field="All fields", status_filter="All"):
    """Return record indices matching the explicit batch filters."""
    visible = []
    for idx, record in enumerate(records):
        if overall_filter != "All" and record.get("Overall Status") != overall_filter:
            continue
        if selected_field != "All fields" and status_filter != "All":
            if status_records[idx].get(selected_field) != status_filter:
                continue
        visible.append(idx)
    return visible
