"""Deterministic conflict detection for extracted engineering parameters."""

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Conflict:
    field_name: str
    values: tuple[Any, ...]
    record_indexes: tuple[int, ...]
    reason: str = "Multiple distinct values found"

    def to_dict(self):
        return asdict(self)

def _key(value: Any):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ("number", round(float(value), 9))
    if value is None:
        return ("none", None)
    return (type(value).__name__, str(value).strip().casefold())

def _record_value(record: Any):
    normalized = getattr(record, "normalized_value", None) if hasattr(record, "normalized_value") else record.get("normalized_value")
    value = getattr(record, "value", None) if hasattr(record, "value") else record.get("value")
    return normalized if normalized is not None else value

def detect_conflicts(records: Iterable[Any]) -> list[Conflict]:
    grouped = {}
    for idx, record in enumerate(records):
        field = getattr(record, "field_name", None) or record.get("field_name")
        value = _record_value(record)
        if value is None or value == "":
            continue
        grouped.setdefault(field, []).append((idx, value))
    conflicts = []
    for field, items in grouped.items():
        distinct = {}
        for idx, value in items:
            distinct.setdefault(_key(value), (value, []))[1].append(idx)
        if len(distinct) > 1:
            values = tuple(item[0] for item in distinct.values())
            indexes = tuple(idx for item in distinct.values() for idx in item[1])
            conflicts.append(Conflict(field, values, indexes))
    return conflicts
