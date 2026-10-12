"""운전자금 규모 — 두 가지를 구분한다.

① 순운전자본 NWC = 유동자산 - 유동부채
   (현금·단기차입금까지 포함한 '단기 지급능력' 관점)

② 영업운전자본 OWC = 매출채권 + 계약자산 + 재고자산 + 선택된 기타영업유동자산
                     - 매입채무 - 계약부채 - 선택된 기타영업유동부채
   (영업을 돌리기 위해 묶여 있는 돈 관점. 현금·차입금 제외)

OWC 증가 = 현금이 추가로 운전자본에 묶임 / OWC 감소 = 운전자본에서 현금이 회수됨
"""
from __future__ import annotations

from config.accounts import OWC_ASSET_CODES, OWC_LIAB_CODES

from .common import Num, delta, get
from .formatting import approx


def nwc(values: dict) -> Num:
    ca, cl = get(values, "CA_TOTAL"), get(values, "CL_TOTAL")
    if ca is None or cl is None:
        return None
    return ca - cl


def owc(values: dict) -> tuple[Num, dict[str, float]]:
    """(영업운전자본, 구성내역). 매출채권·재고·매입채무 중 하나라도 없으면 None."""
    breakdown: dict[str, float] = {}
    for code in ("AR", "INV", "AP"):
        if get(values, code) is None:
            return None, breakdown
    total = 0.0
    for code in OWC_ASSET_CODES:
        v = get(values, code) or 0.0
        breakdown[code] = v
        total += v
    for code in OWC_LIAB_CODES:
        v = get(values, code) or 0.0
        breakdown[code] = -v
        total -= v
    return total, breakdown


def owc_change(curr_owc: Num, prev_owc: Num) -> tuple[Num, str]:
    d = delta(curr_owc, prev_owc)
    if d is None:
        return None, "전기 영업운전자본 자료가 없어 증감을 계산할 수 없습니다."
    if d > 0:
        return d, f"영업운전자본이 {approx(d)} 증가 → 약 그만큼의 현금이 추가로 영업활동(운전자본)에 묶인 것으로 해석할 수 있습니다."
    if d < 0:
        return d, f"영업운전자본이 {approx(-d)} 감소 → 운전자본에서 현금이 회수된 것으로 해석할 수 있습니다."
    return d, "영업운전자본 변동이 없습니다."
