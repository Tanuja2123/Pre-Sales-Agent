from __future__ import annotations

import json
import re

from pydantic import ValidationError

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient
from core.logging import get_logger
from models.maf import MAFAuditResult
from models.rfp import DraftResponse, MAFLevel, Requirement, RequirementList

log = get_logger(__name__)

_REQ_ID_RE = re.compile(r"REQ-\d+", re.IGNORECASE)

CRITIC_PROMPT = """You are the MAF Evaluation Agent scoring a vendor proposal draft against mandatory requirements.

Reply with NEW JSON only:
{
  "minimum_met": true,
  "acceptable_coverage": 0.85,
  "full_opportunities": ["specific improvement 1"],
  "overall_rating": "A",
  "blockers": []
}

Rules:
- minimum_met: true if each mandatory requirement is substantively addressed in the draft (by id or by clear paraphrase).
- blockers: only list requirements that are truly missing. Use format "REQ-003: brief reason" — never list an id that appears in the draft.
- If the draft cites REQ-001, REQ-002, etc., do NOT list them as blockers.
- overall_rating: M, A, or F only.
- Do NOT echo the full requirements or draft as top-level JSON keys."""

_AUDIT_REPAIR_SCHEMA = (
    "Return JSON with keys: minimum_met (bool), acceptable_coverage (0-1), "
    "full_opportunities (string[]), overall_rating (M|A|F), blockers (string[])."
)


class EvaluationAgent:
    """Evaluation agent — task-maf-audit-v1."""

    def __init__(self, settings: Settings) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._settings = settings

    async def audit(self, draft: DraftResponse, requirements: RequirementList) -> MAFAuditResult:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return _heuristic_audit(draft, requirements)
        try:
            bodies = _draft_bodies(draft)
            user = json.dumps(
                {
                    "mandatory_requirements": [
                        {"id": r.requirement_id, "text": r.text[:200]}
                        for r in requirements.requirements
                        if r.priority == "mandatory"
                    ][:25],
                    "all_requirement_count": len(requirements.requirements),
                    "draft_sections": [
                        {
                            "section_id": s.section_id,
                            "title": s.title,
                            "body": s.body[:1200],
                        }
                        for s in draft.sections[:10]
                    ],
                    "draft_excerpt": bodies[:3000],
                }
            )
            data = await self._llm.chat_json(
                CRITIC_PROMPT,
                user,
                max_tokens=1024,
                repair_schema=_AUDIT_REPAIR_SCHEMA,
            )
            if "_unparsed" in data:
                raise LLMError("Evaluation agent got non-JSON from model.")
            return _coerce_audit(data, draft, requirements)
        except LLMError:
            raise
        except (ValidationError, ValueError, TypeError) as exc:
            if not self._settings.llm_fallback_on_error:
                raise
            log.warning("evaluation.llm_fallback", error=str(exc))
            return _heuristic_audit(draft, requirements)


def _draft_bodies(draft: DraftResponse) -> str:
    return " ".join(s.body for s in draft.sections).lower()


def _unwrap_audit_payload(data: dict[str, object]) -> dict[str, object]:
    for key in ("audit", "maf_audit", "evaluation", "result"):
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
    return data


def _safe_maf_level(value: object, default: MAFLevel) -> MAFLevel:
    if isinstance(value, MAFLevel):
        return value
    text = str(value).strip().upper()
    if text in ("M", "MINIMUM"):
        return MAFLevel.MINIMUM
    if text in ("F", "FULL"):
        return MAFLevel.FULL
    if text in ("A", "ACCEPTABLE"):
        return MAFLevel.ACCEPTABLE
    return default


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "yes", "1"):
        return True
    if text in ("false", "no", "0"):
        return False
    return default


def _find_requirement(requirements: RequirementList, req_id: str) -> Requirement | None:
    needle = req_id.strip().upper()
    for r in requirements.requirements:
        if r.requirement_id.upper() == needle:
            return r
    return None


def _requirement_covered(req: Requirement, bodies: str) -> bool:
    """True when draft text references the requirement id or substantive content."""
    rid = req.requirement_id.lower()
    if rid in bodies:
        return True
    normalized = re.sub(r"\s+", " ", req.text.lower()).strip()
    if len(normalized) >= 24 and normalized[:80] in bodies:
        return True
    words = [w for w in re.findall(r"[a-z]{4,}", normalized) if len(w) >= 4]
    if len(words) >= 3:
        hits = sum(1 for w in words[:15] if w in bodies)
        if hits >= max(2, len(words[:15]) // 3):
            return True
    return False


def _expand_blocker_tokens(raw: str) -> list[str]:
    """Split 'REQ-001; REQ-002' or list entries into individual blocker strings."""
    parts = re.split(r"[;\n,]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _filter_blockers(
    blockers: list[str], draft: DraftResponse, requirements: RequirementList
) -> list[str]:
    """Drop LLM false positives when the draft already mentions the requirement."""
    bodies = _draft_bodies(draft)
    out: list[str] = []
    seen: set[str] = set()

    for entry in blockers:
        for piece in _expand_blocker_tokens(entry):
            req_ids = _REQ_ID_RE.findall(piece)
            if req_ids:
                actually_missing: list[str] = []
                for rid in req_ids:
                    req = _find_requirement(requirements, rid)
                    if req and not _requirement_covered(req, bodies):
                        actually_missing.append(rid.upper())
                if not actually_missing:
                    continue
                piece = f"Missing coverage: {', '.join(actually_missing)}"

            key = piece.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(piece[:500])

    return out


def _coerce_audit(
    data: dict[str, object], draft: DraftResponse, requirements: RequirementList
) -> MAFAuditResult:
    """Map LLM output to MAFAuditResult; verify blockers against draft text."""
    payload = _unwrap_audit_payload(data)
    heuristic = _heuristic_audit(draft, requirements)

    blockers_raw = payload.get("blockers")
    if isinstance(blockers_raw, list):
        llm_blockers = [str(b) for b in blockers_raw if str(b).strip()]
    else:
        llm_blockers = []

    verified = _filter_blockers(llm_blockers, draft, requirements)
    # Merge with heuristic misses (draft-based, avoids model listing every REQ id)
    final_blockers = list(verified)
    for msg in heuristic.blockers:
        if msg not in final_blockers:
            final_blockers.append(msg)

    minimum_met = len(final_blockers) == 0

    coverage_raw = payload.get("acceptable_coverage", heuristic.acceptable_coverage)
    try:
        coverage = float(coverage_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        coverage = heuristic.acceptable_coverage
    coverage = max(0.0, min(1.0, coverage))
    if minimum_met and coverage < 0.7:
        coverage = max(coverage, 0.75)

    opps_raw = payload.get("full_opportunities", heuristic.full_opportunities)
    if isinstance(opps_raw, list):
        opportunities = [str(o)[:300] for o in opps_raw[:10] if str(o).strip()]
    else:
        opportunities = list(heuristic.full_opportunities)

    rating = _safe_maf_level(
        payload.get("overall_rating"),
        MAFLevel.ACCEPTABLE if minimum_met else MAFLevel.MINIMUM,
    )

    if not minimum_met:
        log.info("maf.audit.gaps", blockers=final_blockers[:8])

    return MAFAuditResult(
        minimum_met=minimum_met,
        acceptable_coverage=coverage,
        full_opportunities=opportunities or list(heuristic.full_opportunities),
        overall_rating=rating,
        blockers=final_blockers,
    )


def _heuristic_audit(draft: DraftResponse, requirements: RequirementList) -> MAFAuditResult:
    bodies = _draft_bodies(draft)
    blockers: list[str] = []
    mandatory = [r for r in requirements.requirements if r.priority == "mandatory"]
    if not mandatory:
        mandatory = requirements.requirements[:10]

    for r in mandatory:
        if not _requirement_covered(r, bodies):
            blockers.append(
                f"{r.requirement_id}: no clear coverage in draft (add explicit mention)"
            )

    minimum_met = len(blockers) == 0
    covered = sum(1 for r in mandatory if _requirement_covered(r, bodies))
    coverage = (covered / len(mandatory)) if mandatory else 1.0

    return MAFAuditResult(
        minimum_met=minimum_met,
        acceptable_coverage=coverage,
        full_opportunities=["Expand win themes on top-weighted criteria."],
        overall_rating=MAFLevel.ACCEPTABLE if minimum_met else MAFLevel.MINIMUM,
        blockers=blockers,
    )
