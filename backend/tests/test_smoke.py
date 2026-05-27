import asyncio
import json
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agents.ingestion_agent import IngestionPlugin
from main import app
from services import run_store, user_store


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("RUN_DB_PATH", str(db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "uploads"))
    run_store._INIT_DONE.clear()
    user_store._USERS_INIT.clear()
    return db_path


async def _register_and_auth(client: AsyncClient) -> dict[str, str]:
    email = f"tester-{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": email,
            "password": "SecurePass1",
            "confirm_password": "SecurePass1",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ingest_txt_chunks(tmp_path: Path) -> None:
    p = tmp_path / "sample.txt"
    p.write_text(
        "Section I: Scope\n" + ("We must deliver widgets by Friday.\n" * 50), encoding="utf-8"
    )
    agent = IngestionPlugin()
    doc = await agent.ingest_document(str(p), "txt")
    assert doc.raw_text
    assert doc.chunks
    assert all(len(c.chunk_id) > 3 for c in doc.chunks)


@pytest.mark.asyncio
async def test_auth_register_login_validation(isolated_env: Path) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        dup_email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        ok = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Jane Doe",
                "email": dup_email,
                "password": "SecurePass1",
                "confirm_password": "SecurePass1",
            },
        )
        assert ok.status_code == 200

        dup = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Jane Doe",
                "email": dup_email,
                "password": "SecurePass1",
                "confirm_password": "SecurePass1",
            },
        )
        assert dup.status_code == 409

        bad_login = await client.post(
            "/api/v1/auth/login",
            json={"email": dup_email, "password": "WrongPass1"},
        )
        assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_analyze_endpoint(isolated_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "mock")
    monkeypatch.setenv("LLM_ONLY_MODE", "false")

    sample = tmp_path / "rfp.txt"
    sample.write_text(
        "REQ mandatory: The vendor shall provide 24/7 support.\n" * 5,
        encoding="utf-8",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_auth(client)
        with open(sample, "rb") as f:
            r = await client.post(
                "/api/v1/rfp/analyze",
                files={"file": ("rfp.txt", f, "text/plain")},
                headers=headers,
            )
        assert r.status_code == 200
        body = r.json()
        run_id = body["run_id"]
        assert "message" in body
        for _ in range(80):
            s = await client.get(f"/api/v1/rfp/{run_id}/status", headers=headers)
            if s.json().get("status") in ("complete", "failed", "aborted"):
                break
            await asyncio.sleep(0.1)
        out = await client.get(f"/api/v1/rfp/{run_id}/output", headers=headers)
        assert out.status_code == 200
        payload = out.json()
        assert payload["run_id"] == run_id
        assert "rfp" in payload
        assert payload["rfp"]["filename"] == "rfp.txt"
        assert "stored_file" in payload["rfp"].get("metadata", {})
        assert "timeline" in payload
        assert len(payload["timeline"]) >= 1
        assert payload["timeline"][0].get("project_name")
        assert payload["timeline"][0].get("required_deliverables")
        assert payload["timeline"][0].get("status")
        assert payload.get("submission_date")
        assert payload.get("expected_completion_date")
        resolve_payload = {
            "answers": {"Q-001": "Primary users are operations managers and admins."},
            "suggested_inputs": {"Q-001": "Confirm user personas, access roles, and support windows."},
            "additional_notes": "Prefer phased rollout with strict compliance checkpoints.",
        }
        resolve = await client.post(
            f"/api/v1/rfp/{run_id}/clarifications/resolve",
            data={"payload": json.dumps(resolve_payload)},
            headers=headers,
        )
        assert resolve.status_code == 200
        out2 = await client.get(f"/api/v1/rfp/{run_id}/output", headers=headers)
        assert out2.status_code == 200
        body2 = out2.json()
        assert body2.get("clarification_document")
