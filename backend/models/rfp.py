from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RequirementType(StrEnum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    DEADLINE = "deadline"


class MAFLevel(StrEnum):
    MINIMUM = "M"
    ACCEPTABLE = "A"
    FULL = "F"


class DocumentChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Requirement(BaseModel):
    requirement_id: str
    type: RequirementType
    priority: str  # mandatory | desirable | optional
    maf_classification: MAFLevel
    source_section: str
    text: str
    ambiguity_score: int = Field(ge=0, le=10, default=0)


class RequirementList(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)


class ClarifyingQuestion(BaseModel):
    question_id: str
    category: str  # scope | evaluation | commercial | submission | market
    priority: str  # CRITICAL | STRATEGIC | STANDARD
    question_text: str
    assumption_if_unanswered: str = ""
    source_requirement: str = ""


class QuestionList(BaseModel):
    questions: list[ClarifyingQuestion] = Field(default_factory=list)


class DraftSection(BaseModel):
    section_id: str
    title: str
    body: str


class DraftResponse(BaseModel):
    sections: list[DraftSection] = Field(default_factory=list)


class RFPSummary(BaseModel):
    client_overview: str
    strategic_objectives: str
    key_requirements: list[str] = Field(default_factory=list)
    evaluation_criteria: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    bid_strategy: str = ""
    go_no_go_recommendation: str = ""


class RFPDocument(BaseModel):
    document_id: str
    filename: str
    upload_timestamp: datetime
    raw_text: str
    chunks: list[DocumentChunk] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
