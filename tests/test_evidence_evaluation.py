from evals.sutreva_eval import load_cases, score_case, self_check, summarize


def test_benchmark_self_check_is_perfect():
    report = self_check()
    assert report["summary"]["cases"] == 8
    assert report["summary"]["assessment_accuracy"] == 1.0
    assert report["summary"]["risk_accuracy"] == 1.0
    assert report["summary"]["evidence_grounding"] == 1.0
    assert report["summary"]["status_preservation"] == 1.0


def test_unsupported_evidence_reference_is_rejected():
    case = next(c for c in load_cases() if c["case_id"] == "EV-004")
    result = {
        "status_preserved": True,
        "field_assessments": [{
            "field_name": "shaft_material",
            "assessment": "UNSUPPORTED",
            "risk": "HIGH",
            "evidence_refs": [{"page": 3, "line": 99, "quote": "Shaft: A276-410"}],
        }],
    }
    score = score_case(case, result)
    assert score["assessment_correct"] is True
    assert score["risk_correct"] is True
    assert score["evidence_grounded"] is False


def test_summary_handles_empty_scores():
    assert summarize([])["cases"] == 0
