"""OCR fallback (스캔 PDF 전용).

텍스트 레이어가 없는 페이지에서만 사용한다.
Tesseract(한국어 kor 언어팩)와 pytesseract가 설치되어 있지 않으면 사용하지 않고
'수동 입력 필요'로 안내한다. OCR 결과는 모두 '확인 필요'로 표시된다.
"""
from __future__ import annotations

import shutil

from .models import Word

OCR_DPI = 300


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def ocr_page(page) -> list[Word]:
    """PyMuPDF page → OCR 단어 목록 (좌표는 PDF point 단위로 환산)."""
    import io

    import pytesseract
    from PIL import Image

    zoom = OCR_DPI / 72
    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    data = pytesseract.image_to_data(
        image, lang="kor+eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    words: list[Word] = []
    for i, text in enumerate(data["text"]):
        text = (text or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if conf < 0:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append(Word(text, x / zoom, y / zoom, (x + w) / zoom, (y + h) / zoom))
    return words
