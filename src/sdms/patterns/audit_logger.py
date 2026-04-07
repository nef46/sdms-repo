"""AuditLogger -- Singleton pattern.

Why Singleton here
------------------
Every component in SDMS that mutates state (login, upload, download, report
generation) needs to write to the same audit trail. A Singleton guarantees
that they all share one in-memory store, so a report generated five seconds
later sees the events those components produced.

Implementation notes
--------------------
The Singleton is enforced by overriding ``__new__``. A class-level lock
makes the construction thread-safe, which matters because the SDS sequence
diagrams show concurrent upload/download flows.

OOP and coupling
----------------
* Encapsulation: the underlying list is private; consumers go through
  ``log_action`` and ``get_logs``.
* Low coupling: the logger depends only on ``AuditLog`` (a plain dataclass)
  and the standard library, so it can be reused in any other module.
* High cohesion: the class has one responsibility -- own the audit trail.
"""
from __future__ import annotations

import threading
from typing import List, Optional

from ..models.audit_log import AuditLog


class AuditLogger:
    _instance: Optional["AuditLogger"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AuditLogger":
        # Double-checked locking: cheap fast path, safe slow path.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._entries = []  # type: ignore[attr-defined]
                    cls._instance._next_id = 1   # type: ignore[attr-defined]
        return cls._instance

    # ----- Public API ---------------------------------------------------
    def log_action(
        self,
        user_id: int,
        action_type: str,
        document_id: Optional[int] = None,
        details: str = "",
    ) -> AuditLog:
        entry = AuditLog(
            audit_id=self._next_id,
            user_id=user_id,
            action_type=action_type,
            document_id=document_id,
            details=details,
        )
        self._entries.append(entry)
        self._next_id += 1
        return entry

    def get_logs(self) -> List[AuditLog]:
        # Return a copy so external callers cannot mutate internal state.
        return list(self._entries)

    def archive_logs(self) -> List[AuditLog]:
        archived = list(self._entries)
        self._entries.clear()
        return archived

    # Test helper -- not part of the public API.
    @classmethod
    def _reset(cls) -> None:
        with cls._lock:
            cls._instance = None
