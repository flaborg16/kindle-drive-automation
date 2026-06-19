from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def safe_filename(value: str, max_len: int = 120) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.replace("/", "-").replace("\\", "-")
    value = re.sub(r"[^\w\s.,;:()\[\]-]+", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip(". ")
    if not value:
        value = "Untitled"
    return value[:max_len].rstrip(". ")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    parent = path.parent
    i = 2
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def read_text_if_possible(path: Path, max_bytes: int = 2_000_000) -> str | None:
    data = path.read_bytes()[:max_bytes]
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            if "\x00" in text[:1000] and enc != "utf-16":
                continue
            printable_ratio = sum(ch.isprintable() or ch.isspace() for ch in text) / max(len(text), 1)
            if printable_ratio > 0.85:
                return text
        except UnicodeDecodeError:
            pass
    return None
