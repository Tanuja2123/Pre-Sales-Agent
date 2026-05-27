from __future__ import annotations

from fastapi import HTTPException, status

from core.config import Settings
from models.user import UserPublic
from orchestrator.pipeline import RUNS
from services import run_store


def assert_run_access(settings: Settings, run_id: str, user: UserPublic) -> None:
    state = RUNS.get(run_id)
    if state and state.user_id and state.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this run.")
    row = run_store.get_run_row(settings, run_id)
    if row and row.get("user_id") and row["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this run.")
