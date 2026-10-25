# Session 42 — Theme Architecture Fix

## Root cause

The previous Session 42 patch placed Streamlit `--st-*` CSS tokens on the application's global `:root`. Those tokens are intended to be exposed in component styling and are not a reliable global styling API for arbitrary markdown HTML. As a result, Sutreva custom surfaces could fall back to the light palette even while Streamlit's native UI had switched to Dark mode.

## Fix

1. `.streamlit/config.toml` remains the single source of truth for the native Light/Dark themes.
2. `app.py` no longer overrides the global application background, text, widget, or sidebar palette with `--st-*` tokens.
3. Sutreva custom HTML uses inherited `currentColor` and low-opacity `color-mix()` tints so its cards, evidence blocks, navigation accents, and decorative surfaces track the active Streamlit palette.
4. The results-table status styling no longer depends on an undefined Python `PALETTE` object.
5. The Streamlit dependency floor is raised to `1.52.1` because Streamlit 1.51–1.52.0 had a confirmed custom light/dark theme persistence regression.

## Validation target

Light/Dark switching is delegated to Streamlit's native theme system. Sutreva custom surfaces must not pin the page to a Python snapshot or to global `--st-*` variables.
