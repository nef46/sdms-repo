"""OTPService.

Maps to ``OTPService`` on the SDS class diagram. Generates, validates and
expires one-time passwords used during the multi-factor login flow.

Cohesion: this class deals only with OTP lifecycle. Email/SMS delivery is
abstracted behind a callable so the class does not depend on a specific
transport.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional


class OTPService:
    OTP_LENGTH = 6
    DEFAULT_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        sender: Optional[Callable[[str, str], None]] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._codes: Dict[int, tuple[str, datetime]] = {}
        self._sender = sender or (lambda email, code: None)
        self._ttl = timedelta(seconds=ttl_seconds)

    def generate_otp(self, user_id: int) -> str:
        code = "".join(secrets.choice(string.digits) for _ in range(self.OTP_LENGTH))
        self._codes[user_id] = (code, datetime.utcnow() + self._ttl)
        return code

    def send_otp(self, user_id: int, email: str) -> str:
        code = self.generate_otp(user_id)
        self._sender(email, code)
        return code

    def validate_otp(self, user_id: int, code: str) -> bool:
        record = self._codes.get(user_id)
        if record is None:
            return False
        stored, expires = record
        if datetime.utcnow() > expires:
            self.expire_otp(user_id)
            return False
        if secrets.compare_digest(stored, code):
            self.expire_otp(user_id)
            return True
        return False

    def expire_otp(self, user_id: int) -> None:
        self._codes.pop(user_id, None)
