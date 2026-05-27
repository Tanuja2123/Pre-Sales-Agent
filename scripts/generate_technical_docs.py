"""Regenerate TECHNICAL_IMPLEMENTATION.docx and .pdf from concise markdown."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs" / "TECHNICAL_IMPLEMENTATION.md"
DOCX = REPO_ROOT / "docs" / "TECHNICAL_IMPLEMENTATION.docx"
PDF = REPO_ROOT / "docs" / "TECHNICAL_IMPLEMENTATION.pdf"

# Tighter layout for fewer pages in Word/PDF exports
PANDOC_EXTRA = [
    "--variable=geometry:margin=0.65in",
    "--variable=fontsize:9pt",
    "--variable=linestretch:1.05",
]


def main() -> int:
    if not SRC.is_file():
        print(f"Missing source: {SRC}", file=sys.stderr)
        return 1

    import pypandoc

    pypandoc.convert_file(
        str(SRC),
        "docx",
        outputfile=str(DOCX),
        extra_args=PANDOC_EXTRA,
    )
    print(f"Wrote {DOCX} ({DOCX.stat().st_size:,} bytes)")

    try:
        from docx2pdf import convert

        convert(str(DOCX), str(PDF))
        print(f"Wrote {PDF} ({PDF.stat().st_size:,} bytes)")
    except Exception as exc:  # noqa: BLE001
        print(f"PDF via Word failed ({exc}); trying pandoc pdf...", file=sys.stderr)
        try:
            pypandoc.convert_file(
                str(SRC),
                "pdf",
                outputfile=str(PDF),
                extra_args=[*PANDOC_EXTRA, "--pdf-engine=weasyprint"],
            )
            print(f"Wrote {PDF} ({PDF.stat().st_size:,} bytes)")
        except Exception as exc2:  # noqa: BLE001
            print(f"PDF generation failed: {exc2}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
