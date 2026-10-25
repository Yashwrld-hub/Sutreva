"""Validated, traceable extraction records for industrial audit workflows."""

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceRef:
    page: Optional[int] = None
    line: Optional[int] = None
    cell: Optional[str] = None
    quote: str = ""

@dataclass(frozen=True)
class ExtractionRecord:
    field_name: str
    value: Any = None
    source_unit: Optional[str] = None
    target_unit: Optional[str] = None
    evidence: Optional[EvidenceRef] = None
    confidence: Optional[float] = None
    verification_status: str = "UNVERIFIED"
    normalized_value: Any = None

    def to_dict(self):
        data = asdict(self)
        if self.evidence is None:
            data["evidence"] = None
        return data

VALID_STATUSES = {"UNVERIFIED", "VERIFIED", "NEEDS_REVIEW", "REJECTED"}

def validate_record(record: ExtractionRecord) -> list[str]:
    errors = []
    if not record.field_name.strip():
        errors.append("field_name must not be empty")
    if record.verification_status not in VALID_STATUSES:
        errors.append("invalid verification_status")
    if record.confidence is not None and not 0 <= record.confidence <= 1:
        errors.append("confidence must be between 0 and 1")
    if record.evidence:
        if record.evidence.page is not None and record.evidence.page < 1:
            errors.append("evidence page must be 1 or greater")
        if record.evidence.line is not None and record.evidence.line < 1:
            errors.append("evidence line must be 1 or greater")
    return errors

def records_from_extracted(
    extracted: dict,
    schema: dict,
    evidence_map: Optional[dict] = None,
    *,
    source_units: Optional[dict] = None,
    normalized_values: Optional[dict] = None,
    verification_status: str = "UNVERIFIED",
) -> list[ExtractionRecord]:
    evidence_map = evidence_map or {}
    source_units = source_units or {}
    normalized_values = normalized_values or {}
    records = []
    for field in schema.get("fields", []):
        name = field["field_name"]
        evidence = evidence_map.get(name)
        ref = None
        if evidence:
            ref = EvidenceRef(
                page=evidence.get("page"),
                line=evidence.get("line"),
                cell=evidence.get("cell"),
                quote=str(evidence.get("text") or evidence.get("quote") or ""),
            )
        records.append(ExtractionRecord(
            field_name=name,
            value=extracted.get(name),
            source_unit=source_units.get(name),
            target_unit=field.get("unit"),
            evidence=ref,
            verification_status=verification_status,
            normalized_value=normalized_values.get(name),
        ))
    return records
