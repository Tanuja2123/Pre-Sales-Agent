from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class PDFParser:
    async def extract(self, file_path: str) -> str:
        path = Path(file_path)
        reader = PdfReader(str(path))
        parts: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            t = page.extract_text() or ""
            # Keep a stable marker so downstream chunking can preserve page context.
            parts.append(f"[PAGE {idx}]\n{t.strip()}")
        return "\n\n".join(parts).strip()
