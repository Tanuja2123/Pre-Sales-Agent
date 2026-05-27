from __future__ import annotations

import json

from pydantic import ValidationError

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient
from core.logging import get_logger
from models.maf import MAFContext
from models.rfp import MAFLevel, RequirementList, RFPDocument, RFPSummary

log = get_logger(__name__)

SUMMARIZE_PROMPT = """You are the RFP Summarization Agent.

The user message is INPUT only. Your reply must be a NEW compact JSON object with EXACTLY these keys:
- client_overview (string, 2-4 sentences max)
- strategic_objectives (string, brief)
- key_requirements (array of at most 10 short strings)
- evaluation_criteria (string, brief)
- risk_flags (array of short strings, can be empty)
- bid_strategy (string, brief)
- go_no_go_recommendation (string: "PROCEED - ..." or "NO_BID - ...")

Rules:
- Do NOT echo or restructure the RFP document.
- Do NOT use keys like rfp_excerpt, document_version, or section headings as JSON keys.
- Keep the entire response under 1200 words."""

_SUMMARY_REPAIR_SCHEMA = (
    "Output JSON with keys: client_overview, strategic_objectives, key_requirements (string[]), "
    "evaluation_criteria, risk_flags (string[]), bid_strategy, go_no_go_recommendation."
)


class SummarizationAgent:
    """SK-style templated chain — task-summarize-v1 / prompt-summarize-v1."""

    def __init__(self, settings: Settings, maf_context: MAFContext | None = None) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._settings = settings
        self.maf_context = maf_context or MAFContext(target_level=MAFLevel.ACCEPTABLE)

    async def summarize(self, rfp: RFPDocument, requirements: RequirementList) -> RFPSummary:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return _mock_summary(rfp, requirements)
        try:
            user = json.dumps(
                {
                    "rfp_filename": rfp.filename,
                    "rfp_excerpt": rfp.raw_text[:2500],
                    "requirement_count": len(requirements.requirements),
                    "requirements_sample": [
                        {
                            "id": r.requirement_id,
                            "priority": r.priority,
                            "text": r.text[:200],
                        }
                        for r in requirements.requirements[:15]
                    ],
                    "maf_target": self.maf_context.target_level.value,
                }
            )
            data = await self._llm.chat_json(
                SUMMARIZE_PROMPT,
                user,
                max_tokens=1536,
                repair_schema=_SUMMARY_REPAIR_SCHEMA,
            )
            if "_unparsed" in data:
                raise LLMError("Summarization agent got non-JSON from model.")
            return _coerce_summary(data, rfp, requirements)
        except LLMError:
            raise
        except (ValidationError, ValueError, TypeError) as exc:
            if not self._settings.llm_fallback_on_error:
                raise
            log.warning("summarization.llm_fallback", error=str(exc))
            return _mock_summary(rfp, requirements)


def _coerce_summary(
    data: dict[str, object], rfp: RFPDocument, requirements: RequirementList
) -> RFPSummary:
    """Map model output to RFPSummary even if some keys are missing."""
    mand = [r for r in requirements.requirements if r.priority == "mandatory"]
    default_keys = [r.text[:120] for r in mand[:10]] or [
        r.text[:120] for r in requirements.requirements[:10]
    ]
    key_req = data.get("key_requirements")
    if not isinstance(key_req, list):
        key_req = default_keys
    else:
        key_req = [str(x)[:200] for x in key_req[:10]]

    risk = data.get("risk_flags")
    if not isinstance(risk, list):
        risk = []
    else:
        risk = [str(x)[:200] for x in risk[:10]]

    return RFPSummary(
        client_overview=str(
            data.get("client_overview")
            or f"RFP from {rfp.filename} with {len(requirements.requirements)} requirements."
        )[:2000],
        strategic_objectives=str(
            data.get("strategic_objectives") or "Deliver a compliant, competitive proposal."
        )[:2000],
        key_requirements=key_req,
        evaluation_criteria=str(data.get("evaluation_criteria") or "See RFP evaluation section.")[
            :2000
        ],
        risk_flags=risk,
        bid_strategy=str(data.get("bid_strategy") or "Target acceptable baseline coverage.")[:2000],
        go_no_go_recommendation=str(
            data.get("go_no_go_recommendation")
            or ("PROCEED" if rfp.raw_text.strip() else "NO_BID — empty document")
        )[:500],
    )


def _mock_summary(rfp: RFPDocument, requirements: RequirementList) -> RFPSummary:
    mand = [r for r in requirements.requirements if r.priority == "mandatory"]
    return RFPSummary(
        client_overview=f"Summary for {rfp.filename}: {len(requirements.requirements)} requirements identified.",
        strategic_objectives="Deliver compliant, competitive response aligned to evaluation criteria.",
        key_requirements=[r.text[:120] for r in mand[:10]]
        or [r.text[:120] for r in requirements.requirements[:10]],
        evaluation_criteria="See RFP evaluation section; weights not parsed in heuristic mode.",
        risk_flags=[],
        bid_strategy="Target Acceptable baseline; pursue Full on top-weighted themes.",
        go_no_go_recommendation="PROCEED" if rfp.raw_text.strip() else "NO_BID — empty document",
    )
