# Sutreva Hackathon Demo Runbook — Session 53

## Story

Sutreva turns an OEM engineering datasheet into an evidence-backed audit that a
mechanical engineer can review, challenge, and sign off.

## 180-second sequence

### 0–20 seconds — Problem

Show the landing page. Explain that OEM datasheets are information-dense, while
auditors need field-level compliance, source evidence, and a defensible review trail.

### 20–45 seconds — Start

Click **Open audit workspace**. Select the centrifugal-pump template. Show the
explicit engineering fields/rules.

### 45–95 seconds — Audit

Load the prepared synthetic datasheet or a permitted real document. Run the audit
with the Nemotron reasoning pass enabled.

Show:

- extracted field
- authoritative audit status
- page/line evidence
- Nemotron rationale

### 95–125 seconds — Engineering intelligence

Show one exception. Explain that deterministic rules decide the audit status; the
intelligence layer adds context, severity, engineering impact, and an action.

### 125–150 seconds — Human review

Open Review Queue. Record a disposition and learning signal. Emphasize that human
review remains authoritative and feedback is captured for evaluation rather than
used for silent auto-training.

### 150–170 seconds — Evaluation flywheel

Show the curated/evaluation view and explain that reviewer feedback becomes a
versioned regression case for evidence grounding and model/prompt evaluation.

### 170–180 seconds — Nebius/NVIDIA proof

Show the runtime/provider information and state plainly:

**Sutreva application → Nebius Token Factory → NVIDIA Nemotron**

Do not claim a live run unless the run actually used the configured live provider.
