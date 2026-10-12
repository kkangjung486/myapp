"""영업활동현금흐름(CFO).

1) 현금흐름표가 있으면 '공시 영업활동현금흐름'을 우선 사용한다.
2) 없으면 재무상태표·손익계산서로 간접법 추정한다 → '추정 영업활동현금흐름'.

추정 영업활동현금흐름 =
    당기순이익
  + 감가상각비 + 무형자산상각비            (비현금비용)
  + 퇴직급여충당부채(순액) 증가             (비현금비용 성격 – 확인 가능한 경우)
  - 매출채권 증가  - 계약자산 증가  - 재고자산 증가  - 선택된 기타영업유동자산 증가
  + 매입채무 증가  + 계약부채 증가  + 선택된 기타영업유동부채 증가

부호 원칙: 영업자산 증가 = 현금 감소, 영업자산 감소 = 현금 증가,
          영업부채 증가 = 현금 증가, 영업부채 감소 = 현금 감소.

[회계판단 / 한계]
- 매출채권은 대손충당금 차감 후 순액을 쓰므로 대손상각비는 따로 가산하지 않는다(이중 반영 방지).
- 법인세·이자의 미지급/선급 변동, 외화환산손익, 자산처분손익, 평가손익 등은 재무제표 본문만으로
  정확히 분리할 수 없어 반영하지 않는다. → 반드시 '재무제표만을 이용한 추정치'로 표시한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .common import Num, delta, get

ESTIMATE_WARNING = "재무제표만을 이용한 추정치입니다. 법인세·이자 지급 시기 차이, 외화환산·처분손익 등 기타 비현금손익, 비영업 자산·부채 변동은 반영되지 않았습니다."


@dataclass
class CFOComponent:
    label: str
    amount: float
    rule: str


@dataclass
class CFOEstimate:
    value: Num
    components: list[CFOComponent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    complete: bool = False


# (표준코드, 화면 이름, 현금 영향 부호) — 자산 증가는 -1, 부채 증가는 +1
WC_ITEMS = [
    ("AR", "매출채권 증가(-)/감소(+)", -1),
    ("CONTRACT_ASSET", "계약자산(미청구공사) 증가(-)/감소(+)", -1),
    ("INV", "재고자산 증가(-)/감소(+)", -1),
    ("OTHER_OP_CA", "기타영업유동자산 증가(-)/감소(+)", -1),
    ("AP", "매입채무 증가(+)/감소(-)", +1),
    ("CONTRACT_LIAB", "계약부채(초과청구·선수) 증가(+)/감소(-)", +1),
    ("OTHER_OP_CL", "기타영업유동부채 증가(+)/감소(-)", +1),
]


def estimate_cfo(curr: dict, prev: dict | None, include_retirement: bool = True) -> CFOEstimate:
    est = CFOEstimate(value=None, warnings=[ESTIMATE_WARNING])
    ni = get(curr, "NET_INCOME")
    if ni is None:
        est.warnings.append("당기순이익을 확인할 수 없어 추정할 수 없습니다.")
        return est
    if prev is None:
        est.warnings.append("전기말 재무상태표가 없어 운전자본 증감을 계산할 수 없습니다(추정 불가).")
        return est

    comps = [CFOComponent("당기순이익", ni, "손익계산서 당기순이익")]
    dep = get(curr, "DEPRECIATION")
    if dep is None:
        est.warnings.append("감가상각비를 찾지 못해 0으로 계산했습니다. 비현금비용 가산이 누락되어 추정치가 작게 나올 수 있습니다.")
        dep = 0.0
    comps.append(CFOComponent("감가상각비(가산)", dep, "비현금비용 가산 (판관비+제조원가)"))
    amort = get(curr, "AMORTIZATION")
    if amort:
        comps.append(CFOComponent("무형자산상각비(가산)", amort, "비현금비용 가산"))
    if include_retirement:
        d_ret = delta(get(curr, "RETIREMENT"), get(prev, "RETIREMENT"))
        if d_ret:
            comps.append(CFOComponent("퇴직급여충당부채(순액) 증감", d_ret,
                                      "퇴직급여 전입액-지급액 추정 (비현금비용 성격, 확인 필요)"))

    for code, label, sign in WC_ITEMS:
        c, p = get(curr, code), get(prev, code)
        d = delta(c, p)
        if d is None:
            if code in ("AR", "INV", "AP"):
                est.warnings.append(f"{label.split(' ')[0]} 자료가 없어 추정할 수 없습니다.")
                est.components = comps
                return est
            continue
        if c == 0 and p == 0:
            continue
        comps.append(CFOComponent(label, sign * d, f"{'-' if sign < 0 else '+'}(당기말 {c:,.0f} - 전기말 {p:,.0f})"))

    est.components = comps
    est.value = sum(c.amount for c in comps)
    est.complete = get(curr, "DEPRECIATION") is not None
    return est


def choose_cfo(disclosed: Num, estimate: CFOEstimate) -> tuple[Num, str | None]:
    """공시값이 있으면 공시값, 없으면 추정값. (값, '공시'/'추정'/None)"""
    if disclosed is not None:
        return disclosed, "공시"
    if estimate.value is not None:
        return estimate.value, "추정"
    return None, None
