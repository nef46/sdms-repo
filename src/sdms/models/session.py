"""Session model.

Maps to ``Session`` in the SDS class diagram.

OOP / cohesion notes
--------------------
The class is responsible for one thing only: tracking the lifetime of a
single authenticated session. Storage, authentication and authorisation are
handled elsewhere, which keeps cohesion high and coupling low.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    session_id: int
    user_id: int
    ip_address: str
    login_time: datetime = field(default_factory=datetime.utcnow)
    logout_time: Optional[datetime] = None

    @classmethod
    def create_session(cls, session_id: int, user_id: int, ip_address: str) -> "Session":
        """Factory helper that mirrors ``createSession()`` on the diagram."""
        return cls(session_id=session_id, user_id=user_id, ip_address=ip_address)

    def is_active(self) -> bool:
        """True while the session has not been closed."""
        return self.logout_time is None

    def close(self) -> None:
        """End the session by stamping the logout time."""
        self.logout_time = datetime.utcnow()
