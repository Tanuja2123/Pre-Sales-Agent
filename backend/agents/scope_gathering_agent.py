from __future__ import annotations

import json

from pydantic import ValidationError

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient
from core.logging import get_logger
from models.rfp import RequirementList, RFPDocument, RFPSummary
from models.scope import PresalesScopeDocument, ScopeRequirementItem, UserStory

log = get_logger(__name__)

SCOPE_PROMPT = """You are an AI Presales & Requirement Gathering Agent.

Analyze the INPUT (RFP excerpt + extracted requirements). Reply with ONE JSON object only:

{
  "project_summary": "2-4 paragraphs",
  "business_requirements": [{"requirement_id": "BR-001", "text": "...", "priority": "mandatory", "notes": ""}],
  "functional_requirements": [{"requirement_id": "FR-001", "text": "...", "priority": "mandatory", "notes": ""}],
  "non_functional_requirements": [{"requirement_id": "NFR-001", "text": "...", "priority": "desirable", "notes": ""}],
  "user_stories": [{"story_id": "US-001", "role": "user", "story": "As a ... I want ... so that ...", "acceptance_criteria": ["..."]}],
  "draft_scope_document": "Markdown scope: objectives, in-scope, out-of-scope, milestones, assumptions",
  "suggested_questions": ["5-10 smart questions the client may not have considered"]
}

Rules:
- Ground content in the INPUT; do not invent unrelated products.
- At least 3 items per requirement list when possible; at least 3 user stories.
- suggested_questions: cover gaps in business, features, technical, UX, deployment when unclear.
- Do NOT echo INPUT keys as top-level JSON."""

_SCOPE_REPAIR = (
    "Return JSON with keys: project_summary, business_requirements, functional_requirements, "
    "non_functional_requirements, user_stories, draft_scope_document, suggested_questions."
)


class ScopeGatheringAgent:
    """Produces BR/FR/NFR, user stories, scope draft, and suggested questions."""

    def __init__(self, settings: Settings) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._settings = settings

    async def gather(
        self,
        rfp: RFPDocument,
        requirements: RequirementList,
        summary: RFPSummary | None = None,
    ) -> PresalesScopeDocument:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return _mock_scope(rfp, requirements)
        try:
            user = json.dumps(
                {
                    "filename": rfp.filename,
                    "rfp_excerpt": rfp.raw_text[:3500],
                    "executive_summary": summary.model_dump() if summary else None,
                    "requirements": [
                        {
                            "id": r.requirement_id,
                            "type": r.type.value,
                            "priority": r.priority,
                            "text": r.text[:250],
                        }
                        for r in requirements.requirements[:30]
                    ],
                }
            )
            data = await self._llm.chat_json(
                SCOPE_PROMPT,
                user,
                max_tokens=4096,
                repair_schema=_SCOPE_REPAIR,
            )
            if "_unparsed" in data:
                raise LLMError("Scope gathering agent got non-JSON from model.")
            return _coerce_scope(data, rfp, requirements)
        except LLMError:
            raise
        except (ValidationError, ValueError, TypeError) as exc:
            if not self._settings.llm_fallback_on_error:
                raise
            log.warning("scope.llm_fallback", error=str(exc))
            return _mock_scope(rfp, requirements)


def _coerce_req_list(raw: object, prefix: str) -> list[ScopeRequirementItem]:
    if not isinstance(raw, list):
        return []
    out: list[ScopeRequirementItem] = []
    for i, item in enumerate(raw[:40]):
        if isinstance(item, str) and item.strip():
            out.append(
                ScopeRequirementItem(
                    requirement_id=f"{prefix}-{i + 1:03d}",
                    text=item.strip(),
                )
            )
        elif isinstance(item, dict):
            rid = str(item.get("requirement_id") or f"{prefix}-{i + 1:03d}")
            text = str(item.get("text") or "").strip()
            if text:
                out.append(
                    ScopeRequirementItem(
                        requirement_id=rid,
                        text=text,
                        priority=str(item.get("priority") or "mandatory"),
                        notes=str(item.get("notes") or ""),
                    )
                )
    return out


def _coerce_stories(raw: object) -> list[UserStory]:
    if not isinstance(raw, list):
        return []
    out: list[UserStory] = []
    for i, item in enumerate(raw[:25]):
        if not isinstance(item, dict):
            continue
        story = str(item.get("story") or "").strip()
        if not story:
            continue
        ac = item.get("acceptance_criteria")
        criteria = [str(x) for x in ac[:8]] if isinstance(ac, list) else []
        out.append(
            UserStory(
                story_id=str(item.get("story_id") or f"US-{i + 1:03d}"),
                role=str(item.get("role") or ""),
                story=story,
                acceptance_criteria=criteria,
            )
        )
    return out


def _coerce_scope(
    data: dict[str, object], rfp: RFPDocument, requirements: RequirementList
) -> PresalesScopeDocument:
    baseline = _mock_scope(rfp, requirements)
    sq = data.get("suggested_questions", baseline.suggested_questions)
    suggested = [str(x).strip() for x in sq[:12]] if isinstance(sq, list) else baseline.suggested_questions

    return PresalesScopeDocument(
        project_summary=str(data.get("project_summary") or baseline.project_summary)[:8000],
        business_requirements=_coerce_req_list(data.get("business_requirements"), "BR")
        or baseline.business_requirements,
        functional_requirements=_coerce_req_list(data.get("functional_requirements"), "FR")
        or baseline.functional_requirements,
        non_functional_requirements=_coerce_req_list(
            data.get("non_functional_requirements"), "NFR"
        )
        or baseline.non_functional_requirements,
        user_stories=_coerce_stories(data.get("user_stories")) or baseline.user_stories,
        draft_scope_document=str(
            data.get("draft_scope_document") or baseline.draft_scope_document
        )[:12000],
        suggested_questions=suggested or baseline.suggested_questions,
    )


def _mock_scope(rfp: RFPDocument, requirements: RequirementList) -> PresalesScopeDocument:
    fn = [r for r in requirements.requirements if r.type.value == "functional"][:5]
    nfn = [r for r in requirements.requirements if r.type.value != "functional"][:5]
    return PresalesScopeDocument(
        project_summary=f"Pre-sales scope analysis for {rfp.filename}.",
        business_requirements=[
            ScopeRequirementItem(requirement_id="BR-001", text="Deliver solution per RFP objectives.")
        ],
        functional_requirements=[
            ScopeRequirementItem(requirement_id=r.requirement_id, text=r.text[:300])
            for r in fn
        ]
        or [
            ScopeRequirementItem(requirement_id="FR-001", text="Core workflow per RFP.")
        ],
        non_functional_requirements=[
            ScopeRequirementItem(requirement_id=r.requirement_id, text=r.text[:300])
            for r in nfn
        ]
        or [
            ScopeRequirementItem(
                requirement_id="NFR-001", text="Availability and security per client standards."
            )
        ],
        user_stories=[
            UserStory(
                story_id="US-001",
                role="user",
                story="As a user I want to complete the primary workflow described in the RFP.",
                acceptance_criteria=["Happy path documented", "Errors handled"],
            )
        ],
        draft_scope_document="## Scope\n\nIn-scope: requirements extracted from upload.\n\nOut-of-scope: TBD pending clarification.",
        suggested_questions=[
            "What are the target user roles?",
            "Is admin panel required?",
            "Preferred cloud and database?",
            "Authentication method (SSO, email/password)?",
            "Expected go-live timeline?",
        ],
    )
