from __future__ import annotations

from agents.evaluation_agent import EvaluationAgent
from agents.response_agent import ResponseDraftAgent
from models.maf import MAFAuditResult
from models.rfp import DraftResponse, RequirementList, RFPSummary
from rag.retrieval import AbstractVectorStore


class RetrievalToolPlugin:
    """Agent Framework tool: retrieve RAG context snippets for drafting."""

    def __init__(self, vector_store: AbstractVectorStore) -> None:
        self._vector_store = vector_store

    async def retrieve_context(self, query: str, k: int = 6) -> str:
        snippets = await self._vector_store.query(query, k=max(1, min(k, 12)))
        formatted: list[str] = []
        for s in snippets:
            section = str(s.metadata.get("section_title", "")).strip()
            if section:
                formatted.append(f"[{section}]\n{s.text}")
            else:
                formatted.append(s.text)
        return "\n\n".join(formatted)


class AuditToolPlugin:
    """Agent Framework tool: evaluate draft against mandatory requirements."""

    def __init__(self, evaluator: EvaluationAgent) -> None:
        self._evaluator = evaluator

    async def audit_draft(
        self, draft: DraftResponse, requirements: RequirementList
    ) -> MAFAuditResult:
        return await self._evaluator.audit(draft, requirements)


class RevisionToolPlugin:
    """Agent Framework tool: generate or revise proposal draft from context."""

    def __init__(self, drafter: ResponseDraftAgent) -> None:
        self._drafter = drafter

    async def revise_draft(
        self,
        requirements: RequirementList,
        summary: RFPSummary,
        rfp_excerpt: str,
        rag_context: str = "",
        critique_note: str = "",
    ) -> DraftResponse:
        note = critique_note if critique_note.strip() else None
        context = rag_context if rag_context.strip() else None
        return await self._drafter.draft(
            requirements,
            summary,
            rfp_excerpt,
            critique_note=note,
            rag_context=context,
        )
