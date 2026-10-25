# Session 54 — Hackathon Demo Hardening

## Objective

Turn the hackathon demo into a reproducible, truthful end-to-end walkthrough using
one prepared synthetic centrifugal-pump PDF while keeping the normal live provider
path unchanged.

## Prepared fixture

`sample_data/hackathon_pump_demo.pdf`

The fixture is explicitly synthetic and intentionally contains two review triggers:

1. Rated Power = **720 kW** against a configured maximum of **700 kW**.
2. Shaft Material = **A479-316** against the configured expected value **A276-410**.

All other pump fields are valid for the selected template.

## Live demo path

1. Landing page → **Start hackathon demo**.
2. Audit type is set to **Centrifugal Pump Audit**.
3. Click **Load demo PDF**.
4. Confirm the source is the synthetic pump PDF.
5. Click **Run demo audit** with the Nemotron reasoning pass enabled.
6. Show the authoritative status, field evidence, engineering exceptions, and Nemotron evidence-backed rationale.
7. Open **Review Queue** and record a reviewer disposition + learning signal + optional gold label.
8. Run the recorded evaluation and show the evaluation gate.
9. Finish on the runtime provenance: **Sutreva → Nebius Token Factory → NVIDIA Nemotron**.

## Truthfulness rules

- The synthetic PDF is clearly labelled as synthetic.
- The offline rehearsal script uses deterministic model fixtures and never claims live inference.
- A live demo may only be described as live when `NEBIUS_API_KEY` is configured and the actual run completed through the provider.
- Historical patterns, engineering intelligence, reviewer feedback, and evaluation results never override the authoritative deterministic audit status.

## Offline rehearsal

Run:

```bash
python scripts/hackathon_demo_rehearsal.py
```

This exercises the real PDF evidence extractor, deterministic comparison, Nemotron
reasoning contract, engineering intelligence, review queue, feedback capture, and
evaluation flywheel without network access or API credits.

## Acceptance criteria

A submission rehearsal is considered healthy when:

- the demo PDF loads without manual file browsing;
- the audit completes and exposes page/line evidence;
- at least the two intentional review triggers appear;
- the review queue accepts a disposition and learning signal;
- the evaluation gate renders without changing the authoritative status;
- runtime provenance is visible and matches the configured provider/model.

## Extraction hardening discovered during rehearsal

The rehearsal caught a deterministic-text edge case: a narrative note such as
“field differs from configured expected value …” could look like a labelled source
line and trigger a material override. The matcher now rejects candidate values when
explicit narrative cues occur between the field alias and the configured candidate.
A regression test protects this behavior.
