from __future__ import annotations

import io
import re
import zipfile
from typing import Literal

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

WatermarkPosition = Literal["center", "top", "bottom", "diagonal"]


class PdfError(Exception):
    """Raised when PDF input is invalid or processing fails."""


def _read_pdf(data: bytes) -> PdfReader:
    if not data:
        raise PdfError("Empty file")
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if len(reader.pages) == 0:
            raise PdfError("PDF has no pages")
        return reader
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError(f"Invalid or corrupt PDF: {exc}") from exc


def merge_pdfs(files: list[bytes]) -> bytes:
    if not files:
        raise PdfError("At least one PDF file is required")
    if len(files) < 2:
        raise PdfError("Merge requires at least two PDF files")

    writer = PdfWriter()
    for index, data in enumerate(files, start=1):
        reader = _read_pdf(data)
        for page in reader.pages:
            writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _parse_pages_spec(spec: str, total_pages: int) -> list[tuple[int, int]]:
    spec = spec.strip()
    if not spec:
        raise PdfError("pages parameter is required (e.g. '1-3,5' or 'all')")

    if spec.lower() == "all":
        return [(page, page) for page in range(1, total_pages + 1)]

    ranges: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            try:
                start, end = int(start_str.strip()), int(end_str.strip())
            except ValueError as exc:
                raise PdfError(f"Invalid page range: {part}") from exc
        else:
            try:
                start = end = int(part)
            except ValueError as exc:
                raise PdfError(f"Invalid page number: {part}") from exc

        if start < 1 or end < 1 or start > total_pages or end > total_pages:
            raise PdfError(
                f"Page range {part} is out of bounds (document has {total_pages} pages)"
            )
        if start > end:
            raise PdfError(f"Invalid page range: {part} (start > end)")
        ranges.append((start, end))

    if not ranges:
        raise PdfError("No valid page ranges found in pages parameter")
    return ranges


def _extract_range(reader: PdfReader, start: int, end: int) -> bytes:
    writer = PdfWriter()
    for page_num in range(start, end + 1):
        writer.add_page(reader.pages[page_num - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def split_pdf(data: bytes, pages_spec: str) -> tuple[bytes, str]:
    reader = _read_pdf(data)
    total = len(reader.pages)
    ranges = _parse_pages_spec(pages_spec, total)

    outputs: list[tuple[str, bytes]] = []
    for start, end in ranges:
        label = f"pages_{start}" if start == end else f"pages_{start}-{end}"
        outputs.append((f"{label}.pdf", _extract_range(reader, start, end)))

    if len(outputs) == 1:
        return outputs[0][1], "application/pdf"

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in outputs:
            zf.writestr(name, content)
    return zip_buf.getvalue(), "application/zip"


def compress_pdf(data: bytes) -> bytes:
    reader = _read_pdf(data)
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _make_watermark_page(
    page_width: float,
    page_height: float,
    text: str,
    position: WatermarkPosition,
) -> PdfReader:
    font_size = max(18, int(min(page_width, page_height) * 0.08))
    img_w = int(page_width)
    img_h = int(page_height)
    image = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    if position == "top":
        x = (img_w - text_w) / 2
        y = img_h * 0.05
    elif position == "bottom":
        x = (img_w - text_w) / 2
        y = img_h * 0.85 - text_h
    elif position == "diagonal":
        x = (img_w - text_w) / 2
        y = (img_h - text_h) / 2
        image = image.rotate(45, expand=False, fillcolor=(255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        x = (img_w - text_w) / 2
        y = (img_h - text_h) / 2
    else:
        x = (img_w - text_w) / 2
        y = (img_h - text_h) / 2

    draw.text((x, y), text, fill=(128, 128, 128, 128), font=font)

    pdf_buf = io.BytesIO()
    image.convert("RGB").save(pdf_buf, format="PDF", resolution=72.0)
    pdf_buf.seek(0)
    return PdfReader(pdf_buf)


def watermark_pdf(
    data: bytes,
    text: str,
    position: WatermarkPosition = "center",
) -> bytes:
    text = text.strip()
    if not text:
        raise PdfError("Watermark text is required")
    if len(text) > 200:
        raise PdfError("Watermark text must be 200 characters or fewer")

    reader = _read_pdf(data)
    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        wm_reader = _make_watermark_page(width, height, text, position)
        wm_page = wm_reader.pages[0]
        if position == "diagonal":
            wm_page.scale_to(width, height)
        page.merge_page(wm_page)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def validate_pdf_filename(filename: str | None) -> None:
    if filename and not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise PdfError(f"Expected a PDF file, got: {filename}")
