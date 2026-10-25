# Sutreva — Hackathon Submission Architecture

## Product positioning

Sutreva is an evidence-backed engineering document intelligence application for OEM equipment audits.

It turns an OEM datasheet into a traceable engineering audit result by combining:

1. document/evidence extraction;
2. NVIDIA Nemotron-assisted structured understanding;
3. deterministic engineering rules and configurable audit templates;
4. exception detection and human review;
5. exportable audit records.

## Why Nebius + NVIDIA is material

The planned demonstration should make a clear distinction between model contribution and deterministic engineering control.

### Nemotron contribution

- understand semi-structured engineering language;
- extract candidate field values from document evidence;
- support reasoning over document context where deterministic parsing alone is insufficient;
- return structured candidates to the validation layer.

### Sutreva control layer

- normalize evidence;
- apply deterministic PDF/checkbox overrides;
- validate structured outputs;
- compare values against engineering standards/templates;
- surface exceptions and missing information;
- preserve reviewer disposition and audit traceability.

### Nebius role

- provide the hosted inference path through Token Factory;
- keep the model invocation behind a provider abstraction;
- provide the runtime foundation used by the submitted build.

## Demonstration narrative

The final demo should be organized around one realistic engineering audit case:

```text
1. Upload OEM datasheet
2. Select equipment audit template
3. Sutreva constructs document evidence
4. Nemotron assists structured extraction/reasoning
5. Sutreva validates and compares against engineering rules
6. Exceptions are highlighted with evidence
7. Reviewer checks the evidence
8. Final audit record is exported
```

The final script should be short enough to fit within the official three-minute video limit and should explicitly name Nebius Token Factory and the NVIDIA model used.

## Evaluation evidence to collect

Before submission, collect measured evidence for:

- field-level extraction accuracy;
- evidence-presence accuracy;
- structured-output validity;
- deterministic override precision on known cases;
- audit status accuracy;
- review/disposition outcomes;
- latency and failure rate;
- model/provider usage for representative cases.

Do not report a metric until the underlying test procedure and sample population are recorded.

## Evaluation design

Sutreva uses two complementary evaluation layers:

1. **Sutreva domain benchmark** — measures field assessment correctness, risk classification, exact evidence-reference grounding, and preservation of deterministic engineering status across representative audit cases.
2. **NeMo Evaluator regression smoke test** — measures the hosted Nemotron endpoint with a standard language benchmark to provide a reproducible model/provider health signal.

The two layers are intentionally not conflated: generic language-model scores do not stand in for engineering-document evidence quality.
