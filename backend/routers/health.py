from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    boot_id = getattr(request.app.state, "server_boot_id", "")
    return {"status": "ok", "server_boot_id": boot_id}
