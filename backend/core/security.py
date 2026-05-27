from __future__ import annotations

import re

import bcrypt

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_email(email)))


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return "Password must include at least one letter."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    return None
