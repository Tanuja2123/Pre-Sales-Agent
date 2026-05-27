from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.config import get_settings
from models.rfp import DocumentChunk, RFPDocument
from parsers.docx_parser import DOCXParser
from parsers.pdf_parser import PDFParser


@dataclass
class _SectionSlice:
    title: str
    text: str
    start: int


class IngestionPlugin:
    """Ingestion agent — task-ingest-v1, task-chunk-v1."""

    def __init__(self) -> None:
        self._pdf = PDFParser()
        self._docx = DOCXParser()

    async def ingest_document(self, file_path: str, file_type: str) -> RFPDocument:
        path = Path(file_path)
        ft = file_type.lower().lstrip(".")
        if ft == "pdf":
            raw_text = await self._pdf.extract(file_path)
        elif ft in ("docx", "doc"):
            raw_text = await self._docx.extract(file_path)
        elif ft == "txt":
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        else:
            msg = f"Unsupported file type: {file_type}"
            raise ValueError(msg)
        doc_id = str(uuid.uuid4())
        settings = get_settings()
        target_chars = max(800, settings.chunk_target_chars)
        overlap_chars = max(80, min(settings.chunk_overlap_chars, target_chars // 3))
        chunks = self._chunk(
            raw_text,
            doc_id=doc_id,
            target_chars=target_chars,
            overlap_chars=overlap_chars,
            min_chunk_chars=max(250, settings.chunk_min_chars),
        )
        sections = self._detect_sections(raw_text)
        return RFPDocument(
            document_id=doc_id,
            filename=path.name,
            upload_timestamp=datetime.now(UTC),
            raw_text=raw_text,
            chunks=chunks,
            sections=sections,
            metadata=self._extract_metadata(raw_text, path.name),
        )

    def _chunk(
        self,
        text: str,
        doc_id: str,
        target_chars: int,
        overlap_chars: int,
        min_chunk_chars: int,
    ) -> list[DocumentChunk]:
        if not text.strip():
            return []
        chunks: list[DocumentChunk] = []
        idx = 0
        for section_idx, section in enumerate(self._split_sections(text), start=1):
            for chunk in self._chunk_section(
                section,
                doc_id=doc_id,
                section_idx=section_idx,
                target_chars=target_chars,
                overlap_chars=overlap_chars,
                min_chunk_chars=min_chunk_chars,
                chunk_idx_start=idx,
            ):
                chunks.append(chunk)
            idx = len(chunks)
        return chunks

    def _detect_sections(self, text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        for idx, section in enumerate(self._split_sections(text), start=1):
            key = section.title if section.title != "body" else f"body_{idx}"
            sections[key] = section.text[:1200]
        if not sections:
            sections["body_1"] = text[:1200]
        return sections

    def _extract_metadata(self, raw_text: str, filename: str) -> dict[str, str]:
        meta: dict[str, str] = {"filename": filename}
        dm = re.search(
            r"(submission|due)\s*(date)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            raw_text,
            re.I,
        )
        if dm:
            meta["deadline_hint"] = dm.group(3)
            meta["submission_date_hint"] = dm.group(3)
        named_date = re.search(
            r"(submission|due)\s*(date)?[:\s]+"
            r"(\d{1,2}\s+(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+\d{4})",
            raw_text,
            re.I,
        )
        if named_date:
            meta["submission_date_hint"] = named_date.group(3)
        org = re.search(r"(?:from|client|organization)\s*[:\s]+(.{3,80})", raw_text, re.I)
        if org:
            meta["org_hint"] = org.group(1).strip()
        return meta

    def _split_sections(self, text: str) -> list[_SectionSlice]:
        heading_pattern = re.compile(
            r"^(?:(?:section|part)\s+[A-Za-z0-9IVXLCM.-]+[:.)-]?\s+.+|(?:\d+(?:\.\d+){0,3})\s+.+)$",
            re.I | re.M,
        )
        matches = list(heading_pattern.finditer(text))
        if not matches:
            return [_SectionSlice(title="body", text=text.strip(), start=0)]

        sections: list[_SectionSlice] = []
        first = matches[0]
        if first.start() > 0:
            preface = text[: first.start()].strip()
            if preface:
                sections.append(_SectionSlice(title="preface", text=preface, start=0))
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if not body:
                continue
            heading = m.group(0).strip()[:180]
            sections.append(_SectionSlice(title=heading, text=body, start=m.start()))
        return sections or [_SectionSlice(title="body", text=text.strip(), start=0)]

    def _chunk_section(
        self,
        section: _SectionSlice,
        doc_id: str,
        section_idx: int,
        target_chars: int,
        overlap_chars: int,
        min_chunk_chars: int,
        chunk_idx_start: int,
    ) -> list[DocumentChunk]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", section.text) if p.strip()]
        if not paragraphs:
            paragraphs = [section.text.strip()]

        pieces: list[tuple[str, int, int]] = []
        carry_over = ""
        carry_start = section.start
        local_offset = 0
        for para in paragraphs:
            para_start = section.start + local_offset
            local_offset += len(para) + 2
            candidate = f"{carry_over}\n\n{para}".strip() if carry_over else para
            if len(candidate) <= target_chars:
                if not carry_over:
                    carry_start = para_start
                carry_over = candidate
                continue

            if carry_over:
                pieces.append((carry_over, carry_start, carry_start + len(carry_over)))
                tail = carry_over[-overlap_chars:].strip() if overlap_chars > 0 else ""
                combined = f"{tail}\n\n{para}".strip() if tail else para
                combined_start = max(para_start - len(tail), section.start)
                if len(combined) > target_chars:
                    pieces.extend(
                        self._split_long_paragraph(
                            combined, combined_start, target_chars, overlap_chars
                        )
                    )
                    carry_over = ""
                else:
                    carry_over = combined
                    carry_start = combined_start
            else:
                pieces.extend(self._split_long_paragraph(para, para_start, target_chars, overlap_chars))
                carry_over = ""

        if carry_over:
            pieces.append((carry_over, carry_start, carry_start + len(carry_over)))

        merged: list[tuple[str, int, int]] = []
        for piece, p_start, p_end in pieces:
            if not merged:
                merged.append((piece, p_start, p_end))
                continue
            prev_piece, prev_start, _prev_end = merged[-1]
            if len(prev_piece) < min_chunk_chars:
                merged[-1] = (f"{prev_piece}\n\n{piece}".strip(), prev_start, p_end)
            else:
                merged.append((piece, p_start, p_end))

        out: list[DocumentChunk] = []
        for idx, (piece, p_start, p_end) in enumerate(merged, start=chunk_idx_start):
            chunk_text = (
                f"Section: {section.title}\n{piece}".strip()
                if section.title not in {"body", "preface"}
                else piece.strip()
            )
            chunk_id = f"{doc_id[:8]}-chk-{idx:05d}"
            out.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata={
                        "document_id": doc_id,
                        "section_index": str(section_idx),
                        "section_title": section.title,
                        "start": str(max(0, p_start)),
                        "end": str(max(0, p_end)),
                    },
                )
            )
        return out

    def _split_long_paragraph(
        self, paragraph: str, paragraph_start: int, target_chars: int, overlap_chars: int
    ) -> list[tuple[str, int, int]]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        if len(sentences) <= 1:
            return self._split_hard(paragraph, paragraph_start, target_chars, overlap_chars)

        out: list[tuple[str, int, int]] = []
        buffer = ""
        cursor = paragraph_start
        for sentence in sentences:
            candidate = f"{buffer} {sentence}".strip() if buffer else sentence
            if len(candidate) <= target_chars:
                buffer = candidate
                continue
            if buffer:
                out.append((buffer, cursor, cursor + len(buffer)))
                tail = buffer[-overlap_chars:].strip() if overlap_chars > 0 else ""
                cursor = max(cursor + len(buffer) - len(tail), paragraph_start)
                buffer = f"{tail} {sentence}".strip() if tail else sentence
            else:
                out.extend(self._split_hard(sentence, cursor, target_chars, overlap_chars))
                cursor += len(sentence)
                buffer = ""
        if buffer:
            out.append((buffer, cursor, cursor + len(buffer)))
        return out

    def _split_hard(
        self, text: str, text_start: int, target_chars: int, overlap_chars: int
    ) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + target_chars, n)
            piece = text[start:end].strip()
            if piece:
                out.append((piece, text_start + start, text_start + end))
            if end >= n:
                break
            start = max(end - overlap_chars, start + 1)
        return out
