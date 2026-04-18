"""EncryptionStrategy -- Strategy Pattern.

Intent
------
Define a family of encryption algorithms, encapsulate each one, and make
them interchangeable. The DocumentService varies encryption independently
from the code that uses it.

Why this matters for SDMS
-------------------------
NFR-01 mandates AES-256 at rest. The coursework also anticipates future
migration paths (e.g., ChaCha20 or post-quantum algorithms). Placing the
algorithm behind an interface turns a cipher swap into a configuration
change rather than a rewrite.

Design principles applied
-------------------------
* Open/Closed: new ciphers are added by subclassing ``EncryptionStrategy``
  without touching ``DocumentService``.
* Liskov substitution: any strategy can replace ``AES256Strategy`` so long
  as it honours the abstract interface.
* Low coupling: callers depend only on the abstract ``EncryptionStrategy``.
* High cohesion: each strategy owns a single cipher and nothing else.

Refactoring note (BEFORE / AFTER)
---------------------------------
BEFORE::

    # document_service.py -- pre-refactor
    from cryptography.fernet import Fernet
    class DocumentService:
        def upload(self, user, data):
            key = load_key_from_config()
            token = Fernet(key).encrypt(data)   # tight coupling
            self._repo.save(token)

AFTER::

    # document_service.py -- post-refactor
    class DocumentService:
        def __init__(self, repo, encryption: EncryptionStrategy):
            self._repo = repo
            self._cipher = encryption           # dependency inversion
        def upload(self, user, data):
            self._repo.save(self._cipher.encrypt(data))

The service no longer knows *how* encryption happens, only *that* it does.
This satisfies FR-02 and NFR-01 while keeping ``DocumentService`` closed
to modification as algorithms evolve.

Authors
-------
Konstantinos Tserkezidis -- Phase 3, Design & Architecture owner.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionStrategy(ABC):
    """Abstract strategy -- concrete subclasses implement a single cipher."""

    @abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        """Return the ciphertext for ``plaintext``."""

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Return the plaintext for ``ciphertext``."""


class AES256Strategy(EncryptionStrategy):
    """AES-256-GCM concrete strategy (satisfies NFR-01).

    GCM mode provides *authenticated* encryption, which detects tampering
    with the stored blob -- a hard requirement for the SDMS audit trail.

    The nonce is generated per-call using ``os.urandom`` (12 bytes, the
    size recommended by NIST SP 800-38D) and is prepended to the ciphertext
    so ``decrypt`` can recover it without an external side-channel.

    Parameters
    ----------
    key : bytes
        32-byte (256-bit) symmetric key. The caller is responsible for
        sourcing this from a secure key store (AWS KMS, HashiCorp Vault,
        or an equivalent). **Never** hard-code it.
    """

    _NONCE_SIZE = 12  # 96-bit nonce is GCM best practice

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
            raise ValueError("AES-256 requires a 32-byte (256-bit) key")
        # Refactor note: previously stored the raw key on the instance, which
        # leaked via repr()/__dict__. Now only the AESGCM primitive is held.
        self._aesgcm = AESGCM(bytes(key))

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(self._NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data=None)
        # Prepend nonce so decrypt() can recover it later.
        return nonce + ciphertext

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < self._NONCE_SIZE:
            raise ValueError("ciphertext too short -- nonce missing")
        nonce, ciphertext = blob[: self._NONCE_SIZE], blob[self._NONCE_SIZE :]
        return self._aesgcm.decrypt(nonce, ciphertext, associated_data=None)


class NoOpStrategy(EncryptionStrategy):
    """Pass-through strategy used in unit tests.

    Isolates business logic from cryptographic concerns so tests stay fast
    and deterministic. **Never** register this in production.
    """

    def encrypt(self, plaintext: bytes) -> bytes:  # noqa: D401 - trivial
        return plaintext

    def decrypt(self, ciphertext: bytes) -> bytes:  # noqa: D401 - trivial
        return ciphertext
