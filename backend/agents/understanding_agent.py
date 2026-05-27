from __future__ import annotations

import re

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient
from core.logging import get_logger
from models.rfp import MAFLevel, Requirement, RequirementList, RequirementType, RFPDocument

log = get_logger(__name__)


class UnderstandingAgent:
    """Requirement extraction — task-req-extract-v1 (LLM or heuristic fallback)."""

    SYSTEM = """You are the RFP Understanding Agent. Extract requirements as JSON with key
"requirements": list of objects with requirement_id, type (functional|non_functional|constraint|deadline),
priority (mandatory|desirable|optional), maf_classification (M|A|F), source_section, text, ambiguity_score (0-10).
Use REQ-001 style ids. If unsure, still list best-effort items."""

    def __init__(self, settings: Settings) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._settings = settings

    async def extract_requirements(self, rfp: RFPDocument) -> RequirementList:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return RequirementList(requirements=_heuristic_requirements(rfp))
        try:
            user = f"RFP filename: {rfp.filename}\n\nExcerpt:\n{rfp.raw_text[:6000]}"
            data = await self._llm.chat_json(self.SYSTEM, user)
            if "_unparsed" in data:
                preview = str(data["_unparsed"])[:200]
                raise LLMError(f"Understanding agent got non-JSON from model: {preview}…")
            items = data.get("requirements") if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise LLMError("Model JSON is missing a 'requirements' array.")
            reqs: list[Requirement] = []
            for i, raw in enumerate(items):
                if not isinstance(raw, dict):
                    continue
                rid = str(raw.get("requirement_id") or f"REQ-{i + 1:03d}")
                rtype = _safe_enum(RequirementType, raw.get("type"), RequirementType.FUNCTIONAL)
                prio = str(raw.get("priority") or "desirable")
                maf = _safe_enum(MAFLevel, raw.get("maf_classification"), MAFLevel.ACCEPTABLE)
                if prio == "mandatory":
                    maf = MAFLevel.MINIMUM
                reqs.append(
                    Requirement(
                        requirement_id=rid,
                        type=rtype,
                        priority=prio,
                        maf_classification=maf,
                        source_section=str(raw.get("source_section") or "unknown"),
                        text=str(raw.get("text") or "")[:4000],
                        ambiguity_score=_resolve_ambiguity(
                            raw.get("ambiguity_score"), str(raw.get("text") or "")
                        ),
                    )
                )
            if not reqs:
                raise LLMError("Model returned an empty requirements list.")
            return RequirementList(requirements=reqs)
        except LLMError:
            raise
        except (ValueError, TypeError) as exc:
            if not self._settings.llm_fallback_on_error:
                raise
            log.warning("understanding.llm_fallback", error=str(exc))
            return RequirementList(requirements=_heuristic_requirements(rfp))


def _heuristic_requirements(rfp: RFPDocument) -> list[Requirement]:
    """Deterministic fallback for tests / offline."""
    lines = [ln.strip() for ln in rfp.raw_text.splitlines() if len(ln.strip()) > 40]
    out: list[Requirement] = []
    for i, line in enumerate(lines[:25]):
        prio = "mandatory" if re.search(r"\b(shall|must|required)\b", line, re.I) else "desirable"
        out.append(
            Requirement(
                requirement_id=f"REQ-{i + 1:03d}",
                type=RequirementType.FUNCTIONAL,
                priority=prio,
                maf_classification=MAFLevel.MINIMUM if prio == "mandatory" else MAFLevel.ACCEPTABLE,
                source_section="heuristic",
                text=line[:2000],
                ambiguity_score=5,
            )
        )
    if not out:
        out.append(
            Requirement(
                requirement_id="REQ-001",
                type=RequirementType.FUNCTIONAL,
                priority="mandatory",
                maf_classification=MAFLevel.MINIMUM,
                source_section="default",
                text=rfp.raw_text[:2000] or "Empty document",
                ambiguity_score=2,
            )
        )
    return out


def _estimate_ambiguity(text: str) -> int:
    """Heuristic 0–10 score when the model returns 0 or omits ambiguity."""
    if not text.strip():
        return 0
    score = 2
    vague = re.search(
        r"\b(appropriate|reasonable|as needed|as required|flexible|scalable|"
        r"best effort|vendor shall|may|should consider|etc\.?|tbd|to be determined)\b",
        text,
        re.I,
    )
    if vague:
        score += 3
    if "?" in text:
        score += 2
    if len(text) < 60:
        score += 2
    if re.search(r"\b(shall|must|required)\b", text, re.I):
        score += 1
    return min(10, score)


def _resolve_ambiguity(raw_value: object, requirement_text: str) -> int:
    llm_score = _coerce_score(raw_value, 0)
    estimated = _estimate_ambiguity(requirement_text)
    if llm_score <= 0:
        return estimated
    return llm_score


def _coerce_score(value: object, default: int) -> int:
    try:
        score = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(0, min(10, score))


def _safe_enum(enum_cls, value, default):
    try:
        return enum_cls(str(value))
    except Exception:
        return default
