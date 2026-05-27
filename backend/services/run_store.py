"""Persistent SQLite-backed store for pipeline runs.

Survives server restarts so the run history is always available, not only
for the lifetime of the current uvicorn process.

Schema
------
runs           — one row per run with status/progress/error and timing.
run_outputs    — serialized `OutputBundle` JSON for completed runs.

The store is intentionally small and dependency-free (Python stdlib only).
All writes are guarded by a process-level lock so concurrent FastAPI
requests / background tasks remain safe.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import Settings
from models.pipeline import OutputBundle, PipelineState, PipelineStatus

log = logging.getLogger(__name__)

_DB_LOCK = threading.RLock()
_INIT_DONE: set[str] = set()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _db_path(settings: Settings) -> Path:
    path = Path(settings.run_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(settings: Settings) -> sqlite3.Connection:
    path = _db_path(settings)
    conn = sqlite3.connect(
        path,
        timeout=10.0,
        isolation_level=None,  # autocommit; we wrap multi-statement work in BEGIN/COMMIT
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id           TEXT PRIMARY KEY,
            status           TEXT NOT NULL,
            progress         INTEGER NOT NULL DEFAULT 0,
            error            TEXT,
            filename         TEXT,
            document_id      TEXT,
            started_at       TEXT,
            finished_at      TEXT,
            duration_seconds REAL,
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS run_outputs (
            run_id     TEXT PRIMARY KEY,
            payload    TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        );
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE runs ADD COLUMN user_id TEXT")

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_runs_created_at  ON runs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_runs_status      ON runs(status);
        CREATE INDEX IF NOT EXISTS idx_runs_user_id     ON runs(user_id);
        """
    )


def ensure_initialized(settings: Settings) -> None:
    """Create tables once per database file (idempotent)."""
    key = str(_db_path(settings))
    if key in _INIT_DONE:
        return
    with _DB_LOCK:
        if key in _INIT_DONE:
            return
        try:
            with _connect(settings) as conn:
                _init_schema(conn)
            _INIT_DONE.add(key)
            log.info("run_store.init db=%s", key)
        except sqlite3.Error as exc:
            log.error("run_store.init_failed db=%s error=%s", key, exc)
            raise


# --------------------------------------------------------------------------- #
# Run metadata                                                                #
# --------------------------------------------------------------------------- #


def upsert_run_state(settings: Settings, state: PipelineState) -> None:
    """Persist (insert or update) the latest snapshot of a `PipelineState`."""
    ensure_initialized(settings)
    now = _now_iso()
    status_value = state.status.value if isinstance(state.status, PipelineStatus) else str(state.status)
    started_at = state.started_at.isoformat() if state.started_at else None
    finished_at = state.finished_at.isoformat() if state.finished_at else None
    duration = None
    if state.started_at and state.finished_at:
        duration = (state.finished_at - state.started_at).total_seconds()

    filename = state.rfp.filename if state.rfp else None
    document_id = state.rfp.document_id if state.rfp else None

    with _DB_LOCK, _connect(settings) as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, status, progress, error, filename, document_id, user_id,
                started_at, finished_at, duration_seconds, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status           = excluded.status,
                progress         = excluded.progress,
                error            = excluded.error,
                filename         = COALESCE(excluded.filename, runs.filename),
                document_id      = COALESCE(excluded.document_id, runs.document_id),
                user_id          = COALESCE(excluded.user_id, runs.user_id),
                started_at       = COALESCE(excluded.started_at, runs.started_at),
                finished_at      = COALESCE(excluded.finished_at, runs.finished_at),
                duration_seconds = COALESCE(excluded.duration_seconds, runs.duration_seconds),
                updated_at       = excluded.updated_at
            """,
            (
                state.run_id,
                status_value,
                int(state.progress),
                state.error,
                filename,
                document_id,
                state.user_id,
                started_at,
                finished_at,
                duration,
                now,
                now,
            ),
        )


def get_run_row(settings: Settings, run_id: str) -> dict[str, Any] | None:
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def list_runs(settings: Settings, limit: int = 200, user_id: str | None = None) -> list[dict[str, Any]]:
    """Most-recent-first list of runs with metadata for the history page."""
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT run_id, status, progress, error, filename, document_id, user_id,
                       started_at, finished_at, duration_seconds, created_at, updated_at
                FROM runs
                WHERE user_id = ?
                ORDER BY datetime(COALESCE(started_at, created_at)) DESC,
                         created_at DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT run_id, status, progress, error, filename, document_id, user_id,
                       started_at, finished_at, duration_seconds, created_at, updated_at
                FROM runs
                ORDER BY datetime(COALESCE(started_at, created_at)) DESC,
                         created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
    return [dict(r) for r in rows]


def delete_run(settings: Settings, run_id: str) -> None:
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))


# --------------------------------------------------------------------------- #
# Output bundle                                                               #
# --------------------------------------------------------------------------- #


def upsert_run_output(settings: Settings, bundle: OutputBundle) -> None:
    ensure_initialized(settings)
    now = _now_iso()
    payload = bundle.model_dump_json()
    with _DB_LOCK, _connect(settings) as conn:
        conn.execute(
            """
            INSERT INTO run_outputs (run_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload    = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (bundle.run_id, payload, now),
        )


def load_run_output(settings: Settings, run_id: str) -> OutputBundle | None:
    ensure_initialized(settings)
    with _DB_LOCK, _connect(settings) as conn:
        row = conn.execute(
            "SELECT payload FROM run_outputs WHERE run_id = ?", (run_id,)
        ).fetchone()
    if not row:
        return None
    try:
        return OutputBundle.model_validate_json(row["payload"])
    except (ValueError, json.JSONDecodeError) as exc:
        log.warning("run_store.output_load_failed run_id=%s error=%s", run_id, exc)
        return None


# --------------------------------------------------------------------------- #
# Bootstrap helpers                                                           #
# --------------------------------------------------------------------------- #


def hydrate_in_memory_caches(
    settings: Settings,
    runs: dict[str, PipelineState],
    outputs: dict[str, OutputBundle],
) -> int:
    """Repopulate the in-memory `RUNS`/`OUTPUTS` dicts from disk.

    Called once at startup so previously persisted runs are immediately
    queryable through the existing in-memory APIs.
    Returns the number of run rows restored.
    """
    ensure_initialized(settings)
    rows = list_runs(settings, limit=1000)
    restored = 0
    for r in rows:
        if r["run_id"] in runs:
            continue
        try:
            state = PipelineState(
                run_id=r["run_id"],
                user_id=r.get("user_id"),
                status=PipelineStatus(r["status"]),
                progress=int(r["progress"] or 0),
                error=r["error"],
                started_at=_parse_iso(r["started_at"]),
                finished_at=_parse_iso(r["finished_at"]),
            )
        except (ValueError, KeyError) as exc:
            log.warning("run_store.hydrate_state_failed run_id=%s error=%s", r["run_id"], exc)
            continue
        runs[state.run_id] = state
        bundle = load_run_output(settings, state.run_id)
        if bundle is not None:
            outputs[state.run_id] = bundle
        restored += 1
    if restored:
        log.info("run_store.hydrated count=%s", restored)
    return restored


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
