from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .notebook_parser import Annotation
from .utils import safe_filename, unique_path


def _font(size: int, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if serif:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ])
    else:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ])
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_by_pixels(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_quote_image(annotation: Annotation, out_dir: Path, width: int = 1236, height: int = 1648, index: int = 1) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = hash((annotation.book_title, annotation.page, annotation.text)) & 0xFFFFFFFF
    rng = random.Random(seed)
    style = rng.choice(["light", "dark", "paper"])

    if style == "dark":
        bg = (14, 14, 14)
        fg = (245, 245, 240)
        muted = (190, 190, 180)
        line = (245, 245, 240)
    elif style == "paper":
        bg = (238, 232, 220)
        fg = (20, 20, 18)
        muted = (70, 70, 64)
        line = (20, 20, 18)
    else:
        bg = (250, 248, 242)
        fg = (12, 12, 12)
        muted = (65, 65, 65)
        line = (12, 12, 12)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Subtle e-ink-safe texture, no low contrast dependency.
    if style == "paper":
        for _ in range(1800):
            x, y = rng.randrange(width), rng.randrange(height)
            v = rng.choice([-8, -5, 5, 8])
            base = bg[0]
            c = max(0, min(255, base + v))
            draw.point((x, y), fill=(c, c, c))

    margin = 110
    max_text_width = width - margin * 2
    quote_len = len(annotation.text)
    if quote_len < 140:
        quote_size = 62
    elif quote_len < 280:
        quote_size = 52
    elif quote_len < 520:
        quote_size = 43
    else:
        quote_size = 36

    quote_font = _font(quote_size, bold=True, serif=True)
    meta_font = _font(30, bold=True, serif=False)
    small_font = _font(24, bold=False, serif=False)
    page_font = _font(22, bold=True, serif=False)

    quote = annotation.text.strip()
    if not quote.startswith(("“", "\"", "‘", "'")):
        quote = "“" + quote
    if not quote.endswith(("”", "\"", "’", "'")):
        quote = quote + "”"

    lines = _wrap_by_pixels(quote, draw, quote_font, max_text_width)
    line_height = int(quote_size * 1.45)
    quote_block_height = len(lines) * line_height

    meta_lines = [
        f"— {annotation.book_title}",
        annotation.first_author,
        f"Page {annotation.page}",
    ]
    meta_height = 120
    total_height = quote_block_height + 70 + meta_height
    y = max(180, (height - total_height) // 2)

    # Border and ornament.
    draw.rectangle((54, 54, width - 54, height - 54), outline=line, width=4)
    draw.rectangle((74, 74, width - 74, height - 74), outline=line, width=1)
    draw.line((margin, y - 55, margin + 170, y - 55), fill=line, width=8)
    draw.text((width - margin - 140, 105), f"p. {annotation.page}", fill=muted, font=page_font)

    for line_text in lines:
        draw.text((margin, y), line_text, fill=fg, font=quote_font)
        y += line_height

    y += 48
    for n, meta in enumerate(meta_lines):
        font = meta_font if n == 0 else small_font
        color = fg if n == 0 else muted
        safe_meta = meta if len(meta) <= 70 else meta[:67] + "..."
        draw.text((margin, y), safe_meta, fill=color, font=font)
        y += 42

    if annotation.note:
        note = annotation.note.strip()
        if note:
            note = "Note: " + (note[:150] + "..." if len(note) > 150 else note)
            note_lines = _wrap_by_pixels(note, draw, small_font, max_text_width)
            y += 20
            for note_line in note_lines[:3]:
                draw.text((margin, y), note_line, fill=muted, font=small_font)
                y += 34

    filename = f"page_{int(annotation.page):03d}_quote_{index:03d}.png" if annotation.page.isdigit() else f"page_{safe_filename(annotation.page)}_quote_{index:03d}.png"
    out = unique_path(out_dir / filename)
    img.save(out, "PNG", optimize=True)
    return out


def write_metadata(annotations: list[Annotation], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "metadata.json"
    path.write_text(json.dumps([a.to_dict() for a in annotations], indent=2, ensure_ascii=False), encoding="utf-8")
    return path
