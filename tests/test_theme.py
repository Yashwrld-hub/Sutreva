from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CONFIG = ROOT / ".streamlit" / "config.toml"


def test_custom_light_and_dark_themes_are_configured():
    text = CONFIG.read_text(encoding="utf-8")
    assert "[theme.light]" in text
    assert "[theme.dark]" in text
    assert "[theme.light.sidebar]" in text
    assert "[theme.dark.sidebar]" in text
    assert 'primaryColor = "#4F46E5"' in text
    assert 'primaryColor = "#818CF8"' in text
    assert 'backgroundColor = "#EEF2FF"' in text
    assert 'backgroundColor = "#0B1020"' in text


def test_app_does_not_override_global_theme_palette():
    text = APP.read_text(encoding="utf-8")
    assert "st.context.theme" not in text
    assert "_active_theme_type" not in text
    assert "var(--st-background-color" not in text
    assert "var(--st-text-color" not in text
    assert "var(--st-primary-color" not in text
    assert "var(--st-secondary-background-color" not in text
    assert 'background:var(--oa-bg)' not in text
    assert 'color:var(--oa-ink)' not in text


def test_custom_css_inherits_active_streamlit_theme():
    text = APP.read_text(encoding="utf-8")
    assert 'color:inherit' in text
    assert 'currentColor' in text
    assert 'CSS = r"""<style>' in text
    assert "CSS.replace(" not in text


def test_theme_does_not_force_native_widget_colors():
    text = APP.read_text(encoding="utf-8")
    for selector in (
        '[data-testid="stTextInput"] input',
        '[data-testid="stNumberInput"] input',
        '[data-testid="stTextArea"] textarea',
        '[data-testid="stSelectbox"] [data-baseweb="select"] > div',
        '[data-testid="stMultiSelect"] [data-baseweb="select"] > div',
        '[data-testid="stExpander"] details',
        '[data-testid="stAlert"]',
    ):
        assert selector not in text or "background:" not in text.split(selector, 1)[1].split("}", 1)[0]


def test_streamlit_version_supports_dual_themes_and_theme_persistence_fix():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit>=1.52.1,<1.65.0" in text
