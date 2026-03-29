from __future__ import annotations

import html
import os
import re
from pathlib import Path


class DocsService:
    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)

    def list_docs(self) -> list[dict]:
        docs = []
        if not self.docs_root.exists():
            return docs

        for path in sorted(self.docs_root.rglob("*.md")):
            rel_path = path.relative_to(self.docs_root).as_posix()
            docs.append(
                {
                    "path": rel_path,
                    "title": self._title_for_path(rel_path),
                    "section": rel_path.split("/", 1)[0] if "/" in rel_path else "root",
                }
            )
        return docs

    def get_doc(self, relative_path: str) -> dict | None:
        safe_path = self._safe_path(relative_path)
        if safe_path is None or not safe_path.exists() or safe_path.suffix.lower() != ".md":
            return None

        raw = safe_path.read_text(encoding="utf-8")
        return {
            "path": safe_path.relative_to(self.docs_root).as_posix(),
            "title": self._title_for_path(safe_path.relative_to(self.docs_root).as_posix(), raw),
            "raw": raw,
            "html": self._render_markdown(raw),
        }

    def _safe_path(self, relative_path: str) -> Path | None:
        candidate = (self.docs_root / relative_path).resolve()
        try:
            candidate.relative_to(self.docs_root.resolve())
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _title_for_path(relative_path: str, content: str | None = None) -> str:
        if content:
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
        stem = Path(relative_path).stem.replace("-", " ").replace("_", " ")
        return stem.title()

    def _render_markdown(self, raw: str) -> str:
        lines = raw.splitlines()
        output = []
        in_code = False
        in_list = False
        paragraph = []

        def flush_paragraph():
            nonlocal paragraph
            if paragraph:
                text = " ".join(part.strip() for part in paragraph if part.strip())
                output.append(f"<p>{self._inline(text)}</p>")
                paragraph = []

        def close_list():
            nonlocal in_list
            if in_list:
                output.append("</ul>")
                in_list = False

        for line in lines:
            stripped = line.rstrip()
            marker = stripped.strip()

            if marker.startswith("```"):
                flush_paragraph()
                close_list()
                if in_code:
                    output.append("</code></pre>")
                    in_code = False
                else:
                    output.append("<pre class=\"docs-code\"><code>")
                    in_code = True
                continue

            if in_code:
                output.append(html.escape(stripped))
                output.append("\n")
                continue

            if not marker:
                flush_paragraph()
                close_list()
                continue

            if marker.startswith("# "):
                flush_paragraph()
                close_list()
                output.append(f"<h1>{self._inline(marker[2:].strip())}</h1>")
                continue
            if marker.startswith("## "):
                flush_paragraph()
                close_list()
                output.append(f"<h2>{self._inline(marker[3:].strip())}</h2>")
                continue
            if marker.startswith("### "):
                flush_paragraph()
                close_list()
                output.append(f"<h3>{self._inline(marker[4:].strip())}</h3>")
                continue
            if marker.startswith("- "):
                flush_paragraph()
                if not in_list:
                    output.append("<ul>")
                    in_list = True
                output.append(f"<li>{self._inline(marker[2:].strip())}</li>")
                continue

            numbered = re.match(r"^\d+\.\s+(.*)$", marker)
            if numbered:
                flush_paragraph()
                if not in_list:
                    output.append("<ul>")
                    in_list = True
                output.append(f"<li>{self._inline(numbered.group(1).strip())}</li>")
                continue

            paragraph.append(marker)

        flush_paragraph()
        close_list()
        if in_code:
            output.append("</code></pre>")

        return "".join(output)

    @staticmethod
    def _inline(text: str) -> str:
        escaped = html.escape(text)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        return escaped
