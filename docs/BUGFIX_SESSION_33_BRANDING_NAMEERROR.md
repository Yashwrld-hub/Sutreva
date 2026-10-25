# Bugfix Session 33 — Branding `NameError`

## Symptom

The Streamlit application failed during startup with:

`NameError: name 'page_title' is not defined`

## Root cause

`app.py` called `page_title()` in `st.set_page_config()` and later referenced `PRODUCT_NAME`, `PRODUCT_TAGLINE`, `PRODUCT_DESCRIPTION`, and `PRODUCT_VERSION`, but the Session 32 branding refactor did not import those symbols from `product_brand.py`.

## Fix

`app.py` now imports the complete branding API explicitly:

- `PRODUCT_DESCRIPTION`
- `PRODUCT_NAME`
- `PRODUCT_TAGLINE`
- `PRODUCT_VERSION`
- `page_title`

A static regression test checks that the application imports all five symbols whenever branding is used.

## Validation

- Test suite: 126 passed.
- Python compilation: passed.
- Offline deployment sanity check: passed.
- Streamlit runtime smoke launch was not executed in this environment because the `streamlit` executable is not installed in the current runtime; `requirements.txt` remains the deployment dependency source.
