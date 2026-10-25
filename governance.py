"""Lightweight governance primitives for Sutreva.

# Legacy product name retained for historical traceability: OEM Audit Copilot.

This module deliberately does not authenticate users; it records identity and
approval events supplied by an upstream authenticated application.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

ROLES = {"ADMIN", "AUDITOR", "REVIEWER", "APPROVER", "VIEWER"}
APPROVAL_DISPOSITIONS = {"ACCEPTED", "REJECTED", "WAIVED", "REQUIRES_ACTION"}

@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    display_name: str
    role: str

    def __post_init__(self):
        if not self.user_id.strip() or not self.display_name.strip():
            raise ValueError("user_id and display_name are required")
        if self.role.upper() not in ROLES:
            raise ValueError(f"Unsupported role: {self.role}")

@dataclass(frozen=True)
class ApprovalEvent:
    item_id: str
    actor: UserIdentity
    disposition: str
    comment: str = ""
    occurred_at: str = ""

    def __post_init__(self):
        if not self.item_id.strip():
            raise ValueError("item_id is required")
        if self.disposition.upper() not in APPROVAL_DISPOSITIONS:
            raise ValueError(f"Unsupported disposition: {self.disposition}")
        if not self.occurred_at:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc).isoformat())
