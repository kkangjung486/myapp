"""③ 분석 결과 대시보드."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.accounts import STANDARD_ACCOUNTS, label_of
from config.industry_rules import profile
from data_pipeline.aggregation import aggregate, to_values
from diagnostic_rules.rules import run_diagnostics
from export.excel_export import FORMULAS, build_excel
from financial_calculations.ccc import DPO_COGS_PROXY_MSG
from financial_calculations.formatting import days, eok_man, eok_short, pct, times, won
from financial_calculations.summary import analyze, metric_kinds, metrics_table
from financial_calculations.validation import checks_frame, has_failure, run_checks

from . import charts
from .styles import badge, cfo_badge


def compute():
    s = st.session_state
    rows = s.committed
    std = aggregate(rows)
    analyses = analyze(to_values(std), s.analysis_years)
    checks = run_checks(std, rows, s.analysis_years, s.metas)
    signals = run_diagnostics(analyses, s.industry)
    return std, analyses, checks, signals


def _fmt_table(df: pd.DataFrame, raw: bool) -> pd.DataFrame:
    kinds = metric_kinds()
    out = df.copy().astype(object)
    for label in out.index:
        k = kinds.get(label, "money")
        for c in out.columns:
            v = df.at[label, c]
            if k == "money":
                out.at[label, c] = won(v) if raw else eok_man(v)
            elif k == "days":
                out.at[label, c] = days(v)
            elif k == "pct":
                out.at[label, c] = pct(v)
            elif k == "times":
                out.at[label, c] = times(v)
            else:
                out.at[label, c] = v
    return out


def render_results() -> None:
    s = st.session_state
    std, analyses, checks, signals = compute()
    years = [a.year for a in analyses]
    last = analyses[-1]
    prev = analyses[-2] if len(analyses) > 1 else None

    st.subheader(f"{s.company or '(회사명 미입력)'} · {s.industry} · {years[0]}~{years[-1]}년")
    cdf = checks_frame(checks)
    if has_failure(checks):
        st.error("⚠️ **검증 실패 항목이 있습니다.** 아래 숫자를 확정적으로 사용하지 말고, '검증·계산근거' 탭과 추출 결과를 다시 확인하세요.")
    n_warn = int((cdf["결과"] == "경고").sum()) if not cdf.empty else 0
    if n_warn:
        st.warning(f"검증 경고 {n_warn}건 – '검증·계산근거' 탭에서 확인하세요.")
    if any(a.cfo_basis == "추정" for a in analyses):
        st.info("ℹ️ 일부 연도는 현금흐름표가 없어 **추정 영업활동현금흐름**(재무제표만을 이용한 추정치)을 사용했습니다.")

    excel = build_excel(
        company=s.company or "", industry=s.industry, analysis_years=years, files=[d.filename for d in s.docs],
        metas=s.metas, warnings=s.source_warnings + [w for d in s.docs for w in d.warnings],
        selected_rows=s.committed, std=std, analyses=analyses, signals=signals, checks_df=cdf,
    )
    fname = f"KCFM_현금흐름진단_{(s.company or '회사').replace(' ', '')}_{years[0]}-{years[-1]}.xlsx"
    st.download_button("📥 분석 결과 Excel 다운로드", excel, file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

    tabs = st.tabs(["핵심 요약", "돈이 어디에 묶였나", "영업활동현금흐름", "운전자본", "현금전환주기(CCC)",
                    "진단 신호", "검증·계산근거"])

    # ── 핵심 요약 ────────────────────────────────────────────
    with tabs[0]:
        st.markdown(f"#### {last.year}년 핵심 숫자 " + cfo_badge(last.cfo_basis), unsafe_allow_html=True)

        def delta_money(cur, old):
            if cur is None or old is None:
                return None
            return eok_man(cur - old, signed=True) + " (전년비)"

        def delta_days(cur, old):
            if cur is None or old is None:
                return None
            return f"{cur - old:+.1f}일 (전년비)"

        p = prev
        r1 = st.columns(4)
        r1[0].metric("영업활동현금흐름", eok_short(last.cfo), delta_money(last.cfo, p and p.cfo),
                     help=f"{won(last.cfo)} · {('공시' if last.cfo_basis == '공시' else '추정')} 기준")
        r1[1].metric("영업운전자본(OWC)", eok_short(last.owc), delta_money(last.owc, p and p.owc), delta_color="inverse",
                     help=f"{won(last.owc)} · 증가 = 현금이 더 묶임")
        r1[2].metric("현재 현금", eok_short(last.cash), delta_money(last.cash, p and p.cash), help=won(last.cash))
        r1[3].metric("총차입금", eok_short(last.total_borrowings), delta_money(last.total_borrowings, p and p.total_borrowings),
                     delta_color="inverse", help=won(last.total_borrowings))
        r2 = st.columns(4)
        c, pc = last.ccc, (p.ccc if p else None)
        r2[0].metric("DSO 매출채권 회수기간", days(c.dso), delta_days(c.dso, pc and pc.dso), delta_color="inverse")
        r2[1].metric("DIO 재고 보유기간", days(c.dio), delta_days(c.dio, pc and pc.dio), delta_color="inverse")
        r2[2].metric("DPO 매입채무 지급기간", days(c.dpo), delta_days(c.dpo, pc and pc.dpo))
        r2[3].metric("CCC 현금전환주기", days(c.ccc), delta_days(c.ccc, pc and pc.ccc), delta_color="inverse")
        if c.purchases_basis == "매출원가 대용":
            st.caption(f"※ {DPO_COGS_PROXY_MSG}")
        if c.ar_method.startswith("평균잔액 자료 부족"):
            st.caption("※ 평균잔액 자료 부족으로 기말잔액 사용")

        st.markdown("#### 3개년 핵심지표")
        raw = st.toggle("원 단위로 보기", value=False, help="끄면 억/만원 단위로 표시합니다.")
        mt = metrics_table(analyses)
        st.dataframe(_fmt_table(mt, raw), width="stretch", height=740)

        st.markdown("#### 3개년 추이")
        g1, g2 = st.columns(2)
        g1.plotly_chart(charts.bar_money(years, [a.cfo for a in analyses], "영업활동현금흐름"), width="stretch")
        g2.plotly_chart(charts.bar_money(years, [a.cash for a in analyses], "현금잔액"), width="stretch")
        g3, g4 = st.columns(2)
        g3.plotly_chart(charts.grouped_money(years, {"매출채권": [a.ar for a in analyses], "재고자산": [a.inv for a in analyses],
                                                     "매입채무": [a.ap for a in analyses]}, "매출채권·재고·매입채무"),
                        width="stretch")
        g4.plotly_chart(charts.lines_days(years, {"DSO": [a.ccc.dso for a in analyses], "DIO": [a.ccc.dio for a in analyses],
                                                  "DPO": [a.ccc.dpo for a in analyses]}, "DSO·DIO·DPO (일)"),
                        width="stretch")
        g5, g6 = st.columns(2)
        g5.plotly_chart(charts.lines_days(years, {"CCC": [a.ccc.ccc for a in analyses]}, "CCC 현금전환주기 (일)"),
                        width="stretch")
        g6.plotly_chart(charts.bar_money(years, [a.owc for a in analyses], "영업운전자본(OWC)"), width="stretch")
        g7, _ = st.columns(2)
        g7.plotly_chart(charts.grouped_money(years, {"총차입금": [a.total_borrowings for a in analyses],
                                                     "현금잔액": [a.cash for a in analyses]}, "차입금과 현금잔액 비교"),
                        width="stretch")

    # ── 돈이 어디에 묶였나 ──────────────────────────────────
    with tabs[1]:
        st.markdown("### 우리 회사의 돈은 어디에 묶여 있을까요?")
        avail = [a for a in analyses if a.bridge]
        if not avail:
            st.info("전년도 재무상태표가 없어 전년 대비 변화를 계산할 수 없습니다.")
        else:
            sel_year = st.radio("연도", [a.year for a in avail], index=len(avail) - 1, horizontal=True,
                                format_func=lambda y: f"{y}년 (전년 대비)")
            a = next(x for x in avail if x.year == sel_year)
            b = a.bridge
            st.markdown('<div class="kc-narr">' + "<br>".join(b.narrative) + "</div>", unsafe_allow_html=True)
            st.write("")
            st.plotly_chart(charts.waterfall([(i.label, i.amount) for i in b.items], "현금 증감",
                                             f"{sel_year}년 현금 증감 분해 (억원)"), width="stretch")
            tbl = pd.DataFrame([{"항목": i.label, "현금 영향": eok_man(i.amount, signed=True), "원 단위": won(i.amount)}
                                for i in b.items]
                               + [{"항목": "최종 현금 증가·감소액", "현금 영향": eok_man(b.cash_change, signed=True),
                                   "원 단위": won(b.cash_change)}])
            st.dataframe(tbl, hide_index=True, width="stretch")
            st.caption("현금 영향이 플러스(+)면 현금을 늘린 요인, 마이너스(-)면 현금을 줄인(묶은) 요인입니다. "
                       "유형자산은 감가상각 후 장부가 증가액입니다. '기타'는 위 항목으로 설명되지 않는 잔여 차이입니다.")

    # ── 영업활동현금흐름 ────────────────────────────────────
    with tabs[2]:
        st.markdown("#### 공시 vs 추정 영업활동현금흐름")
        cf_tbl = pd.DataFrame([{
            "연도": f"{a.year}년", "공시 영업활동현금흐름": eok_man(a.cfo_disclosed) if a.cfo_disclosed is not None else "현금흐름표 없음",
            "추정 영업활동현금흐름": eok_man(a.cfo_estimate.value), "차이(공시-추정)": eok_man(a.cfo_diff) if a.cfo_diff is not None else "-",
            "분석 사용값": eok_man(a.cfo), "사용 기준": a.cfo_basis or "확인 필요",
            "영업현금흐름률": pct(a.ocf_margin), "현금이익전환율": times(a.cash_conversion) if a.cash_conversion is not None else (a.cash_conversion_note or "확인 필요"),
        } for a in analyses])
        st.dataframe(cf_tbl, hide_index=True, width="stretch")
        st.caption("공시값이 있으면 공시값을 우선 사용합니다. 공시와 추정의 차이는 추정식에 반영되지 않는 항목(미지급법인세·미수금·미지급금 변동 등) 때문입니다.")
        for a in analyses:
            with st.expander(f"{a.year}년 추정 영업활동현금흐름 계산 내역"):
                est = a.cfo_estimate
                for w in est.warnings:
                    st.warning(w)
                if est.components:
                    st.dataframe(pd.DataFrame([{"항목": c.label, "금액": eok_man(c.amount, signed=True), "원 단위": won(c.amount),
                                                "계산 근거": c.rule} for c in est.components]
                                              + [{"항목": "추정 영업활동현금흐름", "금액": eok_man(est.value), "원 단위": won(est.value),
                                                  "계산 근거": "위 항목 합계"}]),
                                 hide_index=True, width="stretch")

    # ── 운전자본 ────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### 순운전자본(NWC)과 영업운전자본(OWC)")
        st.markdown("- **순운전자본 NWC** = 유동자산 − 유동부채 (현금·단기차입금 포함, 단기 지급능력 관점)\n"
                    "- **영업운전자본 OWC** = 매출채권 + 계약자산 + 재고자산 + 선택된 기타영업유동자산 − 매입채무 − 계약부채 − 선택된 기타영업유동부채 "
                    "(영업에 묶인 돈 관점)")
        codes = ["AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA", "AP", "CONTRACT_LIAB", "OTHER_OP_CL"]
        recs = {}
        for a in analyses:
            col = {f"(+) {label_of(c)}" if c in ("AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA") else f"(−) {label_of(c)}":
                   eok_man(abs(a.owc_breakdown.get(c, 0))) for c in codes if any(x.owc_breakdown.get(c) for x in analyses)}
            col["= 영업운전자본(OWC)"] = eok_man(a.owc)
            col["전년 대비 OWC 증감"] = eok_man(a.owc_change, signed=True) if a.owc_change is not None else "확인 필요"
            col["순운전자본(NWC)"] = eok_man(a.nwc)
            recs[f"{a.year}년"] = col
        st.dataframe(pd.DataFrame(recs), width="stretch")
        for a in analyses:
            st.markdown(f"**{a.year}년** — {a.owc_change_text}")
        st.plotly_chart(charts.bar_money(years, [a.owc_change for a in analyses], "전년 대비 영업운전자본 증감 (증가 = 현금이 묶임)"),
                        width="stretch")

    # ── CCC ────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("#### 현금전환주기 계산 내역")
        st.markdown("DSO = 평균 매출채권 ÷ 매출액 × 365 · DIO = 평균 재고자산 ÷ 매출원가 × 365 · "
                    "DPO = 평균 매입채무 ÷ 연간 매입액 × 365 · **CCC = DSO + DIO − DPO**")
        st.dataframe(pd.DataFrame([{
            "연도": f"{a.year}년", "DSO": days(a.ccc.dso), "DIO": days(a.ccc.dio), "DPO": days(a.ccc.dpo), "CCC": days(a.ccc.ccc),
            "잔액 기준": a.ccc.ar_method, "DPO 분모": f"{a.ccc.purchases_basis} {eok_man(a.ccc.purchases)}",
            "참고 DPO(재고증감 반영 추정매입액)": days(a.ccc.dpo_ref),
        } for a in analyses]), hide_index=True, width="stretch")
        for a in analyses:
            for n in a.ccc.notes:
                st.caption(f"{a.year}년: {n}")
            if a.ccc.dso_with_contract is not None:
                st.caption(f"{a.year}년: 참고 – 계약자산(미청구공사) 포함 DSO {days(a.ccc.dso_with_contract)}")
        st.caption("참고 DPO의 추정매입액 = 매출원가 + 기말재고 − 기초재고. 제조업은 노무비·경비가 포함되어 매입액이 과대 추정될 수 있어 참고용입니다.")

    # ── 진단 ──────────────────────────────────────────────
    with tabs[5]:
        st.markdown("#### 자동 현금흐름 진단")
        st.caption("업종 평균 기준이 없으므로 '정상/비정상'으로 단정하지 않고 관찰 · 주의 · 집중점검 단계로 표시합니다.")
        if not signals:
            st.success("탐지된 신호가 없습니다.")
        for sg in signals:
            basis = f'<div class="kc-small">기준: {sg.basis}</div>' if sg.basis else ""
            st.markdown(f'<div class="kc-signal"><div class="t">{badge(sg.level)}{sg.title}</div>'
                        f'<div class="d">{sg.detail}</div>{basis}</div>', unsafe_allow_html=True)
        st.markdown("##### 업종별 점검 포인트")
        for fp in profile(s.industry)["focus_points"]:
            st.markdown(f"- {fp}")

    # ── 검증·계산근거 ─────────────────────────────────────
    with tabs[6]:
        st.markdown("#### 검증 결과")
        st.dataframe(cdf, hide_index=True, width="stretch")
        st.markdown("#### 표준화 재무데이터 (원)")
        yrs = sorted(std)
        recs = []
        for acc in STANDARD_ACCOUNTS:
            if acc.kind == "excluded":
                continue
            vals = {f"{y}년": std[y].values.get(acc.code) for y in yrs}
            if all(v is None for v in vals.values()):
                continue
            recs.append({"표준 계정": acc.label, **{k: won(v) if v is not None else "-" for k, v in vals.items()},
                         "비고": "; ".join(n for y in yrs for n in std[y].notes.get(acc.code, []))})
        st.dataframe(pd.DataFrame(recs), hide_index=True, width="stretch", height=600)
        st.markdown("#### 계산식")
        st.dataframe(pd.DataFrame(FORMULAS, columns=["지표", "계산식"]), hide_index=True, width="stretch")

    st.divider()
    if st.button("← 추출 결과 확인으로 돌아가기"):
        s.step = 1
        st.rerun()
