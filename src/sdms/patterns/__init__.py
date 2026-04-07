"""Design pattern implementations for SDMS Phase 3.

Three of the five patterns from the SDS are implemented here:

* ``SecurityProxy``  : Proxy pattern wrapping ``RealDocumentService``.
* ``AuditLogger``    : Singleton holding the in-memory audit trail.
* ``UserFactory``    : Factory Method that creates User subclasses by role.
"""
from .security_proxy import SecurityProxy
from .audit_logger import AuditLogger
from .user_factory import UserFactory

__all__ = ["SecurityProxy", "AuditLogger", "UserFactory"]
