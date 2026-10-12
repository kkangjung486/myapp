"""'우리 회사의 돈은 어디에 묶여 있을까요?' — 전년 대비 현금 증감 분해.

현금 영향(+는 현금 증가, -는 현금 감소)
  당기순이익                       +당기순이익
  매출채권 증가로 묶인 현금          -(매출채권 증가액)
  계약자산(미청구공사) 증가          -(증가액)
  재고 증가로 묶인 현금              -(재고 증가액)
  매입채무 증가로 확보한 현금        +(매입채무 증가액)
  계약부채 증가                      +(증가액)
  유형자산 증가액(장부가 순증가)     -(유형자산 증가액)   ※ 감가상각 후 장부가 기준
  차입금 증가액                      +(총차입금 증가액)
  기타(잔여)                         = 현금 증감 - 위 항목 합계  (자본변동·기타 자산부채 등)
  ───────────────────────────────
  최종 현금 증가·감소액              = 당기말 현금 - 전기말 현금

순이익과 '유형자산 장부가 순증가'를 함께 쓰면 감가상각비가 서로 상쇄되므로 별도로 더하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from config.accounts import BORROWING_CODES

from .common import Num, delta, get, sum_codes
from .formatting import approx


@dataclass
class BridgeItem:
    key: str
    label: str
    amount: float


@dataclass
class CashBridge:
    items: list[BridgeItem] = field(default_factory=list)
    cash_change: Num = None
    other: Num = None
    wc_tied: float = 0.0          # 매출채권·계약자산·재고 증가로 묶인 현금(양수)
    narrative: list[str] = field(default_factory=list)


def cash_bridge(curr: dict, prev: dict | None, revenue_growth: Num = None) -> CashBridge | None:
    if prev is None:
        return None
    b = CashBridge()
    b.cash_change = delta(get(curr, "CASH"), get(prev, "CASH"))
    d = {c: delta(get(curr, c), get(prev, c)) for c in ("AR", "CONTRACT_ASSET", "INV", "AP", "CONTRACT_LIAB", "PPE")}
    d_borrow = delta(sum_codes(curr, BORROWING_CODES), sum_codes(prev, BORROWING_CODES))
    ni = get(curr, "NET_INCOME")

    def add(key, label_up, label_down, change, sign):
        if change is None or change == 0:
            return
        b.items.append(BridgeItem(key, label_up if change > 0 else label_down, sign * change))

    if ni is not None:
        b.items.append(BridgeItem("NI", "당기순이익", ni))
    add("AR", "매출채권 증가로 묶인 현금", "매출채권 감소로 회수된 현금", d["AR"], -1)
    add("CONTRACT_ASSET", "계약자산(미청구공사) 증가로 묶인 현금", "계약자산 감소로 회수된 현금", d["CONTRACT_ASSET"], -1)
    add("INV", "재고 증가로 묶인 현금", "재고 감소로 회수된 현금", d["INV"], -1)
    add("AP", "매입채무 증가로 확보한 현금", "매입채무 감소로 지급한 현금", d["AP"], +1)
    add("CONTRACT_LIAB", "계약부채(선수) 증가로 확보한 현금", "계약부채 감소", d["CONTRACT_LIAB"], +1)
    add("PPE", "유형자산 증가액(장부가)", "유형자산 감소액(장부가)", d["PPE"], -1)
    add("BORROW", "차입금 증가액", "차입금 상환(감소)액", d_borrow, +1)

    if b.cash_change is not None:
        b.other = b.cash_change - sum(i.amount for i in b.items)
        b.items.append(BridgeItem("OTHER", "기타 항목(잔여: 자본변동·기타 자산부채 등)", b.other))

    tied = sum(max(0.0, x or 0.0) for x in (d["AR"], d["CONTRACT_ASSET"], d["INV"]))
    released = sum(-min(0.0, x or 0.0) for x in (d["AR"], d["CONTRACT_ASSET"], d["INV"]))
    b.wc_tied = tied
    b.narrative = _narrative(d, d_borrow, b.cash_change, tied, released, revenue_growth)
    return b


def _narrative(d, d_borrow, cash_change, tied, released, revenue_growth) -> list[str]:
    s: list[str] = []
    parts = [n for n, k in (("매출채권", "AR"), ("계약자산(미청구공사)", "CONTRACT_ASSET"), ("재고", "INV"))
             if (d[k] or 0) > 0]
    subject = "과 ".join(parts) if len(parts) <= 2 else ", ".join(parts[:-1]) + "와 " + parts[-1]
    if tied > 0:
        if revenue_growth is not None and revenue_growth > 0:
            s.append(f"매출은 {revenue_growth:.1f}% 성장했지만 {subject}{'가' if subject.endswith('고') else '이'} "
                     f"증가하면서 {approx(tied)}의 현금이 운전자본에 추가로 묶였습니다.")
        else:
            s.append(f"{subject} 증가로 {approx(tied)}의 현금이 운전자본에 추가로 묶였습니다.")
    elif released > 0:
        s.append(f"매출채권·재고가 줄어 운전자본에서 {approx(released)}의 현금이 회수되었습니다.")
    ap = d["AP"] or 0
    if ap > 0 and tied > 0:
        s.append(f"매입채무가 {approx(ap)} 늘어 그 중 일부는 거래처 신용으로 충당되었습니다.")
    elif ap < 0:
        s.append(f"매입채무는 오히려 {approx(-ap)} 줄어 현금 부담이 커졌습니다.")
    net_wc_need = tied - max(ap, 0)
    if (d["PPE"] or 0) > 0:
        s.append(f"유형자산도 장부가 기준 {approx(d['PPE'])} 늘어 설비투자 자금이 필요했습니다.")
    if d_borrow is not None and d_borrow > 0:
        if net_wc_need > 0 or (d["PPE"] or 0) > 0:
            s.append(f"같은 기간 차입금이 {approx(d_borrow)} 증가했습니다. 운전자본·투자 자금 부족분을 차입으로 메운 구조인지 점검이 필요합니다.")
        else:
            s.append(f"차입금은 {approx(d_borrow)} 증가했습니다.")
    elif d_borrow is not None and d_borrow < 0:
        s.append(f"차입금은 {approx(-d_borrow)} 상환되었습니다.")
    if cash_change is not None:
        word = "증가" if cash_change > 0 else ("감소" if cash_change < 0 else "변동 없음")
        s.append(f"그 결과 현금은 {approx(abs(cash_change))} {word}했습니다." if cash_change else "그 결과 현금 잔액은 변동이 없습니다.")
    return s
