"""Design pattern implementations for SDMS Phase 3.

Five patterns from the SDS are implemented in this package:

* ``SecurityProxy``      : Proxy pattern wrapping ``RealDocumentService``.
* ``AuditLogger``        : Singleton holding the in-memory audit trail.
* ``UserFactory``        : Factory Method that creates User subclasses by role.
* ``AES256Strategy``     : Strategy pattern for AES-256-GCM encryption.
* ``NotificationService``: Observer pattern for document event notifications.
"""

from .security_proxy import SecurityProxy
from .audit_logger import AuditLogger
from .user_factory import UserFactory
from .encryption_strategy import AES256Strategy, EncryptionStrategy, NoOpStrategy
from .observer import DocumentEvent, NotificationService, Observer, Subject

__all__ = [
    "SecurityProxy",
    "AuditLogger",
    "UserFactory",
    "AES256Strategy",
    "EncryptionStrategy",
    "NoOpStrategy",
    "DocumentEvent",
    "NotificationService",
    "Observer",
    "Subject",
]
