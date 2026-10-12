"""금액 표기 (억/만원). 계산 결과 문장과 화면 표시에 공통으로 쓴다."""
from __future__ import annotations

import math


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def won(v: float | None) -> str:
    """원 단위 전체 표기: 1,234,567,890원"""
    if _is_missing(v):
        return "확인 필요"
    return f"{v:,.0f}원"


def eok_man(v: float | None, signed: bool = False) -> str:
    """억/만원 표기: 1,234,567,890 → '12억 3,457만원', 50,000,000 → '5,000만원'."""
    if _is_missing(v):
        return "확인 필요"
    sign = "-" if v < 0 else ("+" if signed and v > 0 else "")
    a = abs(v)
    if a < 10_000:
        return f"{sign}{a:,.0f}원"
    man_total = int(round(a / 10_000))
    eok, man = divmod(man_total, 10_000)
    if eok and man:
        return f"{sign}{eok:,}억 {man:,}만원"
    if eok:
        return f"{sign}{eok:,}억원"
    return f"{sign}{man:,}만원"


def eok_short(v: float | None, digits: int = 1) -> str:
    """큰 숫자 카드용: 1,234,567,890 → '12.3억원', 45,000,000 → '4,500만원'."""
    if _is_missing(v):
        return "확인 필요"
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 100_000_000:
        return f"{sign}{a / 100_000_000:,.{digits}f}억원"
    return eok_man(v)


def approx(v: float | None) -> str:
    """문장용 근사 표기: 130,000,000 → '약 1억 3,000만 원'."""
    if _is_missing(v):
        return "확인 필요"
    a = abs(v)
    if a >= 100_000_000:
        man_total = int(round(a / 1_000_000)) * 100  # 백만원 단위 반올림
        eok, man = divmod(man_total, 10_000)
        return f"약 {eok:,}억 {man:,}만 원" if man else f"약 {eok:,}억 원"
    if a >= 10_000:
        return f"약 {int(round(a / 10_000)):,}만 원"
    return f"약 {a:,.0f}원"


def days(v: float | None) -> str:
    return "확인 필요" if _is_missing(v) else f"{v:,.1f}일"


def pct(v: float | None, digits: int = 1) -> str:
    return "확인 필요" if _is_missing(v) else f"{v:,.{digits}f}%"


def times(v: float | None) -> str:
    return "확인 필요" if _is_missing(v) else f"{v:,.2f}배"
