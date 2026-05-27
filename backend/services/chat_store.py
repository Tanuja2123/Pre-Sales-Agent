"""Per-run clarification chat history on disk."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import Settings
from models.scope import ChatMessage

log = logging.getLogger(__name__)


def _chat_path(settings: Settings, run_id: str) -> Path:
    root = Path(settings.data_dir).parent / "chat"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{run_id}.json"


def load_messages(settings: Settings, run_id: str) -> list[ChatMessage]:
    path = _chat_path(settings, run_id)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw.get("messages") or []
        return [ChatMessage.model_validate(m) for m in rows]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log.warning("chat.load_failed", run_id=run_id, error=str(exc))
        return []


def save_messages(settings: Settings, run_id: str, messages: list[ChatMessage]) -> None:
    path = _chat_path(settings, run_id)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "updated_at": datetime.now(UTC).isoformat(),
        "messages": [m.model_dump(mode="json") for m in messages],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_message(settings: Settings, run_id: str, role: str, content: str) -> list[ChatMessage]:
    messages = load_messages(settings, run_id)
    messages.append(
        ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(UTC).isoformat(),
        )
    )
    save_messages(settings, run_id, messages)
    return messages
