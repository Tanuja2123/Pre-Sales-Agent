from __future__ import annotations

from agents.response_agent import (
    _apply_company_name,
    _extract_sections,
    _normalize_final_document,
    apply_company_name_to_draft,
)
from core.llm import _groq_payload_too_large
from models.rfp import DraftResponse, DraftSection


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text
        self.headers: dict[str, str] = {}


def test_groq_429_is_not_payload_too_large() -> None:
    resp = _FakeResponse(
        429,
        '{"error":{"message":"Rate limit reached ... Please try again in 10.52s"}}',
    )
    assert _groq_payload_too_large(resp) is False  # type: ignore[arg-type]


def test_extract_sections_from_top_level_body() -> None:
    data = {"body": "# Executive Summary\nWe propose a secure solution."}
    sections = _normalize_final_document(_extract_sections(data))
    assert len(sections) == 1
    assert "Executive Summary" in sections[0].body


def test_extract_sections_from_proposal_key() -> None:
    data = {"proposal": "# Cover Page\nClient: Example Corp"}
    sections = _normalize_final_document(_extract_sections(data))
    assert sections[0].section_id == "FINAL-PROPOSAL"


def test_extract_sections_from_nested_section_object() -> None:
    data = {
        "section_id": "FINAL-PROPOSAL",
        "title": "Enterprise Proposal Response",
        "body": "# Conclusion\nThank you for the opportunity.",
    }
    sections = _normalize_final_document(_extract_sections(data))
    assert sections[0].body.startswith("# Conclusion")


def test_title_only_sections_are_not_substantive() -> None:
    from agents.response_agent import _sections_are_substantive
    from models.rfp import DraftSection

    sections = [
        DraftSection(
            section_id="FINAL-PROPOSAL",
            title="Enterprise Proposal Response",
            body="Enterprise Proposal Response",
        )
    ]
    assert _sections_are_substantive(sections) is False


def test_apply_company_name_replaces_placeholders() -> None:
    body = (
        "# Cover Page\n"
        "Company Name: [COMPANY NAME]\n"
        "Prepared by [Company Name] for the client.\n"
    )
    assert "MAQ Software" in _apply_company_name(body, "MAQ Software")
    assert "[COMPANY NAME]" not in _apply_company_name(body, "MAQ Software")


def test_apply_company_name_to_draft() -> None:
    draft = DraftResponse(
        sections=[
            DraftSection(
                section_id="FINAL-PROPOSAL",
                title="Enterprise Proposal Response",
                body="Company Name: Your Company",
            )
        ]
    )
    updated = apply_company_name_to_draft(draft, "MAQ Software")
    assert updated.sections[0].body == "Company Name: MAQ Software"
