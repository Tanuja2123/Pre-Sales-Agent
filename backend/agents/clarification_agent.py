from __future__ import annotations

import json
import uuid

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient
from core.logging import get_logger
from models.rfp import ClarifyingQuestion, QuestionList, RequirementList

log = get_logger(__name__)

CLARIFY_PROMPT = """You are a pre-sales analyst writing a client clarification email before submitting a proposal.

The user message lists RFP requirements. For the items that are vague, risky, or mandatory, write specific questions you would email the client.

Reply with JSON: {"questions": [ ... ]}

Each question must include:
- question_id (Q-001, Q-002, ...)
- category: scope | evaluation | commercial | submission | market
- priority: CRITICAL | STRATEGIC | STANDARD
- question_text: a complete, specific question (mention concrete topics: timelines, SLAs, security, integrations, data residency, acceptance criteria, etc.)
- assumption_if_unanswered: what your bid team will assume if the client does not answer
- source_requirement: the REQ-xxx id you are clarifying

Rules:
- Produce 3 to 8 questions.
- question_text must be a real business question, not a label or placeholder.
- Never write generic phrases like "clear question for the client" or "what we assume if they do not answer" without specifics.
- Link each question to one requirement id from the input."""

_CLARIFY_REPAIR_SCHEMA = (
    'Return {"questions":[{"question_id":"Q-001","category":"scope","priority":"STANDARD",'
    '"question_text":"...","assumption_if_unanswered":"...","source_requirement":"REQ-001"}]} '
    "with at least 3 questions."
)


class ClarificationAgent:
    """AutoGen-style tool use simulated via structured JSON — task-ambiguity-v1, task-question-gen-v1."""

    def __init__(self, settings: Settings) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._settings = settings

    async def generate_questions(self, requirements: RequirementList) -> QuestionList:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return _mock_questions(requirements)
        try:
            user = json.dumps(
                {
                    "requirements": [
                        {
                            "requirement_id": r.requirement_id,
                            "priority": r.priority,
                            "ambiguity_score": r.ambiguity_score,
                            "text": r.text[:300],
                        }
                        for r in requirements.requirements[:25]
                    ]
                }
            )
            data = await self._llm.chat_json(
                CLARIFY_PROMPT,
                user,
                max_tokens=1536,
                repair_schema=_CLARIFY_REPAIR_SCHEMA,
            )
            if "_unparsed" in data:
                raise LLMError("Clarification agent got non-JSON from model.")

            questions = _extract_questions(data)
            if not questions:
                retry_user = json.dumps(
                    {
                        "instruction": "Generate at least 5 clarifying questions for these mandatory items.",
                        "mandatory": [
                            {"id": r.requirement_id, "text": r.text[:200]}
                            for r in requirements.requirements
                            if r.priority == "mandatory"
                        ][:10],
                    }
                )
                data2 = await self._llm.chat_json(
                    CLARIFY_PROMPT,
                    retry_user,
                    max_tokens=1536,
                    repair_schema=_CLARIFY_REPAIR_SCHEMA,
                )
                questions = _extract_questions(data2)

            if not questions:
                raise LLMError(
                    "Model returned an empty questions list. "
                    "Try OLLAMA_MODEL=phi3.5 in .env."
                )
            return QuestionList(questions=questions[:8])
        except LLMError:
            raise
        except (ValueError, TypeError) as exc:
            if not self._settings.llm_fallback_on_error:
                raise
            log.warning("clarification.llm_fallback", error=str(exc))
            return _mock_questions(requirements)


def _extract_questions(data: dict[str, object]) -> list[ClarifyingQuestion]:
    for key in ("questions", "clarifying_questions", "clarifications"):
        raw = data.get(key)
        if isinstance(raw, list):
            parsed = _parse_question_list(raw)
            if parsed:
                return parsed
    return []


def _parse_question_list(items: list[object]) -> list[ClarifyingQuestion]:
    questions: list[ClarifyingQuestion] = []
    for i, item in enumerate(items):
        if isinstance(item, str) and item.strip():
            questions.append(
                ClarifyingQuestion(
                    question_id=f"Q-{i + 1:03d}",
                    category="scope",
                    priority="STANDARD",
                    question_text=item.strip()[:1000],
                    assumption_if_unanswered="Industry-standard interpretation applies.",
                    source_requirement="",
                )
            )
            continue
        if not isinstance(item, dict):
            continue

        qtext = str(
            item.get("question_text")
            or item.get("question")
            or item.get("text")
            or item.get("clarification")
            or ""
        ).strip()
        src = str(item.get("source_requirement") or item.get("requirement_id") or "")
        if not qtext:
            if src:
                qtext = f"Please clarify the intent and acceptance criteria for {src}."
            else:
                qtext = f"Please clarify requirement item {i + 1} from the RFP."

        questions.append(
            ClarifyingQuestion(
                question_id=str(item.get("question_id") or item.get("id") or f"Q-{i + 1:03d}"),
                category=str(item.get("category") or "scope")[:50],
                priority=str(item.get("priority") or "STANDARD")[:20],
                question_text=qtext[:1000],
                assumption_if_unanswered=str(
                    item.get("assumption_if_unanswered")
                    or item.get("assumption")
                    or "We will apply a reasonable industry-standard interpretation."
                )[:500],
                source_requirement=src[:100],
            )
        )
    return questions


def _mock_questions(requirements: RequirementList) -> QuestionList:
    qs: list[ClarifyingQuestion] = []
    for r in requirements.requirements:
        if r.ambiguity_score >= 7:
            qs.append(
                ClarifyingQuestion(
                    question_id=f"Q-{uuid.uuid4().hex[:6]}",
                    category="scope",
                    priority="CRITICAL" if r.maf_classification.value == "M" else "STRATEGIC",
                    question_text=f"Please clarify intent of: {r.text[:200]}",
                    assumption_if_unanswered="We will map to industry-standard interpretation.",
                    source_requirement=r.requirement_id,
                )
            )
        if len(qs) >= 8:
            break
    if not qs:
        qs.append(
            ClarifyingQuestion(
                question_id="Q-001",
                category="evaluation",
                priority="STANDARD",
                question_text="Confirm evaluation weighting for mandatory requirements.",
                assumption_if_unanswered="Equal weighting within mandatory bucket.",
                source_requirement="",
            )
        )
    return QuestionList(questions=qs)
