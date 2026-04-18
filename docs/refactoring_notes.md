# Refactoring Notes — Konstantinos (Phase 3)

Evidence of refactoring decisions for the SIS document (Section 3).

---

## R1 — Add `reserve` / `release` to `DocumentService` ABC

**Motivation.** FR-05 requires document reservation with email alerts.
The original interface only had `upload_file`, `download_file`, and
`search`, so `SecurityProxy` could not intercept reservation calls.

**Change.** Added two abstract methods to `DocumentService`.  Both
`RealDocumentService` and `SecurityProxy` implement them.

**Principle.** Interface segregation, Liskov substitution.

---

## R2 — Inject the cipher via Strategy (dependency inversion)

**Before.**

```python
from cryptography.fernet import Fernet

class RealDocumentService(DocumentService):
    def upload_file(self, doc, user_id):
        key = load_key_from_config()
        doc.content = Fernet(key).encrypt(doc.content)  # tight coupling
        self._repo[doc.doc_id] = doc
        return True
```

**After.**

```python
class RealDocumentService(DocumentService, Subject):
    def __init__(self, encryption=None):
        self._cipher = encryption or NoOpStrategy()

    def upload_file(self, doc, user_id):
        doc.content = self._cipher.encrypt(doc.content)
        self._repo[doc.doc_id] = doc
        ...
```

**Principle.** Open/Closed, dependency inversion, testability.

---

## R3 — Replace direct `EmailService.send` with Observer fan-out

**Before.**

```python
def upload_file(self, doc, user_id):
    self._repo[doc.doc_id] = doc
    EmailService.send(to=team(doc.doc_id), subject="Uploaded", ...)
    return True
```

**After.**

```python
def upload_file(self, doc, user_id):
    doc.content = self._encrypt(doc.content)
    self._repo[doc.doc_id] = doc
    self.notify(DocumentEvent(event_type="uploaded", ...))
    return True
```

**Principle.** Low coupling, Open/Closed, single responsibility.

---

## R4 — Extract `_encrypt` / `_decrypt` helpers

**Motivation.** `upload_file` was mixing validation, encryption,
persistence, and notification in one block (~30 lines).

**Change.** Moved the cipher call into `_encrypt` and `_decrypt` one-
liners, turning `upload_file` into a four-step orchestration method.

**Principle.** High cohesion, composed-method pattern.

---

## R5 — Copy observer list before broadcasting

**Motivation.** Iterating `self._observers` directly raised
`RuntimeError: list changed size during iteration` when an observer
detached itself inside `update()`.

**Change.** `for obs in list(self._observers)` — iteration is now
decoupled from membership mutation.

**Evidence.** `test_self_detach_during_update_is_safe` reproduces and
guards against the original bug.

---

## R6 — Frozen `DocumentEvent` dataclass

**Motivation.** An observer that accidentally mutated the event would
corrupt the view seen by the next observer in the chain.

**Change.** `@dataclass(frozen=True)` — any mutation raises
`FrozenInstanceError`.

**Evidence.** `test_event_is_immutable` verifies the guard.

---

## R7 — Never store the raw AES key

**Motivation.** Storing the 32-byte key on `self._key` leaked it via
`repr()` and `__dict__` inspection.

**Change.** Only the `AESGCM` primitive is kept; the raw key is consumed
in `__init__` and discarded.

**Principle.** Principle of least privilege for sensitive material.
