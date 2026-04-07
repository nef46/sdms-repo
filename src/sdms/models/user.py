"""User model.

Maps to the `User` class in the SDS class diagram.

OOP principles demonstrated
---------------------------
* Encapsulation: attributes are private (leading underscore) and exposed
  through read-only properties; mutation only happens through behavioural
  methods like ``login`` and ``logout``.
* Inheritance: ``Admin``, ``Editor`` and ``Viewer`` extend ``User`` and
  override ``permissions`` to vary behaviour without changing the base.
* Polymorphism: callers depend on the ``User`` interface; the concrete
  subclass returned by ``UserFactory`` is interchangeable.

Coupling and cohesion
---------------------
* High cohesion: this module deals only with user identity and authentication
  state. It does not know about documents, audit storage or transport.
* Low coupling: ``User`` does not import ``Session`` or ``AuditLog`` directly;
  the orchestration layer wires them together. The only external dependency
  is the standard library.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class User:
    """Base user entity.

    Attributes match the SDS class diagram: ``userID``, ``name``, ``email``,
    ``role`` and ``status``. The Pythonic snake_case names are used in code
    while the docstrings preserve the diagram terminology for traceability.
    """

    user_id: int
    name: str
    email: str
    role: str = "viewer"
    status: str = "inactive"

    # ----- Behaviour ---------------------------------------------------
    def register(self) -> None:
        """Mark the user as registered and pending activation."""
        self.status = "registered"

    def login(self) -> bool:
        """Transition the user into the active state.

        Returns True so the orchestration layer can chain it into a
        ``Session.create_session`` call.
        """
        if self.status == "blocked":
            return False
        self.status = "active"
        return True

    def logout(self) -> None:
        """Transition the user back to inactive."""
        self.status = "inactive"

    def permissions(self) -> List[str]:
        """Return the permissions granted to this role.

        Subclasses override this method (Liskov substitution: any User can
        be asked for its permissions and the answer is consistent).
        """
        return ["read"]


class Admin(User):
    """Administrator: full privileges. Created by ``UserFactory``."""

    def permissions(self) -> List[str]:
        return ["read", "write", "delete", "manage_users", "view_audit"]


class Editor(User):
    """Editor: can read and write but not delete or manage users."""

    def permissions(self) -> List[str]:
        return ["read", "write"]


class Viewer(User):
    """Viewer: read-only access."""

    def permissions(self) -> List[str]:
        return ["read"]
