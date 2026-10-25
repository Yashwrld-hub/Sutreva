"""
ai_orchestration.py — Sutreva's evidence-grounded AI intelligence layer.

The orchestration layer sits between the engineering audit engine and the
model-provider boundary. It deliberately does not decide engineering status;
that remains deterministic in core.py. Nemotron is used here for a second,
source-grounded reasoning pass that explains risk/ambiguity without changing
the configured rule outcome.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ai_provider import DEFAULT_MODEL_NAME, get_model_provider


GenerateFn = Callable[[str, str], str]
REASONING_PROMPT_VERSION = "sutreva.reasoning.v2"

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class IntelligenceResult:
    """Structured result from the evidence-grounded reasoning stage."""

    enabled: bool
    provider: str = ""
    model: str = ""
    status: str = "SKIPPED"
    overall_flag: str = "NONE"
    document_flags: list[str] = field(default_factory=list)
    field_assessments: list[dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""
    error: str | None = None
    prompt_version: str = REASONING_PROMPT_VERSION
    evidence_mode: str = "deterministic_source_map"

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "overall_flag": self.overall_flag,
            "document_flags": list(self.document_flags),
            "field_assessments": list(self.field_assessments),
            "raw_output": self.raw_output,
            "error": self.error,
            "prompt_version": self.prompt_version,
            "evidence_mode": self.evidence_mode,
        }


def _build_reasoning_prompt(rows: list[dict[str, Any]], schema: dict[str, Any], extracted: dict[str, Any]) -> str:
    row_by_name = {r.get("field_name"): r for r in rows if r.get("field_name")}
    audit_fields = []
    for field_spec in schema.get("fields", []):
        name = field_spec.get("field_name")
        row = row_by_name.get(name, {})
        audit_fields.append({
            "field_name": name,
            "label": field_spec.get("label"),
            "rule": {k: field_spec[k] for k in ("acceptable_values", "expected_value", "min_value", "max_value") if k in field_spec},
            "extracted_value": extracted.get(name),
            "normalized_value": row.get("normalized_value", extracted.get(name)),
            "deterministic_status": row.get("status"),
            "evidence": row.get("evidence") or None,
            "conflict": row.get("conflict") or None,
        })

    return f"""You are Sutreva's evidence-grounded engineering review assistant.

Your job is a SECOND reasoning pass after deterministic comparison. You must NOT
change the configured engineering status and must NOT invent missing values.
Use ONLY the supplied extracted values, configured rules, and source evidence.

For each field, assess whether the evidence clearly supports the extracted value
and identify ambiguity or conflict. A missing value is not a guess opportunity.

Return ONLY one JSON object with this exact structure:
{{
  "overall_flag": "NONE" | "REVIEW",
  "document_flags": ["short factual flag", ...],
  "field_assessments": [
    {{
      "field_name": "...",
      "assessment": "SUPPORTED" | "AMBIGUOUS" | "UNSUPPORTED" | "MISSING",
      "risk": "LOW" | "MEDIUM" | "HIGH",
      "reason": "one concise evidence-grounded sentence",
      "evidence_refs": [{{"page": 1, "line": 1, "quote": "exact source line copied from supplied evidence"}}]
    }}
  ]
}}

Audited engineering fields, rules, statuses, and source evidence:
{json.dumps(audit_fields, ensure_ascii=False, indent=2)}

Evidence rules:
- Copy evidence_refs only from the supplied source evidence for that field.
- Each reference must use the supplied page, line, and exact source text.
- If no source evidence exists, evidence_refs must be [].
- Never invent page/line numbers or paraphrase a quote.

Do not output any value that is not supported by the supplied material. Return JSON only.
"""


def _parse_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Reasoning model returned an empty response.")

    cleaned = _THINK_BLOCK_RE.sub("", text).strip() or text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        candidate_positions = [m.start() for m in re.finditer(r"\{", cleaned)]
        if not candidate_positions:
            raise ValueError("Reasoning model response was not valid JSON.") from None
        parsed = None
        for start in reversed(candidate_positions):
            try:
                candidate, _ = decoder.raw_decode(cleaned[start:])
                if isinstance(candidate, dict):
                    parsed = candidate
                    break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            raise ValueError("Reasoning model response was not valid JSON.") from None

    if not isinstance(parsed, dict):
        raise ValueError("Reasoning model response must be a JSON object.")
    return parsed


def _normalize_result(payload: dict[str, Any]) -> tuple[str, list[str], list[dict[str, Any]]]:
    overall = str(payload.get("overall_flag") or "NONE").upper()
    if overall not in {"NONE", "REVIEW"}:
        overall = "REVIEW"

    flags = payload.get("document_flags") or []
    if not isinstance(flags, list):
        flags = [str(flags)]
    flags = [str(x).strip() for x in flags if str(x).strip()]

    raw_assessments = payload.get("field_assessments") or []
    if not isinstance(raw_assessments, list):
        raw_assessments = []

    assessments = []
    for item in raw_assessments:
        if not isinstance(item, dict):
            continue
        assessment = str(item.get("assessment") or "MISSING").upper()
        risk = str(item.get("risk") or "LOW").upper()
        if assessment not in {"SUPPORTED", "AMBIGUOUS", "UNSUPPORTED", "MISSING"}:
            assessment = "AMBIGUOUS"
        if risk not in {"LOW", "MEDIUM", "HIGH"}:
            risk = "MEDIUM"
        refs = item.get("evidence_refs") or []
        if not isinstance(refs, list):
            refs = [refs]
        evidence_refs = []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            page = ref.get("page")
            line = ref.get("line")
            quote = str(ref.get("quote") or ref.get("text") or "").strip()
            if page is None or line is None or not quote:
                continue
            evidence_refs.append({"page": page, "line": line, "quote": quote})
        assessments.append({
            "field_name": str(item.get("field_name") or ""),
            "assessment": assessment,
            "risk": risk,
            "reason": str(item.get("reason") or "").strip(),
            "evidence_refs": evidence_refs,
        })
    return overall, flags, assessments


def run_engineering_reasoning(
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
    extracted: dict[str, Any],
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    generate: GenerateFn | None = None,
) -> IntelligenceResult:
    """Run a non-authoritative reasoning pass over an existing audit result."""
    provider = get_model_provider()
    generate_fn = generate or (lambda prompt, model: provider.generate(prompt, model_name=model))

    try:
        raw = generate_fn(_build_reasoning_prompt(rows, schema, extracted), model_name)
        payload = _parse_json_object(raw)
        overall, flags, assessments = _normalize_result(payload)
        return IntelligenceResult(
            enabled=True,
            provider=getattr(provider, "name", "unknown"),
            model=model_name,
            status="COMPLETED",
            overall_flag=overall,
            document_flags=flags,
            field_assessments=assessments,
            raw_output=raw,
        )
    except Exception as exc:  # noqa: BLE001
        return IntelligenceResult(
            enabled=True,
            provider=getattr(provider, "name", "unknown"),
            model=model_name,
            status="FAILED",
            error=str(exc),
        )
