from pathlib import Path

from product_brand import NAV_GROUPS, PRODUCT_DESCRIPTION, PRODUCT_NAME, PRODUCT_TAGLINE, page_title


def test_product_identity_is_centralized():
    assert PRODUCT_NAME == "Sutreva"
    assert PRODUCT_TAGLINE
    assert PRODUCT_DESCRIPTION
    source = (Path(__file__).resolve().parents[1] / "product_brand.py").read_text(encoding="utf-8")
    assert "Legacy product name retained for historical traceability: OEM Audit Copilot" in source


def test_navigation_groups_have_expected_workflow():
    assert NAV_GROUPS["WORK"] == ("Audit", "Bulk Audit")
    assert NAV_GROUPS["REVIEW"] == ("Review Queue",)
    assert NAV_GROUPS["INSIGHTS"] == ("Pilot Dashboard",)
    assert NAV_GROUPS["ADMIN"] == ("Templates",)


def test_page_title_can_include_template():
    assert page_title() == PRODUCT_NAME
    assert page_title("Centrifugal Pump") == "Sutreva — Centrifugal Pump"


def test_app_imports_all_brand_symbols():
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "from product_brand import (" in app_source
    for symbol in (
        "PRODUCT_DESCRIPTION",
        "PRODUCT_NAME",
        "PRODUCT_TAGLINE",
        "PRODUCT_VERSION",
        "page_title",
    ):
        assert symbol in app_source
