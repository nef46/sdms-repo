"""Observer Pattern -- DocumentService as Subject, NotificationService as Observer.

Intent
------
Allow a one-to-many dependency between objects so that when the subject's
state changes (e.g., a document is reserved or released), all attached
observers are notified automatically.

Why this matters for SDMS
-------------------------
FR-05 requires team members to be notified via email when a document is
reserved for editing. The alternative -- ``DocumentService`` directly
calling ``EmailService.send(...)`` -- would couple the two modules and
make it hard to add further listeners later (an audit stream, a Slack
connector, a push-notification worker, etc.).

Design principles applied
-------------------------
* Low coupling: ``DocumentService`` depends only on the abstract
  ``Observer`` contract, not on concrete notification channels.
* High cohesion: each observer has a single responsibility (email,
  analytics, ...).
* Open/Closed: new observers are added via ``subject.attach(...)`` with
  no edits to the subject itself.

Refactoring note (BEFORE / AFTER)
---------------------------------
BEFORE::

    # document_service.py -- pre-refactor
    class DocumentService:
        def reserve(self, doc_id, user):
            self._repo.lock(doc_id, user)
            EmailService.send(                                # hard-coded
                to=team_members(doc_id),
                subject="Doc reserved",
                body=f"{user} locked {doc_id}",
            )

AFTER::

    # document_service.py -- post-refactor
    class DocumentService(Subject):
        def reserve(self, doc_id, user):
            self._repo.lock(doc_id, user)
            self.notify(DocumentEvent(
                event_type="reserved",
                document_id=doc_id,
                actor_user_id=user.user_id,
            ))

``NotificationService`` (and any future observer) attaches at wire-up
time. Adding a Slack observer is now a one-liner in the composition root.

Authors
-------
Konstantinos Tserkezidis -- Phase 3, Design & Architecture owner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentEvent:
    """Immutable value object describing what happened to a document.

    Using a frozen dataclass guards against accidental mutation while the
    event is being fanned out to multiple observers -- an observer that
    mutated the event could otherwise corrupt the view seen by the next
    observer in the list.
    """

    event_type: str  # "reserved" | "released" | "uploaded" | "downloaded"
    document_id: int
    actor_user_id: int
    details: str = ""


# ---------------------------------------------------------------------------
# Abstract observer and subject mixin
# ---------------------------------------------------------------------------


class Observer(ABC):
    """Abstract observer -- concrete classes react to ``DocumentEvent``s."""

    @abstractmethod
    def update(self, event: DocumentEvent) -> None:
        """Called by the subject for each published event."""


class Subject:
    """Mixin providing ``attach`` / ``detach`` / ``notify`` semantics.

    Any class that inherits from ``Subject`` gains a private observer
    registry and a safe broadcast method. ``notify`` iterates over a copy
    of the observer list so that an observer may ``detach`` itself during
    ``update`` without raising ``RuntimeError: list changed size``.
    """

    def __init__(self) -> None:
        self._observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: DocumentEvent) -> None:
        # Refactor note: iterated over `self._observers` directly in the
        # first draft, which blew up when an observer detached itself
        # inside `update`. Copying the list decouples iteration from
        # membership changes.
        for obs in list(self._observers):
            obs.update(event)


# ---------------------------------------------------------------------------
# Concrete observer: NotificationService
# ---------------------------------------------------------------------------


@dataclass
class NotificationService(Observer):
    """Concrete observer -- emits email alerts via the SMTP adapter.

    In the demo and unit-test environment outbound emails are captured in
    ``sent`` so tests can assert on them without touching a real server.

    Parameters
    ----------
    email_gateway : Any, optional
        Object exposing ``send_email(subject: str, body: str) -> None``.
        When omitted the observer records events but does not attempt I/O
        -- useful for unit tests and the Phase 3 demo video.
    """

    email_gateway: Optional[object] = None
    sent: List[DocumentEvent] = field(default_factory=list)

    def update(self, event: DocumentEvent) -> None:
        self.sent.append(event)
        if self.email_gateway is not None:
            subject, body = self._format(event)
            self.email_gateway.send_email(subject=subject, body=body)

    @staticmethod
    def _format(event: DocumentEvent) -> Tuple[str, str]:
        subject = f"SDMS: Document {event.document_id} {event.event_type}"
        body = (
            f"User {event.actor_user_id} {event.event_type} "
            f"document {event.document_id}. {event.details}"
        ).strip()
        return subject, body
