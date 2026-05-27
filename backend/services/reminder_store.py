from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from datetime import UTC, datetime

from core.config import Settings

log = logging.getLogger(__name__)

_DB_LOCK = threading.RLock()
_REMINDERS_INIT: set[str] = set()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect(settings: Settings) -> sqlite3.Connection:
    from services.run_store import _connect as run_connect
    from services.run_store import ensure_initialized  # noqa: PLC0415

    ensure_initialized(settings)
    return run_connect(settings)


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS email_reminders (
            id                    TEXT PRIMARY KEY,
            user_id               TEXT NOT NULL,
            user_email            TEXT NOT NULL,
            run_id                TEXT NOT NULL,
            project_name          TEXT NOT NULL,
            milestone_name        TEXT NOT NULL,
            deadline_date         TEXT NOT NULL,
            reminder_date         TEXT NOT NULL,
            required_deliverables TEXT NOT NULL DEFAULT '',
            pending_tasks         TEXT NOT NULL DEFAULT '',
            submission_date       TEXT NOT NULL DEFAULT '',
            priority              TEXT NOT NULL DEFAULT 'Medium',
            status                TEXT NOT NULL DEFAULT 'Pending',
            sent_at               TEXT,
            created_at            TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reminders_due ON email_reminders(reminder_date, sent_at);
        CREATE INDEX IF NOT EXISTS idx_reminders_user ON email_reminders(user_id);
        CREATE INDEX IF NOT EXISTS idx_reminders_run ON email_reminders(run_id);
        """
    )


def ensure_initialized(settings: Settings) -> None:
    key = str(settings.run_db_path)
    if key in _REMINDERS_INIT:
        return
    with _DB_LOCK:
        if key in _REMINDERS_INIT:
            return
        with _connect(settings) as conn:
            _init_schema(conn)
        _REMINDERS_INIT.add(key)


def schedule_reminders(
    settings: Settings,
    *,
    user_id: str,
    user_email: str,
    run_id: str,
    project_name: str,
    submission_date: str,
    milestones: list[dict[str, str]],
) -> int:
    """Create reminder rows for each milestone deadline (idempotent per run+milestone)."""
    ensure_initialized(settings)
    created = 0
    now = _now_iso()
    with _DB_LOCK, _connect(settings) as conn:
        for row in milestones:
            deadline = row.get("end_deadline") or row.get("deadline_date") or ""
            reminder_date = row.get("reminder_date") or ""
            milestone_name = row.get("milestone") or row.get("milestone_name") or "Milestone"
            if not deadline or not reminder_date:
                continue
            existing = conn.execute(
                """
                SELECT id FROM email_reminders
                WHERE run_id = ? AND milestone_name = ? AND deadline_date = ?
                """,
                (run_id, milestone_name, deadline),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """
                INSERT INTO email_reminders (
                    id, user_id, user_email, run_id, project_name, milestone_name,
                    deadline_date, reminder_date, required_deliverables, pending_tasks,
                    submission_date, priority, status, sent_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    str(uuid.uuid4()),
                    user_id,
                    user_email,
                    run_id,
                    project_name,
                    milestone_name,
                    deadline,
                    reminder_date,
                    row.get("required_deliverables") or row.get("dependency") or "",
                    row.get("pending_tasks") or row.get("required_deliverables") or "",
                    submission_date,
                    row.get("priority") or "Medium",
                    row.get("status") or "Pending",
                    now,
                ),
            )
            created += 1
    return created


def list_due_reminders(settings: Settings, as_of_date: str) -> list[dict[str, str]]:
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        rows = conn.execute(
            """
            SELECT * FROM email_reminders
            WHERE sent_at IS NULL AND reminder_date <= ?
            ORDER BY reminder_date ASC, deadline_date ASC
            """,
            (as_of_date,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminder_sent(settings: Settings, reminder_id: str) -> None:
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        conn.execute(
            "UPDATE email_reminders SET sent_at = ? WHERE id = ?",
            (_now_iso(), reminder_id),
        )
