from __future__ import annotations

import json
import re

from core.config import Settings
from core.llm import LLMError, OpenAICompatibleClient, groq_cooldown
from core.logging import get_logger
from models.rfp import DraftResponse, DraftSection, RequirementList, RFPSummary
from rag.retrieval import AbstractVectorStore

log = get_logger(__name__)

_PROPOSAL_HEADINGS = [
    "Cover Page",
    "Executive Summary",
    "About the Company",
    "Understanding of Client Requirements",
    "Proposed Solution",
    "Scope of Work",
    "Project Timeline & Implementation Plan",
    "Team Structure",
    "Commercial Proposal / Pricing",
    "Risk Management",
    "Support & Maintenance",
    "Competitive Advantages",
    "Compliance Matrix",
    "Terms and Conditions",
    "Conclusion",
]

_DRAFT_JSON_SCHEMA = (
    '{"sections":[{"section_id":"FINAL-PROPOSAL","title":"Enterprise Proposal Response","body":"..."}]}'
)

_DRAFT_REPAIR_SCHEMA = (
    f"Return {_DRAFT_JSON_SCHEMA} with one non-empty body containing all 15 requested proposal headings."
)

DRAFT_PROMPT = """Act as a senior business proposal consultant and enterprise bid writer with expertise in creating winning Response to Proposal (RFP/RFQ/RFI) documents for companies responding to clients.

Your task is to draft a highly professional, persuasive, and structured proposal response document from [COMPANY NAME] to [CLIENT NAME].

The proposal response should look like a real enterprise-level submission used by consulting firms, IT companies, engineering firms, SaaS providers, or service organizations.

The user message JSON contains RFP context, extracted requirements, executive summary, and a clarification_resolution_document built from the user's answers to clarifying questions. Treat the clarification document as authoritative for resolved ambiguities; where no answer was provided, state assumptions clearly.

Reply with a NEW JSON object only:
{"sections": [
  {"section_id": "FINAL-PROPOSAL", "title": "Enterprise Proposal Response", "body": "..."}
]}

The document body must contain these sections in professional business language, using markdown headings (# / ##), bullet points, and tables where appropriate:

1. Cover Page — Proposal Title, Client Name, Company Name, Submission Date, Confidentiality Statement
2. Executive Summary — understanding of requirements, business goals, key challenges, value proposition, why we are the right partner
3. About the Company — overview, experience, industry presence, certifications/awards, core competencies
4. Understanding of Client Requirements — problem statement, pain points, expected outcomes, strategic alignment
5. Proposed Solution — solution approach, methodology/framework, technologies/tools/platforms, architecture/workflow, innovation, scalability, security
6. Scope of Work — in-scope activities, out-of-scope activities, deliverables, milestones
7. Project Timeline & Implementation Plan — phase-wise implementation, duration, resources, deployment, testing, validation
8. Team Structure — key roles, hierarchy, relevant expertise
9. Commercial Proposal / Pricing — cost breakdown, licensing/services/support, payment terms, assumptions
10. Risk Management — key risks, mitigation strategies, governance model
11. Support & Maintenance — post-implementation support, SLA commitments, escalation matrix, maintenance approach
12. Competitive Advantages — why choose us, differentiators, case studies/success stories, ROI/business benefits
13. Compliance Matrix — requirement-wise table with Fully Compliant / Partially Compliant / Non-Compliant indicators
14. Terms and Conditions — legal/commercial terms, confidentiality, IP, termination clauses
15. Conclusion — final value summary, commitment statement, call to action

Formatting and style:
- Use formal corporate language in the style of Deloitte, Accenture, Infosys, TCS, McKinsey, IBM, or Capgemini.
- Return the complete proposal in ONE comprehensive section body (not separate JSON sections S-1, S-2, etc.).
- Make the response client-centric, persuasive yet concise, with measurable outcomes and business impact.
- Explicitly address mandatory requirements by requirement_id in Understanding, Proposed Solution, and Compliance Matrix.
- Integrate clarification_resolution_document answers throughout; do not ignore user-provided clarifications.
- Use additional_inputs (industry, project type, tone, length) from the payload when present.
- If final_pass is true, produce the strongest integrated final proposal using all context.
- Do NOT echo input keys (requirements, summary, rfp_excerpt) as top-level JSON keys.
- Do NOT copy the client's invitation language verbatim.
- The responding vendor is the company_name in additional_inputs (MAQ Software). Use it on the Cover Page, in About the Company, and throughout — never placeholders or invented vendor names."""

DRAFT_PROMPT_COMPACT = """Act as a senior enterprise bid writer. Draft a complete RFP proposal from [COMPANY NAME] to [CLIENT NAME].

Return JSON only:
{"sections":[{"section_id":"FINAL-PROPOSAL","title":"Enterprise Proposal Response","body":"..."}]}

Use one markdown body with ALL 15 headings in order:
Cover Page, Executive Summary, About the Company, Understanding of Client Requirements,
Proposed Solution, Scope of Work, Project Timeline & Implementation Plan, Team Structure,
Commercial Proposal / Pricing, Risk Management, Support & Maintenance, Competitive Advantages,
Compliance Matrix, Terms and Conditions, Conclusion.

Rules:
- Use clarification_resolution_document from the payload — it contains answers to clarifying questions.
- Address mandatory requirements by requirement_id.
- Include tables for Compliance Matrix; include pricing assumptions where exact costs are unknown.
- Write substantive content under every heading (not just titles).
- Do not echo input keys as top-level JSON keys.
- The responding vendor is company_name from additional_inputs — use it everywhere, not placeholders."""

PROSE_DRAFT_PROMPT = """Act as a senior business proposal consultant and enterprise bid writer.

Draft a complete, highly professional RFP/RFQ/RFI proposal response from [COMPANY NAME] to [CLIENT NAME] in markdown (not JSON).

Include all 15 sections with # headings:
Cover Page, Executive Summary, About the Company, Understanding of Client Requirements,
Proposed Solution, Scope of Work, Project Timeline & Implementation Plan, Team Structure,
Commercial Proposal / Pricing, Risk Management, Support & Maintenance, Competitive Advantages,
Compliance Matrix, Terms and Conditions, Conclusion.

Use the clarification_resolution_document in the user message — it contains the client's answers to clarifying questions. Integrate those answers throughout the proposal.

Write in formal consulting style (Deloitte, Accenture, Infosys, TCS level). Be client-centric, persuasive, and include measurable outcomes, tables, and bullet points where useful.
Use company_name from the payload as the responding vendor throughout — never placeholders or alternate vendor names."""

_MIN_DRAFT_BODY_CHARS = 400

_COMPANY_PLACEHOLDER_VALUES = (
    "[COMPANY NAME]",
    "[Company Name]",
    "[COMPANY]",
    "[Company]",
    "Your Company Name",
    "Your Company",
    "Our Company",
    "The Company",
)


def _default_company_name(settings: Settings) -> str:
    return (settings.proposal_company_name or "MAQ Software").strip()


def _inject_company_name(prompt: str, company_name: str) -> str:
    return prompt.replace("[COMPANY NAME]", company_name)


def _apply_company_name(body: str, company_name: str) -> str:
    if not body.strip() or not company_name:
        return body
    out = body
    for placeholder in _COMPANY_PLACEHOLDER_VALUES:
        out = out.replace(placeholder, company_name)
    out = re.sub(
        rf"Company Name:\s*(?:{'|'.join(re.escape(v) for v in _COMPANY_PLACEHOLDER_VALUES)})\s*",
        f"Company Name: {company_name}",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"Company Name:\s*\[[^\]]+\]",
        f"Company Name: {company_name}",
        out,
        flags=re.IGNORECASE,
    )
    return out


def apply_company_name_to_draft(draft: DraftResponse, company_name: str) -> DraftResponse:
    name = (company_name or "MAQ Software").strip()
    return DraftResponse(
        sections=[
            DraftSection(
                section_id=section.section_id,
                title=section.title,
                body=_apply_company_name(section.body, name),
            )
            for section in draft.sections
        ]
    )


def _is_groq_small_model(settings: Settings) -> bool:
    if settings.llm_backend != "groq":
        return False
    model = settings.groq_model.lower()
    return "8b" in model or "instant" in model


class ResponseDraftAgent:
    """Proposal draft via LLM (Groq / Ollama / Azure) — mock only when LLM_BACKEND=mock."""

    def __init__(self, settings: Settings, vector_store: AbstractVectorStore) -> None:
        self._llm = OpenAICompatibleClient(settings)
        self._vector_store = vector_store
        self._settings = settings

    async def draft(
        self,
        requirements: RequirementList,
        summary: RFPSummary,
        rfp_excerpt: str,
        critique_note: str | None = None,
        rag_context: str | None = None,
        clarification_context: str | None = None,
        final_pass: bool = False,
    ) -> DraftResponse:
        if self._settings.llm_backend == "mock":
            if self._settings.llm_only_mode:
                raise LLMError("LLM-only mode is enabled; mock backend is not allowed.")
            return _mock_draft(requirements, summary)

        if rag_context is None:
            rag_q = " ".join(summary.key_requirements[:8]) or "RFP compliance delivery security"
            snippets = await self._vector_store.query(rag_q, k=6)
            rag_context = "\n\n".join(s.text for s in snippets)

        user_payload = self._build_user_payload(
            requirements,
            summary,
            rfp_excerpt,
            rag_context,
            critique_note=critique_note,
            clarification_context=clarification_context,
            final_pass=final_pass,
        )
        max_tokens = _draft_max_tokens(self._settings)
        company_name = _default_company_name(self._settings)
        draft_prompt = _inject_company_name(
            DRAFT_PROMPT_COMPACT if _is_groq_small_model(self._settings) else DRAFT_PROMPT,
            company_name,
        )

        data = await self._llm.chat_json(
            draft_prompt,
            user_payload,
            max_tokens=max_tokens,
            repair_schema=_DRAFT_REPAIR_SCHEMA,
        )
        if "_unparsed" in data:
            raise LLMError("Response draft agent got non-JSON from model.")

        sections = _extract_sections(data)
        sections = _normalize_final_document(sections)
        if not _sections_are_substantive(sections):
            log.warning(
                "response.draft.retry",
                reason="empty or title-only sections on first pass",
                keys=sorted(str(k) for k in data.keys())[:12],
                body_chars=_section_body_chars(sections),
            )
            sections = []
        if not sections:
            await groq_cooldown(self._settings)
            retry_user = json.dumps(
                _build_retry_payload(
                    requirements,
                    summary,
                    clarification_context=clarification_context,
                    company_name=company_name,
                )
            )
            data = await self._llm.chat_json(
                draft_prompt,
                retry_user,
                max_tokens=max_tokens,
                repair_schema=_DRAFT_REPAIR_SCHEMA,
            )
            sections = _extract_sections(data)
            sections = _normalize_final_document(sections)
            if not _sections_are_substantive(sections):
                sections = []

        if not sections and isinstance(data, dict):
            repaired = await self._repair_empty_sections(data, draft_prompt, max_tokens)
            sections = _normalize_final_document(repaired)
            if not _sections_are_substantive(sections):
                sections = []

        if not sections:
            await groq_cooldown(self._settings)
            sections = await self._draft_prose_fallback(
                requirements,
                summary,
                clarification_context=clarification_context,
                max_tokens=max_tokens,
                company_name=company_name,
            )

        if not sections:
            raise LLMError(
                "Model did not return a substantive proposal draft. Groq free-tier limits may have "
                "truncated the output. Wait 1 minute and retry, or set GROQ_MODEL=llama-3.3-70b-versatile in .env."
            )

        log.info(
            "response.draft.complete",
            sections=len(sections),
            body_chars=_section_body_chars(sections),
            backend=self._settings.llm_backend,
        )
        return apply_company_name_to_draft(DraftResponse(sections=sections), company_name)

    def _build_user_payload(
        self,
        requirements: RequirementList,
        summary: RFPSummary,
        rfp_excerpt: str,
        rag_context: str,
        critique_note: str | None = None,
        clarification_context: str | None = None,
        final_pass: bool = False,
    ) -> str:
        compact = _is_groq_small_model(self._settings)
        req_limit = 15 if compact else 30
        req_text = 200 if compact else 350
        clar_limit = 1500 if compact else 5000
        company_name = _default_company_name(self._settings)
        payload: dict[str, object] = {
            "summary": {
                "client_overview": summary.client_overview[:600 if compact else 800],
                "strategic_objectives": summary.strategic_objectives[:350 if compact else 500],
                "key_requirements": summary.key_requirements[:6 if compact else 8],
                "evaluation_criteria": summary.evaluation_criteria[:250 if compact else 350],
                "bid_strategy": summary.bid_strategy[:350 if compact else 500],
                "go_no_go_recommendation": summary.go_no_go_recommendation[:200 if compact else 300],
            },
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "priority": r.priority,
                    "type": str(r.type),
                    "source_section": r.source_section,
                    "ambiguity_score": r.ambiguity_score,
                    "text": r.text[:req_text],
                }
                for r in requirements.requirements[:req_limit]
            ],
            "rag_snippets": rag_context[:800 if compact else 1500],
            "rfp_excerpt": rfp_excerpt[:1200 if compact else 2200],
            "final_pass": final_pass,
            "additional_inputs": {
                "company_name": company_name,
                "client_industry": "Infer from RFP context; if unknown, state as [INDUSTRY] to be confirmed.",
                "project_type": "Infer from RFP requirements and scope as [PROJECT TYPE].",
                "client_requirements": [
                    {"id": r.requirement_id, "priority": r.priority, "text": r.text[:req_text]}
                    for r in requirements.requirements[:req_limit]
                ],
                "company_services": summary.bid_strategy[:400 if compact else 800]
                or "Enterprise consulting, solution delivery, and managed support.",
                "proposal_objective": summary.strategic_objectives[:400 if compact else 800]
                or "Win the engagement with a compliant, differentiated, client-centric response.",
                "tone": "Professional / Technical / Executive / Persuasive",
                "length": "DETAILED",
            },
            "required_headings": _PROPOSAL_HEADINGS,
        }
        if critique_note and critique_note.strip():
            payload["revision_instructions"] = critique_note[:1200 if compact else 2000]
        if clarification_context and clarification_context.strip():
            payload["clarification_resolution_document"] = clarification_context[:clar_limit]
        return json.dumps(payload)

    async def _repair_empty_sections(
        self,
        data: dict[str, object],
        draft_prompt: str,
        max_tokens: int,
    ) -> list[DraftSection]:
        await groq_cooldown(self._settings)
        snippet = json.dumps(data)[:2500]
        repair_user = (
            f"{_DRAFT_REPAIR_SCHEMA}\n\n"
            "The model returned JSON without usable proposal sections. "
            "Rewrite it into one valid JSON object with a non-empty sections array.\n\n"
            f"{snippet}"
        )
        repaired = await self._llm.chat_json(
            "You convert malformed proposal JSON into the required sections schema.",
            repair_user,
            max_tokens=max_tokens,
            repair_schema=_DRAFT_REPAIR_SCHEMA,
        )
        return _extract_sections(repaired)

    async def _draft_prose_fallback(
        self,
        requirements: RequirementList,
        summary: RFPSummary,
        *,
        clarification_context: str | None,
        company_name: str,
        max_tokens: int,
    ) -> list[DraftSection]:
        log.warning("response.draft.prose_fallback", backend=self._settings.llm_backend)
        user = json.dumps(
            _build_retry_payload(
                requirements,
                summary,
                clarification_context=clarification_context,
                company_name=company_name,
            )
        )
        body = await self._llm.chat_text(
            _inject_company_name(PROSE_DRAFT_PROMPT, company_name),
            user,
            max_tokens=max_tokens,
        )
        if len(body.strip()) < _MIN_DRAFT_BODY_CHARS:
            return []
        return _normalize_final_document(
            [
                DraftSection(
                    section_id="FINAL-PROPOSAL",
                    title="Enterprise Proposal Response",
                    body=body.strip()[:20000],
                )
            ]
        )


def _build_retry_payload(
    requirements: RequirementList,
    summary: RFPSummary,
    *,
    clarification_context: str | None,
    company_name: str = "MAQ Software",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "task": "Write one complete enterprise RFP proposal with all 15 required sections.",
        "client_overview": summary.client_overview[:600],
        "strategic_objectives": summary.strategic_objectives[:500],
        "key_requirements": summary.key_requirements[:8],
        "mandatory_requirements": [
            {"id": r.requirement_id, "text": r.text[:300]}
            for r in requirements.requirements
            if r.priority == "mandatory"
        ][:15],
        "all_requirements": [
            {"id": r.requirement_id, "priority": r.priority, "text": r.text[:220]}
            for r in requirements.requirements[:20]
        ],
        "additional_inputs": {
            "company_name": company_name,
            "client_industry": "[INDUSTRY — infer from RFP]",
            "project_type": "[PROJECT TYPE — infer from RFP]",
            "company_services": summary.bid_strategy[:600] or "[COMPANY SERVICES]",
            "proposal_objective": summary.strategic_objectives[:600] or "[GOAL]",
            "tone": "Professional / Technical / Executive / Persuasive",
            "length": "DETAILED",
        },
        "required_headings": _PROPOSAL_HEADINGS,
    }
    if clarification_context and clarification_context.strip():
        payload["clarification_resolution_document"] = clarification_context[:5000]
    return payload


def _section_body_chars(sections: list[DraftSection]) -> int:
    return sum(len(s.body.strip()) for s in sections)


def _sections_are_substantive(sections: list[DraftSection], min_chars: int = _MIN_DRAFT_BODY_CHARS) -> bool:
    if not sections:
        return False
    body = sections[0].body.strip()
    if len(body) < min_chars:
        return False
    title = sections[0].title.strip().lower()
    if body.lower() == title:
        return False
    if title and body.lower().startswith(title) and len(body) < min_chars + len(title):
        return False
    return True


def _extract_sections(data: dict[str, object]) -> list[DraftSection]:
    """Parse sections from several common LLM JSON shapes."""
    for key in ("sections", "draft_sections", "proposal_sections"):
        raw = data.get(key)
        if isinstance(raw, list):
            parsed = _parse_section_list(raw)
            if parsed:
                return parsed
        if isinstance(raw, dict):
            parsed = _parse_section_list([raw])
            if parsed:
                return parsed

    if any(k in data for k in ("section_id", "title", "body", "content", "text")):
        parsed = _parse_section_list([data])
        if parsed:
            return parsed

    for key in ("proposal", "draft", "response", "document", "final_proposal"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return [
                DraftSection(
                    section_id="FINAL-PROPOSAL",
                    title="Enterprise Proposal Response",
                    body=val.strip()[:20000],
                )
            ]
        if isinstance(val, dict):
            parsed = _parse_section_list([val])
            if parsed:
                return parsed
        if isinstance(val, list):
            parsed = _parse_section_list(val)
            if parsed:
                return parsed

    body = data.get("body") or data.get("content") or data.get("text")
    if isinstance(body, str) and body.strip():
        return [
            DraftSection(
                section_id="FINAL-PROPOSAL",
                title="Enterprise Proposal Response",
                body=body.strip()[:20000],
            )
        ]

    skip = {
        "requirements",
        "summary",
        "rag_context",
        "rag_snippets",
        "rfp_excerpt",
        "task",
        "mandatory_ids",
        "overview",
        "all_requirements",
        "mandatory_requirements",
        "client",
        "clarification_document",
        "clarification_resolution_document",
        "clarifications",
        "revision_instructions",
        "proposal_instructions",
        "additional_inputs",
        "required_headings",
    }
    flat: list[DraftSection] = []
    idx = 0
    for key, value in data.items():
        if key in skip:
            continue
        if isinstance(value, str) and value.strip():
            idx += 1
            flat.append(
                DraftSection(
                    section_id=f"S-{idx}",
                    title=key.replace("_", " ").title()[:120],
                    body=value.strip()[:8000],
                )
            )
            continue
        if isinstance(value, dict):
            parsed = _parse_section_list([value])
            if parsed:
                return parsed
    if flat:
        return flat[:10]

    longest = _longest_text_value(data, skip=skip)
    if longest:
        return [
            DraftSection(
                section_id="FINAL-PROPOSAL",
                title="Enterprise Proposal Response",
                body=longest[:20000],
            )
        ]

    return []


def _longest_text_value(data: dict[str, object], *, skip: set[str]) -> str:
    best = ""
    for key, value in data.items():
        if key in skip:
            continue
        if isinstance(value, str) and len(value.strip()) > len(best):
            best = value.strip()
        elif isinstance(value, dict):
            nested = _longest_text_value(value, skip=skip)
            if len(nested) > len(best):
                best = nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item.strip()) > len(best):
                    best = item.strip()
                elif isinstance(item, dict):
                    nested = _longest_text_value(item, skip=skip)
                    if len(nested) > len(best):
                        best = nested
    return best


def _parse_section_list(items: list[object]) -> list[DraftSection]:
    sections: list[DraftSection] = []
    for i, item in enumerate(items):
        if isinstance(item, str) and item.strip():
            sections.append(
                DraftSection(
                    section_id=f"S-{i + 1}",
                    title=f"Section {i + 1}",
                    body=item.strip()[:8000],
                )
            )
            continue
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or item.get("heading") or f"Section {i + 1}")
        body = str(
            item.get("body") or item.get("content") or item.get("text") or item.get("description") or ""
        ).strip()
        if not body:
            nested = item.get("sections")
            if isinstance(nested, list):
                parsed = _parse_section_list(nested)
                if parsed:
                    return parsed
            continue
        sections.append(
            DraftSection(
                section_id=str(item.get("section_id") or item.get("id") or f"S-{i + 1}"),
                title=title[:200],
                body=body[:8000],
            )
        )
    return sections


def _draft_max_tokens(settings: Settings) -> int:
    if settings.llm_backend != "groq":
        return 3000
    model = settings.groq_model.lower()
    if "8b" in model or "instant" in model:
        return min(settings.groq_max_output_tokens, 1536)
    return min(max(3000, settings.groq_max_output_tokens), 4096)


def _normalize_final_document(sections: list[DraftSection]) -> list[DraftSection]:
    if not sections:
        return []
    if len(sections) == 1:
        only = sections[0]
        return [
            DraftSection(
                section_id="FINAL-PROPOSAL",
                title="Enterprise Proposal Response",
                body=only.body[:20000].strip(),
            )
        ]
    merged = "\n\n".join(
        f"## {s.title}\n{s.body}".strip()
        for s in sections
        if s.body.strip() and "strict timeline table" not in s.title.lower()
    ).strip()
    if not merged:
        return []
    return [
        DraftSection(
            section_id="FINAL-PROPOSAL",
            title="Enterprise Proposal Response",
            body=merged[:20000],
        )
    ]


def _mock_draft(requirements: RequirementList, summary: RFPSummary) -> DraftResponse:
    """Used only when LLM_BACKEND=mock (CI / offline)."""
    mandatory = [r for r in requirements.requirements if r.priority == "mandatory"]
    mandatory_ids = [r.requirement_id for r in mandatory[:8]]
    mandatory_text = ", ".join(mandatory_ids) if mandatory_ids else "all mandatory requirements"
    full_doc = (
        "# Cover Page\n"
        "Proposal Title: Enterprise Solution Proposal\n"
        "Client Name: [CLIENT NAME]\n"
        "Company Name: MAQ Software\n"
        "Submission Date: To be confirmed\n"
        "Confidentiality Statement: This proposal is confidential and intended solely for the client evaluation team.\n\n"
        "# Executive Summary\n"
        f"We understand that {summary.client_overview[:400]}. Our proposal provides a practical, secure, "
        "and outcome-led delivery approach aligned to the client objectives.\n\n"
        "# About the Company\n"
        "MAQ Software brings consulting, engineering, delivery governance, and managed support capabilities across enterprise technology programs.\n\n"
        "# Understanding of Client Requirements\n"
        f"We will address {mandatory_text}, with particular focus on mandatory scope, measurable outcomes, and operational readiness.\n\n"
        "# Proposed Solution\n"
        "We propose a modular, API-first, secure-by-design solution using scalable architecture, automated delivery pipelines, observability, and governed integrations.\n\n"
        "# Scope of Work\n"
        "## In-Scope Activities\n"
        "Discovery, solution design, implementation, integration, validation, deployment, and transition.\n"
        "## Out-of-Scope Activities\n"
        "Items not confirmed in the RFP or clarification responses; listed explicitly for transparency.\n"
        "## Deliverables\n"
        "Solution blueprint, configured platform, test evidence, deployment package, and support handover.\n"
        "## Milestones\n"
        "Phase gates aligned to discovery, build, test, deploy, and hypercare.\n\n"
        "# Project Timeline & Implementation Plan\n"
        "We will execute through discovery, design, build, validation, deployment, and hypercare phases with clear governance checkpoints.\n\n"
        "# Team Structure\n"
        "The delivery team includes a program manager, solution architect, business analyst, engineering team, QA lead, DevOps engineer, and support lead.\n\n"
        "# Commercial Proposal / Pricing\n"
        "Commercials will be finalized after scope validation and will separate implementation, licensing, support, and change-control assumptions.\n\n"
        "# Risk Management\n"
        "Key risks include requirement ambiguity, dependency delays, data readiness, security approvals, and adoption gaps. Each risk will have an owner and mitigation plan.\n\n"
        "# Support & Maintenance\n"
        "Post-implementation support includes SLA-based incident handling, monitoring, escalation, maintenance, and knowledge transfer.\n\n"
        "# Competitive Advantages\n"
        "Our differentiators include enterprise delivery discipline, reusable accelerators, security-first engineering, and measurable business outcomes.\n\n"
        "# Compliance Matrix\n"
        "| Requirement | Compliance Status | Response |\n"
        "| --- | --- | --- |\n"
        f"| {mandatory_text} | Fully Compliant | Covered through proposed delivery approach and governance. |\n\n"
        "# Terms and Conditions\n"
        "Final legal, commercial, confidentiality, intellectual property, and termination terms will be agreed during contracting.\n\n"
        "# Conclusion\n"
        "We are committed to delivering a high-quality, scalable, and business-aligned solution with clear accountability and measurable impact."
    )
    return DraftResponse(
        sections=[
            DraftSection(section_id="FINAL-PROPOSAL", title="Enterprise Proposal Response", body=full_doc),
        ]
    )
