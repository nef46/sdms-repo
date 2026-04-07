"""Document model.

Maps to the ``DocumentSubject`` / ``Document`` family in the SDS class
diagram. The full Observer pattern from the SDS is summarised here as a
small notification hook to keep this Phase-3 implementation focused on the
three patterns owned by the lead developer (Proxy, Singleton, Factory).

Cohesion: this class only knows about a document's metadata, locking and
versioning. Persistence and security checks are intentionally left to the
``DocumentService`` and ``SecurityProxy`` layers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional


@dataclass
class Document:
    doc_id: int
    name: str
    owner_id: int
    content: bytes = b""
    version: int = 1
    locked_by: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    _observers: List[Callable[["Document", str], None]] = field(default_factory=list)

    # ----- Locking ------------------------------------------------------
    def get_lock_status(self) -> bool:
        return self.locked_by is not None

    def reserve(self, user_id: int) -> bool:
        """Lock the document for editing. Returns False if already locked."""
        if self.get_lock_status():
            return False
        self.locked_by = user_id
        self._notify("reserved")
        return True

    def release(self, user_id: int) -> bool:
        if self.locked_by != user_id:
            return False
        self.locked_by = None
        self._notify("released")
        return True

    # ----- Content ------------------------------------------------------
    def upload(self, content: bytes) -> None:
        self.content = content
        self.version += 1
        self._notify("uploaded")

    def download(self) -> bytes:
        self._notify("downloaded")
        return self.content

    # ----- Observer hook (lightweight) ---------------------------------
    def attach(self, observer: Callable[["Document", str], None]) -> None:
        self._observers.append(observer)

    def detach(self, observer: Callable[["Document", str], None]) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self, event: str) -> None:
        for obs in list(self._observers):
            obs(self, event)
