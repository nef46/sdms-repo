"""UserFactory -- Factory Method pattern.

Intent
------
Decouple the *creation* of ``User`` subclasses from the code that *uses*
them. Callers ask the factory for a user with a given role and get back the
right concrete class (``Admin``, ``Editor``, ``Viewer``) without ever
mentioning those classes themselves.

Why this matters for SDMS
-------------------------
The registration use case (see SRS) accepts a role from the user form. If
that role string was wired straight into ``if/elif`` chains across the
codebase, every new role would touch every chain. The factory localises
that knowledge in one place, satisfying the Open/Closed principle.

OOP / cohesion / coupling
-------------------------
* Encapsulation: subclass selection is hidden inside ``create_user``.
* Polymorphism: the return type is the abstract ``User`` and callers
  treat it as such.
* Low coupling: callers depend on the factory + ``User`` interface and
  not on the concrete subclasses, so adding a new role is a one-line
  change in the registry below.
"""
from __future__ import annotations

from typing import Dict, Type

from ..models.user import Admin, Editor, User, Viewer


class UserFactory:
    """Factory Method that builds the correct ``User`` subclass."""

    _registry: Dict[str, Type[User]] = {
        "admin": Admin,
        "editor": Editor,
        "viewer": Viewer,
    }

    @classmethod
    def create_user(
        cls,
        user_id: int,
        name: str,
        email: str,
        role: str,
    ) -> User:
        role_key = role.lower().strip()
        try:
            klass = cls._registry[role_key]
        except KeyError as exc:
            raise ValueError(f"Unknown role: {role!r}") from exc
        user = klass(user_id=user_id, name=name, email=email, role=role_key)
        user.register()
        return user

    @classmethod
    def register_role(cls, role: str, klass: Type[User]) -> None:
        """Open/Closed: extend with new roles without editing this class."""
        cls._registry[role.lower().strip()] = klass
