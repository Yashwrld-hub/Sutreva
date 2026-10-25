from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
RESULTS_UI = ROOT / "results_ui.py"


def _source():
    return APP.read_text(encoding="utf-8") + "\n" + RESULTS_UI.read_text(encoding="utf-8")


def test_launch_ui_has_overview_workspace_and_workflow_path():
    source = _source()
    assert '"Overview"' in source
    assert '"Audit"' in source
    assert '"Review Queue"' in source
    for label in ("Source", "Check", "Review", "Record"):
        assert f"{label}" in source


def test_pdf_audits_use_evidence_aware_pipeline():
    source = _source()
    assert "run_pdf_audit_with_evidence" in source
    assert "pending_pdf_bytes" in source


def test_ui_exposes_source_evidence_panel():
    source = _source()
    assert "Source evidence" in source
    assert "row.get(\"evidence\")" in source
    assert "oa-evidence" in source


def test_ui_has_no_raw_emoji_brand_title():
    source = _source()
    assert '🔩 {PRODUCT_NAME}' not in source


def test_workspace_navigation_is_programmatic_and_tabs_are_not_used():
    source = _source()
    assert 'active_view = st.radio(' in source
    assert 'st.session_state.active_view = view' in source
    assert 'st.tabs(' not in source
    assert 'if active_view == "Audit":' in source


def test_landing_workspace_button_uses_navigation_callback():
    source = _source()
    assert "def _navigate_to(view: str):" in source
    assert 'key="workspace_nav"' in source
    assert "on_change=_sync_workspace_navigation" in source
    assert "on_click=_navigate_to" in source
    assert 'args=("Audit",)' in source
    assert 'key="active_view"' not in source


def test_hackathon_demo_path_is_explicitly_wired():
    source = _source()
    for marker in (
        "_start_hackathon_demo",
        'key="template_selector"',
        'demo_mode',
        'Load demo PDF',
        'Run demo audit',
        'demo_path = schema.get("demo_file")',
    ):
        assert marker in source


def test_ui_downloads_do_not_trigger_rerun_during_audit():
    source = _source()
    assert 'on_click="ignore"' in source
    assert 'audit_processing' in source
    assert 'if reasoning_enabled:' in source


def test_results_ui_is_file_centric_and_filterable():
    source = _source()
    for marker in (
        "Primary comparison view",
        "one row per file, one column per audited field",
        'build_file_centric_results',
        'filter_file_centric_results',
        'Filter by field status',
        'Field status',
        'Use the table\'s column filters',
        'Field-by-field review for every',
    ):
        assert marker in source
