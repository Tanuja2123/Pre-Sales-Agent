"""Persistent user accounts in SQLite (same database as run history)."""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from datetime import UTC, datetime

from core.config import Settings
from core.security import normalize_email
from models.user import UserRecord

log = logging.getLogger(__name__)

_DB_LOCK = threading.RLock()
_USERS_INIT: set[str] = set()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect(settings: Settings) -> sqlite3.Connection:
    from services.run_store import _connect as run_connect
    from services.run_store import ensure_initialized  # noqa: PLC0415

    ensure_initialized(settings)
    return run_connect(settings)


def _init_users_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            full_name     TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    )


def ensure_users_initialized(settings: Settings) -> None:
    key = str(settings.run_db_path)
    if key in _USERS_INIT:
        return
    with _DB_LOCK:
        if key in _USERS_INIT:
            return
        with _connect(settings) as conn:
            _init_users_schema(conn)
        _USERS_INIT.add(key)


def create_user(settings: Settings, full_name: str, email: str, password_hash: str) -> UserRecord:
    ensure_users_initialized(settings)
    normalized = normalize_email(email)
    user_id = str(uuid.uuid4())
    now = _now_iso()
    with _DB_LOCK, _connect(settings) as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (id, full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, full_name.strip(), normalized, password_hash, now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists.") from exc
    return UserRecord(
        id=user_id,
        full_name=full_name.strip(),
        email=normalized,
        password_hash=password_hash,
        created_at=now,
    )


def get_user_by_email(settings: Settings, email: str) -> UserRecord | None:
    ensure_users_initialized(settings)
    normalized = normalize_email(email)
    with _DB_LOCK, _connect(settings) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (normalized,)).fetchone()
    if not row:
        return None
    return UserRecord(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )


def get_user_by_id(settings: Settings, user_id: str) -> UserRecord | None:
    ensure_users_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return UserRecord(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )
