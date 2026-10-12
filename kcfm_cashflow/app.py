"""KCFM 기업 현금흐름 진단 — Streamlit 앱 진입점.

실행:  streamlit run app.py
"""
from __future__ import annotations

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.industry_rules import INDUSTRIES  # noqa: E402
from data_pipeline.extraction import block_metas  # noqa: E402
from pdf_parser.ocr import ocr_available  # noqa: E402
from pdf_parser.statement_parser import parse_pdf  # noqa: E402
from ui.results import render_results  # noqa: E402
from ui.review import rebuild_rows, render_review  # noqa: E402
from ui.styles import CSS, header_html  # noqa: E402

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data", "pdfs")
SAMPLE_FILES = ["2023년_재무제표_케이씨정밀.pdf", "2024년_재무제표_케이씨정밀.pdf", "2025년_재무제표_케이씨정밀.pdf"]

st.set_page_config(page_title="KCFM 기업 현금흐름 진단", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

s = st.session_state
s.setdefault("step", 0)


def load(files: list[tuple[str, bytes]], use_ocr: bool) -> None:
    docs = []
    progress = st.progress(0.0, text="PDF를 읽는 중...")
    for i, (name, data) in enumerate(files):
        progress.progress(i / len(files), text=f"{name} 읽는 중...")
        try:
            docs.append(parse_pdf(data, name, use_ocr=use_ocr))
        except Exception as e:  # 손상된 PDF 등
            st.error(f"{name}: PDF를 읽을 수 없습니다 ({e})")
    progress.empty()
    if not docs:
        return
    s.docs = docs
    s.metas = block_metas(docs)
    s.company = next((d.company_name for d in docs if d.company_name), "")
    rebuild_rows()
    s.step = 1
    st.rerun()


def render_upload() -> None:
    st.markdown("#### 1. 업종 선택")
    industry = st.selectbox("업종", INDUSTRIES, index=None, placeholder="업종을 선택하세요",
                            help="업종에 따라 계정 해석과 진단 포인트가 달라집니다. (MVP에서는 업종별 점수·기준치를 쓰지 않습니다)")
    st.markdown("#### 2. 최근 3개년 재무제표 PDF 업로드")
    st.caption("예: 2023년 재무제표.pdf, 2024년 재무제표.pdf, 2025년 재무제표.pdf · 한 PDF에 3개년이 모두 있어도 됩니다. "
               "각 PDF의 '전기' 열은 첫 해의 기초잔액(평균잔액·증감 계산)에 사용됩니다.")
    uploads = st.file_uploader("PDF 파일", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    if ocr_available():
        use_ocr = st.checkbox("스캔 PDF는 OCR로 읽기 (텍스트가 있는 PDF는 OCR을 쓰지 않음)", value=True)
    else:
        use_ocr = False
        st.caption("ℹ️ OCR(Tesseract)이 설치되어 있지 않아 스캔 PDF는 자동으로 읽을 수 없습니다. 이 경우 검증 화면에서 직접 입력하세요.")

    c1, c2 = st.columns([1, 1])
    if c1.button("PDF 읽기 ▶", type="primary", disabled=not uploads or not industry, width="stretch"):
        s.industry = industry
        load([(u.name, u.getvalue()) for u in uploads], use_ocr)
    if c2.button("샘플 데이터로 체험하기 (가상 제조업체)", width="stretch"):
        if not all(os.path.exists(os.path.join(SAMPLE_DIR, f)) for f in SAMPLE_FILES):
            from sample_data.generate_sample_pdfs import generate
            generate(SAMPLE_DIR)
        s.industry = industry or "제조업"
        load([(f, open(os.path.join(SAMPLE_DIR, f), "rb").read()) for f in SAMPLE_FILES], False)
    if uploads and not industry:
        st.caption("업종을 선택하면 'PDF 읽기' 버튼이 활성화됩니다.")


st.markdown(header_html(s.step), unsafe_allow_html=True)
if s.step == 0:
    render_upload()
elif s.step == 1:
    render_review()
else:
    if s.get("committed") is None:
        s.step = 1
        st.rerun()
    render_results()
