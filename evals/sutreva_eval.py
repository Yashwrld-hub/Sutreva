"""Sutreva domain evaluation harness for evidence-grounded Nemotron reasoning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BENCHMARK_PATH = Path(__file__).with_name("sutreva_evidence_benchmark.jsonl")
REASONING_PROMPT_VERSION = "sutreva.reasoning.v2"


def load_cases(path: Path = BENCHMARK_PATH) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _evidence_matches(expected: dict[str, Any] | None, refs: Any) -> bool:
    if expected is None:
        return not refs
    if not isinstance(refs, list) or not refs:
        return False
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        if (
            ref.get("page") == expected.get("page")
            and ref.get("line") == expected.get("line")
            and str(ref.get("quote") or "").strip() == str(expected.get("text") or "").strip()
        ):
            return True
    return False


def score_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    assessments = result.get("field_assessments") or []
    assessment = next(
        (a for a in assessments if a.get("field_name") == case["field_name"]),
        None,
    )
    assessment_value = assessment.get("assessment") if assessment else None
    risk_value = assessment.get("risk") if assessment else None
    evidence_ok = _evidence_matches(case.get("evidence"), assessment.get("evidence_refs") if assessment else None)
    return {
        "case_id": case["case_id"],
        "assessment_correct": assessment_value == case["expected_assessment"],
        "risk_correct": risk_value == case["expected_risk"],
        "evidence_grounded": evidence_ok == bool(case.get("expected_evidence_match")),
        "assessment": assessment_value,
        "risk": risk_value,
        "status_preserved": bool(result.get("status_preserved", True)),
    }


def summarize(scores: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(scores)
    if not n:
        return {"cases": 0, "assessment_accuracy": 0.0, "risk_accuracy": 0.0, "evidence_grounding": 0.0, "status_preservation": 0.0}
    return {
        "cases": n,
        "assessment_accuracy": sum(s["assessment_correct"] for s in scores) / n,
        "risk_accuracy": sum(s["risk_correct"] for s in scores) / n,
        "evidence_grounding": sum(s["evidence_grounded"] for s in scores) / n,
        "status_preservation": sum(s["status_preserved"] for s in scores) / n,
    }


def self_check() -> dict[str, Any]:
    """Verify benchmark/scorer integrity using its own gold labels."""
    cases = load_cases()
    scores = []
    for case in cases:
        result = {
            "status_preserved": True,
            "field_assessments": [{
                "field_name": case["field_name"],
                "assessment": case["expected_assessment"],
                "risk": case["expected_risk"],
                "evidence_refs": ([{
                    "page": case["evidence"]["page"],
                    "line": case["evidence"]["line"],
                    "quote": case["evidence"]["text"],
                }] if case.get("evidence") else []),
            }],
        }
        scores.append(score_case(case, result))
    summary = summarize(scores)
    return {"prompt_version": REASONING_PROMPT_VERSION, "summary": summary, "cases": scores}


def score_jsonl(response_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    cases = {c["case_id"]: c for c in load_cases()}
    scores: list[dict[str, Any]] = []
    for line in response_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        case = cases[record["case_id"]]
        result = record.get("result") or record
        scores.append(score_case(case, result))
    report = {"prompt_version": REASONING_PROMPT_VERSION, "summary": summarize(scores), "cases": scores}
    if output_path:
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Sutreva evidence-grounded reasoning outputs.")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_check:
        print(json.dumps(self_check(), indent=2))
        return 0
    if not args.responses:
        parser.error("--responses is required unless --self-check is used")
    print(json.dumps(score_jsonl(args.responses, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
