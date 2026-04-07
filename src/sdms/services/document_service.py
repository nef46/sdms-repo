"""DocumentService interface and concrete implementation.

The interface matches the ``<<interface>> DocumentService`` block on the SDS
class diagram. The Proxy pattern (see ``patterns/security_proxy.py``)
implements the same interface so the proxy and the real service are
substitutable, satisfying the Liskov principle.

Coupling: callers depend on the abstract ``DocumentService`` ABC, not on
the concrete class. This is the textbook way to achieve low coupling.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from ..models.document import Document


class DocumentService(ABC):
    """Abstract document service contract."""

    @abstractmethod
    def upload_file(self, doc: Document, user_id: int) -> bool: ...

    @abstractmethod
    def download_file(self, doc_id: int, user_id: int) -> Document: ...

    @abstractmethod
    def search(self, query: str) -> List[Document]: ...


class RealDocumentService(DocumentService):
    """In-memory implementation. Persistence is out of scope for Phase 3."""

    def __init__(self) -> None:
        self._repo: Dict[int, Document] = {}

    def upload_file(self, doc: Document, user_id: int) -> bool:
        self._repo[doc.doc_id] = doc
        return True

    def download_file(self, doc_id: int, user_id: int) -> Document:
        if doc_id not in self._repo:
            raise FileNotFoundError(f"Document {doc_id} not found")
        return self._repo[doc_id]

    def search(self, query: str) -> List[Document]:
        q = query.lower()
        return [d for d in self._repo.values() if q in d.name.lower()]
