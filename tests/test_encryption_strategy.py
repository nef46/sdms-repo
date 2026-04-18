"""Unit tests for the Strategy pattern (EncryptionStrategy / AES256Strategy).

Covers
------
* AES-256-GCM round-trip correctness.
* Rejection of keys that are not exactly 32 bytes.
* Authenticated-encryption tamper detection.
* Unique nonce generation per call (GCM safety requirement).
* The ``NoOpStrategy`` test double behaves as an identity function.

Author: Konstantinos Tserkezidis -- Phase 3.
"""

from __future__ import annotations

import os

import pytest

from sdms.patterns.encryption_strategy import AES256Strategy, NoOpStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def key() -> bytes:
    return os.urandom(32)


@pytest.fixture()
def strategy(key: bytes) -> AES256Strategy:
    return AES256Strategy(key)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_aes256_round_trip(strategy: AES256Strategy) -> None:
    """Encrypt then decrypt must return the original plaintext."""
    plaintext = b"FR-02: sensitive engineering drawing"
    assert strategy.decrypt(strategy.encrypt(plaintext)) == plaintext


def test_aes256_empty_payload(strategy: AES256Strategy) -> None:
    """Edge case: empty bytes must round-trip correctly."""
    assert strategy.decrypt(strategy.encrypt(b"")) == b""


def test_aes256_nonce_differs_each_call(strategy: AES256Strategy) -> None:
    """GCM must never reuse a (key, nonce) pair -- verify uniqueness."""
    a = strategy.encrypt(b"same-input")
    b = strategy.encrypt(b"same-input")
    assert a != b, "Two encryptions of the same plaintext must differ"


def test_aes256_rejects_short_key() -> None:
    with pytest.raises(ValueError, match="32-byte"):
        AES256Strategy(b"too-short")


def test_aes256_rejects_long_key() -> None:
    with pytest.raises(ValueError, match="32-byte"):
        AES256Strategy(os.urandom(64))


def test_aes256_detects_tampering(strategy: AES256Strategy) -> None:
    """Flipping a single bit in the ciphertext must cause decryption to fail."""
    blob = bytearray(strategy.encrypt(b"payload"))
    blob[-1] ^= 0x01
    with pytest.raises(Exception):
        strategy.decrypt(bytes(blob))


def test_noop_strategy_is_identity() -> None:
    noop = NoOpStrategy()
    assert noop.encrypt(b"x") == b"x"
    assert noop.decrypt(b"x") == b"x"
