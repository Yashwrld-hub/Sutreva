"""
app.py — the web UI, built with Streamlit.

Run with:
    streamlit run app.py

This file handles DISPLAY only. Extraction/comparison lives in core.py,
and file generation lives in exports.py.
"""

import copy
import time

import pandas as pd
import streamlit as st

from core import (
    audit_summary,
    guess_column_mapping,
    guess_identifier_column,
    list_templates,
    load_schema,
    run_audit,
    run_batch_audit,
    run_batch_pdf_audit,
    run_bulk_audit,
    run_pdf_audit_with_evidence,
    save_template,
    slugify,
)
from evaluation_flywheel import (
    EVAL_SCHEMA,
    curate_feedback_record,
    evaluate_snapshot,
    export_cases_jsonl,
    load_curated_cases,
    predictions_from_cases,
    record_curated_case,
)
from feedback_loop import (
    build_feedback_record,
    export_feedback_jsonl,
    feedback_summary,
    load_feedback,
    record_feedback,
)
from governance import ApprovalEvent, UserIdentity
from lifecycle import create_audit_run
from pilot_dashboard import build_pilot_dashboard
from pilot_metrics import compare_cycle_times, summarize_results
from pilot_report import build_pilot_report, report_json_bytes, report_summary_csv_bytes
from product_brand import (
    PRODUCT_DESCRIPTION,
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
    PRODUCT_VERSION,
    page_title,
)
from results_ui import render_group_results
from review_queue import build_review_queue, update_review_item
from review_store import load_items, record_approval_event, upsert_items
from field_ontology import enrich_field_with_nemotron, match_ontology_entry
from runtime_config import get_runtime_config

st.set_page_config(
    page_title=page_title(),
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = r"""<style>
.block-container {max-width:1380px; padding-top:1.4rem; padding-bottom:4rem;}
section[data-testid="stSidebar"] {border-right:1px solid color-mix(in srgb, currentColor 20%, transparent);}
section[data-testid="stSidebar"] > div {padding-top:1.1rem;}
.stRadio {margin-bottom:.15rem;}
[data-testid="stRadio"] div[role="radiogroup"] {display:flex; gap:.1rem; border-bottom:1px solid color-mix(in srgb, currentColor 20%, transparent); padding-bottom:0;}
[data-testid="stRadio"] div[role="radiogroup"] > label {padding:.62rem .95rem .58rem; border-radius:0; color:inherit; opacity:.72; font-weight:650; border-bottom:3px solid transparent;}
[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {color:inherit; opacity:1; border-bottom-color:#4F46E5; background:color-mix(in srgb, currentColor 8%, transparent);}
[data-testid="stRadio"] div[role="radiogroup"] > label:hover {background:color-mix(in srgb, currentColor 6%, transparent); opacity:.9;}
.stButton > button {border-radius:9px; min-height:2.6rem; font-weight:650;}
button[kind="primary"] {box-shadow:0 6px 16px rgba(79,70,229,.18);}
[data-testid="stFileUploader"] {border:1px dashed color-mix(in srgb, currentColor 28%, transparent); border-radius:14px; padding:.35rem;}
[data-testid="stMetric"] {border:1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius:12px; padding:.85rem .95rem;}
[data-testid="stDataFrame"] {border:1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius:10px; overflow:hidden;}
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] strong {color:inherit;}
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] {color:inherit;}
[data-baseweb="popover"] [role="option"], [data-baseweb="menu"] [role="option"] {color:inherit;}
.oa-brand {display:flex; align-items:center; gap:.75rem; margin-bottom:.6rem;}
.oa-mark {width:34px; height:34px; border:2px solid currentColor; border-radius:10px; position:relative; box-sizing:border-box; background:color-mix(in srgb, currentColor 7%, transparent);}
.oa-mark:before {content:""; position:absolute; inset:7px; border:2px solid #6D5BD0; border-radius:50%;}
.oa-mark:after {content:""; position:absolute; width:8px; height:2px; background:#6D5BD0; right:-4px; top:15px; transform:rotate(45deg); border-radius:2px;}
.oa-brand-name {font-size:1rem; font-weight:780; color:inherit; line-height:1.05;}
.oa-brand-sub {font-size:.72rem; color:inherit; opacity:.68; margin-top:.12rem;}
.oa-hero {border:1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius:18px; padding:1.5rem 1.55rem; background:color-mix(in srgb, currentColor 4%, transparent); margin-bottom:1rem; box-shadow:0 8px 28px rgba(0,0,0,.06);}
.oa-kicker {color:inherit; opacity:.68;font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.45rem;}
.oa-hero h1 {color:inherit; margin:0; font-size:2.15rem; line-height:1.15; letter-spacing:-.025em;}
.oa-hero p {color:inherit; opacity:.74; margin:.48rem 0 0; max-width:66rem; font-size:1rem;}
.oa-flow {display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin:.9rem 0 1.1rem;}
.oa-flow-card {border:1px solid color-mix(in srgb, currentColor 18%, transparent);background:color-mix(in srgb, currentColor 3%, transparent);border-radius:12px;padding:.8rem .9rem;position:relative;overflow:hidden;}
.oa-flow-card:before {content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#4F46E5;}
.oa-flow-card:nth-child(2):before {background:#6D5BD0;}
.oa-flow-card:nth-child(3):before {background:#A86F16;}
.oa-flow-card:nth-child(4):before {background:#6D5BD0;}
.oa-flow-step {font-size:.7rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:inherit;opacity:.68;}
.oa-flow-title {font-size:.95rem;font-weight:720;color:inherit;margin-top:.2rem;}
.oa-flow-copy {font-size:.78rem;color:inherit;opacity:.72;margin-top:.15rem;line-height:1.35;}
.oa-session {border:1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius:12px; padding:.8rem .95rem; background:color-mix(in srgb, currentColor 4%, transparent); margin:.4rem 0 .95rem; box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.oa-session-label {color:inherit; opacity:.68; font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase;}
.oa-session-value {color:inherit !important; font-weight:700;}
.oa-home-card {border:1px solid color-mix(in srgb, currentColor 18%, transparent);border-radius:14px;background:color-mix(in srgb, currentColor 3%, transparent);padding:1rem 1.05rem;height:100%;box-shadow:0 5px 18px rgba(0,0,0,.05);}
.oa-home-title {font-weight:760;color:inherit;font-size:1rem;}
.oa-home-copy {color:inherit;opacity:.74;font-size:.84rem;line-height:1.42;margin-top:.2rem;}
.oa-outcome {border:1px solid color-mix(in srgb, currentColor 18%, transparent);border-radius:13px;background:color-mix(in srgb, currentColor 3%, transparent);padding:1rem 1.05rem;margin:.7rem 0 1rem;}
.oa-outcome.good {border-color:color-mix(in srgb, #28724F 55%, currentColor 22%);background:color-mix(in srgb, #28724F 8%, transparent);}
.oa-outcome.warn {border-color:color-mix(in srgb, #A86F16 55%, currentColor 22%);background:color-mix(in srgb, #A86F16 8%, transparent);}
.oa-outcome.bad {border-color:color-mix(in srgb, #B13E4A 55%, currentColor 22%);background:color-mix(in srgb, #B13E4A 9%, transparent);}
.oa-outcome-title {font-weight:800;color:inherit;font-size:1rem;}
.oa-outcome-copy {color:inherit;opacity:.74;font-size:.82rem;margin-top:.18rem;}
.oa-evidence {border-left:4px solid #4F46E5;padding:.65rem .85rem;background:color-mix(in srgb, currentColor 4%, transparent);border-radius:0 9px 9px 0;}
.oa-evidence-meta {font-size:.72rem;font-weight:750;color:inherit;opacity:.68;text-transform:uppercase;letter-spacing:.05em;}
.oa-evidence-text {font-size:.84rem;color:inherit;line-height:1.45;margin-top:.25rem;}
.oa-rule-summary {color:inherit;opacity:.68;font-size:.85em;}
.oa-footer {margin-top:2rem;padding-top:.9rem;border-top:1px solid color-mix(in srgb, currentColor 20%, transparent);color:inherit;opacity:.68;font-size:.72rem;text-align:center;}
@media (max-width:900px) {.oa-flow {grid-template-columns:repeat(2,1fr);} .oa-hero h1{font-size:1.75rem;}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

CHECK_TYPES = [
    "Must be one of a list of values",
    "Must exactly match a value",
    "Must not exceed a maximum",
    "Must be at least a minimum",
    "No check (just record it)",
]


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

def _init_state():
    defaults = {
        "editor_fields": [],
        "editor_name": "",
        "audit_results": None,
        "audit_results_template": None,
        "review_items": [],
        "feedback_records": [],
        "lifecycle_context": None,
        "ai_reasoning_enabled": True,
        "audit_history": [],
        "active_view": "Overview",
        "workspace_nav": "Overview",
        "template_selector": "Centrifugal Pump Audit",
        "demo_mode": False,
        "demo_pdf_loaded": False,
        "audit_processing": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.get("review_store_loaded"):
        st.session_state.review_items = load_items()
        st.session_state.review_store_loaded = True
    if not st.session_state.get("feedback_store_loaded"):
        st.session_state.feedback_records = load_feedback()
        st.session_state.evaluation_cases = load_curated_cases()
        st.session_state.feedback_store_loaded = True


_init_state()


def _navigate_to(view: str):
    st.session_state.active_view = view
    st.session_state.workspace_nav = view


def _sync_workspace_navigation():
    st.session_state.active_view = st.session_state.workspace_nav


def _field_from_inputs(label, unit, check_type, rule_value, required, enrich_with_ai=False):
    field = {
        "field_name": slugify(label),
        "label": label.strip(),
        "unit": unit.strip() or None,
        "required": required,
    }
    if check_type == CHECK_TYPES[0]:
        values = [v.strip() for v in (rule_value or "").split(",") if v.strip()]
        if values:
            field["acceptable_values"] = values
    elif check_type == CHECK_TYPES[1] and rule_value:
        field["expected_value"] = str(rule_value).strip()
    elif check_type == CHECK_TYPES[2]:
        field["max_value"] = rule_value
    elif check_type == CHECK_TYPES[3]:
        field["min_value"] = rule_value

    profile = (
        enrich_field_with_nemotron(label.strip(), unit.strip() or None)
        if enrich_with_ai
        else match_ontology_entry(field)
    )
    if profile.get("aliases"):
        field["extraction_aliases"] = profile["aliases"][:12]
        if field["unit"]:
            field["deterministic_source_aliases"] = profile["aliases"][:12]
    if profile.get("negative_cues"):
        field["negative_cues"] = profile["negative_cues"][:8]
    return field


def _rule_summary(f):
    if "acceptable_values" in f:
        return "one of: " + ", ".join(str(v) for v in f["acceptable_values"])
    if "expected_value" in f:
        return f"must equal {f['expected_value']}"
    if "max_value" in f:
        return f"max {f['max_value']}"
    if "min_value" in f:
        return f"min {f['min_value']}"
    return "recorded only"


_EMPTY_SUMMARY = dict.fromkeys(("MATCHED", "MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW", "TOTAL"), 0)


def _error_result(identifier, error):
    return {"identifier": identifier, "rows": [], "raw_output": None,
            "summary": dict(_EMPTY_SUMMARY), "error": str(error)}


def _inject_ai_context(results):
    enriched = []
    for result in results:
        copied = dict(result)
        intelligence = result.get("intelligence") or {}
        assessments = {
            str(item.get("field_name")): item
            for item in intelligence.get("field_assessments") or []
            if isinstance(item, dict) and item.get("field_name")
        }
        rows = []
        for row in result.get("rows", []):
            row_copy = dict(row)
            field_name = str(row_copy.get("field_name") or "")
            ai = assessments.get(field_name)
            if ai:
                row_copy["ai_context"] = {
                    "provider": intelligence.get("provider"),
                    "model": intelligence.get("model"),
                    "prompt_version": intelligence.get("prompt_version"),
                    "assessment": ai.get("assessment"),
                    "risk": ai.get("risk"),
                    "reason": ai.get("reason"),
                    "evidence_refs": ai.get("evidence_refs") or [],
                }
            rows.append(row_copy)
        copied["rows"] = rows
        enriched.append(copied)
    return enriched


def _sync_review_items_from_results(source_results, lifecycle_context):
    if not source_results:
        return
    generated = build_review_queue(_inject_ai_context(source_results), lifecycle_context=lifecycle_context)
    existing = {item.item_id: item for item in st.session_state.review_items}
    changed = False
    for item in generated:
        if item.item_id not in existing:
            existing[item.item_id] = item
            changed = True
        else:
            cur = existing[item.item_id]
            if (not cur.project_id and item.project_id) or (not cur.ai_context and item.ai_context):
                cur.project_id = cur.project_id or item.project_id
                cur.run_id = cur.run_id or item.run_id
                cur.document_revision = cur.document_revision or item.document_revision
                cur.ai_context = cur.ai_context or item.ai_context
                changed = True
    if changed:
        st.session_state.review_items = list(existing.values())
        upsert_items(st.session_state.review_items)


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""<div class="oa-brand"><div class="oa-mark"></div><div><div class="oa-brand-name">{PRODUCT_NAME}</div><div class="oa-brand-sub">{PRODUCT_VERSION} workspace</div></div></div>""",
        unsafe_allow_html=True,
    )
    st.caption(PRODUCT_TAGLINE)
    runtime_cfg = get_runtime_config()
    st.caption(f"Runtime · {runtime_cfg.provider.replace('_', ' ')} · {runtime_cfg.model_name}")
    st.button(
        "Go to audit workspace",
        use_container_width=True,
        on_click=_navigate_to,
        args=("Audit",),
    )

    def _start_new_audit():
        st.session_state.audit_results = None
        st.session_state.audit_results_template = None
        st.session_state.lifecycle_context = None
        st.session_state.demo_mode = False
        st.session_state.demo_pdf_loaded = False
        _navigate_to("Audit")

    def _start_hackathon_demo():
        st.session_state.audit_results = None
        st.session_state.audit_results_template = None
        st.session_state.lifecycle_context = None
        st.session_state.template_selector = "Centrifugal Pump Audit"
        st.session_state.demo_mode = True
        st.session_state.demo_pdf_loaded = False
        _navigate_to("Audit")

    st.button(
        "＋ New audit",
        use_container_width=True,
        type="primary",
        on_click=_start_new_audit,
    )
    st.button(
        "🎬 Start hackathon demo",
        use_container_width=True,
        on_click=_start_hackathon_demo,
        help="Open the prepared synthetic centrifugal-pump demo path for a reproducible rehearsal.",
    )
    st.divider()

    templates = list_templates()
    if not templates:
        st.error("No templates found in `templates/`.")
        st.stop()

    template_name = st.selectbox(
        "Audit type",
        list(templates.keys()),
        key="template_selector",
    )
    st.markdown("#### Audit context")
    project_id = st.text_input("Project ID", value="DEMO-PROJECT", key="project_id")
    document_revision = st.text_input("Document revision", value="REV-0", key="document_revision")
    reviewer_id = st.text_input("Operator ID", value="local-user", key="operator_id")

    try:
        schema = load_schema(templates[template_name])
    except ValueError as e:
        st.error(f"This template can't be loaded: {e}")
        st.stop()

    st.caption(f"{len(schema['fields'])} fields checked")
    with st.expander("Fields in this template"):
        for f in schema["fields"]:
            unit = f" ({f['unit']})" if f.get("unit") else ""
            req = "" if f.get("required", True) else " · optional"
            st.markdown(
                f"**{f['label']}**{unit}{req}  \n"
                f"<span class='oa-rule-summary'>{_rule_summary(f)}</span>",
                unsafe_allow_html=True,
            )

    st.divider()
    if st.button("✏️ Edit this template", use_container_width=True):
        st.session_state.editor_fields = copy.deepcopy(schema["fields"])
        st.session_state.editor_name = schema["template_name"]
        st.rerun()

    if st.button("➕ New blank template", use_container_width=True):
        st.session_state.editor_fields = []
        st.session_state.editor_name = ""
        st.rerun()


# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------

st.markdown(
    f"""
    <div class="oa-hero">
      <div class="oa-kicker">Engineering workspace · {PRODUCT_VERSION}</div>
      <h1>{PRODUCT_NAME}</h1>
      <p>{PRODUCT_DESCRIPTION}</p>
    </div>
    <div class="oa-flow">
      <div class="oa-flow-card"><div class="oa-flow-step">01 · Source</div><div class="oa-flow-title">Bring the OEM document</div><div class="oa-flow-copy">Keep the original file and revision tied to the audit.</div></div>
      <div class="oa-flow-card"><div class="oa-flow-step">02 · Check</div><div class="oa-flow-title">Apply the engineering standard</div><div class="oa-flow-copy">Compare extracted values against the selected template.</div></div>
      <div class="oa-flow-card"><div class="oa-flow-step">03 · Review</div><div class="oa-flow-title">Inspect what needs attention</div><div class="oa-flow-copy">Open source evidence before accepting a finding.</div></div>
      <div class="oa-flow-card"><div class="oa-flow-step">04 · Record</div><div class="oa-flow-title">Export an audit trail</div><div class="oa-flow-copy">Carry the review result into the next engineering step.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_options = ["Overview", "Audit", "Bulk Audit", "Pilot Dashboard", "Review Queue", "Templates"]
st.session_state.workspace_nav = st.session_state.get("active_view", "Overview")
active_view = st.radio(
    "Workspace",
    nav_options,
    key="workspace_nav",
    horizontal=True,
    on_change=_sync_workspace_navigation,
    label_visibility="collapsed",
)

if active_view == "Overview":
    st.markdown("### Start here")
    h1, h2 = st.columns([1.6, 1])
    with h1:
        st.markdown("""<div class="oa-home-card"><div class="oa-home-title">Ready for a document?</div><div class="oa-home-copy">The fastest path is a focused audit: choose the standard in the sidebar, upload the source, and move straight to evidence-backed results.</div></div>""", unsafe_allow_html=True)
        st.button(
            "Open audit workspace",
            type="primary",
            use_container_width=True,
            on_click=_navigate_to,
            args=("Audit",),
        )
        st.button(
            "🎬 Start hackathon demo",
            use_container_width=True,
            on_click=_start_hackathon_demo,
        )
    with h2:
        last = st.session_state.get("audit_results") or []
        if last:
            total = sum(r.get("summary", {}).get("TOTAL", 0) for r in last if not r.get("error"))
            flagged = sum(sum(r.get("summary", {}).get(k, 0) for k in ("MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW")) for r in last if not r.get("error"))
            state = "Review focus" if flagged else "Ready to record"
            copy_text = f"{total} field checks in the latest run · {flagged} requiring attention."
        else:
            state = "No active run"
            copy_text = "Your first audit will appear here with its source, standard, and outcome."
        st.markdown(f"""<div class="oa-home-card"><div class="oa-home-title">Latest session</div><div class="oa-home-copy"><strong>{state}</strong><br>{copy_text}</div></div>""", unsafe_allow_html=True)

    st.markdown("### Built for the review moment")
    c1, c2, c3 = st.columns(3)
    for col, title, body in [
        (c1, "Source stays close", "Field results can carry page-level evidence, so the reviewer does not have to search the document from scratch."),
        (c2, "Rules stay explicit", "Each template shows the rule being checked instead of hiding the standard inside the model."),
        (c3, "The engineer stays in control", "Flags can be reviewed, accepted, rejected, or left open before sign-off."),
    ]:
        with col:
            st.markdown(f"""<div class="oa-home-card"><div class="oa-home-title">{title}</div><div class="oa-home-copy">{body}</div></div>""", unsafe_allow_html=True)

    st.markdown("### Session history")
    history = st.session_state.get("audit_history", [])
    if history:
        st.dataframe(pd.DataFrame(history[-8:][::-1]), use_container_width=True, hide_index=True)
    else:
        st.caption("No completed sessions in this workspace yet.")


# ---------------------------- AUDIT TAB -------------------------------

if active_view == "Audit":
    st.subheader("Engineering Audit")
    st.caption("A focused review workspace for one or more OEM documents.")
    st.markdown(
        f"""
        <div class="oa-session">
          <div class="oa-session-label">Audit session</div>
          <span class="oa-session-value">Template:</span> {template_name} &nbsp;·&nbsp;
          <span class="oa-session-value">Fields:</span> {len(schema['fields'])} &nbsp;·&nbsp;
          <span class="oa-session-value">Project:</span> {project_id} &nbsp;·&nbsp;
          <span class="oa-session-value">Revision:</span> {document_revision}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("""<div class="oa-outcome"><div class="oa-outcome-title">Review path</div><div class="oa-outcome-copy">Source document → extraction → rule check → evidence → engineer disposition</div></div>""", unsafe_allow_html=True)

    sample_path = schema.get("sample_file")
    demo_path = schema.get("demo_file")
    reasoning_enabled = st.toggle(
        "Enable Nemotron engineering reasoning pass",
        value=st.session_state.get("ai_reasoning_enabled", True),
        key="ai_reasoning_enabled",
        help="Runs a second, non-authoritative Nemotron pass over extracted values, rules, and source evidence. It can add rationale and ambiguity flags but never changes the deterministic audit status.",
    )
    st.caption("The reasoning pass is advisory only; configured engineering rules remain authoritative.")
    if st.session_state.get("demo_mode") and template_name == "Centrifugal Pump Audit" and demo_path:
        st.markdown(
            """<div class='oa-outcome'><div class='oa-outcome-title'>Hackathon demo rehearsal</div>
            <div class='oa-outcome-copy'>Synthetic pump PDF · intentionally includes one configured limit exceedance and one material mismatch.
            The audit is real; only the document fixture is synthetic.</div></div>""",
            unsafe_allow_html=True,
        )
    col_upload, col_sample = st.columns([3, 1])
    with col_upload:
        uploaded_files = st.file_uploader(
            "Upload OEM datasheet(s)", type=["txt", "pdf"],
            accept_multiple_files=True, key="audit_uploader",
            help="Digitally-created PDFs and plain text files. Scanned images aren't supported yet.",
        )
    with col_sample:
        st.write("")
        st.write("")
        demo_button = st.button(
            "Load demo PDF" if st.session_state.get("demo_mode") and demo_path else "Use sample",
            use_container_width=True,
            disabled=not (demo_path if st.session_state.get("demo_mode") and demo_path else sample_path),
            help="Load the prepared synthetic pump PDF for the hackathon demo."
            if st.session_state.get("demo_mode") and demo_path
            else ("Load the built-in example datasheet for this template." if sample_path else "This template has no sample file."),
        )
        use_sample = demo_button and not (st.session_state.get("demo_mode") and demo_path)
        if demo_button and st.session_state.get("demo_mode") and demo_path:
            st.session_state.demo_pdf_loaded = True

    pending_files = []
    pending_pdf_bytes = {}
    pre_errors = []

    for uf in (uploaded_files or []):
        try:
            if uf.name.lower().endswith(".pdf"):
                pending_pdf_bytes[uf.name] = uf.getvalue()
                pending_files.append((uf.name, None))
            else:
                pending_files.append((uf.name, uf.getvalue().decode("utf-8")))
        except UnicodeDecodeError:
            pre_errors.append(_error_result(uf.name, "File isn't valid UTF-8 text."))

    if st.session_state.get("demo_mode") and st.session_state.get("demo_pdf_loaded") and demo_path:
        try:
            with open(demo_path, "rb") as f:
                demo_bytes = f.read()
            demo_name = demo_path.split("/")[-1]
            pending_pdf_bytes[demo_name] = demo_bytes
            pending_files.append((demo_name, None))
        except OSError as e:
            st.error(f"Couldn't open the demo PDF: {e}")

    if use_sample and sample_path:
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                pending_files.append((sample_path.split("/")[-1], f.read()))
        except OSError as e:
            st.error(f"Couldn't open the sample file: {e}")

    n_files = len(pending_files) + len(pre_errors)

    if n_files == 0:
        st.info("Upload one or more datasheets, or click “Use sample”, to run an audit.")
    else:
        if n_files == 1 and pending_files:
            name, preview = pending_files[0]
            if preview is None:
                st.caption(f"PDF ready: {name}. Evidence-aware extraction will run when you start the audit.")
            else:
                with st.expander(f"Source text — {name}"):
                    st.text(preview[:6000] + ("\n…(truncated for display)" if len(preview) > 6000 else ""))
        else:
            st.caption(f"{n_files} file(s) ready.")

        workers = 3
        if len(pending_files) > 1:
            workers = st.slider(
                "Parallel requests", min_value=1, max_value=6, value=3,
                help="Controls simultaneous AI requests. Three is the default to reduce API rate-limit pressure while keeping multi-file audits responsive.",
            )
            if len(pending_files) > 50:
                st.warning("Large batches take a while and use meaningfully more API credits — "
                           "consider testing with a smaller batch first.")

        if st.button(
            "Run demo audit" if st.session_state.get("demo_mode") else "Run audit",
            type="primary",
            disabled=st.session_state.get("audit_processing", False),
        ):
            st.session_state.audit_processing = True
            st.session_state.audit_results = None
            st.session_state.audit_results_template = None
            try:
                if len(pending_files) <= 1:
                    ai_results = []
                    if pending_files:
                        name, text = pending_files[0]
                        with st.spinner("Extracting fields and checking against the standard…"):
                            started = time.perf_counter()
                            try:
                                if text is None:
                                    result = run_pdf_audit_with_evidence(
                                        pending_pdf_bytes[name], schema,
                                        include_intelligence=reasoning_enabled,
                                    )
                                    if reasoning_enabled:
                                        rows, raw, _extracted, _pages, intelligence = result
                                    else:
                                        rows, raw, _extracted, _pages = result
                                        intelligence = None
                                else:
                                    rows, raw, _ = run_audit(text, schema)
                                    intelligence = None
                                ai_results = [{
                                    "identifier": name, "rows": rows, "raw_output": raw,
                                    "summary": audit_summary(rows), "error": None,
                                    "intelligence": intelligence.to_dict() if intelligence is not None else None,
                                    "performance": {"total_s": round(time.perf_counter() - started, 3)},
                                }]
                            except Exception as e:  # noqa: BLE001
                                err_res = _error_result(name, e)
                                err_res["performance"] = {"total_s": round(time.perf_counter() - started, 3)}
                                ai_results = [err_res]
                else:
                    batch_pdf_files = []
                    batch_text_files = []
                    for name, text in pending_files:
                        if text is not None:
                            batch_text_files.append((name, text))
                        else:
                            batch_pdf_files.append((name, pending_pdf_bytes[name]))

                    total_batch = len(batch_pdf_files) + len(batch_text_files)
                    progress_bar = st.progress(0.0, text=f"Starting 0 of {total_batch} datasheets…")

                    def _update(done, total):
                        progress_bar.progress(min(done / total, 1.0), text=f"Processed {done} of {total} datasheets…")

                    pdf_results = run_batch_pdf_audit(
                        batch_pdf_files, schema, max_workers=workers,
                        progress_callback=_update,
                        include_intelligence=reasoning_enabled,
                    ) if batch_pdf_files else []

                    pdf_done = len(pdf_results)
                    text_results = run_batch_audit(
                        batch_text_files, schema, max_workers=workers,
                        progress_callback=lambda done, total: _update(pdf_done + done, total),
                    ) if batch_text_files else []

                    result_pool = {}
                    for result in pdf_results + text_results:
                        result_pool.setdefault(result["identifier"], []).append(result)
                    ai_results = []
                    for name, _ in pending_files:
                        bucket = result_pool.get(name) or []
                        if bucket:
                            ai_results.append(bucket.pop(0))

                    progress_bar.progress(1.0, text=f"Completed {len(ai_results)} of {total_batch} datasheets.")
                    progress_bar.empty()

                run = create_audit_run(project_id, document_revision, reviewer_id)
                st.session_state.lifecycle_context = {
                    "project_id": run.project_id,
                    "run_id": run.run_id,
                    "document_revision": run.document_revision,
                }
                st.session_state.audit_results = pre_errors + ai_results
                st.session_state.audit_results_template = template_name
                _sync_review_items_from_results(
                    st.session_state.audit_results,
                    st.session_state.lifecycle_context,
                )
                total_fields = sum(r.get("summary", {}).get("TOTAL", 0) for r in pre_errors + ai_results if not r.get("error"))
                matched_fields = sum(r.get("summary", {}).get("MATCHED", 0) for r in pre_errors + ai_results if not r.get("error"))
                flagged_fields = sum(sum(r.get("summary", {}).get(k, 0) for k in ("MISSING", "MISMATCHED", "OUT OF RANGE", "NEEDS_REVIEW")) for r in pre_errors + ai_results if not r.get("error"))
                st.session_state.audit_history.append({
                    "Template": template_name,
                    "Files": len(ai_results) + len(pre_errors),
                    "Fields": total_fields,
                    "Matched": matched_fields,
                    "Attention": flagged_fields,
                    "Project": project_id,
                    "Revision": document_revision,
                })
                if st.session_state.get("demo_mode"):
                    st.success("Demo checkpoint 1/4: audit completed. Next: inspect evidence, then record a reviewer disposition.")
            finally:
                st.session_state.audit_processing = False

    results = st.session_state.get("audit_results")
    if results and st.session_state.get("audit_results_template") == template_name:
        render_group_results(results, template_name, "audit", "file", show_errors=True, schema=schema)


# ---------------------------- BULK AUDIT TAB -------------------------------

if active_view == "Bulk Audit":
    st.subheader(f"Bulk audit — {template_name}")
    st.caption("For equipment lists already in spreadsheet form (like a lubrication "
               "schedule or equipment register). Columns are mapped to template fields "
               "directly — no AI extraction needed, since the data is already structured.")

    bulk_file = st.file_uploader(
        "Upload an equipment list", type=["xlsx", "csv"], key="bulk_uploader",
    )

    col_sample, _ = st.columns([1, 3])
    with col_sample:
        use_bulk_sample = st.button("Use sample equipment list")

    bulk_df = None
    if bulk_file is not None:
        try:
            bulk_df = (pd.read_csv(bulk_file) if bulk_file.name.lower().endswith(".csv")
                       else pd.read_excel(bulk_file))
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't read that file: {e}")
    elif use_bulk_sample:
        try:
            bulk_df = pd.read_excel("sample_data/lube_oil_bulk_sample.xlsx")
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't load the sample: {e}")

    if bulk_df is not None and not bulk_df.empty:
        columns = list(bulk_df.columns)
        st.success(f"Loaded {len(bulk_df)} rows, {len(columns)} columns.")

        with st.expander("Preview uploaded data", expanded=False):
            st.dataframe(bulk_df.head(10), use_container_width=True)

        st.markdown("##### Map spreadsheet columns to template fields")
        st.caption("Best guesses are pre-selected — check and correct them before running.")

        suggested_identifier = guess_identifier_column(columns)
        identifier_col = st.selectbox(
            "Which column identifies each equipment row?",
            columns,
            index=columns.index(suggested_identifier) if suggested_identifier in columns else 0,
        )

        guessed = guess_column_mapping(schema, columns)
        column_map = {}
        none_option = "— not in this spreadsheet —"
        options = [none_option] + columns

        for f in schema["fields"]:
            default = guessed.get(f["field_name"])
            default_idx = options.index(default) if default in options else 0
            chosen = st.selectbox(
                f"{f['label']}" + (f" ({f['unit']})" if f.get("unit") else ""),
                options, index=default_idx, key=f"colmap_{f['field_name']}",
            )
            column_map[f["field_name"]] = None if chosen == none_option else chosen

        if st.button("Run bulk audit", type="primary"):
            records = bulk_df.to_dict("records")
            results = run_bulk_audit(records, schema, column_map, identifier_col)
            run = create_audit_run(project_id, document_revision, reviewer_id)
            st.session_state.lifecycle_context = {
                "project_id": run.project_id,
                "run_id": run.run_id,
                "document_revision": run.document_revision,
            }
            st.session_state.bulk_results = results
            st.session_state.bulk_template = template_name
            _sync_review_items_from_results(results, st.session_state.lifecycle_context)

    bulk_results = st.session_state.get("bulk_results")
    if bulk_results and st.session_state.get("bulk_template") == template_name:
        render_group_results(bulk_results, template_name, "bulk", "equipment", show_errors=False, schema=schema)
    elif bulk_df is None:
        st.info("Upload a spreadsheet or use the sample to run a bulk audit.")


# ---------------------------- PILOT DASHBOARD TAB ---------------------------

if active_view == "Pilot Dashboard":
    st.subheader("Pilot dashboard")
    st.caption("Operational metrics for pilot evaluation. These metrics describe workflow output; they do not constitute engineering approval.")
    combined = (st.session_state.get("audit_results") or []) + (st.session_state.get("bulk_results") or [])
    metrics = summarize_results(combined)
    cols = st.columns(4)
    cols[0].metric("Files processed", metrics["files_processed"])
    cols[1].metric("Rows evaluated", metrics["rows_evaluated"])
    cols[2].metric("Matched rows", metrics["matched_rows"])
    cols[3].metric("Flagged rows", metrics["flagged_rows"])
    st.metric("Flag rate", f"{metrics['flag_rate']:.1%}")
    if metrics["status_counts"]:
        st.markdown("#### Status distribution")
        st.dataframe(pd.DataFrame(list(metrics["status_counts"].items()), columns=["Status", "Count"]), use_container_width=True, hide_index=True)

    st.markdown("#### Pilot benchmark register")
    st.caption("Paste or edit measured benchmark records. Accuracy values must come from a reviewer-approved reference set.")
    benchmark_default = pd.DataFrame(st.session_state.get("pilot_benchmark_records", [
        {"equipment_type": "Pump", "value_accuracy": 0.0, "status_accuracy": 0.0},
    ]))
    benchmark_editor = st.data_editor(benchmark_default, num_rows="dynamic", use_container_width=True, key="pilot_benchmark_editor")
    st.session_state.pilot_benchmark_records = benchmark_editor.to_dict("records")

    st.markdown("#### Reviewer dispositions")
    disposition_default = pd.DataFrame(st.session_state.get("pilot_review_records", [{"disposition": "UNSET"}]))
    disposition_editor = st.data_editor(disposition_default, num_rows="dynamic", use_container_width=True, key="pilot_review_editor")
    st.session_state.pilot_review_records = disposition_editor.to_dict("records")

    dashboard = build_pilot_dashboard(
        benchmark_records=st.session_state.pilot_benchmark_records,
        cycle_records=st.session_state.get("pilot_cycle_records", []),
        review_records=st.session_state.pilot_review_records,
    )
    d1, d2, d3 = st.columns(3)
    d1.metric("Benchmark cases", dashboard["benchmark_cases"])
    d2.metric("Value accuracy", f"{dashboard['overall_value_accuracy']:.1%}")
    d3.metric("Status accuracy", f"{dashboard['overall_status_accuracy']:.1%}")
    if dashboard["by_equipment"]:
        st.dataframe(pd.DataFrame.from_dict(dashboard["by_equipment"], orient="index").reset_index(names="Equipment type"), use_container_width=True, hide_index=True)

    st.markdown("#### Cycle-time measurement")
    st.caption("Enter measured pilot timings to calculate time saved.")
    c1, c2 = st.columns(2)
    with c1:
        manual = st.number_input("Manual process (minutes)", min_value=0.0, value=120.0, step=5.0)
    with c2:
        assisted = st.number_input("Sutreva-assisted process (minutes)", min_value=0.0, value=45.0, step=5.0)
    timing = compare_cycle_times(manual, assisted)
    st.session_state.pilot_cycle_records = [{"manual_minutes": manual, "assisted_minutes": assisted}]
    t1, t2 = st.columns(2)
    t1.metric("Minutes saved", f"{timing['minutes_saved']:.1f}")
    t2.metric("Reduction", f"{timing['reduction_rate']:.1%}")

    st.markdown("#### Export pilot report")
    st.caption("Exports summarize entered measurements. They do not constitute engineering approval.")
    report = build_pilot_report(
        benchmark_records=st.session_state.get("pilot_benchmark_records", []),
        cycle_records=st.session_state.get("pilot_cycle_records", []),
        review_records=st.session_state.get("pilot_review_records", []),
        data_classification="USER_ENTERED_PILOT_DATA",
    )
    e1, e2 = st.columns(2)
    with e1:
        st.download_button(
            "Download JSON report",
            data=report_json_bytes(report),
            file_name="sutreva_pilot_report.json",
            mime="application/json",
        )
    with e2:
        st.download_button(
            "Download KPI CSV",
            data=report_summary_csv_bytes(report),
            file_name="sutreva_pilot_kpis.csv",
            mime="text/csv",
        )


# ---------------------------- REVIEW QUEUE TAB -----------------------------

if active_view == "Review Queue":
    st.subheader("Engineering Review Queue")
    st.caption("Review non-matching findings, assign ownership, and record a disposition.")
    if st.session_state.get("demo_mode"):
        st.markdown(
            """<div class='oa-outcome'><div class='oa-outcome-title'>Demo checkpoint 2/4</div>
            <div class='oa-outcome-copy'>Open the cited evidence, record one disposition and learning signal, then continue to the evaluation flywheel.</div></div>""",
            unsafe_allow_html=True,
        )

    source_results = []
    if st.session_state.get("audit_results"):
        source_results.extend(st.session_state["audit_results"])
    if st.session_state.get("bulk_results"):
        source_results.extend(st.session_state["bulk_results"])

    if source_results:
        _sync_review_items_from_results(source_results, st.session_state.get("lifecycle_context"))

    items = st.session_state.review_items
    open_items = [item for item in items if item.is_open]
    c1, c2, c3 = st.columns(3)
    c1.metric("Total findings", len(items))
    c2.metric("Open", len(open_items))
    c3.metric("Closed", len(items) - len(open_items))

    feedback_stats = feedback_summary(st.session_state.feedback_records)
    f1, f2, f3 = st.columns(3)
    f1.metric("Feedback events", feedback_stats["total_feedback_events"])
    f2.metric("Evaluation-ready", feedback_stats["evaluation_ready"])
    f3.metric("Rule-update signals", feedback_stats["rule_update_signals"])

    st.markdown("### Evaluation Flywheel")
    st.caption("Explicitly curate closed reviews into a versioned gold set. This never retrains or changes the production model automatically.")
    curated_cases = st.session_state.get("evaluation_cases", [])
    ec1, ec2 = st.columns(2)
    ec1.metric("Curated cases", len(curated_cases))
    ec2.metric("Schema", EVAL_SCHEMA)
    if curated_cases:
        if st.button("Run evaluation on recorded Nemotron outputs", key="run_recorded_evaluation", use_container_width=True):
            predictions = predictions_from_cases(curated_cases)
            report = evaluate_snapshot(
                curated_cases,
                predictions,
                model_version=str((curated_cases[0].original_ai_context or {}).get("model") or "recorded-model"),
                prompt_version=str((curated_cases[0].original_ai_context or {}).get("prompt_version") or "recorded-prompt"),
            )
            st.session_state.last_evaluation_report = report
        report = st.session_state.get("last_evaluation_report")
        if report:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Assessment accuracy", f"{report.assessment_accuracy:.0%}")
            r2.metric("Risk accuracy", f"{report.risk_accuracy:.0%}")
            r3.metric("Evidence grounding", f"{report.evidence_grounding_rate:.0%}")
            r4.metric("Status preserved", f"{report.status_preservation_rate:.0%}")
            st.success("Evaluation gate passed." if report.regression_passed else "Evaluation gate failed; review the regression report before changing the model/prompt.")
            if st.session_state.get("demo_mode"):
                st.info("Demo checkpoint 4/4: evaluation gate displayed. The demo can now close with the Nebius + NVIDIA runtime provenance visible.")
        st.download_button(
            "⬇️ Download curated evaluation set",
            data=export_cases_jsonl(curated_cases),
            file_name="sutreva_curated_evaluation.jsonl",
            mime="application/x-ndjson",
            use_container_width=True,
            key="download_curated_evaluation",
        )
    if feedback_stats["evaluation_ready"]:
        st.download_button(
            "⬇️ Download reviewed feedback (JSONL)",
            data=export_feedback_jsonl(st.session_state.feedback_records, include_identity=False),
            file_name="sutreva_review_feedback.jsonl",
            mime="application/x-ndjson",
            use_container_width=True,
            key="download_feedback_jsonl",
        )
    st.caption("Human feedback is captured as an append-only learning signal. Exported records are evaluation candidates only; Sutreva never auto-trains or changes the model from reviewer feedback.")

    if not items:
        st.info("Run an audit first. Findings requiring attention will appear here.")
    else:
        status_filter = st.multiselect("Filter by status", sorted({i.status for i in items}), default=sorted({i.status for i in items}))
        visible = [i for i in items if i.status in status_filter and i.is_open]
        if not visible:
            st.success("No open findings match the selected filters.")
        for item in visible:
            with st.expander(f"{item.equipment_id} · {item.field} · {item.status}"):
                st.write(f"**Reason:** {item.reason}")
                if item.evidence:
                    st.json(item.evidence)
                with st.form(f"review_{item.item_id}"):
                    assignee = st.text_input("Assignee", value=item.assignee or "")
                    disposition_options = ["OPEN", "ACCEPTED", "REJECTED", "WAIVED", "REQUIRES_ACTION", "REOPENED"]
                    current_disposition = item.disposition or "OPEN"
                    if current_disposition not in disposition_options:
                        current_disposition = "OPEN"
                    disposition = st.selectbox("Disposition", disposition_options, index=disposition_options.index(current_disposition))
                    feedback_options = ["CONFIRMED_FINDING", "OVERRIDDEN_FINDING", "INSUFFICIENT_EVIDENCE", "RULE_UPDATE_SIGNAL", "WAIVED_BY_REVIEW", "ACTION_REQUIRED", "OTHER"]
                    default_label = {
                        "ACCEPTED": "CONFIRMED_FINDING",
                        "REJECTED": "OVERRIDDEN_FINDING",
                        "WAIVED": "WAIVED_BY_REVIEW",
                        "REQUIRES_ACTION": "ACTION_REQUIRED",
                    }.get(disposition, "OTHER")
                    feedback_label = st.selectbox("Learning signal", feedback_options, index=feedback_options.index(default_label))
                    corrected_value = st.text_input("Reviewer-corrected value (optional)", value="", placeholder="Enter the verified value when the extracted value was wrong.")
                    comment = st.text_area("Reviewer comment", value=item.reviewer_comment)
                    st.markdown("**Evaluation gold label (optional)**")
                    gold_assessment = st.selectbox("Gold assessment", ["", "SUPPORTED", "AMBIGUOUS", "UNSUPPORTED", "MISSING"], key=f"gold_assessment_{item.item_id}")
                    gold_risk = st.selectbox("Gold risk", ["", "LOW", "MEDIUM", "HIGH"], key=f"gold_risk_{item.item_id}")
                    gold_status = st.text_input("Gold authoritative status", value=item.status, key=f"gold_status_{item.item_id}")
                    if st.form_submit_button("Save review"):
                        updated = update_review_item(item, assignee=assignee, disposition=disposition, comment=comment)
                        st.session_state.review_items = [updated if x.item_id == updated.item_id else x for x in st.session_state.review_items]
                        upsert_items(st.session_state.review_items)
                        if disposition in {"ACCEPTED", "REJECTED", "WAIVED", "REQUIRES_ACTION"}:
                            try:
                                actor_id = st.session_state.get("operator_id", "local-user")
                                actor = UserIdentity(
                                    user_id=actor_id,
                                    display_name=actor_id,
                                    role="REVIEWER",
                                )
                                record_approval_event(
                                    ApprovalEvent(
                                        item_id=updated.item_id,
                                        actor=actor,
                                        disposition=disposition,
                                        comment=comment,
                                    )
                                )
                            except (OSError, ValueError) as exc:
                                st.warning(f"Review saved, but governance event could not be recorded: {exc}")
                        feedback = build_feedback_record(
                            updated,
                            disposition=disposition,
                            reviewer_comment=comment,
                            corrected_value=corrected_value,
                            feedback_label=feedback_label,
                            reviewer_id=st.session_state.get("operator_id", "local-user"),
                            reviewer_name=st.session_state.get("operator_id", "local-user"),
                            reviewer_role="REVIEWER",
                        )
                        record_feedback(feedback)
                        st.session_state.feedback_records.append(feedback)
                        if gold_assessment and gold_risk and gold_status:
                            try:
                                case = curate_feedback_record(
                                    feedback,
                                    gold_status=gold_status,
                                    gold_assessment=gold_assessment,
                                    gold_risk=gold_risk,
                                    gold_evidence_refs=item.evidence and [item.evidence] or [],
                                )
                                record_curated_case(case)
                                existing_cases = [c for c in st.session_state.get("evaluation_cases", []) if c.case_id != case.case_id and c.feedback_id != case.feedback_id]
                                st.session_state.evaluation_cases = existing_cases + [case]
                                st.success("Demo checkpoint 3/4: review + learning signal + gold label recorded. Audit status remains authoritative and unchanged.")
                            except ValueError as exc:
                                st.warning(f"Review saved, but evaluation curation was skipped: {exc}")
                        else:
                            st.success("Review and learning signal recorded. Add a gold assessment and risk later to curate this case for evaluation.")


# ---------------------------- EDITOR TAB ----------------------------------

if active_view == "Templates":
    st.subheader("Template Administration")
    st.caption("Build or edit an audit standard. Saving with an existing name updates "
               "that template; a new name creates a new one.")

    st.session_state.editor_name = st.text_input(
        "Template name",
        value=st.session_state.editor_name,
        placeholder="e.g. Lube Oil List Audit",
    )

    with st.form("add_field", clear_on_submit=True):
        c1, c2 = st.columns(2)
        label = c1.text_input("Field label", placeholder="e.g. Viscosity Grade")
        unit = c2.text_input("Unit (optional)", placeholder="e.g. cSt")

        check_type = st.selectbox("How should this field be checked?", CHECK_TYPES)

        rule_value = None
        if check_type == CHECK_TYPES[0]:
            rule_value = st.text_input("Acceptable values (comma-separated)",
                                       placeholder="ISO VG68, ISO VG32")
        elif check_type == CHECK_TYPES[1]:
            rule_value = st.text_input("Expected value")
        elif check_type == CHECK_TYPES[2]:
            rule_value = st.number_input("Maximum value", value=0.0)
        elif check_type == CHECK_TYPES[3]:
            rule_value = st.number_input("Minimum value", value=0.0)

        required = st.checkbox("Required field", value=True)
        enrich_ai = st.checkbox(
            "🧠 Auto-discover vendor aliases & collision guards with Nemotron (saves to ontology library)",
            value=False,
        )

        if st.form_submit_button("Add field"):
            if not label.strip():
                st.warning("Give the field a label first.")
            else:
                new_f = _field_from_inputs(label, unit, check_type, rule_value, required, enrich_with_ai=enrich_ai)
                st.session_state.editor_fields.append(new_f)
                aliases_preview = ", ".join((new_f.get("extraction_aliases") or [])[:5])
                st.success(f"Added “{label.strip()}” (Mapped aliases: {aliases_preview}).")

    if st.session_state.editor_fields:
        st.markdown("##### Fields in this template")
        for i, f in enumerate(st.session_state.editor_fields):
            c1, c2, c3 = st.columns([4, 3, 1])
            unit = f" ({f['unit']})" if f.get("unit") else ""
            c1.markdown(f"**{f['label']}**{unit}")
            c2.caption(_rule_summary(f))
            if c3.button("Remove", key=f"rm_{i}", use_container_width=True):
                st.session_state.editor_fields.pop(i)
                st.rerun()

        st.divider()
        s1, s2 = st.columns([1, 4])
        with s1:
            if st.button("💾 Save template", type="primary", use_container_width=True):
                try:
                    path = save_template(
                        st.session_state.editor_name,
                        st.session_state.editor_fields,
                    )
                    st.success(f"Saved to `{path}`. Pick it in the sidebar to use it.")
                    st.session_state.editor_fields = []
                    st.session_state.editor_name = ""
                except ValueError as e:
                    st.error(str(e))
        with s2:
            if st.button("Clear editor", use_container_width=False):
                st.session_state.editor_fields = []
                st.session_state.editor_name = ""
                st.rerun()
    else:
        st.info("No fields yet. Add one above, or click “Edit this template” in the "
                "sidebar to start from an existing standard.")


st.markdown("<div class=\"oa-footer\">{name} · source-first review workspace · engineer verification remains the final control</div>".format(name=PRODUCT_NAME), unsafe_allow_html=True)
