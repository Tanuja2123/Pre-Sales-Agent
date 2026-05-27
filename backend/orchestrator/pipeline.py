from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.clarification_agent import ClarificationAgent
from agents.evaluation_agent import EvaluationAgent
from agents.ingestion_agent import IngestionPlugin
from agents.presales_chat_agent import PresalesChatAgent
from agents.response_agent import ResponseDraftAgent
from agents.scope_gathering_agent import ScopeGatheringAgent
from agents.stage_tools import AuditToolPlugin, RetrievalToolPlugin, RevisionToolPlugin
from agents.summarization_agent import SummarizationAgent
from agents.understanding_agent import UnderstandingAgent
from services.chat_store import append_message, load_messages
from services import run_store
from services.timeline_builder import build_strict_timeline, ensure_bundle_timeline
from core.agent_runtime import AgentRuntime, make_tool
from core.config import Settings, get_settings
from core.llm import format_pipeline_error
from core.logging import get_logger
from models.maf import MAFContext
from models.pipeline import (
    GoNoGoDecision,
    OutputBundle,
    PipelineState,
    PipelineStatus,
)
from models.rfp import MAFLevel, RFPDocument, RequirementList
from rag.retrieval import AbstractVectorStore, make_vector_store

log = get_logger(__name__)

RUNS: dict[str, PipelineState] = {}
OUTPUTS: dict[str, OutputBundle] = {}


def _persist_state(settings: Settings, state: PipelineState) -> None:
    """Best-effort persistence — never let store failures break the pipeline."""
    try:
        run_store.upsert_run_state(settings, state)
    except Exception as exc:  # noqa: BLE001
        log.warning("run_store.persist_state_failed", run_id=state.run_id, error=str(exc))


def _persist_output(settings: Settings, bundle: OutputBundle) -> None:
    try:
        run_store.upsert_run_output(settings, bundle)
    except Exception as exc:  # noqa: BLE001
        log.warning("run_store.persist_output_failed", run_id=bundle.run_id, error=str(exc))


def hydrate_caches() -> int:
    """Reload persisted runs from SQLite into the in-memory caches.

    Safe to call multiple times — only missing entries are restored.
    """
    settings = get_settings()
    return run_store.hydrate_in_memory_caches(settings, RUNS, OUTPUTS)


# Hydrate eagerly on first import so the API exposes prior history immediately
# (e.g. right after `uvicorn` boots, before any new request arrives).
try:
    hydrate_caches()
except Exception as exc:  # noqa: BLE001
    log.warning("run_store.hydrate_failed", error=str(exc))


def _groq_pipeline_delay(settings: Settings) -> float:
    """Seconds between agent LLM calls — 70B models need longer gaps on free-tier TPM."""
    base = settings.groq_inter_request_delay_seconds
    model = settings.groq_model.lower()
    if "70b" in model or "versatile" in model:
        return max(base, 55.0)
    if "8b" in model or "instant" in model:
        return max(base, 25.0)
    return base


async def _groq_cooldown(settings: Settings) -> None:
    """Pause between pipeline LLM steps to stay under Groq TPM (~6k/min on 70B free tier)."""
    if settings.llm_backend != "groq":
        return
    delay = _groq_pipeline_delay(settings)
    if delay > 0:
        log.info("groq.cooldown", seconds=delay, model=settings.groq_model)
        await asyncio.sleep(delay)


def _go_no_go(rfp: RFPDocument, parse_ok: bool) -> GoNoGoDecision:
    if not parse_ok or not rfp.raw_text.strip():
        return GoNoGoDecision(
            proceed=False, rationale="Document empty or parse failed", blockers=["parse"]
        )
    return GoNoGoDecision(
        proceed=True, rationale="Document parsed; pipeline may continue", blockers=[]
    )


def _build_draft_revision_note(blockers: list[str], iteration: int) -> str:
    blocker_lines = "\n".join(f"- {b}" for b in blockers[:12]) or "- Improve coverage quality."
    return (
        f"Revision pass #{iteration}: address these coverage gaps before re-drafting.\n"
        "Ensure each blocker is covered explicitly by requirement id or clear paraphrase.\n"
        f"{blocker_lines}"
    )


class PipelineOrchestrator:
    """Orchestrator — routes agents and shared PipelineState."""

    def __init__(
        self,
        settings: Settings,
        vector_store: AbstractVectorStore | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:
        self._settings = settings
        self._runtime = runtime
        self._ingestion = IngestionPlugin()
        self._understanding = UnderstandingAgent(settings)
        self._summarization = SummarizationAgent(
            settings, MAFContext(target_level=MAFLevel.ACCEPTABLE)
        )
        self._clarification = ClarificationAgent(settings)
        self._scope = ScopeGatheringAgent(settings)
        self._chat = PresalesChatAgent(settings)
        self._evaluation = EvaluationAgent(settings)
        self._vector_store = vector_store or make_vector_store(settings)
        self._response = ResponseDraftAgent(settings, self._vector_store)
        self._retrieval_tool = RetrievalToolPlugin(self._vector_store)
        self._audit_tool = AuditToolPlugin(self._evaluation)
        self._revision_tool = RevisionToolPlugin(self._response)
        self._register_agent_tools()

    def _register_agent_tools(self) -> None:
        if self._runtime is None:
            return
        tools = [
            make_tool(
                self._ingestion.ingest_document,
                name="ingest_document",
                description="Parse RFP document into structured RFPDocument",
            ),
            make_tool(
                self._retrieval_tool.retrieve_context,
                name="retrieve_context",
                description="Retrieve top-k relevant RFP snippets for proposal drafting",
            ),
            make_tool(
                self._audit_tool.audit_draft,
                name="audit_draft",
                description="Run MAF-style coverage audit on proposal draft",
            ),
            make_tool(
                self._revision_tool.revise_draft,
                name="revise_draft",
                description="Generate or revise draft proposal with optional critique guidance",
            ),
        ]
        self._runtime.register_tools(tools)

    async def start_run(
        self,
        file_path: str,
        file_type: str,
        original_filename: str | None = None,
        user_id: str | None = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        state = PipelineState(run_id=run_id, user_id=user_id, status=PipelineStatus.PENDING)
        RUNS[run_id] = state
        _persist_state(self._settings, state)
        asyncio.create_task(
            self._execute_pipeline(run_id, file_path, file_type, original_filename, user_id)
        )
        return run_id

    async def _execute_pipeline(
        self,
        run_id: str,
        file_path: str,
        file_type: str,
        original_filename: str | None = None,
        user_id: str | None = None,
    ) -> None:
        state = RUNS[run_id]
        state.status = PipelineStatus.RUNNING
        state.started_at = datetime.now(UTC)
        _persist_state(self._settings, state)
        t0 = time.perf_counter()
        try:
            state.add_event("agent_started", "IngestionAgent", {})
            rfp = await self._ingestion.ingest_document(file_path, file_type)
            display_name = _safe_upload_display_name(original_filename, file_path)
            stored_name = Path(file_path).name
            rfp = rfp.model_copy(
                update={
                    "filename": display_name,
                    "metadata": {**rfp.metadata, "stored_file": stored_name},
                }
            )
            state.rfp = rfp
            state.progress = 20
            state.add_event("agent_completed", "IngestionAgent", {"document_id": rfp.document_id})
            _persist_state(self._settings, state)
            await self._vector_store.upsert(rfp.chunks)

            gng = _go_no_go(rfp, True)
            state.go_no_go = gng
            if not gng.proceed:
                state.status = PipelineStatus.ABORTED
                state.progress = 100
                state.add_event("pipeline_complete", "Orchestrator", {"aborted": True})
                state.finished_at = datetime.now(UTC)
                _persist_state(self._settings, state)
                return

            state.add_event("agent_started", "UnderstandingAgent", {})
            req_list = await self._understanding.extract_requirements(rfp)
            state.requirements = req_list.requirements
            timeline_rows, submission_date, expected_completion_date = build_strict_timeline(
                rfp, state.requirements
            )
            state.progress = 40
            state.add_event(
                "agent_completed", "UnderstandingAgent", {"count": len(state.requirements)}
            )
            _persist_state(self._settings, state)
            await _groq_cooldown(self._settings)

            state.add_event("agent_started", "SummarizationAgent", {})
            summary = await self._summarization.summarize(rfp, req_list)
            state.summary = summary
            state.progress = 60
            state.add_event("agent_completed", "SummarizationAgent", {})
            _persist_state(self._settings, state)
            await _groq_cooldown(self._settings)

            state.add_event("agent_started", "ScopeGatheringAgent", {})
            scope_doc = await self._scope.gather(rfp, req_list, summary)
            state.progress = 70
            state.add_event(
                "agent_completed",
                "ScopeGatheringAgent",
                {
                    "business": len(scope_doc.business_requirements),
                    "user_stories": len(scope_doc.user_stories),
                },
            )
            _persist_state(self._settings, state)
            await _groq_cooldown(self._settings)

            state.add_event("agent_started", "ClarificationAgent", {})
            ql = await self._clarification.generate_questions(req_list)
            state.questions = ql.questions
            state.progress = 80
            state.add_event(
                "agent_completed", "ClarificationAgent", {"count": len(state.questions)}
            )
            _persist_state(self._settings, state)
            await _groq_cooldown(self._settings)

            # Draft is intentionally deferred until user submits clarification inputs.
            # This ensures final proposal is generated only from completed clarification context.
            state.draft = None
            state.audit = None
            state.progress = 100
            state.add_event(
                "agent_completed",
                "ClarificationPhase",
                {"ready_for_final_draft": True, "llm": self._settings.llm_backend},
            )

            duration = time.perf_counter() - t0
            bundle = OutputBundle(
                run_id=run_id,
                rfp=rfp,
                summary=summary,
                timeline=timeline_rows,
                submission_date=submission_date,
                expected_completion_date=expected_completion_date,
                scope=scope_doc,
                requirements=state.requirements,
                questions=state.questions,
                draft_response=None,
                maf_audit=None,
                go_no_go=gng,
                pipeline_duration_seconds=duration,
            )
            OUTPUTS[run_id] = bundle
            opening = self._chat.opening_message(bundle)
            append_message(self._settings, run_id, "assistant", opening)
            bundle.clarification_started = True
            _persist_output(self._settings, bundle)
            state.progress = 100
            state.status = PipelineStatus.COMPLETE
            state.error = None
            state.add_event(
                "pipeline_complete",
                "Orchestrator",
                {"ok": True, "clarification_chat": True},
            )
            if user_id:
                try:
                    from models.user import UserPublic
                    from services import notification_service, user_store

                    record = user_store.get_user_by_id(self._settings, user_id)
                    if record is not None:
                        user = UserPublic(id=record.id, full_name=record.full_name, email=record.email)
                        notify_result = notification_service.schedule_project_reminders(
                            self._settings, user, bundle
                        )
                        state.add_event(
                            "reminders_scheduled",
                            "NotificationService",
                            {"reminders_scheduled": notify_result},
                        )
                except Exception as exc:  # noqa: BLE001
                    log.warning("pipeline.notification_failed", run_id=run_id, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            err_msg = format_pipeline_error(exc)
            log.error("pipeline.failed", run_id=run_id, error=err_msg, exc_type=type(exc).__name__)
            state.status = PipelineStatus.FAILED
            state.error = err_msg
            state.add_event("pipeline_error", "Orchestrator", {"error": err_msg})
        finally:
            state.finished_at = datetime.now(UTC)
            _persist_state(self._settings, state)

    async def stream(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Poll-based stream for WebSocket — yields latest events."""
        for _ in range(300):
            st = RUNS.get(run_id)
            if not st:
                yield {
                    "type": "error",
                    "agent": "",
                    "progress": 0,
                    "data": {"message": "unknown run"},
                }
                return
            if st.events:
                ev = st.events[-1]
                yield {
                    "event": ev["type"],
                    "agent": ev["agent"],
                    "progress": st.progress,
                    "data": ev.get("data") or {},
                }
            if st.status in (
                PipelineStatus.COMPLETE,
                PipelineStatus.FAILED,
                PipelineStatus.ABORTED,
            ):
                return
            await asyncio.sleep(0.4)

    def get_output(self, run_id: str) -> OutputBundle | None:
        bundle = OUTPUTS.get(run_id)
        if bundle is None:
            bundle = run_store.load_run_output(self._settings, run_id)
        if bundle is None:
            return None
        bundle, changed = ensure_bundle_timeline(bundle)
        OUTPUTS[run_id] = bundle
        if changed:
            _persist_output(self._settings, bundle)
        return bundle

    async def regenerate_final_draft(
        self, run_id: str, clarification_context: str, critique_note: str = ""
    ) -> OutputBundle:
        bundle = self.get_output(run_id)
        if not bundle or not bundle.summary:
            raise ValueError("run not found or summary unavailable")

        req_list = RequirementList(requirements=bundle.requirements)
        rag_query = " ".join(bundle.summary.key_requirements[:8]) or "RFP compliance delivery security"
        rag_context = await self._retrieval_tool.retrieve_context(rag_query, k=8)
        merged_context = f"{rag_context[:800]}\n\n{clarification_context[:1500]}".strip()
        final_note = (
            "Generate the final integrated proposal using all clarified answers and assumptions. "
            "Ensure every ambiguous requirement is resolved explicitly."
        )
        if critique_note.strip():
            final_note = f"{final_note}\n{critique_note.strip()}"
        draft = await self._response.draft(
            req_list,
            bundle.summary,
            bundle.rfp.raw_text,
            critique_note=final_note,
            rag_context=merged_context,
            clarification_context=clarification_context,
            final_pass=True,
        )
        bundle.draft_response = draft
        OUTPUTS[run_id] = bundle
        _persist_output(self._settings, bundle)
        return bundle


def persist_upload(settings: Settings, filename: str, data: bytes) -> tuple[str, str]:
    dest_dir = Path(settings.data_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower().lstrip(".") or "txt"
    name = f"{uuid.uuid4().hex}.{suffix}"
    path = dest_dir / name
    path.write_bytes(data)
    return str(path), suffix


def _safe_upload_display_name(original: str | None, stored_path: str) -> str:
    """Use client-provided basename only; fall back to stored file name."""
    fallback = Path(stored_path).name
    if not original or not original.strip():
        return fallback
    base = Path(original.strip()).name
    if not base or base in (".", ".."):
        return fallback
    return base
