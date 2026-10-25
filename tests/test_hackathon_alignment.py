import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs" / "SUTREVA_HACKATHON_TRACKER.json"
ALIGNMENT = ROOT / "docs" / "HACKATHON_ALIGNMENT_SESSION_45.md"
SUBMISSION_ARCH = ROOT / "docs" / "SUTREVA_SUBMISSION_ARCHITECTURE.md"


def _tracker():
    return json.loads(TRACKER.read_text(encoding="utf-8"))


def test_hackathon_track_and_platform_are_explicit():
    data = _tracker()
    assert data["hackathon"]["track"] == "Best Apps and Agents"
    assert data["required_platform"]["primary"] == "Nebius Token Factory"


def test_nvidia_model_and_provider_are_explicit():
    data = _tracker()
    assert data["nvidia_model"]["provider"] == "NVIDIA"
    assert data["nvidia_model"]["model"].startswith("nvidia/NVIDIA-Nemotron")


def test_submission_artifacts_are_tracked():
    data = _tracker()
    required = {
        "Working demo URL",
        "Public source repository URL",
        "Open-source license",
        "README with installation and runtime instructions",
        "Public YouTube demonstration video under 3 minutes",
    }
    assert required.issubset(set(data["submission_artifacts"]))


def test_alignment_documents_name_the_submission_requirements():
    alignment = ALIGNMENT.read_text(encoding="utf-8")
    submission = SUBMISSION_ARCH.read_text(encoding="utf-8")
    for content in (alignment, submission):
        assert "Nebius Token Factory" in content
        assert "Nemotron" in content
        assert "human" in content.lower()
