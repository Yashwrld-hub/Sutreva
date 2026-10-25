"""Streamlit results rendering for Sutreva audit runs.

This module owns presentation-only result rendering. Audit extraction,
comparison, evidence and engineering intelligence remain in their existing
modules; this keeps the main application routing file focused on workflow.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import bulk_overview
from engineering_intelligence import analyze_engineering_rows
from exports import (
    build_technical_query_rows,
    suggested_filename,
    to_csv_bytes_bulk,
    to_excel_bytes_bulk,
    to_pdf_bytes_bulk,
    to_tq_csv_bytes,
    to_tq_excel_bytes,
)
from pattern_intelligence import build_historical_pattern_matches, history_summary
from results_view import build_file_centric_results, filter_file_centric_results


STATUS_STYLE = {
    "MATCHED": "font-weight:700;",
    "MISSING": "font-weight:700;",
    "MISMATCHED": "font-weight:700;",
    "OUT OF RANGE": "font-weight:700;",
}


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_engineering_report(rows, schema, ai_assessments):
    """Cache deterministic engineering intelligence across Streamlit reruns."""
    return analyze_engineering_rows(rows, schema, ai_assessments=ai_assessments)


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_historical_matches(current_exceptions, review_items):
    """Cache advisory historical-pattern matching across normal reruns."""
    return build_historical_pattern_matches(current_exceptions, review_items)


@st.cache_data(show_spinner=False, max_entries=24)
def _cached_excel_export(results, template_name, id_label):
    """Cache an export artifact so reruns do not regenerate the workbook."""
    return to_excel_bytes_bulk(results, template_name, id_label)


@st.cache_data(show_spinner=False, max_entries=24)
def _cached_pdf_export(results, template_name, id_label):
    """Cache an export artifact so reruns do not regenerate the PDF."""
    return to_pdf_bytes_bulk(results, template_name, id_label)


@st.cache_data(show_spinner=False, max_entries=24)
def _cached_csv_export(results, template_name, id_label):
    """Cache an export artifact so reruns do not regenerate the CSV."""
    return to_csv_bytes_bulk(results, template_name, id_label)


def _status_label(overview_row):
    if overview_row.get("error"):
        return "ERROR"
    return "OK" if overview_row["all_matched"] else "REVIEW"


def _status_color(value):
    if value == "ERROR":
        return "font-weight:700;background-color:rgba(177,62,74,.10);"
    return "font-weight:700;"


def _prepare_result_context(results, schema, row_label):
    overview = bulk_overview(results)
    n_ok = sum(o["all_matched"] for o in overview)
    n_error = sum(bool(o.get("error")) for o in overview)
    attention = sum(
        o.get(key, 0) for o in overview for key in ("missing", "mismatched", "out_of_range")
    )

    engineering_reports = []
    if schema is not None:
        for result in results:
            if result.get("error"):
                continue
            intelligence = result.get("intelligence") or {}
            engineering_reports.append(
                (
                    result["identifier"],
                    _cached_engineering_report(
                        result.get("rows", []),
                        schema,
                        intelligence.get("field_assessments") or [],
                    ),
                )
            )

    detail_rows = []
    evidence_items = []
    needs_review = 0
    for result in results:
        if result.get("error"):
            continue
        for row in result.get("rows", []):
            if row.get("status") == "NEEDS_REVIEW":
                needs_review += 1
            evidence = row.get("evidence") or {}
            detail_rows.append(
                {
                    row_label.capitalize(): result["identifier"],
                    "Field": row["field"],
                    "Extracted Value": "—" if row["extracted_value"] in (None, "") else str(row["extracted_value"]),
                    "Status": row["status"],
                    "Evidence": f"Page {evidence.get('page')}" if evidence.get("page") else "—",
                }
            )
            if evidence:
                evidence_items.append((result["identifier"], row, evidence))

    return {
        "overview": overview,
        "n_ok": n_ok,
        "n_error": n_error,
        "attention": attention,
        "engineering_reports": engineering_reports,
        "detail_rows": detail_rows,
        "evidence_items": evidence_items,
        "needs_review": needs_review,
    }


def _render_performance_summary(results):
    timings = []
    for result in results:
        performance = result.get("performance") or {}
        total_s = performance.get("total_s")
        if total_s is not None:
            timings.append(float(total_s))
    if not timings:
        return

    avg_s = sum(timings) / len(timings)
    st.caption(
        f"Processing telemetry · {len(timings)} files · "
        f"average {avg_s:.1f}s/file · min {min(timings):.1f}s · "
        f"max {max(timings):.1f}s"
    )

def _render_outcome_summary(context, row_label, show_errors):
    overview = context["overview"]
    n_ok = context["n_ok"]
    n_error = context["n_error"]
    attention = context["attention"]
    needs_review = context["needs_review"]

    st.divider()
    st.subheader("Audit outcome")
    if n_error:
        err_msgs = "; ".join(
            f"{o['identifier']}: {o.get('error')}" for o in overview if o.get("error")
        )
        st.markdown(
            f'<div class="oa-outcome bad"><div class="oa-outcome-title">Processing needs attention</div>'
            f'<div class="oa-outcome-copy">One or more files could not be completed ({err_msgs}). Resolve the processing issue before relying on the report.</div></div>',
            unsafe_allow_html=True,
        )
    elif attention or needs_review:
        st.markdown(
            f'<div class="oa-outcome warn"><div class="oa-outcome-title">Review focus</div>'
            f'<div class="oa-outcome-copy">{attention + needs_review} field(s) need engineering attention. Open the source evidence before recording a disposition.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="oa-outcome good"><div class="oa-outcome-title">Ready to record</div>'
            '<div class="oa-outcome-copy">All checked fields satisfied the configured rules. Keep the source evidence with the audit record.</div></div>',
            unsafe_allow_html=True,
        )

    cols = st.columns(4 if (show_errors and n_error) else 3)
    cols[0].metric(f"{row_label.capitalize()}s processed", len(overview))
    cols[1].metric("Fully matched", n_ok)
    cols[2].metric("Flagged for review", len(overview) - n_ok - n_error)
    if show_errors and n_error:
        cols[3].metric("Failed to process", n_error, delta_color="inverse")

    overview_df = pd.DataFrame(
        [
            {
                row_label.capitalize(): o["identifier"],
                "Matched": o["matched"],
                "Missing": o["missing"],
                "Mismatched": o["mismatched"],
                "Out of Range": o["out_of_range"],
                "Total": o["total"],
                "Status": _status_label(o),
                **({"Error": o.get("error") or ""} if show_errors else {}),
            }
            for o in overview
        ]
    )
    overview_styler = overview_df.style
    overview_styler = (
        overview_styler.map if hasattr(overview_styler, "map") else overview_styler.applymap
    )(_status_color, subset=["Status"])

    with st.expander("Run-level status counts", expanded=False):
        st.dataframe(overview_styler, use_container_width=True, hide_index=True)


def _render_file_centric_table(results, schema, key_prefix, row_label):
    # Primary comparison view: one row per file, one column per audited field.
    master_records, master_statuses, master_columns = build_file_centric_results(
        results, schema, row_label=row_label
    )
    master_df = (
        pd.DataFrame(master_records).reindex(columns=master_columns)
        if master_records
        else pd.DataFrame(columns=master_columns)
    )

    if master_df.empty:
        st.caption("No audit records are available for the comparison table.")
        return

    fcols = st.columns([1.1, 1.8, 1.1])
    with fcols[0]:
        overall_filter = st.selectbox(
            "Overall status",
            ["All", "MATCHED", "REVIEW", "ERROR"],
            key=f"{key_prefix}_overall_filter",
        )
    with fcols[1]:
        field_filter_options = ["All fields"] + [
            f.get("label") or f.get("field_name") for f in (schema or {}).get("fields", [])
        ]
        selected_field = st.selectbox(
            "Filter by field status",
            field_filter_options,
            key=f"{key_prefix}_field_filter",
        )
    with fcols[2]:
        status_filter = st.selectbox(
            "Field status",
            ["All", "MATCHED", "MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW"],
            key=f"{key_prefix}_status_filter",
        )

    visible = filter_file_centric_results(
        master_records, master_statuses, overall_filter, selected_field, status_filter
    )
    filtered_df = master_df.iloc[visible].reset_index(drop=True)
    st.caption(
        f"Showing {len(filtered_df)} of {len(master_df)} {row_label}s · one row per file, one column per audited field. "
        "Use the table's column filters for value-level sorting/filtering; use the controls above for audit status."
    )

    def _master_cell_style(value):
        return "font-weight:700;" if value in ("—", "ERROR") else ""

    master_styler = filtered_df.style
    value_columns = [c for c in master_columns if c != row_label.capitalize()]
    master_styler = (
        master_styler.map if hasattr(master_styler, "map") else master_styler.applymap
    )(_master_cell_style, subset=value_columns)
    master_styler = (
        master_styler.map if hasattr(master_styler, "map") else master_styler.applymap
    )(_status_color, subset=["Overall Status"])
    st.dataframe(
        master_styler,
        use_container_width=True,
        hide_index=True,
        height=min(620, max(180, 58 + len(filtered_df) * 38)),
    )


def _render_engineering_intelligence(engineering_reports):
    if not engineering_reports:
        return

    total_exceptions = sum(report.exception_count for _, report in engineering_reports)
    total_blocking = sum(1 for _, report in engineering_reports if report.blocking)
    st.markdown("##### Engineering exception intelligence")
    icols = st.columns(4)
    icols[0].metric("Exceptions", total_exceptions)
    icols[1].metric("Critical", sum(r.critical_count for _, r in engineering_reports))
    icols[2].metric("High", sum(r.high_count for _, r in engineering_reports))
    icols[3].metric("Blocking files", total_blocking)

    exception_rows = []
    for identifier, report in engineering_reports:
        for exc in report.exceptions:
            exception_rows.append(
                {
                    "File": identifier,
                    "Field": exc["field"],
                    "Category": exc["category"],
                    "Severity": exc["severity"],
                    "Status": exc["status"],
                    "Domain role": exc.get("domain_role") or "General",
                    "Domain priority": exc.get("domain_priority") or "—",
                    "Engineering impact": exc["impact"],
                    "Recommended action": exc["recommended_action"],
                }
            )

    profile_labels = sorted(
        {r.domain_profile_label for _, r in engineering_reports if r.domain_profile_label}
    )
    if profile_labels:
        st.caption(
            "Equipment context: "
            + ", ".join(profile_labels)
            + ". Domain context guides review priority; configured audit rules remain authoritative."
        )
    if exception_rows:
        st.dataframe(pd.DataFrame(exception_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No engineering exceptions were identified from the authoritative audit statuses.")

    coupled_rows = []
    for identifier, report in engineering_reports:
        for chk in getattr(report, "coupled_checks", None) or []:
            coupled_rows.append({
                "File": identifier,
                "Check": chk["title"],
                "Rule": chk["formula"],
                "Measured": chk["measured_summary"],
                "Status": chk["status"],
                "Engineering Note": chk["engineering_note"],
            })
    if coupled_rows:
        st.markdown("##### Coupled cross-parameter physics & envelope checks")
        st.dataframe(pd.DataFrame(coupled_rows), use_container_width=True, hide_index=True)

    historical_matches = []
    for _, report in engineering_reports:
        historical_matches.extend(
            _cached_historical_matches(report.exceptions, st.session_state.review_items)
        )
    if not historical_matches:
        return

    summary = history_summary(historical_matches)
    st.markdown("##### Historical pattern intelligence")
    hcols = st.columns(3)
    hcols[0].metric("Fields with prior cases", summary["fields_with_history"])
    hcols[1].metric("Similar reviewed cases", summary["similar_cases"])
    hcols[2].metric("Strong patterns", summary["high_strength"])
    history_rows = [
        {
            "Field": match.field,
            "Status": match.status,
            "Prior cases": match.similar_case_count,
            "Common disposition": match.common_disposition or "—",
            "Pattern strength": match.pattern_strength,
            "Prior projects": match.prior_projects,
            "Prior runs": match.prior_runs,
        }
        for match in historical_matches
    ]
    st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
    st.caption(
        "Historical patterns are advisory context only. They never change the current audit status, severity, blocking state, or configured engineering rule."
    )


def _render_field_review(detail_rows, evidence_items, row_label):
    with st.expander(f"Field-by-field review for every {row_label}"):
        if not detail_rows:
            st.caption("No successfully-processed rows to show.")
            return

        detail_df = pd.DataFrame(detail_rows)
        detail_styler = detail_df.style
        detail_styler = (
            detail_styler.map if hasattr(detail_styler, "map") else detail_styler.applymap
        )(lambda value: STATUS_STYLE.get(value, ""), subset=["Status"])
        st.dataframe(detail_styler, use_container_width=True, hide_index=True)

        st.markdown("##### Source evidence")
        if not evidence_items:
            st.caption("No deterministic source evidence was attached to these results.")
            return

        for identifier, row, evidence in evidence_items:
            title = f"{row['field']} · {row['status']}"
            with st.expander(title):
                st.markdown(f"**File:** {identifier}")
                st.markdown(
                    f"**Extracted:** {row['extracted_value'] if row['extracted_value'] not in (None, '') else '—'}"
                )
                st.markdown(f"**Rule:** {row['rule']}")
                st.markdown(
                    f"""<div class="oa-evidence"><div class="oa-evidence-meta">Page {evidence.get('page', '—')} · {evidence.get('type', 'source evidence')}</div><div class="oa-evidence-text">{str(evidence.get('text') or evidence.get('quote') or 'No source quote available.')}</div></div>""",
                    unsafe_allow_html=True,
                )


def _render_exports(results, template_name, key_prefix, row_label):
    st.markdown("##### Export this report")
    id_label = row_label.capitalize()
    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button(
            "⬇️ Excel (.xlsx)",
            data=_cached_excel_export(results, template_name, id_label),
            file_name=suggested_filename(template_name, "xlsx", key_prefix),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"{key_prefix}_dl_xlsx",
            on_click="ignore",
        )
    with e2:
        st.download_button(
            "⬇️ PDF (.pdf)",
            data=_cached_pdf_export(results, template_name, id_label),
            file_name=suggested_filename(template_name, "pdf", key_prefix),
            mime="application/pdf",
            use_container_width=True,
            key=f"{key_prefix}_dl_pdf",
            on_click="ignore",
        )
    with e3:
        st.download_button(
            "⬇️ CSV (.csv)",
            data=_cached_csv_export(results, template_name, id_label),
            file_name=suggested_filename(template_name, "csv", key_prefix),
            mime="text/csv",
            use_container_width=True,
            key=f"{key_prefix}_dl_csv",
            on_click="ignore",
        )

    tq_rows = build_technical_query_rows(results)
    if tq_rows:
        st.markdown("##### 📋 Vendor Technical Queries (TQ / Comments Resolution Sheet)")
        st.caption(
            f"{len(tq_rows)} open technical clarification(s) auto-generated with page/line citations for vendor issue."
        )
        tq1, tq2 = st.columns(2)
        with tq1:
            st.download_button(
                "📋 Download CRS / TQ Sheet (.xlsx)",
                data=to_tq_excel_bytes(results, template_name),
                file_name=suggested_filename(f"{template_name}_CRS_TQ", "xlsx", key_prefix),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"{key_prefix}_dl_tq_xlsx",
                on_click="ignore",
            )
        with tq2:
            st.download_button(
                "📋 Download CRS / TQ Sheet (.csv)",
                data=to_tq_csv_bytes(results, template_name),
                file_name=suggested_filename(f"{template_name}_CRS_TQ", "csv", key_prefix),
                mime="text/csv",
                use_container_width=True,
                key=f"{key_prefix}_dl_tq_csv",
                on_click="ignore",
            )


def _render_ai_reasoning(results):
    intelligible = [result for result in results if result.get("intelligence")]
    if not intelligible:
        return

    with st.expander("🧠 Nemotron engineering reasoning", expanded=False):
        st.caption(
            "Advisory second-pass reasoning grounded only in extracted values, configured rules, and source evidence. It never changes the deterministic audit status."
        )
        for item in intelligible:
            intelligence = item["intelligence"] or {}
            st.markdown(
                f"**{item['identifier']}** · {intelligence.get('status', 'UNKNOWN')} · {intelligence.get('overall_flag', 'NONE')}"
            )
            if intelligence.get("document_flags"):
                st.write("Document flags:", "; ".join(intelligence["document_flags"]))
            assessments = intelligence.get("field_assessments") or []
            if assessments:
                display_assessments = []
                for assessment in assessments:
                    row = dict(assessment)
                    refs = row.pop("evidence_refs", []) or []
                    row["Evidence"] = " | ".join(
                        f"p{ref.get('page')} l{ref.get('line')}: {ref.get('quote')}"
                        for ref in refs
                        if isinstance(ref, dict) and ref.get("quote")
                    ) or "No deterministic evidence reference"
                    display_assessments.append(row)
                st.dataframe(
                    pd.DataFrame(display_assessments),
                    use_container_width=True,
                    hide_index=True,
                )
            if intelligence.get("error"):
                st.warning(f"Reasoning pass did not complete: {intelligence['error']}")


def _render_raw_model_output(results, key_prefix):
    debuggable = [result for result in results if result.get("raw_output")]
    if not debuggable:
        return

    with st.expander("🔍 Raw model output (debug)"):
        st.caption(
            "Exactly what the model returned for a given file, before any comparison logic ran — useful for spotting extraction errors."
        )
        pick = st.selectbox(
            "File",
            [result["identifier"] for result in debuggable],
            key=f"{key_prefix}_debug_pick",
        )
        chosen = next(result for result in debuggable if result["identifier"] == pick)
        st.code(chosen["raw_output"], language="json")


def render_group_results(
    results,
    template_name,
    key_prefix,
    row_label="item",
    show_errors=True,
    schema=None,
):
    """Render the shared file-centric results and detailed review workspace."""
    context = _prepare_result_context(results, schema, row_label)
    _render_outcome_summary(context, row_label, show_errors)
    _render_performance_summary(results)
    _render_file_centric_table(results, schema, key_prefix, row_label)
    _render_engineering_intelligence(context["engineering_reports"])
    _render_field_review(context["detail_rows"], context["evidence_items"], row_label)
    _render_exports(results, template_name, key_prefix, row_label)
    _render_ai_reasoning(results)
    _render_raw_model_output(results, key_prefix)
