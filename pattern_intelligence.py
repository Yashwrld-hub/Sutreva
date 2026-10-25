"""Historical engineering pattern context for Sutreva.

This layer reads prior *reviewed* findings and returns contextual signals for
current exceptions. Historical outcomes never change the current audit status,
severity, blocking state, or engineering-rule result.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable


_STATUS_CATEGORY = {
    "MISSING": "MISSING_REQUIRED_DATA",
    "MISMATCHED": "SPECIFICATION_MISMATCH",
    "OUT OF RANGE": "LIMIT_EXCEEDED",
    "NEEDS_REVIEW": "EVIDENCE_GAP",
}

_OPEN_DISPOSITIONS = {"", "OPEN", "REOPENED"}


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _canonical_disposition(value: Any) -> str | None:
    text = _norm(value).upper()
    return None if text in _OPEN_DISPOSITIONS else (text or None)


def _field_names_match(current: dict[str, Any], historical: Any) -> bool:
    current_name = _norm(current.get("field_name"))
    current_label = _norm(current.get("field"))
    historical_label = _norm(getattr(historical, "field", ""))
    return bool(current_name and current_name == historical_label) or (
        bool(current_label) and current_label == historical_label
    )


@dataclass(frozen=True)
class HistoricalPatternMatch:
    field_name: str
    field: str
    status: str
    category: str
    similar_case_count: int
    disposition_counts: dict[str, int]
    common_disposition: str | None
    pattern_strength: str
    prior_projects: int
    prior_runs: int
    historical_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strength(count: int) -> str:
    if count >= 5:
        return "HIGH"
    if count >= 2:
        return "MEDIUM"
    return "LOW"


def build_historical_pattern_matches(
    current_exceptions: Iterable[dict[str, Any]],
    review_items: Iterable[Any],
) -> list[HistoricalPatternMatch]:
    """Return historical context for current engineering exceptions.

    Only review items with a closed/non-open disposition are considered.
    Matching uses the current field and authoritative status; historical data
    is strictly advisory and never mutates the current exception.
    """
    closed_items = []
    for item in review_items:
        disposition = _canonical_disposition(getattr(item, "disposition", None))
        status = str(getattr(item, "status", "") or "").upper()
        if disposition and status:
            closed_items.append((item, disposition, status))

    matches: list[HistoricalPatternMatch] = []
    for current in current_exceptions:
        field_name = str(current.get("field_name") or "")
        field_label = str(current.get("field") or field_name)
        status = str(current.get("status") or "").upper()
        category = str(current.get("category") or _STATUS_CATEGORY.get(status, "OTHER"))
        similar = [
            (item, disposition)
            for item, disposition, prior_status in closed_items
            if prior_status == status and _field_names_match(current, item)
        ]
        if not similar:
            continue

        disposition_counts = Counter(disposition for _, disposition in similar)
        common_disposition = disposition_counts.most_common(1)[0][0] if disposition_counts else None
        prior_projects = {
            str(getattr(item, "project_id", "") or "")
            for item, _ in similar
            if str(getattr(item, "project_id", "") or "").strip()
        }
        prior_runs = {
            str(getattr(item, "run_id", "") or "")
            for item, _ in similar
            if str(getattr(item, "run_id", "") or "").strip()
        }
        count = len(similar)
        note = (
            f"{count} prior reviewed case(s) share this field/status. "
            f"Most common prior disposition: {common_disposition}. "
            "Historical context is advisory and does not change the current audit result."
        )
        matches.append(
            HistoricalPatternMatch(
                field_name=field_name,
                field=field_label,
                status=status,
                category=category,
                similar_case_count=count,
                disposition_counts=dict(disposition_counts),
                common_disposition=common_disposition,
                pattern_strength=_strength(count),
                prior_projects=len(prior_projects),
                prior_runs=len(prior_runs),
                historical_note=note,
            )
        )
    return matches


def history_summary(matches: Iterable[HistoricalPatternMatch]) -> dict[str, int]:
    """Aggregate simple UI counters from historical pattern matches."""
    values = list(matches)
    return {
        "fields_with_history": len(values),
        "similar_cases": sum(item.similar_case_count for item in values),
        "high_strength": sum(item.pattern_strength == "HIGH" for item in values),
    }
