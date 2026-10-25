"""Offline deployment sanity checks for Sutreva."""
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = [
    "app.py",
    "core.py",
    "requirements.txt",
    "ai_provider.py",
    ".env.example",
    "runtime_config.py",
    "deploy/nebius/Dockerfile",
    "deploy/nebius/docker-compose.yml",
    "scripts/nebius_preflight.py",
    "scripts/hackathon_demo_rehearsal.py",
    "sample_data/hackathon_pump_demo.pdf",
    "docs/NEBIUS_DEPLOYMENT_SESSION_53.md",
    "docs/HACKATHON_DEMO_RUNBOOK.md",
    "docs/HACKATHON_DEMO_SESSION_54.md",
    "pilot_workspace/human_audit_template.csv",
    "pilot_workspace/tool_audit_results_template.csv",
    "pilot_workspace/comparison_template.csv",
    "docs/PILOT_EXECUTION_GUIDE.md",
]
MODULES = [
    "ai_provider", "runtime_config", "core", "extract", "exports", "evaluation_flywheel", "pilot_benchmark", "pilot_dashboard",
    "pilot_report", "pilot_casepack", "review_store", "governance", "lifecycle",
]

for relative in REQUIRED:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Missing required deployment file: {relative}")

for module in MODULES:
    importlib.import_module(module)

print(f"Deployment sanity check passed: {len(REQUIRED)} required files and {len(MODULES)} modules")
