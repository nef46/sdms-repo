"""EncryptionStrategy -- Strategy Pattern.

Intent
------
Define a family of encryption algorithms, encapsulate each one, and make
them interchangeable.  ``RealDocumentService`` varies its cipher without
any change to its own source code.

Why this matters for SDMS
-------------------------
NFR-01 mandates AES-256 encryption at rest.  The coursework also
anticipates future migration paths (e.g., ChaCha20 or post-quantum
ciphers).  Placing the algorithm behind an abstract interface turns a
cipher swap into a configuration change rather than a rewrite.

Design principles applied
-------------------------
* Open/Closed   -- new ciphers are added by subclassing
  ``EncryptionStrategy`` without touching ``RealDocumentService``.
* Liskov substitution -- any strategy can replace ``AES256Strategy`` so
  long as it honours the abstract contract.
* Low coupling   -- callers depend only on the abstract
  ``EncryptionStrategy``, never on a concrete cipher.
* High cohesion  -- each strategy owns exactly one cipher and nothing else.

Refactoring note (BEFORE / AFTER)
---------------------------------
BEFORE::

    # document_service.py -- pre-refactor
    from cryptography.fernet import Fernet

    class RealDocumentService(DocumentService):
        def upload_file(self, doc, user_id):
            key = load_key_from_config()
            doc.content = Fernet(key).encrypt(doc.content)  # tight coupling
            self._repo[doc.doc_id] = doc
            return True

AFTER::

    # document_service.py -- post-refactor
    class RealDocumentService(DocumentService, Subject):
        def __init__(self, encryption: EncryptionStrategy = None):
            self._cipher = encryption or NoOpStrategy()

        def upload_file(self, doc, user_id):
            doc.content = self._cipher.encrypt(doc.content)  # open/closed
            self._repo[doc.doc_id] = doc
            return True

The service no longer knows *how* encryption happens, only *that* it does.
This satisfies NFR-01 while keeping ``RealDocumentService`` closed to
modification as algorithms evolve.

Authors
-------
Konstantinos Tserkezidis -- Phase 3, Design & Architecture owner.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# Abstract strategy
# ---------------------------------------------------------------------------

class EncryptionStrategy(ABC):
    """Abstract strategy -- concrete subclasses implement a single cipher."""

    @abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        """Return the ciphertext for *plaintext*."""

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Return the plaintext for *ciphertext*."""


# ---------------------------------------------------------------------------
# Concrete strategy: AES-256-GCM  (NFR-01)
# ---------------------------------------------------------------------------

class AES256Strategy(EncryptionStrategy):
    """AES-256-GCM concrete strategy satisfying NFR-01.

    GCM mode provides *authenticated* encryption, meaning any tampering
    with the ciphertext is detected on decryption -- a hard requirement
    for the SDMS audit trail.

    The 12-byte nonce is generated per-call via ``os.urandom`` (the size
    recommended by NIST SP 800-38D) and prepended to the ciphertext so
    that ``decrypt`` can recover it without an external side-channel.

    Parameters
    ----------
    key : bytes
        A 32-byte (256-bit) symmetric key.  The caller is responsible for
        sourcing this from a secure key store (e.g. AWS KMS, HashiCorp
        Vault).  **Never** hard-code it.
    """

    _NONCE_SIZE = 12  # 96-bit nonce -- GCM best practice

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
            raise ValueError("AES-256 requires a 32-byte (256-bit) key")
        # Refactoring note: the first draft stored the raw key on self._key,
        # which leaked via repr() / __dict__.  Now only the AESGCM primitive
        # is kept; the key is consumed here and never stored.
        self._aesgcm = AESGCM(bytes(key))

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(self._NONCE_SIZE)
        ct = self._aesgcm.encrypt(nonce, plaintext, associated_data=None)
        return nonce + ct  # prepend nonce so decrypt() can split it off

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < self._NONCE_SIZE:
            raise ValueError("Ciphertext too short -- nonce missing")
        nonce, ct = blob[: self._NONCE_SIZE], blob[self._NONCE_SIZE :]
        return self._aesgcm.decrypt(nonce, ct, associated_data=None)


# ---------------------------------------------------------------------------
# Test double: NoOpStrategy
# ---------------------------------------------------------------------------

class NoOpStrategy(EncryptionStrategy):
    """Pass-through strategy used in unit tests.

    Isolates business logic from cryptographic concerns so that tests stay
    fast and deterministic.  **Never** register this in production.
    """

    def encrypt(self, plaintext: bytes) -> bytes:
        return plaintext

    def decrypt(self, ciphertext: bytes) -> bytes:
        return ciphertext
