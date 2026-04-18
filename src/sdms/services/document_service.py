"""DocumentService interface and concrete implementation.

The interface matches the ``<<interface>> DocumentService`` block on the SDS
class diagram.  The Proxy pattern (see ``patterns/security_proxy.py``)
implements the same interface so the proxy and the real service are
substitutable, satisfying the Liskov principle.

Coupling: callers depend on the abstract ``DocumentService`` ABC, not on
the concrete class.  This is the textbook way to achieve low coupling.

Refactoring history (Konstantinos -- Phase 3)
---------------------------------------------
R1.  Added ``reserve`` and ``release`` to the abstract interface so that
     ``SecurityProxy`` can wrap them with permission checks (FR-05).
R2.  Injected ``EncryptionStrategy`` into ``RealDocumentService`` via the
     constructor -- dependency inversion replaces a hard-coded Fernet call
     (NFR-01).  Defaults to ``NoOpStrategy`` to keep existing tests green.
R3.  Made ``RealDocumentService`` a ``Subject`` (Observer mixin) so that
     ``NotificationService`` is notified on every state-mutating action
     (FR-05, FR-07).
R4.  Extracted ``_encrypt`` and ``_decrypt`` helpers from the upload /
     download paths to raise cohesion (composed-method pattern).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models.document import Document
from ..patterns.encryption_strategy import EncryptionStrategy, NoOpStrategy
from ..patterns.observer import DocumentEvent, Subject


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class DocumentService(ABC):
    """Abstract document service contract.

    Both ``RealDocumentService`` and ``SecurityProxy`` honour this ABC,
    which is the basis of the Proxy pattern (Gamma et al., 1994).
    ``reserve`` and ``release`` were added in Phase 3 to support FR-05.
    """

    @abstractmethod
    def upload_file(self, doc: Document, user_id: int) -> bool: ...

    @abstractmethod
    def download_file(self, doc_id: int, user_id: int) -> Document: ...

    @abstractmethod
    def search(self, query: str) -> List[Document]: ...

    # --- Added in Phase 3 (Konstantinos) for FR-05 ---
    @abstractmethod
    def reserve(self, doc_id: int, user_id: int) -> bool: ...

    @abstractmethod
    def release(self, doc_id: int, user_id: int) -> bool: ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------

class RealDocumentService(DocumentService, Subject):
    """In-memory implementation wired to Strategy + Observer.

    Inherits from ``Subject`` (mixin) so it can notify observers, and from
    ``DocumentService`` (ABC) so ``SecurityProxy`` can wrap it.

    Parameters
    ----------
    encryption : EncryptionStrategy, optional
        Active cipher.  Defaults to ``NoOpStrategy`` so that callers that
        do not need encryption (or existing tests) continue to work with
        no changes.  In production, inject ``AES256Strategy(key)``.
    """

    def __init__(
        self, encryption: Optional[EncryptionStrategy] = None
    ) -> None:
        Subject.__init__(self)   # initialise observer registry
        self._repo: Dict[int, Document] = {}
        # Refactoring note R2: previously there was no cipher at all;
        # encryption was either missing or hard-coded inline.  Now the
        # strategy is injected; NoOpStrategy preserves backward compat.
        self._cipher: EncryptionStrategy = encryption or NoOpStrategy()

    # ---- upload --------------------------------------------------------

    def upload_file(self, doc: Document, user_id: int) -> bool:
        # Refactoring note R4: encrypt in a helper, not inline.
        doc.content = self._encrypt(doc.content)
        self._repo[doc.doc_id] = doc

        # Refactoring note R3: fan-out replaces a direct EmailService call.
        self.notify(DocumentEvent(
            event_type="uploaded",
            document_id=doc.doc_id,
            actor_user_id=user_id,
            details=doc.name,
        ))
        return True

    # ---- download ------------------------------------------------------

    def download_file(self, doc_id: int, user_id: int) -> Document:
        if doc_id not in self._repo:
            raise FileNotFoundError(f"Document {doc_id} not found")
        doc = self._repo[doc_id]
        # Return a copy with decrypted content so the stored blob stays
        # encrypted at rest (NFR-01).
        decrypted = Document(
            doc_id=doc.doc_id,
            name=doc.name,
            owner_id=doc.owner_id,
            content=self._decrypt(doc.content),
            version=doc.version,
            locked_by=doc.locked_by,
            created_at=doc.created_at,
        )
        self.notify(DocumentEvent(
            event_type="downloaded",
            document_id=doc_id,
            actor_user_id=user_id,
        ))
        return decrypted

    # ---- search --------------------------------------------------------

    def search(self, query: str) -> List[Document]:
        q = query.lower()
        return [d for d in self._repo.values() if q in d.name.lower()]

    # ---- reserve / release  (FR-05 -- Phase 3) ------------------------

    def reserve(self, doc_id: int, user_id: int) -> bool:
        doc = self._repo.get(doc_id)
        if doc is None:
            raise FileNotFoundError(f"Document {doc_id} not found")
        if not doc.reserve(user_id):
            return False
        self.notify(DocumentEvent(
            event_type="reserved",
            document_id=doc_id,
            actor_user_id=user_id,
        ))
        return True

    def release(self, doc_id: int, user_id: int) -> bool:
        doc = self._repo.get(doc_id)
        if doc is None:
            raise FileNotFoundError(f"Document {doc_id} not found")
        if not doc.release(user_id):
            return False
        self.notify(DocumentEvent(
            event_type="released",
            document_id=doc_id,
            actor_user_id=user_id,
        ))
        return True

    # ---- private helpers -----------------------------------------------

    def _encrypt(self, data: bytes) -> bytes:
        """Extracted during refactor R4 to keep upload_file focused."""
        return self._cipher.encrypt(data)

    def _decrypt(self, data: bytes) -> bytes:
        """Extracted during refactor R4 to keep download_file focused."""
        return self._cipher.decrypt(data)
