from __future__ import annotations

import hashlib
import secrets


PASSWORD_SCHEME = "pbkdf2_sha256"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return secrets.compare_digest(candidate, password_hash)


def make_password_hash(password: str) -> str:
    digest, salt = hash_password(password)
    return f"{PASSWORD_SCHEME}${salt}${digest}"


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != PASSWORD_SCHEME:
        return False
    return verify_password(password, digest, salt)
