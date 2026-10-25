from pathlib import Path


def test_app_contains_pilot_dashboard_integration():
    source = Path(__file__).parents[1].joinpath("app.py").read_text(encoding="utf-8")
    assert "build_pilot_dashboard" in source
    assert "pilot_benchmark_editor" in source
    assert "pilot_review_editor" in source
