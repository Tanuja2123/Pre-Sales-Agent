from __future__ import annotations

import json
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from agents.presales_chat_agent import PresalesChatAgent
from agents.response_agent import apply_company_name_to_draft
from core.auth import CurrentUser, get_current_user
from core.config import Settings, get_settings
from core.llm import LLMError
from core.logging import get_logger
from orchestrator.pipeline import OUTPUTS, RUNS, PipelineOrchestrator, persist_upload
from parsers.docx_parser import DOCXParser
from parsers.pdf_parser import PDFParser
from routers.access import assert_run_access
from services import run_store
from services.chat_store import append_message, load_messages
from services.clarification_builder import (
    build_clarification_document,
    clarification_to_prompt_context,
)

log = get_logger(__name__)


def _bundle_with_company_draft(bundle: Any, settings: Settings) -> Any:
    if not bundle or not bundle.draft_response:
        return bundle
    return bundle.model_copy(
        update={
            "draft_response": apply_company_name_to_draft(
                bundle.draft_response,
                settings.proposal_company_name,
            )
        }
    )


router = APIRouter(dependencies=[Depends(get_current_user)])


def get_orchestrator(
    request: Request, settings: Settings = Depends(get_settings)
) -> PipelineOrchestrator:
    return PipelineOrchestrator(
        settings, runtime=getattr(request.app.state, "agent_runtime", None)
    )


@router.post("/analyze")
async def analyze_rfp(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, str]:
    if settings.llm_only_mode and settings.llm_backend == "mock":
        raise HTTPException(
            status_code=400,
            detail="LLM-only mode is enabled. Set LLM_BACKEND to groq, ollama, or azure_openai.",
        )
    raw = await file.read()
    path, suffix = persist_upload(settings, file.filename or "upload.bin", raw)
    run_id = await orchestrator.start_run(path, suffix, file.filename, user_id=current_user.id)
    return {
        "run_id": run_id,
        "message": (
            "RFP uploaded successfully. After you submit clarifications and the final draft is "
            f"generated, a project timeline email will be sent to {current_user.email}."
        ),
    }


@router.get("/{run_id}/status")
async def run_status(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    st = RUNS.get(run_id)
    if st:
        return {
            "run_id": run_id,
            "status": st.status.value,
            "progress": st.progress,
            "error": st.error,
        }
    # Fall back to the persistent store (e.g. after a server restart).
    row = run_store.get_run_row(settings, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run_id,
        "status": row["status"],
        "progress": int(row["progress"] or 0),
        "error": row["error"],
    }


@router.get("/{run_id}/output")
async def run_output(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="output not ready or run not found")
    return _bundle_with_company_draft(bundle, settings).model_dump(mode="json")


@router.get("/{run_id}/summary")
async def run_summary(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle or not bundle.summary:
        raise HTTPException(status_code=404, detail="summary not available")
    return bundle.summary.model_dump()


@router.get("/{run_id}/questions")
async def run_questions(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="not found")
    return {"questions": [q.model_dump() for q in bundle.questions]}


@router.get("/{run_id}/draft")
async def run_draft(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle or not bundle.draft_response:
        raise HTTPException(status_code=404, detail="draft not available")
    draft = apply_company_name_to_draft(bundle.draft_response, settings.proposal_company_name)
    return draft.model_dump()


@router.get("/{run_id}/scope")
async def run_scope(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle or not bundle.scope:
        raise HTTPException(status_code=404, detail="scope not available")
    return bundle.scope.model_dump()


@router.get("/{run_id}/chat")
async def get_chat(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    if (
        run_id not in RUNS
        and run_id not in OUTPUTS
        and run_store.get_run_row(settings, run_id) is None
    ):
        raise HTTPException(status_code=404, detail="run not found")
    messages = load_messages(settings, run_id)
    bundle = OUTPUTS.get(run_id) or run_store.load_run_output(settings, run_id)
    return {
        "run_id": run_id,
        "messages": [m.model_dump() for m in messages],
        "clarification_started": bool(bundle and bundle.clarification_started),
    }


@router.post("/{run_id}/chat")
async def post_chat(
    run_id: str,
    body: dict[str, Any],
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    user_message = str(body.get("message") or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    bundle = orchestrator.get_output(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="run not found or not complete")

    append_message(settings, run_id, "user", user_message)
    history = load_messages(settings, run_id)

    agent = PresalesChatAgent(settings)
    try:
        turn = await agent.reply(bundle, history[:-1], user_message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    append_message(settings, run_id, "assistant", turn.assistant_message)
    if turn.scope_updated and bundle.scope:
        OUTPUTS[run_id] = bundle
        run_store.upsert_run_output(settings, bundle)

    return {
        "assistant_message": turn.assistant_message,
        "suggested_questions": turn.suggested_questions,
        "scope_updated": turn.scope_updated,
        "messages": [m.model_dump() for m in load_messages(settings, run_id)],
    }


@router.post("/{run_id}/feedback")
async def run_feedback(
    run_id: str,
    body: dict[str, Any],
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    assert_run_access(settings, run_id, current_user)
    _ = body
    return {"run_id": run_id, "status": "recorded"}


@router.post("/{run_id}/clarifications/resolve")
async def resolve_clarifications(
    run_id: str,
    current_user: CurrentUser,
    payload: str = Form(...),
    answers_file: UploadFile | None = File(default=None),
    additional_files: list[UploadFile] | None = File(default=None),
    settings: Settings = Depends(get_settings),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    assert_run_access(settings, run_id, current_user)
    bundle = orchestrator.get_output(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="run not found or not complete")
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="payload must be valid JSON") from exc

    answers = parsed.get("answers") if isinstance(parsed, dict) else {}
    suggestions = parsed.get("suggested_inputs") if isinstance(parsed, dict) else {}
    additional_notes = str(parsed.get("additional_notes") or "") if isinstance(parsed, dict) else ""
    if not isinstance(answers, dict):
        raise HTTPException(status_code=400, detail="answers must be an object")
    if suggestions is None:
        suggestions = {}
    if not isinstance(suggestions, dict):
        raise HTTPException(status_code=400, detail="suggested_inputs must be an object when provided")

    upload_name = ""
    upload_excerpt = ""
    if answers_file is not None:
        upload_name = answers_file.filename or ""
        upload_excerpt = await _extract_uploaded_answer_text(answers_file)
    if additional_files:
        extra_names: list[str] = []
        extra_parts: list[str] = []
        for upload in additional_files[:5]:
            if not upload.filename:
                continue
            text = await _extract_uploaded_answer_text(upload)
            if not text.strip():
                continue
            extra_names.append(upload.filename)
            extra_parts.append(f"File: {upload.filename}\n{text[:4000]}")
        if extra_names:
            upload_name = ", ".join([name for name in [upload_name, *extra_names] if name])
        if extra_parts:
            upload_excerpt = "\n\n".join([part for part in [upload_excerpt, *extra_parts] if part])[
                :12000
            ]

    chat_history = load_messages(settings, run_id)
    doc = build_clarification_document(
        bundle,
        answers={str(k): str(v) for k, v in answers.items()},
        suggested_inputs={str(k): str(v) for k, v in suggestions.items()},
        additional_notes=additional_notes,
        uploaded_reference_filename=upload_name,
        uploaded_reference_excerpt=upload_excerpt,
        chat_history=chat_history,
    )
    bundle.clarification_document = doc
    context = clarification_to_prompt_context(doc)
    try:
        updated = await orchestrator.regenerate_final_draft(
            run_id,
            clarification_context=context,
            critique_note=(
                "This is the final outcome pass. Integrate all clarified answers to ambiguous requirements. "
                "Where no answer was provided, include the stated assumption and mention it clearly."
            ),
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    notification_result: dict[str, object] = {}
    try:
        from models.user import UserPublic
        from services import notification_service

        user = UserPublic(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
        )
        notification_result = notification_service.notify_draft_complete(settings, user, updated)
    except Exception as exc:  # noqa: BLE001
        log.warning("rfp.draft_notification_failed", run_id=run_id, error=str(exc))

    append_message(
        settings,
        run_id,
        "assistant",
        "Clarification inputs received. I regenerated the final integrated proposal using all provided answers, assumptions, and uploaded notes.",
    )
    email_sent = notification_result.get("email_sent", False)
    return {
        "run_id": run_id,
        "resolved_items": len(doc.items),
        "final_sections": len(updated.draft_response.sections) if updated.draft_response else 0,
        "clarification_document": doc.model_dump(mode="json"),
        "message": (
            f"Final draft generated. A project timeline email has been sent to {current_user.email}."
            if email_sent
            else "Final draft generated. Timeline email could not be sent — check backend logs."
        ),
        "notification": notification_result,
    }


@router.get("/history")
async def history(
    current_user: CurrentUser,
    limit: int = 200,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Return run history for the authenticated user only."""
    rows = run_store.list_runs(settings, limit=limit, user_id=current_user.id)
    seen = {r["run_id"] for r in rows}
    items: list[dict[str, Any]] = []
    for r in rows:
        items.append(
            {
                "run_id": r["run_id"],
                "status": r["status"],
                "progress": int(r["progress"] or 0),
                "error": r["error"],
                "filename": r["filename"],
                "document_id": r["document_id"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "duration_seconds": r["duration_seconds"],
                "created_at": r["created_at"],
            }
        )
    # Surface very fresh runs that haven't been flushed yet.
    for rid, st in RUNS.items():
        if rid in seen:
            continue
        if st.user_id and st.user_id != current_user.id:
            continue
        items.insert(
            0,
            {
                "run_id": rid,
                "status": st.status.value,
                "progress": int(st.progress or 0),
                "error": st.error,
                "filename": st.rfp.filename if st.rfp else None,
                "document_id": st.rfp.document_id if st.rfp else None,
                "started_at": st.started_at.isoformat() if st.started_at else None,
                "finished_at": st.finished_at.isoformat() if st.finished_at else None,
                "duration_seconds": None,
                "created_at": st.started_at.isoformat() if st.started_at else None,
            },
        )
    return {"runs": items, "count": len(items)}


@router.delete("/{run_id}")
async def delete_run(
    run_id: str,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    assert_run_access(settings, run_id, current_user)
    run_store.delete_run(settings, run_id)
    RUNS.pop(run_id, None)
    OUTPUTS.pop(run_id, None)
    return {"run_id": run_id, "status": "deleted"}


@router.websocket("/{run_id}/stream")
async def stream_pipeline(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    settings = get_settings()
    orchestrator = PipelineOrchestrator(
        settings, runtime=getattr(websocket.app.state, "agent_runtime", None)
    )
    try:
        async for event in orchestrator.stream(run_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return


async def _extract_uploaded_answer_text(upload: UploadFile) -> str:
    filename = (upload.filename or "").lower()
    suffix = filename.rsplit(".", 1)[-1] if "." in filename else ""
    data = await upload.read()
    if not data:
        return ""
    if suffix in {"txt", "md", "csv"}:
        return data.decode("utf-8", errors="replace")[:12000]

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix or 'txt'}") as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        if suffix == "pdf":
            return (await PDFParser().extract(str(tmp_path)))[:12000]
        if suffix in {"docx", "doc"}:
            return (await DOCXParser().extract(str(tmp_path)))[:12000]
        return data.decode("utf-8", errors="replace")[:12000]
    finally:
        tmp_path.unlink(missing_ok=True)
