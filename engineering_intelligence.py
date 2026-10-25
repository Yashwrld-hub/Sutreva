"""Deterministic engineering exception & coupled-physics analysis for Sutreva.

This layer translates authoritative audit statuses AND cross-parameter physics
relationships (e.g., NPSHA - NPSHR cavitation margin, Design vs Operating
Pressure/Temperature envelopes, Motor vs Rated Power sizing margin) into
engineering-facing exceptions, impacts, and review actions. It never mutates
the authoritative row status and never treats LLM output as an approval decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from domain_rules import domain_context_for_field, get_domain_profile


_STATUS_META = {
    "MISSING": {
        "category": "MISSING_REQUIRED_DATA",
        "default_severity": "HIGH",
        "impact": "Required engineering input is unavailable for verification.",
        "action": "Verify the source document and obtain the missing parameter before approval.",
    },
    "MISMATCHED": {
        "category": "SPECIFICATION_MISMATCH",
        "default_severity": "CRITICAL",
        "impact": "The extracted specification does not satisfy the configured engineering requirement.",
        "action": "Review the source value against the governing specification and resolve the deviation.",
    },
    "OUT OF RANGE": {
        "category": "LIMIT_EXCEEDED",
        "default_severity": "CRITICAL",
        "impact": "The extracted numeric value exceeds a configured engineering limit.",
        "action": "Verify units and source data, then resolve the limit exceedance before approval.",
    },
    "NEEDS_REVIEW": {
        "category": "EVIDENCE_GAP",
        "default_severity": "MEDIUM",
        "impact": "The source evidence does not clearly support the extracted value or uses a qualitative statement.",
        "action": "Open the cited source evidence and complete human verification.",
    },
}

_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass(frozen=True)
class EngineeringException:
    field_name: str
    field: str
    status: str
    category: str
    severity: str
    impact: str
    recommended_action: str
    required: bool
    extracted_value: Any = None
    evidence: dict[str, Any] | None = None
    ai_assessment: str | None = None
    ai_risk: str | None = None
    profile_id: str | None = None
    profile_label: str | None = None
    domain_role: str | None = None
    domain_focus: str | None = None
    domain_priority: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoupledPhysicsCheck:
    check_id: str
    title: str
    status: str  # "PASS" | "REVIEW" | "VIOLATION"
    formula: str
    measured_summary: str
    engineering_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EngineeringIntelligenceReport:
    exception_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_severity: str
    blocking: bool
    exceptions: list[dict[str, Any]]
    domain_profile_id: str | None = None
    domain_profile_label: str | None = None
    coupled_checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _max_severity(*values: str | None) -> str:
    valid = [v for v in values if v in _SEVERITY_ORDER]
    return max(valid, key=lambda x: _SEVERITY_ORDER[x], default="LOW")


def _ai_lookup(ai_assessment: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in ai_assessment or []:
        if isinstance(item, dict) and item.get("field_name"):
            lookup[str(item["field_name"])] = item
    return lookup


def _numeric_by_concept(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Extract normalized float values keyed by lowercase field_name tokens."""
    values: dict[str, float] = {}
    for row in rows:
        fname = str(row.get("field_name") or "").lower()
        val = row.get("normalized_value", row.get("extracted_value"))
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            values[fname] = float(val)
    return values


def evaluate_coupled_engineering_checks(rows: list[dict[str, Any]]) -> list[CoupledPhysicsCheck]:
    """Run deterministic cross-parameter physics & envelope checks across any equipment type."""
    nums = _numeric_by_concept(rows)
    checks: list[CoupledPhysicsCheck] = []

    # 1. Cavitation Margin: NPSHA - NPSHR >= 1.0 m (Pumps)
    npsha = next((v for k, v in nums.items() if "npsha" in k or ("npsh" in k and "avail" in k)), None)
    npshr = next((v for k, v in nums.items() if "npshr" in k or ("npsh" in k and "req" in k)), None)
    if npsha is not None and npshr is not None:
        margin = round(npsha - npshr, 3)
        passed = margin >= 1.0
        checks.append(
            CoupledPhysicsCheck(
                check_id="cavitation_npsh_margin",
                title="Cavitation Margin (NPSHA − NPSHR)",
                status="PASS" if passed else "VIOLATION",
                formula="NPSHA - NPSHR >= 1.0 m",
                measured_summary=f"NPSHA ({npsha} m) - NPSHR ({npshr} m) = {margin} m",
                engineering_note=(
                    "Satisfies minimum 1.0 m suction head margin."
                    if passed
                    else "Suction head margin is below 1.0 m; high risk of pump cavitation."
                ),
            )
        )

    # 2. Driver Sizing Margin: Motor Power >= 1.10 * Rated Absorbed Power (Pumps, Agitators, Compressors, Fin Fans)
    p_rated = next((v for k, v in nums.items() if k in {"rated_power_kw", "absorbed_power_kw", "brake_power_kw", "shaft_power_kw"}), None)
    p_motor = next((v for k, v in nums.items() if "motor" in k and ("power" in k or "rating" in k or "kw" in k)), None)
    if p_rated is not None and p_motor is not None and p_rated > 0:
        ratio = p_motor / p_rated
        passed = ratio >= 1.10
        checks.append(
            CoupledPhysicsCheck(
                check_id="driver_sizing_margin",
                title="Driver Nameplate Margin (P_motor / P_rated)",
                status="PASS" if passed else "REVIEW",
                formula="P_motor >= 1.10 * P_rated",
                measured_summary=f"{p_motor} kW / {p_rated} kW = {ratio:.1%}",
                engineering_note=(
                    "Driver rating provides >= 10% margin over rated absorbed shaft power."
                    if passed
                    else "Driver margin is < 10% over rated shaft power; verify API/ISO motor sizing margin."
                ),
            )
        )

    # 3. Pressure Envelope: Design Pressure (or MAWP) >= Operating Pressure (Columns, Reactors, Heat Exchangers, Vessels, Pumps)
    p_design = next((v for k, v in nums.items() if ("design" in k or "mawp" in k) and "pressure" in k), None)
    p_oper = next((v for k, v in nums.items() if ("operating" in k or "discharge" in k) and "pressure" in k), None)
    if p_design is not None and p_oper is not None:
        passed = p_design >= p_oper
        checks.append(
            CoupledPhysicsCheck(
                check_id="pressure_containment_envelope",
                title="Pressure Containment Envelope (P_design >= P_operating)",
                status="PASS" if passed else "VIOLATION",
                formula="P_design (MAWP) >= P_operating",
                measured_summary=f"Design: {p_design} vs Operating: {p_oper}",
                engineering_note=(
                    "Design pressure / MAWP safely bounds operating pressure."
                    if passed
                    else "Operating pressure exceeds stated design pressure / MAWP!"
                ),
            )
        )

    # 4. Thermal Envelope: Design Temperature >= Operating Temperature (Columns, Reactors, Heat Exchangers, Vessels, Seals)
    t_design = next((v for k, v in nums.items() if "design" in k and "temp" in k), None)
    t_oper = next((v for k, v in nums.items() if ("operating" in k or "pumping" in k) and "temp" in k), None)
    if t_design is not None and t_oper is not None:
        passed = t_design >= t_oper
        checks.append(
            CoupledPhysicsCheck(
                check_id="thermal_containment_envelope",
                title="Thermal Design Envelope (T_design >= T_operating)",
                status="PASS" if passed else "VIOLATION",
                formula="T_design >= T_operating",
                measured_summary=f"Design: {t_design} vs Operating: {t_oper}",
                engineering_note=(
                    "Design temperature safely bounds operating temperature."
                    if passed
                    else "Operating temperature exceeds stated design temperature!"
                ),
            )
        )

    return checks


def analyze_engineering_rows(
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
    *,
    ai_assessments: list[dict[str, Any]] | None = None,
) -> EngineeringIntelligenceReport:
    """Translate audit rows into deterministic engineering exceptions and coupled physics checks."""
    schema_by_name = {str(f.get("field_name")): f for f in schema.get("fields", [])}
    profile = get_domain_profile(schema)
    ai_by_name = _ai_lookup(ai_assessments)
    exceptions: list[EngineeringException] = []

    for row in rows:
        status = str(row.get("status") or "").upper()
        meta = _STATUS_META.get(status)
        if not meta:
            continue

        field_name = str(row.get("field_name") or "")
        field_cfg = schema_by_name.get(field_name, {})
        ai = ai_by_name.get(field_name, {})
        ai_risk = str(ai.get("risk") or "").upper() or None
        severity = _max_severity(meta["default_severity"], ai_risk)
        domain = domain_context_for_field(schema, field_name)
        exceptions.append(
            EngineeringException(
                field_name=field_name,
                field=str(row.get("field") or field_cfg.get("label") or field_name),
                status=status,
                category=str(meta["category"]),
                severity=severity,
                impact=str(meta["impact"]),
                recommended_action=str(meta["action"]),
                required=bool(field_cfg.get("required", row.get("required", True))),
                extracted_value=row.get("extracted_value"),
                evidence=row.get("evidence") or None,
                ai_assessment=str(ai.get("assessment") or "").upper() or None,
                ai_risk=ai_risk,
                profile_id=domain.get("profile_id"),
                profile_label=domain.get("profile_label"),
                domain_role=domain.get("domain_role"),
                domain_focus=domain.get("domain_focus"),
                domain_priority=domain.get("domain_priority"),
            )
        )

    counts = {key: 0 for key in _SEVERITY_ORDER}
    for exc in exceptions:
        counts[exc.severity] += 1

    coupled = evaluate_coupled_engineering_checks(rows)
    overall = _max_severity(*(e.severity for e in exceptions)) if exceptions else "LOW"
    blocking = any(e.severity == "CRITICAL" or e.status in {"MISMATCHED", "OUT OF RANGE"} for e in exceptions)
    return EngineeringIntelligenceReport(
        exception_count=len(exceptions),
        critical_count=counts["CRITICAL"],
        high_count=counts["HIGH"],
        medium_count=counts["MEDIUM"],
        low_count=counts["LOW"],
        overall_severity=overall,
        blocking=blocking,
        exceptions=[e.to_dict() for e in exceptions],
        domain_profile_id=profile.profile_id if profile else None,
        domain_profile_label=profile.label if profile else None,
        coupled_checks=[c.to_dict() for c in coupled],
    )
