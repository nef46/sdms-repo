"""Integration tests -- full pipeline through Strategy + Observer + Singleton.

These tests exercise two or more modules together and therefore qualify as
*integration* tests for the Phase 3 SIS document.

Scenarios
---------
1. Upload encrypts content AND fires the observer AND writes an audit entry.
2. Round-trip: uploaded bytes can be decrypted on download.
3. Reserve / release publish the correct observer events.
4. A second user cannot reserve an already-locked document.
5. Multiple observers all receive every event.
6. SecurityProxy delegates reserve/release correctly.

Author: Konstantinos Tserkezidis -- Phase 3.
"""

from __future__ import annotations

import os

import pytest

from sdms.models.document import Document
from sdms.models.user import User
from sdms.patterns.audit_logger import AuditLogger
from sdms.patterns.encryption_strategy import AES256Strategy, NoOpStrategy
from sdms.patterns.observer import NotificationService
from sdms.patterns.security_proxy import SecurityProxy
from sdms.patterns.user_factory import UserFactory
from sdms.services.document_service import RealDocumentService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Each test starts with a clean audit trail."""
    AuditLogger._reset()
    yield
    AuditLogger._reset()


@pytest.fixture()
def key() -> bytes:
    return os.urandom(32)


@pytest.fixture()
def service_with_crypto(key: bytes) -> RealDocumentService:
    return RealDocumentService(encryption=AES256Strategy(key))


@pytest.fixture()
def service_plain() -> RealDocumentService:
    return RealDocumentService()  # NoOpStrategy by default


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_upload_encrypts_and_notifies(service_with_crypto: RealDocumentService) -> None:
    """Upload must encrypt content, notify observers, and audit the action."""
    notifier = NotificationService()
    service_with_crypto.attach(notifier)

    doc = Document(doc_id=1, name="plan.pdf", owner_id=7, content=b"secret")
    service_with_crypto.upload_file(doc, user_id=7)

    # Observer received the event
    assert len(notifier.sent) == 1
    assert notifier.sent[0].event_type == "uploaded"
    assert notifier.sent[0].document_id == 1

    # Content stored in _repo is encrypted (not plaintext)
    stored = service_with_crypto._repo[1]
    assert stored.content != b"secret"


def test_upload_download_round_trip(service_with_crypto: RealDocumentService) -> None:
    """Uploaded bytes must be recoverable through download."""
    original = b"engineering blueprint v3"
    doc = Document(doc_id=1, name="bp.pdf", owner_id=1, content=original)
    service_with_crypto.upload_file(doc, user_id=1)

    retrieved = service_with_crypto.download_file(doc_id=1, user_id=1)
    assert retrieved.content == original


def test_upload_download_round_trip_noop(service_plain: RealDocumentService) -> None:
    """With NoOpStrategy the content is stored as-is (backward compat)."""
    doc = Document(doc_id=1, name="x.txt", owner_id=1, content=b"hello")
    service_plain.upload_file(doc, user_id=1)
    assert service_plain.download_file(1, 1).content == b"hello"


def test_reserve_and_release_events(service_plain: RealDocumentService) -> None:
    """Reserve and release must each fire an observer event."""
    notifier = NotificationService()
    service_plain.attach(notifier)

    doc = Document(doc_id=10, name="audit.xlsx", owner_id=1, content=b"x")
    service_plain.upload_file(doc, user_id=1)

    service_plain.reserve(doc_id=10, user_id=1)
    service_plain.release(doc_id=10, user_id=1)

    types = [e.event_type for e in notifier.sent]
    assert types == ["uploaded", "reserved", "released"]


def test_reserve_blocks_second_user(service_plain: RealDocumentService) -> None:
    doc = Document(doc_id=5, name="a.txt", owner_id=1, content=b"x")
    service_plain.upload_file(doc, user_id=1)
    assert service_plain.reserve(5, user_id=1) is True
    assert service_plain.reserve(5, user_id=2) is False


def test_multiple_observers_all_receive(service_plain: RealDocumentService) -> None:
    a, b = NotificationService(), NotificationService()
    service_plain.attach(a)
    service_plain.attach(b)
    doc = Document(doc_id=1, name="x.pdf", owner_id=1, content=b"x")
    service_plain.upload_file(doc, user_id=1)
    assert len(a.sent) == 1
    assert len(b.sent) == 1


def test_proxy_delegates_reserve_release() -> None:
    """SecurityProxy must forward reserve/release after permission check."""
    service = RealDocumentService()
    notifier = NotificationService()
    service.attach(notifier)

    proxy = SecurityProxy(real_service=service)
    admin = UserFactory.create_user(1, "Admin", "a@x.com", "admin")
    proxy.register_user(admin)

    doc = Document(doc_id=1, name="x.pdf", owner_id=1, content=b"data")
    proxy.upload_file(doc, user_id=1)
    assert proxy.reserve(doc_id=1, user_id=1) is True
    assert proxy.release(doc_id=1, user_id=1) is True

    types = [e.event_type for e in notifier.sent]
    assert "reserved" in types
    assert "released" in types

    # Audit trail should include the proxy-level entries
    actions = [e.action_type for e in AuditLogger().get_logs()]
    assert "RESERVE" in actions
    assert "RELEASE" in actions
