"""AuditLog entry.

Maps to the ``AuditLog`` class on the SDS class diagram. This is a passive
data record. The active component that writes and reads these entries is
``AuditLogger`` (see ``patterns/audit_logger.py``), which is a Singleton.

Splitting the entry from the logger is deliberate: it gives the system high
cohesion (each class has one job) and low coupling (consumers that only
need to read entries don't have to import the singleton).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AuditLog:
    audit_id: int
    user_id: int
    action_type: str
    document_id: Optional[int] = None
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.isoformat(timespec='seconds')}] "
            f"user={self.user_id} action={self.action_type} "
            f"doc={self.document_id} :: {self.details}"
        )
