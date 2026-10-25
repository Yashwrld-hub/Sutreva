"""Centralized product identity and UI copy for the Streamlit application."""

# Legacy product name retained for historical traceability: OEM Audit Copilot.
PRODUCT_NAME = "Sutreva"
PRODUCT_TAGLINE = "Evidence-backed engineering document intelligence"
PRODUCT_DESCRIPTION = (
    "Extract engineering values, compare them with an audit standard, and trace findings "
    "back to source evidence."
)
PRODUCT_VERSION = "Pilot"

NAV_GROUPS = {
    "WORK": ("Audit", "Bulk Audit"),
    "REVIEW": ("Review Queue",),
    "INSIGHTS": ("Pilot Dashboard",),
    "ADMIN": ("Templates",),
}


def page_title(template_name: str | None = None) -> str:
    """Build a concise browser/page title."""
    return f"{PRODUCT_NAME} — {template_name}" if template_name else PRODUCT_NAME
