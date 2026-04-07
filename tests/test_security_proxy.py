"""Unit tests for the Proxy pattern (SecurityProxy)."""
import pytest

from sdms.models.document import Document
from sdms.patterns.audit_logger import AuditLogger
from sdms.patterns.security_proxy import SecurityProxy
from sdms.patterns.user_factory import UserFactory


def setup_function(_):
    AuditLogger._reset()


def _make_proxy_with_users():
    proxy = SecurityProxy()
    admin = UserFactory.create_user(1, "Admin", "a@x.com", "admin")
    viewer = UserFactory.create_user(2, "View", "v@x.com", "viewer")
    proxy.register_user(admin)
    proxy.register_user(viewer)
    return proxy, admin, viewer


def test_admin_can_upload():
    proxy, admin, _ = _make_proxy_with_users()
    doc = Document(doc_id=1, name="report.pdf", owner_id=admin.user_id, content=b"hi")
    assert proxy.upload_file(doc, admin.user_id) is True


def test_viewer_cannot_upload():
    proxy, _, viewer = _make_proxy_with_users()
    doc = Document(doc_id=2, name="x.pdf", owner_id=viewer.user_id)
    with pytest.raises(PermissionError):
        proxy.upload_file(doc, viewer.user_id)


def test_unsafe_filename_rejected():
    proxy, admin, _ = _make_proxy_with_users()
    bad = Document(doc_id=3, name="../etc/passwd", owner_id=admin.user_id)
    with pytest.raises(ValueError):
        proxy.upload_file(bad, admin.user_id)


def test_search_blocks_injection_attempt():
    proxy, _, _ = _make_proxy_with_users()
    with pytest.raises(ValueError):
        proxy.search("'; DROP TABLE users; --")


def test_actions_are_audited():
    proxy, admin, _ = _make_proxy_with_users()
    doc = Document(doc_id=4, name="ok.txt", owner_id=admin.user_id, content=b"x")
    proxy.upload_file(doc, admin.user_id)
    proxy.download_file(4, admin.user_id)
    actions = [e.action_type for e in AuditLogger().get_logs()]
    assert "UPLOAD" in actions and "DOWNLOAD" in actions


def test_rate_limit_enforced():
    proxy = SecurityProxy(rate_limit=2)
    admin = UserFactory.create_user(99, "A", "a@x.com", "admin")
    proxy.register_user(admin)
    doc = Document(doc_id=10, name="a.txt", owner_id=99, content=b"x")
    proxy.upload_file(doc, 99)
    proxy.upload_file(doc, 99)
    with pytest.raises(PermissionError):
        proxy.upload_file(doc, 99)
