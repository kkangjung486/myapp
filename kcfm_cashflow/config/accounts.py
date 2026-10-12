"""표준 계정 정의.

앱 전체에서 사용하는 '표준 계정'의 코드와 한글 이름을 한 곳에 모아 둔다.
- code  : 프로그램 내부에서 쓰는 영문 코드 (계산 모듈은 이 코드만 사용)
- label : 화면/엑셀에 표시되는 한글 이름 (검증 화면의 '표준 계정' 선택지)
- statement : BS(재무상태표) / IS(손익계산서) / COGS(원가명세서) / CF(현금흐름표) / ANY
- kind :
    "sum"      같은 표준계정으로 매핑된 여러 행을 합산 (예: 상품+제품+원재료 = 재고자산)
    "total"    합계 성격의 단일 값 (예: 자산총계, 매출액). 여러 행이 있으면 중복 경고
    "info"     참고용. 분석 계산에 직접 사용하지 않음
    "excluded" 분석에서 제외 (소계, 미분류, 제외)
- expense : 비용 항목 여부. 괄호(음수)로 표기된 비용은 양수로 정규화하고 '확인 필요' 표시
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StdAccount:
    code: str
    label: str
    statement: str
    kind: str
    expense: bool = False


STANDARD_ACCOUNTS: list[StdAccount] = [
    # ── 재무상태표: 유동자산 ─────────────────────────────
    StdAccount("CASH", "현금및현금성자산", "BS", "sum"),
    StdAccount("ST_FIN", "단기금융상품", "BS", "sum"),
    StdAccount("AR", "매출채권", "BS", "sum"),
    StdAccount("CONTRACT_ASSET", "계약자산(미청구공사)", "BS", "sum"),
    StdAccount("INV", "재고자산", "BS", "sum"),
    StdAccount("OTHER_OP_CA", "기타영업유동자산", "BS", "sum"),
    StdAccount("OTHER_CA", "기타유동자산(비영업)", "BS", "sum"),
    StdAccount("CA_TOTAL", "유동자산합계", "BS", "total"),
    # ── 재무상태표: 비유동자산 ───────────────────────────
    StdAccount("PPE", "유형자산", "BS", "sum"),
    StdAccount("INTANGIBLE", "무형자산", "BS", "sum"),
    StdAccount("OTHER_NCA", "기타비유동자산", "BS", "sum"),
    StdAccount("NCA_TOTAL", "비유동자산합계", "BS", "total"),
    StdAccount("TOTAL_ASSETS", "자산총계", "BS", "total"),
    # ── 재무상태표: 유동부채 ─────────────────────────────
    StdAccount("AP", "매입채무", "BS", "sum"),
    StdAccount("CONTRACT_LIAB", "계약부채(초과청구공사·공사선수금)", "BS", "sum"),
    StdAccount("OTHER_OP_CL", "기타영업유동부채", "BS", "sum"),
    StdAccount("ST_BORROW", "단기차입금", "BS", "sum"),
    StdAccount("CURRENT_LTD", "유동성장기부채", "BS", "sum"),
    StdAccount("OTHER_CL", "기타유동부채(비영업)", "BS", "sum"),
    StdAccount("CL_TOTAL", "유동부채합계", "BS", "total"),
    # ── 재무상태표: 비유동부채 / 자본 ─────────────────────
    StdAccount("LT_BORROW", "장기차입금", "BS", "sum"),
    StdAccount("BONDS", "사채", "BS", "sum"),
    StdAccount("LEASE_LIAB", "리스부채", "BS", "sum"),
    StdAccount("RETIREMENT", "퇴직급여충당부채(순액)", "BS", "sum"),
    StdAccount("OTHER_NCL", "기타비유동부채", "BS", "sum"),
    StdAccount("NCL_TOTAL", "비유동부채합계", "BS", "total"),
    StdAccount("TOTAL_LIAB", "부채총계", "BS", "total"),
    StdAccount("EQUITY_ITEM", "자본 구성항목", "BS", "info"),
    StdAccount("TOTAL_EQUITY", "자본총계", "BS", "total"),
    StdAccount("LIAB_EQUITY_TOTAL", "부채와자본총계", "BS", "total"),
    # ── 손익계산서 ───────────────────────────────────────
    StdAccount("REVENUE", "매출액", "IS", "total"),
    StdAccount("REVENUE_ITEM", "매출액 구성항목", "IS", "info"),
    StdAccount("COGS", "매출원가", "IS", "total", expense=True),
    StdAccount("COGS_ITEM", "매출원가 구성항목", "IS", "info", expense=True),
    StdAccount("GROSS_PROFIT", "매출총이익", "IS", "total"),
    StdAccount("SGA", "판매비와관리비", "IS", "total", expense=True),
    StdAccount("OP_INCOME", "영업이익", "IS", "total"),
    StdAccount("DEPRECIATION", "감가상각비", "ANY", "sum", expense=True),
    StdAccount("AMORTIZATION", "무형자산상각비", "ANY", "sum", expense=True),
    StdAccount("INTEREST_EXPENSE", "이자비용", "IS", "sum", expense=True),
    StdAccount("PRETAX_INCOME", "법인세비용차감전순이익", "IS", "total"),
    StdAccount("INCOME_TAX", "법인세비용", "IS", "total"),
    StdAccount("NET_INCOME", "당기순이익", "IS", "total"),
    # ── 매입액 (손익계산서 매출원가 내역 / 제조원가명세서) ──
    StdAccount("PURCHASE_MERCH", "당기상품매입액", "ANY", "sum", expense=True),
    StdAccount("PURCHASE_RAW", "당기원재료매입액", "ANY", "sum", expense=True),
    StdAccount("COST_INFO", "원가명세 참고항목", "ANY", "info"),
    # ── 현금흐름표 ───────────────────────────────────────
    StdAccount("CFO", "영업활동현금흐름(공시)", "CF", "total"),
    StdAccount("CFI", "투자활동현금흐름(공시)", "CF", "total"),
    StdAccount("CFF", "재무활동현금흐름(공시)", "CF", "total"),
    StdAccount("CF_NET_CHANGE", "현금의증감(공시)", "CF", "total"),
    StdAccount("CF_BEGIN_CASH", "기초현금(공시)", "CF", "total"),
    StdAccount("CF_END_CASH", "기말현금(공시)", "CF", "total"),
    StdAccount("CF_ITEM", "현금흐름표 세부항목", "CF", "info"),
    # ── 공통 ─────────────────────────────────────────────
    StdAccount("SUBTOTAL", "소계(중복 방지 제외)", "ANY", "excluded"),
    StdAccount("OTHER_INFO", "기타(분석 미사용)", "ANY", "info"),
    StdAccount("UNMAPPED", "미분류(확인 필요)", "ANY", "excluded"),
    StdAccount("EXCLUDED", "제외", "ANY", "excluded"),
]

BY_CODE: dict[str, StdAccount] = {a.code: a for a in STANDARD_ACCOUNTS}
BY_LABEL: dict[str, StdAccount] = {a.label: a for a in STANDARD_ACCOUNTS}

LABEL_OPTIONS: list[str] = [a.label for a in STANDARD_ACCOUNTS]


def label_of(code: str) -> str:
    return BY_CODE[code].label


def code_of(label: str) -> str:
    """화면 라벨 → 코드. 알 수 없는 라벨은 미분류로 처리한다."""
    acc = BY_LABEL.get(label)
    return acc.code if acc else "UNMAPPED"


# 계산에서 사용하는 계정 그룹 ------------------------------------------------

# 유동자산 구성항목 (유동자산합계와 대사 검증에 사용)
CURRENT_ASSET_CODES = ["CASH", "ST_FIN", "AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA", "OTHER_CA"]
# 유동부채 구성항목
CURRENT_LIAB_CODES = ["AP", "CONTRACT_LIAB", "OTHER_OP_CL", "ST_BORROW", "CURRENT_LTD", "OTHER_CL"]

# 총차입금 구성.
# [회계판단] 리스부채는 차입금 성격이 있으나 기업마다 처리 관행이 달라 기본 제외한다.
#           포함하려면 아래 목록에 "LEASE_LIAB"를 추가한다.
BORROWING_CODES = ["ST_BORROW", "CURRENT_LTD", "LT_BORROW", "BONDS"]

# 영업운전자본(OWC) 구성
OWC_ASSET_CODES = ["AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA"]
OWC_LIAB_CODES = ["AP", "CONTRACT_LIAB", "OTHER_OP_CL"]

# 재무상태표가 추출되었는데 해당 계정 행이 하나도 없으면 0으로 간주하는 계정
# (예: 서비스업의 재고자산). 화면에는 '계정 없음 → 0 간주'로 표시한다.
ZERO_IF_ABSENT_CODES = [
    "AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA", "AP", "CONTRACT_LIAB", "OTHER_OP_CL",
    "ST_BORROW", "CURRENT_LTD", "LT_BORROW", "BONDS", "RETIREMENT", "PPE", "ST_FIN",
]
