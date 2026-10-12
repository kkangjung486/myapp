"""자동 현금흐름 진단.

업종 평균 데이터가 없으므로 '정상/비정상'으로 단정하지 않고
'관찰' < '주의' < '집중점검' 세 단계의 신호로 표시한다.
임계값은 config/diagnostic_settings.py에서 조정한다.
각 규칙은 독립 함수이며 RULES 목록에 추가하면 된다.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import diagnostic_settings as S
from config.industry_rules import profile
from financial_calculations.formatting import approx, days, eok_man, pct
from financial_calculations.summary import YearAnalysis

LEVELS = ["관찰", "주의", "집중점검"]
LEVEL_ORDER = {lv: i for i, lv in enumerate(LEVELS)}


@dataclass
class Signal:
    level: str
    title: str
    detail: str
    years: list[int]
    basis: str = ""


def _level(value: float, thresholds: dict[str, float]) -> str | None:
    found = None
    for lv in LEVELS:
        if lv in thresholds and value >= thresholds[lv]:
            found = lv
    return found


def _cfo_label(a: YearAnalysis) -> str:
    return {"공시": "공시 영업활동현금흐름", "추정": "추정 영업활동현금흐름"}.get(a.cfo_basis or "", "영업활동현금흐름")


# ── 규칙들 ────────────────────────────────────────────────────────────────
def rule_profit_but_negative_cfo(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for a in ays:
        if a.net_income is not None and a.cfo is not None and a.net_income > 0 and a.cfo < 0:
            out.append(Signal("집중점검", f"{a.year}년: 흑자인데 영업현금흐름은 마이너스",
                              f"당기순이익 {eok_man(a.net_income)}, {_cfo_label(a)} {eok_man(a.cfo)}. "
                              "이익이 매출채권·재고 등에 묶여 현금으로 들어오지 않았습니다.", [a.year], _cfo_label(a)))
    return out


def rule_ar_vs_revenue(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for a in ays:
        if a.revenue_growth is None or a.ar_growth is None:
            continue
        gap = a.ar_growth - a.revenue_growth
        lv = _level(gap, S.AR_GROWTH_GAP)
        if lv and a.ar_growth > 0:
            out.append(Signal(lv, f"{a.year}년: 매출채권이 매출보다 빠르게 증가",
                              f"매출 증가율 {pct(a.revenue_growth)} vs 매출채권 증가율 {pct(a.ar_growth)} "
                              f"(차이 {gap:.1f}%p). 회수 조건 악화·장기 미회수 채권 여부를 점검하세요.", [a.year]))
    return out


def rule_inventory_vs_revenue(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for a in ays:
        if a.revenue_growth is None or a.inv_growth is None:
            continue
        gap = a.inv_growth - a.revenue_growth
        lv = _level(gap, S.INV_GROWTH_GAP)
        if lv and a.inv_growth > 0:
            out.append(Signal(lv, f"{a.year}년: 재고가 매출보다 빠르게 증가",
                              f"매출 증가율 {pct(a.revenue_growth)} vs 재고 증가율 {pct(a.inv_growth)} "
                              f"(차이 {gap:.1f}%p). 과잉 생산·매입, 진부화 재고 여부를 점검하세요.", [a.year]))
    return out


def _trend_rule(ays, attr: str, name: str, meaning: str) -> list[Signal]:
    vals = [(a.year, getattr(a.ccc, attr) if a.ccc else None) for a in ays]
    vals = [(y, v) for y, v in vals if v is not None]
    if len(vals) < 2:
        return []
    incs = [(vals[i][0], vals[i][1] - vals[i - 1][1]) for i in range(1, len(vals))]
    seq = " → ".join(f"{y}년 {days(v)}" for y, v in vals)
    if len(incs) >= 2 and all(d > 0 for _, d in incs):
        return [Signal("주의", f"{name} 지속 증가", f"{seq}. {meaning}", [y for y, _ in vals])]
    out = []
    for y, d in incs:
        lv = _level(d, S.DAYS_INCREASE)
        if lv:
            out.append(Signal(lv, f"{y}년: {name} {d:.0f}일 증가", f"{seq}. {meaning}", [y]))
    return out


def rule_dso_trend(ays):
    return _trend_rule(ays, "dso", "DSO(매출채권 회수기간)", "외상 회수가 늦어지면 같은 매출에도 더 많은 현금이 묶입니다.")


def rule_dio_trend(ays):
    return _trend_rule(ays, "dio", "DIO(재고 보유기간)", "재고가 오래 머물수록 현금이 재고에 묶입니다.")


def rule_ccc_worsening(ays: list[YearAnalysis]) -> list[Signal]:
    vals = [(a.year, a.ccc.ccc) for a in ays if a.ccc and a.ccc.ccc is not None]
    if len(vals) < 2:
        return []
    seq = " → ".join(f"{y}년 {days(v)}" for y, v in vals)
    incs = [vals[i][1] - vals[i - 1][1] for i in range(1, len(vals))]
    if len(vals) >= 3 and all(d > 0 for d in incs):
        return [Signal("집중점검", f"CCC(현금전환주기) {len(vals)}년 연속 악화",
                       f"{seq}. 매출 1원이 현금으로 돌아오기까지 걸리는 기간이 계속 길어지고 있습니다.", [y for y, _ in vals])]
    if incs[-1] > 0:
        return [Signal("관찰", f"{vals[-1][0]}년 CCC 악화", f"{seq}.", [vals[-1][0]])]
    return []


def rule_borrowing_without_cash(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for a in ays:
        if a.borrowings_change is None or a.cash_change is None or a.borrowings_change <= 0:
            continue
        big = a.borrowings_growth is None or a.borrowings_growth >= S.BORROWING_GROWTH_PCT
        if big and a.cash_change < a.borrowings_change * S.CASH_TO_BORROWING_RATIO:
            out.append(Signal("주의", f"{a.year}년: 차입금은 크게 늘었는데 현금은 거의 늘지 않음",
                              f"차입금 {approx(a.borrowings_change)} 증가({pct(a.borrowings_growth)}), "
                              f"현금 증감 {eok_man(a.cash_change, signed=True)}. 빌린 돈이 어디에 쓰였는지(운전자본·설비) 확인하세요.",
                              [a.year]))
    return out


def rule_owc_increase(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for a in ays:
        if a.owc_change is None or not a.revenue or a.owc_change <= 0:
            continue
        ratio = a.owc_change / a.revenue * 100
        lv = _level(ratio, S.OWC_INCREASE_PCT_OF_REVENUE)
        if lv:
            out.append(Signal(lv, f"{a.year}년: 영업운전자본 증가로 현금이 묶임",
                              f"영업운전자본이 {approx(a.owc_change)} 증가(매출액의 {ratio:.1f}%).", [a.year]))
    return out


def rule_cfo_down_borrow_up(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for prev, a in zip(ays, ays[1:]):
        if None in (a.cfo, prev.cfo, a.borrowings_change):
            continue
        if a.cfo < prev.cfo and a.borrowings_change > 0:
            out.append(Signal("주의", f"{a.year}년: 영업현금흐름 감소 + 차입금 증가",
                              f"영업활동현금흐름 {eok_man(prev.cfo)} → {eok_man(a.cfo)}, 차입금 {approx(a.borrowings_change)} 증가. "
                              "영업에서 부족한 현금을 차입으로 메우는 구조인지 점검하세요.", [prev.year, a.year],
                              f"{prev.year}년 {_cfo_label(prev)}, {a.year}년 {_cfo_label(a)}"))
    return out


def rule_profit_up_cfo_lagging(ays: list[YearAnalysis]) -> list[Signal]:
    out = []
    for prev, a in zip(ays, ays[1:]):
        if None in (a.net_income, prev.net_income, a.cfo, prev.cfo):
            continue
        if a.net_income > prev.net_income and (a.cfo - prev.cfo) < (a.net_income - prev.net_income):
            lv = "주의" if a.cfo < prev.cfo else "관찰"
            out.append(Signal(lv, f"{a.year}년: 순이익 증가를 영업현금흐름이 따라오지 못함",
                              f"순이익 {eok_man(prev.net_income)} → {eok_man(a.net_income)}, "
                              f"영업활동현금흐름 {eok_man(prev.cfo)} → {eok_man(a.cfo)}.", [prev.year, a.year]))
    for a in ays:
        if a.cash_conversion is not None and 0 <= a.cash_conversion < S.CASH_CONVERSION_LOW and a.cfo and a.cfo > 0:
            out.append(Signal("관찰", f"{a.year}년: 현금이익전환율 낮음",
                              f"영업활동현금흐름이 순이익의 {a.cash_conversion:.2f}배에 그칩니다.", [a.year]))
    return out


RULES = [
    rule_profit_but_negative_cfo,
    rule_ar_vs_revenue,
    rule_inventory_vs_revenue,
    rule_dso_trend,
    rule_dio_trend,
    rule_ccc_worsening,
    rule_borrowing_without_cash,
    rule_owc_increase,
    rule_cfo_down_borrow_up,
    rule_profit_up_cfo_lagging,
]


def run_diagnostics(analyses: list[YearAnalysis], industry: str = "기타") -> list[Signal]:
    ays = sorted(analyses, key=lambda a: a.year)
    signals: list[Signal] = []
    for rule in RULES:
        signals.extend(rule(ays))
    prof = profile(industry)
    if not prof.get("dio_meaningful", True):
        signals = [s for s in signals if "DIO" not in s.title and "재고" not in s.title] + [
            Signal("관찰", "업종 특성: 재고 지표 해석 제한", "선택한 업종은 재고 비중이 낮아 DIO·재고 신호는 표시하지 않았습니다.", [])
        ]
    if industry == "건설업":
        for a in ays:
            if a.bridge:
                ca = next((i for i in a.bridge.items if i.key == "CONTRACT_ASSET" and i.amount < 0), None)
                if ca:
                    signals.append(Signal("주의", f"{a.year}년: 미청구공사(계약자산) 증가",
                                          f"{approx(-ca.amount)}의 현금이 미청구공사에 묶였습니다. 공사 진행률·기성 청구 지연 여부를 확인하세요.",
                                          [a.year]))
    signals.sort(key=lambda s: (-LEVEL_ORDER[s.level], s.years[-1] if s.years else 0))
    return signals
