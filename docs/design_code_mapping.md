# Design–Code Mapping (SIS Section 3 reference)

Maps Phase 2 SDS UML elements to Phase 3 source code constructs.
Konstantinos will cite this in the SIS document.

---

## Class Diagram → Source Code

| SDS UML Element | Source File | Code Construct |
|---|---|---|
| `<<interface>> DocumentService` | `services/document_service.py` | `class DocumentService(ABC)` |
| `RealDocumentService` | `services/document_service.py` | `class RealDocumentService(DocumentService, Subject)` |
| `SecurityProxy` (Proxy Pattern) | `patterns/security_proxy.py` | `class SecurityProxy(DocumentService)` |
| `AuditLogger` (Singleton) | `patterns/audit_logger.py` | `class AuditLogger` + `__new__` + Lock |
| `UserFactory` (Factory Method) | `patterns/user_factory.py` | `UserFactory.create_user()` + `_registry` |
| `EncryptionStrategy` (Strategy) | `patterns/encryption_strategy.py` | `class EncryptionStrategy(ABC)` |
| `AES256Strategy` | `patterns/encryption_strategy.py` | `class AES256Strategy(EncryptionStrategy)` |
| `<<interface>> Observer` | `patterns/observer.py` | `class Observer(ABC)` |
| `Subject` mixin | `patterns/observer.py` | `class Subject` with `attach/detach/notify` |
| `NotificationService` (Observer) | `patterns/observer.py` | `class NotificationService(Observer)` |
| `User` + `Admin/Editor/Viewer` | `models/user.py` | `class User` → `Admin(User)`, `Editor(User)`, `Viewer(User)` |
| `Document` | `models/document.py` | `@dataclass Document` |
| `Session` | `models/session.py` | `@dataclass Session` |
| `AuditLog` | `models/audit_log.py` | `@dataclass AuditLog` |
| `Report` | `models/report.py` | `@dataclass Report` |

---

## Strategy Pattern Mapping

| UML Element | Code Construct |
|---|---|
| `<<interface>> EncryptionStrategy` | `class EncryptionStrategy(ABC)` with `encrypt()`, `decrypt()` |
| `AES256Strategy : EncryptionStrategy` | `class AES256Strategy(EncryptionStrategy)` |
| `NoOpStrategy` (test double) | `class NoOpStrategy(EncryptionStrategy)` |
| Association: `DocumentService → EncryptionStrategy` | `self._cipher` field in `RealDocumentService.__init__` |
| `encrypt(data): bytes` | `AES256Strategy.encrypt(self, plaintext: bytes) -> bytes` |

---

## Observer Pattern Mapping

| UML Element | Code Construct |
|---|---|
| `<<interface>> Observer` | `class Observer(ABC)` with abstract `update(event)` |
| `Subject` | `class Subject` mixin with `_observers: List[Observer]` |
| `RealDocumentService` as subject | `class RealDocumentService(DocumentService, Subject)` |
| `NotificationService` as observer | `class NotificationService(Observer)` |
| Trigger on state change (FR-05) | `self.notify(DocumentEvent(...))` in `upload/download/reserve/release` |
| Association `0..*` Subject → Observer | `self._observers: List[Observer]` |

---

## Sequence Diagram → Code (UC-02 Upload Document)

| SDS Sequence Step | Code Location |
|---|---|
| 1. User submits file | `upload_file(doc, user_id)` entry point |
| 2. SecurityProxy intercepts | `SecurityProxy.upload_file` → `_sanitize` + `_check_permission` |
| 3. Encrypt content (NFR-01) | `doc.content = self._encrypt(doc.content)` |
| 4. Persist to repository | `self._repo[doc.doc_id] = doc` |
| 5. Audit log (FR-07) | Logged by `SecurityProxy` via `AuditLogger.log_action` |
| 6. Notify team (FR-05) | `self.notify(DocumentEvent(event_type="uploaded", ...))` |

---

## Requirements Traceability

| Requirement | Realised by | File |
|---|---|---|
| FR-02 | File sanitisation | `SecurityProxy._sanitize` |
| FR-05 | Email on reserve/release | `NotificationService.update` |
| FR-07 | Append-only audit trail | `AuditLogger.log_action` |
| FR-08 | IP block after threshold | `SecurityProxy._check_rate_limit` |
| NFR-01 | AES-256 at rest | `AES256Strategy.encrypt` |
| NFR-04 | < 2 s sanitisation latency | `SecurityProxy` validation pipeline |
