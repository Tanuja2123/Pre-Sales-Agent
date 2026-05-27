from __future__ import annotations

from agents.evaluation_agent import _coerce_audit, _filter_blockers, _heuristic_audit
from models.rfp import DraftResponse, DraftSection, Requirement, RequirementList, RequirementType


def _req(rid: str, *, mandatory: bool = True) -> Requirement:
    return Requirement(
        requirement_id=rid,
        type=RequirementType.FUNCTIONAL,
        priority="mandatory" if mandatory else "desirable",
        maf_classification="M",
        source_section="s1",
        text=f"The vendor shall deliver capability for {rid} with full compliance.",
        ambiguity_score=2,
    )


def test_filter_blockers_drops_covered_req_ids() -> None:
    draft = DraftResponse(
        sections=[
            DraftSection(
                section_id="S-1",
                title="Approach",
                body="We address REQ-001 and REQ-002 with our proven delivery model.",
            )
        ]
    )
    reqs = RequirementList(requirements=[_req("REQ-001"), _req("REQ-002"), _req("REQ-003")])
    filtered = _filter_blockers(["REQ-001", "REQ-002"], draft, reqs)
    assert filtered == []


def test_coerce_audit_ignores_false_positive_llm_blockers() -> None:
    draft = DraftResponse(
        sections=[
            DraftSection(
                section_id="S-1",
                title="Approach",
                body="For REQ-001 we will provide 24/7 support. REQ-002 is covered in section 2.",
            )
        ]
    )
    reqs = RequirementList(
        requirements=[_req("REQ-001"), _req("REQ-002"), _req("REQ-003", mandatory=False)]
    )
    data = {
        "minimum_met": False,
        "acceptable_coverage": 0.2,
        "full_opportunities": [],
        "overall_rating": "M",
        "blockers": ["REQ-001", "REQ-002"],
    }
    audit = _coerce_audit(data, draft, reqs)
    assert audit.minimum_met is True
    assert audit.blockers == []


def test_heuristic_flags_truly_missing() -> None:
    draft = DraftResponse(
        sections=[DraftSection(section_id="S-1", title="Summary", body="Generic proposal text only.")]
    )
    reqs = RequirementList(requirements=[_req("REQ-001")])
    audit = _heuristic_audit(draft, reqs)
    assert audit.minimum_met is False
    assert any("REQ-001" in b for b in audit.blockers)
