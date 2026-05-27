from __future__ import annotations

from datetime import UTC, datetime

from models.pipeline import ClarificationResolutionDocument, ClarificationResolutionItem, OutputBundle
from models.scope import ChatMessage


def build_clarification_document(
    bundle: OutputBundle,
    answers: dict[str, str],
    suggested_inputs: dict[str, str],
    additional_notes: str = "",
    uploaded_reference_filename: str = "",
    uploaded_reference_excerpt: str = "",
    chat_history: list[ChatMessage] | None = None,
) -> ClarificationResolutionDocument:
    items: list[ClarificationResolutionItem] = []
    for q in bundle.questions:
        answer = (answers.get(q.question_id) or "").strip()
        suggestion = (suggested_inputs.get(q.question_id) or "").strip()
        assumption = (q.assumption_if_unanswered or "").strip()
        resolution = answer if answer else (assumption or "No explicit answer provided.")
        source = "user_answer" if answer else "assumption"
        items.append(
            ClarificationResolutionItem(
                question_id=q.question_id,
                source_requirement=q.source_requirement,
                question_text=q.question_text,
                suggested_input=suggestion[:1200],
                user_answer=answer[:3000],
                assumption_if_unanswered=assumption[:2000],
                final_resolution=resolution[:3000],
                resolution_source=source,
            )
        )

    user_lines: list[str] = []
    for msg in chat_history or []:
        if msg.role == "user" and msg.content.strip():
            user_lines.append(msg.content.strip())
    user_excerpt = "\n".join(user_lines[-10:])[:5000]

    return ClarificationResolutionDocument(
        generated_at=datetime.now(UTC).isoformat(),
        uploaded_reference_filename=uploaded_reference_filename[:300],
        uploaded_reference_excerpt=uploaded_reference_excerpt[:6000],
        additional_notes=additional_notes[:4000],
        chat_user_inputs_excerpt=user_excerpt,
        items=items,
    )


def clarification_to_prompt_context(doc: ClarificationResolutionDocument) -> str:
    lines = [
        "Clarification Resolution Document",
        f"Generated at: {doc.generated_at}",
    ]
    if doc.uploaded_reference_filename:
        lines.append(f"Uploaded reference file: {doc.uploaded_reference_filename}")
    if doc.additional_notes:
        lines.append(f"Additional notes: {doc.additional_notes}")
    for item in doc.items:
        lines.append(
            (
                f"- {item.question_id} ({item.source_requirement}): {item.question_text}\n"
                f"  Suggested input: {item.suggested_input}\n"
                f"  Final resolution ({item.resolution_source}): {item.final_resolution}"
            )
        )
    if doc.chat_user_inputs_excerpt:
        lines.append("Recent user chat inputs:")
        lines.append(doc.chat_user_inputs_excerpt)
    if doc.uploaded_reference_excerpt:
        lines.append("Uploaded reference excerpt:")
        lines.append(doc.uploaded_reference_excerpt)
    return "\n".join(lines)[:12000]
