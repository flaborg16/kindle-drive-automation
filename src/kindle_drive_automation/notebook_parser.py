from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

import fitz  # PyMuPDF


DATE_RE = re.compile(r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$")
PAGE_ENTRY_RE = re.compile(r"^Page\s+(\d+)\s*\|\s*(Highlight|Note)(?:\s*\(([^)]+)\))?$", re.I)
CONT_RE = re.compile(r"^Page\s+(\d+)\s*\|\s*Highlight\s+Continued$", re.I)


@dataclass
class Annotation:
    book_title: str
    authors: str
    first_author: str
    page: str
    kind: str
    text: str
    note: str | None = None
    date: str | None = None
    color: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def extract_text_from_pdf(path: Path) -> str:
    doc = fitz.open(str(path))
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    return "\n".join(parts)


def parse_notebook_pdf(path: Path, process_notes_as_quotes: bool = False) -> list[Annotation]:
    text = extract_text_from_pdf(path)
    lines = _clean_lines(text.splitlines())
    title, authors, first_author = _parse_title_authors(lines)

    annotations: list[Annotation] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = PAGE_ENTRY_RE.match(line)
        if not match:
            i += 1
            continue

        page, kind, color = match.groups()
        kind_norm = kind.capitalize()
        i += 1
        content_lines: list[str] = []
        date = None

        while i < len(lines):
            current = lines[i]
            cont = CONT_RE.match(current)
            next_page_entry = PAGE_ENTRY_RE.match(current)
            if cont and cont.group(1) == page and kind_norm.lower() == "highlight":
                i += 1
                continue
            if DATE_RE.match(current):
                date = current
                i += 1
                break
            if next_page_entry:
                break
            # Skip repeated page numbers from PDF footer/header.
            if current.isdigit():
                i += 1
                continue
            content_lines.append(current)
            i += 1

        content = _join_content(content_lines)
        note = None
        # Kindle exports often put a Note: block immediately after a highlight.
        if i < len(lines) and lines[i].startswith("Note:"):
            note = lines[i].replace("Note:", "", 1).strip()
            i += 1
            # Optional date after note.
            if i < len(lines) and DATE_RE.match(lines[i]):
                i += 1

        if content and (kind_norm.lower() == "highlight" or process_notes_as_quotes):
            annotations.append(
                Annotation(
                    book_title=title,
                    authors=authors,
                    first_author=first_author,
                    page=page,
                    kind=kind_norm,
                    text=content,
                    note=note,
                    date=date,
                    color=color,
                )
            )

    return annotations


def _clean_lines(lines: list[str]) -> list[str]:
    cleaned = []
    for line in lines:
        value = re.sub(r"\s+", " ", line).strip()
        if not value:
            continue
        # Remove standalone PDF page numbers. Keep actual Kindle page entry lines.
        if value.isdigit():
            continue
        cleaned.append(value)
    return cleaned


def _parse_title_authors(lines: list[str]) -> tuple[str, str, str]:
    title = "Unknown Book"
    authors = "Unknown Author"

    # Usually first content line is the title and the next author block begins with "by".
    for idx, line in enumerate(lines[:20]):
        if line.lower().startswith("annotations") or line.lower().startswith("free kindle"):
            break
        if line.lower().startswith("by "):
            if idx > 0:
                title = lines[idx - 1]
            author_parts = [line[3:].strip()]
            j = idx + 1
            while j < min(len(lines), idx + 8):
                nxt = lines[j]
                if nxt.lower().startswith("free kindle") or nxt.lower().startswith("annotations"):
                    break
                author_parts.append(nxt)
                j += 1
            authors = " ".join(author_parts).strip()
            break

    # Avoid folder names with a huge list of authors.
    first_author = authors.split(",")[0].strip() if authors else "Unknown Author"
    if not first_author or len(first_author) < 2:
        first_author = "Unknown Author"
    return title, authors, first_author


def _join_content(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text
