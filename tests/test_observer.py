"""Unit tests for the Observer pattern (Subject / Observer / NotificationService).

Covers
------
* ``NotificationService`` receives events published by ``Subject``.
* ``attach`` is idempotent -- attaching the same observer twice delivers
  only one copy of each event.
* ``detach`` stops an observer from receiving further events.
* Detaching from inside ``update`` does not break the broadcast loop.
* The email gateway (when supplied) is called exactly once per event.

Author: Konstantinos Tserkezidis -- Phase 3.
"""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pytest

from sdms.patterns.observer import (
    DocumentEvent,
    NotificationService,
    Observer,
    Subject,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _RecordingObserver(Observer):
    """Minimal concrete observer that records events for assertions."""
    def __init__(self) -> None:
        self.received: List[DocumentEvent] = []

    def update(self, event: DocumentEvent) -> None:
        self.received.append(event)


@pytest.fixture()
def subject() -> Subject:
    return Subject()


@pytest.fixture()
def sample_event() -> DocumentEvent:
    return DocumentEvent(
        event_type="reserved",
        document_id=42,
        actor_user_id=7,
        details="Q4 audit spreadsheet",
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_notification_service_receives_event(
    subject: Subject, sample_event: DocumentEvent
) -> None:
    svc = NotificationService()
    subject.attach(svc)
    subject.notify(sample_event)
    assert svc.sent == [sample_event]


def test_multiple_observers_all_notified(
    subject: Subject, sample_event: DocumentEvent
) -> None:
    a, b = NotificationService(), _RecordingObserver()
    subject.attach(a)
    subject.attach(b)
    subject.notify(sample_event)
    assert len(a.sent) == 1
    assert len(b.received) == 1


def test_attach_is_idempotent(
    subject: Subject, sample_event: DocumentEvent
) -> None:
    obs = _RecordingObserver()
    subject.attach(obs)
    subject.attach(obs)  # duplicate -- must be ignored
    subject.notify(sample_event)
    assert len(obs.received) == 1


def test_detach_stops_updates(
    subject: Subject, sample_event: DocumentEvent
) -> None:
    obs = _RecordingObserver()
    subject.attach(obs)
    subject.detach(obs)
    subject.notify(sample_event)
    assert obs.received == []


def test_self_detach_during_update_is_safe(
    subject: Subject, sample_event: DocumentEvent
) -> None:
    """An observer that detaches itself inside update() must not crash."""
    class _Once(Observer):
        def __init__(self) -> None:
            self.calls = 0
        def update(self, event: DocumentEvent) -> None:
            self.calls += 1
            subject.detach(self)

    once = _Once()
    subject.attach(once)
    subject.notify(sample_event)
    subject.notify(sample_event)  # second broadcast must NOT reach _Once
    assert once.calls == 1


def test_email_gateway_invoked_when_provided(sample_event: DocumentEvent) -> None:
    gateway = MagicMock()
    svc = NotificationService(email_gateway=gateway)
    svc.update(sample_event)
    gateway.send_email.assert_called_once()
    call_kwargs = gateway.send_email.call_args.kwargs
    assert "Document 42 reserved" in call_kwargs["subject"]
    assert "User 7 reserved document 42" in call_kwargs["body"]


def test_event_is_immutable(sample_event: DocumentEvent) -> None:
    """Frozen dataclass must raise on attribute mutation."""
    with pytest.raises(AttributeError):
        sample_event.event_type = "hacked"  # type: ignore[misc]
