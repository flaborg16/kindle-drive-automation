from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Iterable

from PIL import Image

from .utils import read_text_if_possible, safe_filename, unique_path

KINDLE_DIRECT_EXTS = {
    ".epub", ".pdf", ".doc", ".docx", ".txt", ".rtf", ".htm", ".html",
    ".png", ".gif", ".jpg", ".jpeg", ".bmp",
}

OFFICE_EXTS = {".odt", ".ods", ".odp", ".ppt", ".pptx", ".xls", ".xlsx", ".csv"}
EBOOK_EXTS = {".mobi", ".azw", ".azw3", ".fb2", ".lit"}
MARKDOWN_EXTS = {".md", ".markdown"}
COMIC_EXTS = {".cbz"}


def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def convert_for_kindle(input_path: Path, output_dir: Path) -> list[Path]:
    """Convert a file into one or more Kindle Send-to-Kindle-compatible files.

    This function does not bypass DRM. DRM-protected files will fail conversion.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = input_path.suffix.lower()

    if ext in KINDLE_DIRECT_EXTS:
        return [input_path]

    if ext in MARKDOWN_EXTS:
        return [_markdown_to_html(input_path, output_dir)]

    if ext in OFFICE_EXTS:
        return [_libreoffice_to_pdf(input_path, output_dir)]

    if ext in EBOOK_EXTS:
        return [_ebook_to_epub(input_path, output_dir)]

    if ext in COMIC_EXTS:
        return [_cbz_to_pdf(input_path, output_dir)]

    if ext == ".zip":
        return _zip_to_kindle_files(input_path, output_dir)

    text = read_text_if_possible(input_path)
    if text:
        out = unique_path(output_dir / f"{safe_filename(input_path.stem)}.txt")
        out.write_text(text, encoding="utf-8")
        return [out]

    raise RuntimeError(
        f"Unsupported file type: {input_path.name}. This is probably not a readable book/document, "
        "or it needs a specific converter."
    )


def _markdown_to_html(input_path: Path, output_dir: Path) -> Path:
    out = unique_path(output_dir / f"{safe_filename(input_path.stem)}.html")
    if _has_cmd("pandoc"):
        _run(["pandoc", str(input_path), "-o", str(out), "--standalone"])
        return out

    # Dependency-free fallback. It is intentionally simple.
    import html
    text = input_path.read_text(encoding="utf-8", errors="replace")
    escaped = html.escape(text)
    body = "<br>\n".join(escaped.splitlines())
    out.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(input_path.stem)}</title></head><body><pre style='white-space:pre-wrap'>"
        f"{body}</pre></body></html>",
        encoding="utf-8",
    )
    return out


def _libreoffice_to_pdf(input_path: Path, output_dir: Path) -> Path:
    if not _has_cmd("libreoffice") and not _has_cmd("soffice"):
        raise RuntimeError("LibreOffice/soffice is required to convert Office files to PDF")
    cmd = "libreoffice" if _has_cmd("libreoffice") else "soffice"
    _run([cmd, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(input_path)])
    produced = output_dir / f"{input_path.stem}.pdf"
    if not produced.exists():
        # LibreOffice sometimes sanitizes output names.
        pdfs = sorted(output_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not pdfs:
            raise RuntimeError(f"LibreOffice did not produce a PDF for {input_path.name}")
        produced = pdfs[0]
    final = unique_path(output_dir / f"{safe_filename(input_path.stem)}.pdf")
    if produced != final:
        produced.rename(final)
    return final


def _ebook_to_epub(input_path: Path, output_dir: Path) -> Path:
    if not _has_cmd("ebook-convert"):
        raise RuntimeError("Calibre ebook-convert is required to convert old ebook formats to EPUB")
    out = unique_path(output_dir / f"{safe_filename(input_path.stem)}.epub")
    _run(["ebook-convert", str(input_path), str(out)])
    return out


def _cbz_to_pdf(input_path: Path, output_dir: Path) -> Path:
    tmp = output_dir / f"_extract_{safe_filename(input_path.stem)}"
    tmp.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []
    with zipfile.ZipFile(input_path) as zf:
        for member in sorted(zf.namelist()):
            if Path(member).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
                zf.extract(member, tmp)
                image_paths.append(tmp / member)
    if not image_paths:
        raise RuntimeError("CBZ archive did not contain readable images")

    images = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")
        images.append(img)
    out = unique_path(output_dir / f"{safe_filename(input_path.stem)}.pdf")
    first, rest = images[0], images[1:]
    first.save(out, save_all=True, append_images=rest)
    return out


def _zip_to_kindle_files(input_path: Path, output_dir: Path) -> list[Path]:
    extracted_dir = output_dir / f"_zip_{safe_filename(input_path.stem)}"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with zipfile.ZipFile(input_path) as zf:
        zf.extractall(extracted_dir)
    for path in extracted_dir.rglob("*"):
        if path.is_file():
            try:
                outputs.extend(convert_for_kindle(path, output_dir / "zip_outputs"))
            except Exception:
                # Keep processing other files in the archive.
                continue
    if not outputs:
        raise RuntimeError("ZIP archive contained no convertible Kindle documents")
    return outputs
