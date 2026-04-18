"""Observer Pattern -- Subject / Observer / NotificationService.

Intent
------
Allow a one-to-many dependency between objects so that when the subject's
state changes (e.g. a document is uploaded, reserved or released) all
attached observers are notified automatically.

Why this matters for SDMS
-------------------------
FR-05 requires team members to be notified via email when a document is
reserved for editing.  The alternative -- ``RealDocumentService`` directly
calling ``EmailService.send(...)`` -- would couple the two modules and
make it hard to add further listeners later (an audit stream, a Slack
connector, a push-notification worker, etc.).

Design principles applied
-------------------------
* Low coupling  -- ``RealDocumentService`` depends only on the abstract
  ``Observer`` contract, not on concrete notification channels.
* High cohesion -- each observer has a single responsibility.
* Open/Closed   -- new observers are added via ``subject.attach(obs)``
  with no edits to the subject itself.

Refactoring note (BEFORE / AFTER)
---------------------------------
BEFORE::

    # document_service.py -- pre-refactor
    class RealDocumentService(DocumentService):
        def upload_file(self, doc, user_id):
            self._repo[doc.doc_id] = doc
            EmailService.send(                             # hard-coded
                to=team_members(doc.doc_id),
                subject="Document uploaded",
                body=f"User {user_id} uploaded {doc.name}",
            )
            return True

AFTER::

    # document_service.py -- post-refactor
    class RealDocumentService(DocumentService, Subject):
        def upload_file(self, doc, user_id):
            self._repo[doc.doc_id] = doc
            self.notify(DocumentEvent(                     # decoupled
                event_type="uploaded",
                document_id=doc.doc_id,
                actor_user_id=user_id,
            ))
            return True

``NotificationService`` (and any future observer) attaches at wire-up
time.  Adding a Slack observer is now a one-liner in the composition root.

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
    event is fanned out to multiple observers -- an observer that mutated
    the event would corrupt the view seen by the next observer in the list.
    """
    event_type: str          # "uploaded" | "downloaded" | "reserved" | "released"
    document_id: int
    actor_user_id: int
    details: str = ""


# ---------------------------------------------------------------------------
# Abstract observer
# ---------------------------------------------------------------------------

class Observer(ABC):
    """Abstract observer -- concrete classes react to ``DocumentEvent``s."""

    @abstractmethod
    def update(self, event: DocumentEvent) -> None:
        """Called by the subject for each published event."""


# ---------------------------------------------------------------------------
# Subject mixin
# ---------------------------------------------------------------------------

class Subject:
    """Mixin that gives any class ``attach`` / ``detach`` / ``notify``.

    Any class that inherits from ``Subject`` gains a private observer
    registry and a safe broadcast method.  ``notify`` iterates over a
    *copy* of the observer list so that an observer may safely ``detach``
    itself from inside ``update`` without raising a RuntimeError.
    """

    def __init__(self) -> None:
        self._observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        # Refactoring note: using identity (``is``) rather than equality
        # (``==``) because dataclass observers compare equal by field
        # values, which would incorrectly prevent attaching two distinct
        # NotificationService instances with the same initial state.
        if not any(obs is observer for obs in self._observers):
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers[:] = [obs for obs in self._observers if obs is not observer]

    def notify(self, event: DocumentEvent) -> None:
        # Refactoring note: the first draft iterated self._observers
        # directly, which raised RuntimeError when an observer detached
        # itself inside update().  Copying the list decouples iteration
        # from membership changes.
        for obs in list(self._observers):
            obs.update(event)


# ---------------------------------------------------------------------------
# Concrete observer: NotificationService
# ---------------------------------------------------------------------------

@dataclass
class NotificationService(Observer):
    """Concrete observer -- emits email alerts via the SMTP adapter.

    In the demo and unit-test environment outbound emails are captured in
    the ``sent`` list so tests can assert on them without touching a real
    SMTP server.

    Parameters
    ----------
    email_gateway : object, optional
        Any object exposing ``send_email(subject, body) -> None``.
        When omitted the observer records events but does not attempt I/O.
    """

    email_gateway: Optional[object] = None
    sent: List[DocumentEvent] = field(default_factory=list)

    def update(self, event: DocumentEvent) -> None:
        self.sent.append(event)
        if self.email_gateway is not None:
            subj, body = self._format(event)
            self.email_gateway.send_email(subject=subj, body=body)

    @staticmethod
    def _format(event: DocumentEvent) -> Tuple[str, str]:
        subj = f"SDMS: Document {event.document_id} {event.event_type}"
        body = (
            f"User {event.actor_user_id} {event.event_type} "
            f"document {event.document_id}. {event.details}"
        ).strip()
        return subj, body
