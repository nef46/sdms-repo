"""Smoke tests for the simpler domain models."""
from sdms.models.session import Session
from sdms.models.document import Document
from sdms.models.report import Report
from sdms.services.otp_service import OTPService


def test_session_lifecycle():
    s = Session.create_session(1, 42, "127.0.0.1")
    assert s.is_active()
    s.close()
    assert not s.is_active()


def test_document_lock_release():
    doc = Document(doc_id=1, name="a.txt", owner_id=1)
    assert doc.reserve(1) is True
    assert doc.reserve(2) is False  # already locked
    assert doc.release(2) is False
    assert doc.release(1) is True


def test_document_observer_hook():
    events = []
    doc = Document(doc_id=2, name="b.txt", owner_id=1)
    doc.attach(lambda d, e: events.append(e))
    doc.upload(b"hi")
    doc.download()
    assert events == ["uploaded", "downloaded"]


def test_otp_validate_then_expire():
    svc = OTPService()
    code = svc.generate_otp(1)
    assert svc.validate_otp(1, code) is True
    # Second validation must fail because the code was consumed.
    assert svc.validate_otp(1, code) is False


def test_report_generate_contains_entries():
    r = Report(report_id=1, generated_by=42)
    body = r.generate(["entry-A", "entry-B"])
    assert "entry-A" in body and "entry-B" in body
    assert r.download() == body.encode("utf-8")
