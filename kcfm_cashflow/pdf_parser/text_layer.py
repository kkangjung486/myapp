"""PDF → 페이지별 단어(좌표 포함) 추출.

1순위: PyMuPDF 텍스트 레이어
2순위: pdfplumber 텍스트 레이어 (PyMuPDF가 없을 때)
3순위: 텍스트가 거의 없는 페이지(스캔본)만 OCR
"""
from __future__ import annotations

import io

from .models import PageWords, Word
from .ocr import ocr_available, ocr_page

MIN_TEXT_CHARS = 20  # 페이지 텍스트가 이보다 적으면 스캔 페이지로 판단


def _import_pymupdf():
    try:
        import pymupdf  # type: ignore
        return pymupdf
    except ImportError:
        try:
            import fitz  # type: ignore
            return fitz
        except ImportError:
            return None


def extract_pages(pdf_bytes: bytes, use_ocr: bool = True) -> list[PageWords]:
    pymupdf = _import_pymupdf()
    if pymupdf is not None:
        return _extract_with_pymupdf(pymupdf, pdf_bytes, use_ocr)
    return _extract_with_pdfplumber(pdf_bytes)


def _extract_with_pymupdf(pymupdf, pdf_bytes: bytes, use_ocr: bool) -> list[PageWords]:
    pages: list[PageWords] = []
    can_ocr = use_ocr and ocr_available()
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            raw = page.get_text("words")
            words = [Word(w[4], w[0], w[1], w[2], w[3]) for w in raw if str(w[4]).strip()]
            n_chars = sum(len(w.text) for w in words)
            source = "text"
            if n_chars < MIN_TEXT_CHARS:
                if can_ocr:
                    words = ocr_page(page)
                    source = "ocr" if words else "none"
                else:
                    source = "none"
            pages.append(PageWords(i + 1, float(page.rect.width), words, source))
    return pages


def _extract_with_pdfplumber(pdf_bytes: bytes) -> list[PageWords]:
    import pdfplumber

    pages: list[PageWords] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            raw = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            words = [Word(w["text"], w["x0"], w["top"], w["x1"], w["bottom"]) for w in raw]
            n_chars = sum(len(w.text) for w in words)
            source = "text" if n_chars >= MIN_TEXT_CHARS else "none"
            pages.append(PageWords(i + 1, float(page.width), words, source))
    return pages
