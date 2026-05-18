"""Extract docx text + tables to plain text for comparison."""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document


def extract(path: str) -> str:
    doc = Document(path)
    lines: list[str] = []

    # Walk through body elements in order using underlying XML iteration
    from docx.oxml.ns import qn

    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = "".join(t.text or "" for t in child.iter(qn("w:t")))
            if text.strip():
                lines.append(text)
            else:
                lines.append("")
        elif tag == "tbl":
            lines.append("[TABLE START]")
            for row in child.iter(qn("w:tr")):
                cells = []
                for cell in row.iter(qn("w:tc")):
                    cell_text = "".join(t.text or "" for t in cell.iter(qn("w:t")))
                    cells.append(cell_text.strip())
                lines.append(" | ".join(cells))
            lines.append("[TABLE END]")
            lines.append("")

    return "\n".join(lines)


def main(path: str, out: str | None = None) -> int:
    text = extract(path)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out} ({len(text)} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    raise SystemExit(main(in_path, out_path))
