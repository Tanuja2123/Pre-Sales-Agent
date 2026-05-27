from __future__ import annotations

from pydantic import BaseModel, Field


class ScopeRequirementItem(BaseModel):
    requirement_id: str
    text: str
    priority: str = "mandatory"
    notes: str = ""


class UserStory(BaseModel):
    story_id: str
    role: str = ""
    story: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class PresalesScopeDocument(BaseModel):
    """Structured presales deliverable — aligns with prompt-presales-gathering-v1."""

    project_summary: str = ""
    business_requirements: list[ScopeRequirementItem] = Field(default_factory=list)
    functional_requirements: list[ScopeRequirementItem] = Field(default_factory=list)
    non_functional_requirements: list[ScopeRequirementItem] = Field(default_factory=list)
    user_stories: list[UserStory] = Field(default_factory=list)
    draft_scope_document: str = ""
    suggested_questions: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str
    timestamp: str = ""


class ChatTurnResponse(BaseModel):
    assistant_message: str
    suggested_questions: list[str] = Field(default_factory=list)
    scope_updated: bool = False
