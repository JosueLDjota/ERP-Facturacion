from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Final


PBKDF2_NAME: Final[str] = "pbkdf2_sha256"
PBKDF2_ITERATIONS: Final[int] = 390000
SALT_BYTES: Final[int] = 16


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    raw_password = str(password or "")
    salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"{PBKDF2_NAME}${iterations}${salt}${digest}"


def is_password_hashed(value: str | None) -> bool:
    raw_value = str(value or "")
    parts = raw_value.split("$")
    return len(parts) == 4 and parts[0] == PBKDF2_NAME


def verify_password(password: str, stored_value: str | None) -> bool:
    if not is_password_hashed(stored_value):
        return hmac.compare_digest(str(password or ""), str(stored_value or ""))

    _algorithm, iterations, salt, expected_digest = str(stored_value).split("$", 3)
    current_digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password or "").encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(current_digest, expected_digest)


def generate_temporary_password(length: int = 12) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
