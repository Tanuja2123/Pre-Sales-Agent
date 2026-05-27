from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from models.rfp import MAFLevel, Requirement


@dataclass
class MAFContext:
    """Injected into prompts and gates — task-gonogo-v1 / MAF prompts."""

    target_level: MAFLevel
    requirements: list[Requirement] = field(default_factory=list)
    mandatory_clauses: list[str] = field(default_factory=list)
    capability_gaps: list[str] = field(default_factory=list)
    go_no_go: bool = True


class MAFAuditResult(BaseModel):
    minimum_met: bool
    acceptable_coverage: float = Field(ge=0.0, le=1.0)
    full_opportunities: list[str] = Field(default_factory=list)
    overall_rating: MAFLevel
    blockers: list[str] = Field(default_factory=list)


class MAFMinimumNotMetError(RuntimeError):
    def __init__(self, blockers: list[str]) -> None:
        super().__init__(f"MAF minimum not met: {blockers}")
        self.blockers = blockers
