"""3개년 핵심지표 종합.

영업현금흐름률 = 영업활동현금흐름 ÷ 매출액 × 100
현금이익전환율 = 영업활동현금흐름 ÷ 당기순이익   (순이익이 0 이하이면 해석 불가로 표시)
총차입금       = 단기차입금 + 유동성장기부채 + 장기차입금 + 사채 (config.accounts.BORROWING_CODES)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config.accounts import BORROWING_CODES

from .cash_bridge import CashBridge, cash_bridge
from .cashflow import CFOEstimate, choose_cfo, estimate_cfo
from .ccc import CCCResult, compute_ccc
from .common import Num, delta, get, growth_pct, ratio, sum_codes
from .working_capital import nwc, owc, owc_change


@dataclass
class YearAnalysis:
    year: int
    has_prev: bool
    revenue: Num = None
    op_income: Num = None
    net_income: Num = None
    cash: Num = None
    cfo_disclosed: Num = None
    cfo_estimate: CFOEstimate | None = None
    cfo: Num = None
    cfo_basis: str | None = None          # '공시' / '추정'
    cfo_diff: Num = None                   # 공시 - 추정
    ocf_margin: Num = None
    cash_conversion: Num = None
    cash_conversion_note: str = ""
    ar: Num = None
    inv: Num = None
    ap: Num = None
    nwc: Num = None
    owc: Num = None
    owc_breakdown: dict = field(default_factory=dict)
    owc_change: Num = None
    owc_change_text: str = ""
    ccc: CCCResult | None = None
    total_borrowings: Num = None
    ppe: Num = None
    revenue_growth: Num = None
    ar_growth: Num = None
    inv_growth: Num = None
    borrowings_change: Num = None
    borrowings_growth: Num = None
    cash_change: Num = None
    bridge: CashBridge | None = None


def analyze(values: dict[int, dict], years: list[int]) -> list[YearAnalysis]:
    """values: {연도: {표준코드: 금액(원)}}. years: 분석 연도(오름차순). 전년도 자료가 있으면 자동 사용."""
    out = []
    for y in sorted(years):
        cur = values.get(y, {})
        prev = values.get(y - 1)
        # 전기말 재무상태표가 있어야 증감·평균잔액을 계산할 수 있다
        prev_bs = prev if prev and (get(prev, "TOTAL_ASSETS") is not None or get(prev, "CASH") is not None) else None
        a = YearAnalysis(year=y, has_prev=prev_bs is not None)
        a.revenue, a.op_income, a.net_income = get(cur, "REVENUE"), get(cur, "OP_INCOME"), get(cur, "NET_INCOME")
        a.cash, a.ar, a.inv, a.ap, a.ppe = (get(cur, c) for c in ("CASH", "AR", "INV", "AP", "PPE"))
        a.total_borrowings = sum_codes(cur, BORROWING_CODES)

        a.cfo_disclosed = get(cur, "CFO")
        a.cfo_estimate = estimate_cfo(cur, prev_bs)
        a.cfo, a.cfo_basis = choose_cfo(a.cfo_disclosed, a.cfo_estimate)
        if a.cfo_disclosed is not None and a.cfo_estimate.value is not None:
            a.cfo_diff = a.cfo_disclosed - a.cfo_estimate.value

        a.ocf_margin = None if ratio(a.cfo, a.revenue) is None else ratio(a.cfo, a.revenue) * 100
        if a.net_income is not None and a.net_income <= 0:
            a.cash_conversion_note = "당기순이익이 0 이하라 현금이익전환율은 해석할 수 없습니다."
        else:
            a.cash_conversion = ratio(a.cfo, a.net_income)

        a.nwc = nwc(cur)
        a.owc, a.owc_breakdown = owc(cur)
        prev_owc = owc(prev_bs)[0] if prev_bs else None
        a.owc_change, a.owc_change_text = owc_change(a.owc, prev_owc)

        a.ccc = compute_ccc(cur, prev_bs)

        if prev:
            a.revenue_growth = growth_pct(a.revenue, get(prev, "REVENUE"))
        if prev_bs:
            a.ar_growth = growth_pct(a.ar, get(prev_bs, "AR"))
            a.inv_growth = growth_pct(a.inv, get(prev_bs, "INV"))
            pb = sum_codes(prev_bs, BORROWING_CODES)
            a.borrowings_change = delta(a.total_borrowings, pb)
            a.borrowings_growth = growth_pct(a.total_borrowings, pb)
            a.cash_change = delta(a.cash, get(prev_bs, "CASH"))
            a.bridge = cash_bridge(cur, prev_bs, a.revenue_growth)
        out.append(a)
    return out


# 화면·엑셀용 표 ------------------------------------------------------------
METRIC_ROWS = [
    ("매출액", "revenue", "money"),
    ("영업이익", "op_income", "money"),
    ("당기순이익", "net_income", "money"),
    ("현금및현금성자산", "cash", "money"),
    ("영업활동현금흐름", "cfo", "money"),
    ("  └ 구분", "cfo_basis", "text"),
    ("영업현금흐름률(%)", "ocf_margin", "pct"),
    ("현금이익전환율(배)", "cash_conversion", "times"),
    ("매출채권", "ar", "money"),
    ("재고자산", "inv", "money"),
    ("매입채무", "ap", "money"),
    ("순운전자본(NWC)", "nwc", "money"),
    ("영업운전자본(OWC)", "owc", "money"),
    ("영업운전자본 증감", "owc_change", "money"),
    ("DSO(일)", "ccc.dso", "days"),
    ("DIO(일)", "ccc.dio", "days"),
    ("DPO(일)", "ccc.dpo", "days"),
    ("CCC(일)", "ccc.ccc", "days"),
    ("총차입금", "total_borrowings", "money"),
    ("유형자산", "ppe", "money"),
]


def _attr(a: YearAnalysis, path: str):
    obj = a
    for part in path.split("."):
        obj = getattr(obj, part, None) if obj is not None else None
    return obj


def metrics_table(analyses: list[YearAnalysis]) -> pd.DataFrame:
    """행=지표, 열=연도 (원 단위 숫자 그대로)."""
    data = {}
    for a in analyses:
        col = {}
        for label, path, _ in METRIC_ROWS:
            v = _attr(a, path)
            if path == "cfo_basis":
                v = {"공시": "공시 영업활동현금흐름", "추정": "추정 영업활동현금흐름"}.get(v, "확인 필요")
            col[label] = v
        data[f"{a.year}년"] = col
    return pd.DataFrame(data)


def metric_kinds() -> dict[str, str]:
    return {label: kind for label, _, kind in METRIC_ROWS}
