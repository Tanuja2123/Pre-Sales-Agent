from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from models.maf import MAFAuditResult
from models.rfp import (
    ClarifyingQuestion,
    DraftResponse,
    Requirement,
    RFPDocument,
    RFPSummary,
)
from models.scope import PresalesScopeDocument


class PipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"


class GoNoGoDecision(BaseModel):
    proceed: bool
    rationale: str
    blockers: list[str] = Field(default_factory=list)


class TimelineMilestone(BaseModel):
    project_name: str = ""
    milestone: str
    start_date: str
    end_deadline: str
    required_deliverables: str = ""
    dependency: str = ""
    escalation_sla: str = "Escalate within 24 hours"
    status: str = "Pending"
    priority: str = "Medium"


class ClarificationResolutionItem(BaseModel):
    question_id: str
    source_requirement: str = ""
    question_text: str
    suggested_input: str = ""
    user_answer: str = ""
    assumption_if_unanswered: str = ""
    final_resolution: str
    resolution_source: str  # user_answer | assumption


class ClarificationResolutionDocument(BaseModel):
    generated_at: str
    uploaded_reference_filename: str = ""
    uploaded_reference_excerpt: str = ""
    additional_notes: str = ""
    chat_user_inputs_excerpt: str = ""
    items: list[ClarificationResolutionItem] = Field(default_factory=list)


class OutputBundle(BaseModel):
    run_id: str
    rfp: RFPDocument
    summary: RFPSummary | None = None
    timeline: list[TimelineMilestone] = Field(default_factory=list)
    submission_date: str | None = None
    expected_completion_date: str | None = None
    clarification_document: ClarificationResolutionDocument | None = None
    scope: PresalesScopeDocument | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    draft_response: DraftResponse | None = None
    maf_audit: MAFAuditResult | None = None
    go_no_go: GoNoGoDecision | None = None
    pipeline_duration_seconds: float = 0.0
    clarification_started: bool = False


@dataclass
class PipelineState:
    """Shared mutable state for orchestrator — TDD §6.2."""

    run_id: str
    user_id: str | None = None
    status: PipelineStatus = PipelineStatus.PENDING
    rfp: RFPDocument | None = None
    requirements: list[Requirement] = field(default_factory=list)
    summary: RFPSummary | None = None
    questions: list[ClarifyingQuestion] = field(default_factory=list)
    draft: DraftResponse | None = None
    audit: MAFAuditResult | None = None
    go_no_go: GoNoGoDecision | None = None
    error: str | None = None
    progress: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def add_event(self, event_type: str, agent: str, data: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "type": event_type,
                "agent": agent,
                "progress": self.progress,
                "data": data or {},
            }
        )
