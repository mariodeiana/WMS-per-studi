from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000


def hash_password(password: str, *, enforce_policy: bool = True) -> str:
    if not isinstance(password, str):
        raise ValueError("Password non valida")
    if enforce_policy and len(password) < 8:
        raise ValueError("La password deve contenere almeno 8 caratteri")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS,
    ).hex()
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (AttributeError, TypeError, ValueError):
        return False
