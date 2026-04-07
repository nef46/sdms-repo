"""Unit tests for the Factory Method pattern."""
import pytest

from sdms.models.user import Admin, Editor, User, Viewer
from sdms.patterns.user_factory import UserFactory


def test_factory_returns_admin_for_admin_role():
    user = UserFactory.create_user(1, "Alice", "a@x.com", "admin")
    assert isinstance(user, Admin)
    assert "manage_users" in user.permissions()


def test_factory_returns_viewer_for_viewer_role():
    user = UserFactory.create_user(2, "Bob", "b@x.com", "Viewer")
    assert isinstance(user, Viewer)
    assert user.permissions() == ["read"]


def test_factory_marks_user_as_registered():
    user = UserFactory.create_user(3, "Cara", "c@x.com", "editor")
    assert user.status == "registered"


def test_factory_rejects_unknown_role():
    with pytest.raises(ValueError):
        UserFactory.create_user(4, "Dan", "d@x.com", "wizard")


def test_factory_is_open_closed_extensible():
    class Auditor(User):
        def permissions(self):
            return ["read", "view_audit"]

    UserFactory.register_role("auditor", Auditor)
    user = UserFactory.create_user(5, "Eve", "e@x.com", "auditor")
    assert isinstance(user, Auditor)
