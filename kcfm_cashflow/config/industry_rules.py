"""업종별 설정.

[MVP 원칙] 업종별 '적정 기준치'나 점수는 근거 데이터 없이 임의로 만들지 않는다.
여기에는 업종별로 '무엇을 더 주의해서 볼지(진단 포인트)'와 해석 메모만 둔다.
추후 업종 평균 데이터(예: 한국은행 기업경영분석)를 확보하면 BENCHMARKS에 추가한다.
"""
from __future__ import annotations

INDUSTRIES = ["제조업", "도소매업", "건설업", "서비스업", "기타"]

INDUSTRY_PROFILES: dict[str, dict] = {
    "제조업": {
        "focus_points": [
            "원재료·재공품·제품 중 어느 단계에서 재고가 늘었는지 확인하세요.",
            "매출원가에 노무비·경비가 포함되어 있어, 매출원가를 대용한 DPO는 실제보다 짧게 나올 수 있습니다.",
            "설비투자(유형자산 증가)가 차입금으로 조달되었는지 함께 보세요.",
        ],
        "dio_meaningful": True,
    },
    "도소매업": {
        "focus_points": [
            "재고회전(DIO)과 매입처 결제조건(DPO)이 현금흐름의 핵심입니다.",
            "상품매입액이 손익계산서에 표시되어 있으면 DPO 정확도가 높아집니다.",
        ],
        "dio_meaningful": True,
    },
    "건설업": {
        "focus_points": [
            "공사미수금뿐 아니라 미청구공사(계약자산) 증가도 현금이 묶이는 주요 원인입니다.",
            "초과청구공사·공사선수금(계약부채) 감소는 선수령 현금이 줄어든 신호일 수 있습니다.",
            "현장별 공사 진행률·기성 청구 일정은 재무제표만으로 확인할 수 없어 별도 확인이 필요합니다.",
        ],
        "dio_meaningful": True,
    },
    "서비스업": {
        "focus_points": [
            "재고가 거의 없는 업종은 DIO의 의미가 작습니다. DSO(매출채권 회수기간)에 집중하세요.",
            "매출원가 대신 '영업비용'으로 표시된 경우 DIO·DPO 계산 기준을 확인하세요.",
        ],
        "dio_meaningful": False,
    },
    "기타": {
        "focus_points": ["업종 특성에 맞는 계정 분류를 검증 화면에서 확인하세요."],
        "dio_meaningful": True,
    },
}

# 업종별 기준치 (MVP에서는 비어 있음 — 임의 기준 금지)
# 예시 구조: {"제조업": {"DSO": {"median": 60, "source": "한국은행 기업경영분석 2025"}}}
BENCHMARKS: dict[str, dict] = {}


def profile(industry: str) -> dict:
    return INDUSTRY_PROFILES.get(industry, INDUSTRY_PROFILES["기타"])
