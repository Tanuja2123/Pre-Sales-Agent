from __future__ import annotations

from pathlib import Path

import docx


class DOCXParser:
    async def extract(self, file_path: str) -> str:
        path = Path(file_path)
        document = docx.Document(str(path))
        parts: list[str] = []
        for p in document.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style_name = (p.style.name if p.style is not None else "").lower()
            if "heading" in style_name:
                parts.append(f"Section: {text}")
            else:
                parts.append(text)
        return "\n".join(parts).strip()
