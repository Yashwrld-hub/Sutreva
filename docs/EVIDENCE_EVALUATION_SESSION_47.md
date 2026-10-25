# Sutreva — Evidence Intelligence + Evaluation Session 47

## Purpose
Session 47 makes the evidence-grounded Nemotron pass measurable and traceable.

## Evidence contract
Each field assessment can now include `evidence_refs` with exact `page`, `line`, and `quote` values copied from Sutreva's deterministic source evidence. The model is explicitly instructed not to invent references. The UI renders these references alongside the assessment.

## Domain benchmark
`evals/sutreva_evidence_benchmark.jsonl` contains eight representative cases covering:

- supported values;
- missing values;
- ambiguous values;
- unsupported extractions;
- supported-but-rule-violating values;
- deterministic checkbox evidence;
- conflicting-document evidence;
- numeric boundary values.

`evals/sutreva_eval.py` scores assessment accuracy, risk accuracy, evidence grounding, and status preservation. The self-check uses the benchmark's golden labels to verify the scorer itself.

## NeMo Evaluator relationship
`evals/nemo_evaluator.sutreva.yaml` is a generic model-regression smoke configuration against the same Nebius Token Factory + Nemotron endpoint. The domain-specific benchmark remains a Sutreva-owned scorer because engineering evidence quality is not adequately represented by generic language benchmarks.

## Reproducibility
The reasoning layer records prompt version `sutreva.reasoning.v2`, model/provider identity, and `deterministic_source_map` evidence mode.
