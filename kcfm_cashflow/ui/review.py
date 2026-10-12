"""② 재무제표 추출 결과 확인 화면."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.accounts import LABEL_OPTIONS
from data_pipeline.aggregation import aggregate
from data_pipeline.edits import apply_edits
from data_pipeline.extraction import build_rows, default_analysis_years, select_sources
from financial_calculations.validation import checks_frame, run_checks
from pdf_parser.models import STATEMENT_NAMES
from pdf_parser.numbers import UNIT_MULTIPLIERS

EDITOR_COLUMNS = ["statement_name", "label", "raw_text", "unit", "extracted_won", "confirmed_won",
                  "std_label", "include", "status", "note", "page"]


def rebuild_rows() -> None:
    s = st.session_state
    s.all_rows = build_rows(s.docs, s.metas, s.industry)
    s.selected, s.choices, s.source_warnings = select_sources(s.all_rows)
    s.analysis_years = default_analysis_years(s.selected)
    s.editor_version = s.get("editor_version", 0) + 1
    s.committed = None  # '분석 시작' 때 확정한 표 (결과 화면에서 돌아와도 수정 내용 유지)


def display_years() -> list[int]:
    s = st.session_state
    years = sorted(s.analysis_years)
    if not years:
        return []
    opening = years[0] - 1
    has_opening = not s.selected[(s.selected["year"] == opening) & (s.selected["statement"] == "BS")].empty
    return ([opening] if has_opening else []) + years


def rows_for_year(year: int, opening: bool) -> pd.DataFrame:
    committed = st.session_state.get("committed")
    sel = st.session_state.selected
    if committed is not None and (committed["year"] == year).any():
        sel = committed
    g = sel[sel["year"] == year]
    if opening:
        g = g[g["statement"] == "BS"]
    order = {"BS": 0, "IS": 1, "COGS": 2, "CF": 3}
    return g.assign(_o=g["statement"].map(order)).sort_values(["_o", "file", "block", "order"]).drop(columns="_o").reset_index(drop=True)


def render_review() -> None:
    s = st.session_state
    st.subheader("재무제표 추출 결과 확인")
    st.markdown(
        "PDF에서 읽은 숫자와 계정 분류를 **분석 전에 반드시 확인**하세요. "
        "잘못 읽힌 숫자는 `확인금액(원)`에서 고치고, `미분류(확인 필요)` 계정은 표준 계정을 선택하세요. "
        "원본 추출값은 따로 보관됩니다."
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        detected = next((d.company_name for d in s.docs if d.company_name), "")
        s.company = st.text_input("회사명", value=s.get("company") or detected or "", help="PDF에서 자동 인식한 회사명입니다. 수정할 수 있습니다.")
    with c2:
        st.text_input("업종", value=s.industry, disabled=True)

    # 파일 경고
    doc_warnings = [f"[{d.filename}] {w}" for d in s.docs for w in d.warnings]
    block_warnings = [f"[{m.file} / {STATEMENT_NAMES[m.statement]}] {w}" for m in s.metas for w in m.warnings]
    cross = [w for w in s.source_warnings if w.startswith("[대조 불일치]")]
    if cross:
        st.error("**전기·당기 자료 대조 불일치**\n\n" + "\n".join(f"- {w}" for w in cross))
    other = doc_warnings + block_warnings + [w for w in s.source_warnings if w not in cross]
    if other:
        with st.expander(f"인식 경고 {len(other)}건", expanded=True):
            for w in other:
                st.warning(w)

    # 2-1 파일별 인식 정보
    st.markdown("#### 1. 파일별 인식 정보 (단위 · 연도)")
    st.caption("단위가 틀리면 모든 숫자가 1,000배씩 틀립니다. 원본 PDF의 '(단위: 원/천원/백만원)' 표기와 꼭 대조하세요. "
               "연도는 표의 왼쪽 열부터 순서대로 입력합니다(예: 2025, 2024).")
    meta_df = pd.DataFrame([{
        "파일": m.file, "재무제표": STATEMENT_NAMES[m.statement], "페이지": ", ".join(map(str, m.pages)),
        "단위": m.unit, "단위 인식": m.unit_source,
        "연도(왼쪽 열부터)": ", ".join("" if y is None else str(y) for y in m.years),
        "연도 인식": m.year_source, "형식": "연도별 2열(세부/합계)" if m.layout == "paired" else "연도별 1열",
    } for m in s.metas])
    if meta_df.empty:
        st.info("인식된 재무제표 표가 없습니다. 아래 표에서 직접 입력하거나 다른 PDF를 업로드하세요.")
    else:
        edited_meta = st.data_editor(
            meta_df, hide_index=True, width="stretch", key=f"meta_{s.get('meta_version', 0)}",
            disabled=["파일", "재무제표", "페이지", "단위 인식", "연도 인식", "형식"],
            column_config={"단위": st.column_config.SelectboxColumn("단위", options=list(UNIT_MULTIPLIERS), required=True)},
        )
        if st.button("단위·연도 수정 반영", help="수정한 단위·연도로 다시 계산합니다. 아래 표에서 고친 내용은 초기화됩니다."):
            ok = True
            for m, (_, r) in zip(s.metas, edited_meta.iterrows()):
                try:
                    years = [int(x.strip()) if x.strip() else None for x in str(r["연도(왼쪽 열부터)"]).split(",")]
                except ValueError:
                    st.error(f"{m.file} {STATEMENT_NAMES[m.statement]}: 연도는 숫자로 입력하세요.")
                    ok = False
                    break
                if r["단위"] != m.unit:
                    m.unit, m.unit_source = r["단위"], "사용자 지정"
                if years != m.years:
                    m.years = (years + [None] * len(m.years))[: len(m.years)]
                    m.year_source = "사용자 지정"
            if ok:
                rebuild_rows()
                s.meta_version = s.get("meta_version", 0) + 1
                st.rerun()

    with st.expander("연도별로 사용한 자료 (같은 연도가 여러 PDF에 있으면 '당기' 자료 우선)"):
        st.dataframe(pd.DataFrame([{
            "연도": c.year, "재무제표": STATEMENT_NAMES[c.statement], "사용 파일": c.file,
            "열 위치": "당기(첫 열)" if c.col == 0 else f"{c.col + 1}번째 열(전기 등)",
            "대조용 다른 자료": ", ".join(f"{f}({'당기' if col == 0 else '전기'})" for f, _, col in c.alternatives),
        } for c in sorted(s.choices, key=lambda c: (c.year, c.statement))]), hide_index=True, width="stretch")

    # 2-2 분석 연도
    st.markdown("#### 2. 분석 연도")
    all_years = sorted({int(y) for y in s.selected["year"].dropna()}) if not s.selected.empty else []
    if not all_years:
        y0 = pd.Timestamp.now().year - 1
        all_years = [y0 - 2, y0 - 1, y0]
    chosen = st.multiselect("분석할 연도 (최대 3개 권장)", options=all_years,
                            default=[y for y in s.analysis_years if y in all_years] or all_years[-3:])
    if sorted(chosen) != sorted(s.analysis_years):
        s.analysis_years = sorted(chosen)
        st.rerun()
    years = display_years()
    if years and years[0] not in s.analysis_years:
        st.caption(f"※ {years[0]}년 재무상태표는 첫 해({s.analysis_years[0]}년)의 평균잔액·증감 계산용(기초잔액)으로만 사용합니다.")
    elif s.analysis_years:
        st.caption(f"※ {s.analysis_years[0] - 1}년 재무상태표(전기 자료)가 없어 첫 해는 평균잔액 대신 기말잔액을 쓰고, 추정 영업현금흐름은 계산할 수 없습니다.")

    # 2-3 연도별 표
    st.markdown("#### 3. 연도별 추출 결과 (수정 가능)")
    st.caption("상태: 자동 인식 / 자동(유사 명칭) / **확인 필요** / 소계 제외(중복 방지). 미분류 계정에 표준 계정을 고르면 '분석 포함'은 자동으로 반영됩니다. 행 추가(수동 입력)는 표 아래 '+'를 누르세요.")
    if not years:
        st.info("분석 연도를 선택하세요.")
        return
    tabs = st.tabs([f"{y}년" + (" (기초잔액용)" if y not in s.analysis_years else "") for y in years])
    edited_all = []
    for tab, y in zip(tabs, years):
        with tab:
            base = rows_for_year(y, opening=y not in s.analysis_years)
            n_review = int((base["status"] == "확인 필요").sum())
            if n_review:
                st.warning(f"확인 필요 항목 {n_review}개 – '메모'의 제안을 참고해 표준 계정을 선택하세요.")
            edited = st.data_editor(
                base, key=f"ed_{s.editor_version}_{y}", num_rows="dynamic", width="stretch", height=520,
                hide_index=True, column_order=EDITOR_COLUMNS,
                column_config={
                    "statement_name": st.column_config.SelectboxColumn("재무제표", options=list(STATEMENT_NAMES.values()), width="small"),
                    "label": st.column_config.TextColumn("원본 계정명", width="medium"),
                    "raw_text": st.column_config.TextColumn("원문 숫자", disabled=True, width="small"),
                    "unit": st.column_config.TextColumn("단위", disabled=True, width="small"),
                    "extracted_won": st.column_config.NumberColumn("추출금액(원)", disabled=True, format="localized"),
                    "confirmed_won": st.column_config.NumberColumn("확인금액(원) ✎", format="localized",
                                                                   help="잘못 읽힌 숫자는 여기서 수정 (원 단위)"),
                    "std_label": st.column_config.SelectboxColumn("표준 계정 ✎", options=LABEL_OPTIONS, required=True, width="medium"),
                    "include": st.column_config.CheckboxColumn("분석 포함 ✎", width="small"),
                    "status": st.column_config.TextColumn("상태", disabled=True, width="small"),
                    "note": st.column_config.TextColumn("메모", disabled=True, width="large"),
                    "page": st.column_config.NumberColumn("페이지", disabled=True, width="small"),
                },
            )
            fixed = apply_edits(base, edited, y)
            n_edit = int(fixed["status"].isin(["수정됨", "수동 추가"]).sum())
            if n_edit:
                st.caption(f"✎ 이 연도에서 수정·추가한 행: {n_edit}개")
            edited_all.append(fixed)
    final = pd.concat(edited_all, ignore_index=True) if edited_all else pd.DataFrame()
    s.final_rows = final

    # 2-4 실시간 검증
    st.markdown("#### 4. 숫자 검증 (현재 표 기준)")
    std = aggregate(final)
    checks = run_checks(std, final, s.analysis_years, s.metas)
    cdf = checks_frame(checks)
    counts = cdf["결과"].value_counts().to_dict() if not cdf.empty else {}
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("통과", counts.get("통과", 0))
    k2.metric("경고", counts.get("경고", 0))
    k3.metric("실패", counts.get("실패", 0))
    k4.metric("확인불가", counts.get("확인불가", 0))
    issues = cdf[cdf["결과"].isin(["실패", "경고", "확인불가"])]
    if not issues.empty:
        st.dataframe(issues, hide_index=True, width="stretch")
    with st.expander("전체 검증 결과"):
        st.dataframe(cdf, hide_index=True, width="stretch")

    st.divider()
    b1, b2 = st.columns([1, 4])
    if b1.button("← 다시 업로드"):
        s.step = 0
        st.rerun()
    if b2.button("분석 시작 ▶", type="primary", width="stretch", disabled=not s.analysis_years):
        s.committed = final
        s.editor_version += 1
        s.step = 2
        st.rerun()
