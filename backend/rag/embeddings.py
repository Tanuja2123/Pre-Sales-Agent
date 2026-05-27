"""Embedding helpers — production uses Azure OpenAI embeddings; dev can use Chroma defaults."""

from __future__ import annotations

from models.rfp import DocumentChunk


def chunks_to_text_for_embed(chunks: list[DocumentChunk]) -> list[str]:
    return [c.text for c in chunks]
