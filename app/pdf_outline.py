# app/pdf_outline.py
from io import BytesIO
from typing import Tuple
from pypdf import PdfReader

def extract_outline_from_pdf(pdf_bytes: bytes, filename: str = "") -> Tuple[str, int]:
    """
    Lightweight, dependency-free text extractor using pypdf.
    Returns (plain_text, page_count).
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for i, p in enumerate(reader.pages):
        try:
            txt = p.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            pages.append(txt.strip())
    text = "\n\n".join(pages)
    return text, len(reader.pages or [])
