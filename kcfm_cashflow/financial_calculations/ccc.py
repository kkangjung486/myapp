"""현금전환주기(CCC).

DSO = 평균 매출채권 ÷ 매출액 × 365        (매출채권 회수기간)
DIO = 평균 재고자산 ÷ 매출원가 × 365      (재고 보유기간)
DPO = 평균 매입채무 ÷ 연간 매입액 × 365    (매입채무 지급기간)
CCC = DSO + DIO - DPO

평균잔액 = (전기말 + 당기말) ÷ 2. 전기말 자료가 없으면 기말잔액을 쓰고 '평균잔액 자료 부족으로 기말잔액 사용' 표시.

DPO 분모(매입액) 우선순위
  1) 손익계산서 '당기상품매입액' + 제조원가명세서 '당기원재료매입액'  → 실제 매입액
  2) 매입액이 없으면 매출원가로 대용 → 'DPO는 매입액 자료 부족으로 매출원가를 대용하여 추정'
  참고) 추정매입액 = 매출원가 + 기말재고 - 기초재고 (제조업은 노무비·경비 포함으로 과대 가능 → 참고치로만 표시)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .common import Num, average_balance, get

DAYS = 365
DPO_COGS_PROXY_MSG = "DPO는 매입액 자료 부족으로 매출원가를 대용하여 추정"


@dataclass
class CCCResult:
    dso: Num = None
    dio: Num = None
    dpo: Num = None
    ccc: Num = None
    avg_ar: Num = None
    avg_inv: Num = None
    avg_ap: Num = None
    ar_method: str = ""
    inv_method: str = ""
    ap_method: str = ""
    purchases: Num = None
    purchases_basis: str = ""
    dpo_ref: Num = None             # 재고증감 반영 추정매입액 기준 참고 DPO
    dpo_ref_purchases: Num = None
    dso_with_contract: Num = None   # 계약자산(미청구공사) 포함 참고 DSO
    notes: list[str] = field(default_factory=list)


def _days(balance: Num, flow: Num) -> Num:
    if balance is None or flow is None or flow <= 0:
        return None
    return balance / flow * DAYS


def compute_ccc(curr: dict, prev: dict | None) -> CCCResult:
    r = CCCResult()
    revenue, cogs = get(curr, "REVENUE"), get(curr, "COGS")

    # DSO
    r.avg_ar, r.ar_method = average_balance(get(prev, "AR"), get(curr, "AR"))
    r.dso = _days(r.avg_ar, revenue)
    if revenue is None or revenue <= 0:
        r.notes.append("매출액이 없거나 0 이하라 DSO를 계산할 수 없습니다.")
    ca_c, ca_p = get(curr, "CONTRACT_ASSET"), get(prev, "CONTRACT_ASSET")
    if ca_c:
        avg_ca, _ = average_balance(ca_p, ca_c)
        if r.avg_ar is not None and avg_ca is not None:
            r.dso_with_contract = _days(r.avg_ar + avg_ca, revenue)

    # DIO
    r.avg_inv, r.inv_method = average_balance(get(prev, "INV"), get(curr, "INV"))
    if cogs is None or cogs <= 0:
        if r.avg_inv == 0:
            r.dio = 0.0
            r.notes.append("재고자산이 없어 DIO를 0일로 봅니다.")
        else:
            r.notes.append("매출원가를 확인할 수 없어 DIO를 계산할 수 없습니다.")
    else:
        r.dio = _days(r.avg_inv, cogs)

    # DPO
    r.avg_ap, r.ap_method = average_balance(get(prev, "AP"), get(curr, "AP"))
    pm, pr = get(curr, "PURCHASE_MERCH"), get(curr, "PURCHASE_RAW")
    if (pm or 0) + (pr or 0) > 0:
        r.purchases = (pm or 0) + (pr or 0)
        parts = [n for n, v in (("당기상품매입액", pm), ("당기원재료매입액", pr)) if v]
        r.purchases_basis = "매입액(" + "+".join(parts) + ")"
        r.notes.append("DPO 분모: 실제 매입액 사용. 외주가공비 등 기타 매입은 포함되지 않았습니다.")
    elif cogs is not None and cogs > 0:
        r.purchases = cogs
        r.purchases_basis = "매출원가 대용"
        r.notes.append(DPO_COGS_PROXY_MSG)
    else:
        r.notes.append("매입액·매출원가 모두 없어 DPO를 계산할 수 없습니다.")
    r.dpo = _days(r.avg_ap, r.purchases)

    inv_c, inv_p = get(curr, "INV"), get(prev, "INV")
    if cogs and inv_c is not None and inv_p is not None:
        r.dpo_ref_purchases = cogs + inv_c - inv_p
        r.dpo_ref = _days(r.avg_ap, r.dpo_ref_purchases)

    if r.dso is not None and r.dio is not None and r.dpo is not None:
        r.ccc = r.dso + r.dio - r.dpo
    else:
        r.notes.append("DSO·DIO·DPO 중 계산할 수 없는 항목이 있어 CCC를 산출하지 않았습니다.")
    return r
