"""SecurityProxy -- Proxy pattern.

Intent
------
Wrap ``RealDocumentService`` so that every call passes through:

1. Input validation and file sanitisation.
2. Permission and rate-limit checks.
3. Audit logging via the ``AuditLogger`` singleton.

The client only sees the ``DocumentService`` interface, so swapping the
real service for the proxy is transparent.  This is the textbook protective
proxy from Gamma et al. (1994).

OOP / cohesion / coupling
-------------------------
* The proxy *is-a* ``DocumentService``: it implements the same interface
  and forwards each call after the security check (Liskov substitution).
* It *has-a* ``RealDocumentService``: composition over inheritance.
* The audit dependency is the singleton, but the proxy holds it through a
  field rather than reaching into the global, so it can be mocked in
  tests.
* Single responsibility: this class only enforces security policy.  It
  knows nothing about how documents are stored.

Phase 3 changes (Konstantinos)
------------------------------
Added ``reserve`` and ``release`` pass-through methods so the proxy
continues to honour the full ``DocumentService`` interface after R1.
Both methods delegate to the real service after a permission check and
log the action through ``AuditLogger``.
"""

from __future__ import annotations

import re
import time

from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Set

from ..models.document import Document
from ..models.user import User
from ..services.document_service import DocumentService, RealDocumentService
from .audit_logger import AuditLogger

_FILENAME_RE = re.compile(r"^[A-Za-z0-9_\-. ]{1,128}$")


class SecurityProxy(DocumentService):

    def __init__(
        self,
        real_service: Optional[RealDocumentService] = None,
        rate_limit: int = 10,
        rate_window_seconds: int = 60,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self._service = real_service or RealDocumentService()
        self._audit = audit_logger or AuditLogger()
        self._users: Dict[int, User] = {}
        self._blocked_ips: Set[str] = set()
        self._rate_limit = rate_limit
        self._rate_window = rate_window_seconds
        self._calls: Dict[int, Deque[float]] = defaultdict(deque)

    # ----- Registration helpers ----------------------------------------

    def register_user(self, user: User) -> None:
        """The proxy needs to know which permissions each user has."""
        self._users[user.user_id] = user

    def block_ip(self, ip: str) -> None:
        self._blocked_ips.add(ip)

    # ----- DocumentService interface -----------------------------------

    def upload_file(self, doc: Document, user_id: int) -> bool:
        self._check_permission(user_id, "write")
        self._check_rate_limit(user_id)
        self._sanitize(doc)
        result = self._service.upload_file(doc, user_id)
        self._audit.log_action(
            user_id=user_id,
            action_type="UPLOAD",
            document_id=doc.doc_id,
            details=f"name={doc.name} size={len(doc.content)}",
        )
        return result

    def download_file(self, doc_id: int, user_id: int) -> Document:
        self._check_permission(user_id, "read")
        self._check_rate_limit(user_id)
        doc = self._service.download_file(doc_id, user_id)
        self._audit.log_action(
            user_id=user_id,
            action_type="DOWNLOAD",
            document_id=doc_id,
        )
        return doc

    def search(self, query: str) -> List[Document]:
        self._validate_input(query)
        results = self._service.search(query)
        self._audit.log_action(
            user_id=0,
            action_type="SEARCH",
            details=f"query={query!r} hits={len(results)}",
        )
        return results

    # --- Phase 3: reserve / release (Konstantinos) ---------------------

    def reserve(self, doc_id: int, user_id: int) -> bool:
        """Check write permission, delegate to real service, then audit."""
        self._check_permission(user_id, "write")
        result = self._service.reserve(doc_id, user_id)
        self._audit.log_action(
            user_id=user_id,
            action_type="RESERVE",
            document_id=doc_id,
        )
        return result

    def release(self, doc_id: int, user_id: int) -> bool:
        """Check write permission, delegate to real service, then audit."""
        self._check_permission(user_id, "write")
        result = self._service.release(doc_id, user_id)
        self._audit.log_action(
            user_id=user_id,
            action_type="RELEASE",
            document_id=doc_id,
        )
        return result

    # ----- Internal checks ---------------------------------------------

    def _check_permission(self, user_id: int, required: str) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise PermissionError(f"Unknown user {user_id}")
        if required not in user.permissions():
            self._audit.log_action(
                user_id=user_id,
                action_type="DENIED",
                details=f"missing permission {required}",
            )
            raise PermissionError(f"User {user_id} lacks {required}")

    def _check_rate_limit(self, user_id: int) -> None:
        now = time.monotonic()
        bucket = self._calls[user_id]
        cutoff = now - self._rate_window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self._rate_limit:
            self._audit.log_action(
                user_id=user_id,
                action_type="RATE_LIMIT",
                details=f"limit={self._rate_limit}/{self._rate_window}s",
            )
            raise PermissionError("Rate limit exceeded")
        bucket.append(now)

    def _sanitize(self, doc: Document) -> None:
        if not _FILENAME_RE.match(doc.name):
            raise ValueError(f"Unsafe filename: {doc.name!r}")
        if len(doc.content) > 50 * 1024 * 1024:
            raise ValueError("File exceeds 50 MB limit")

    def _validate_input(self, query: str) -> None:
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError("Invalid search query")
        if any(ch in query for ch in ("<", ">", ";", "--")):
            raise ValueError("Suspicious characters in query")
