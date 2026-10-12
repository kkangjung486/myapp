"""공통 계산 도우미. 값이 없으면(None) 결과도 None — 절대 0으로 대체하지 않는다."""
from __future__ import annotations

Num = float | None

AVG_METHOD = "평균잔액((전기말+당기말)÷2)"
END_METHOD = "평균잔액 자료 부족으로 기말잔액 사용"


def get(values: dict | None, code: str) -> Num:
    if values is None:
        return None
    v = values.get(code)
    return None if v is None else float(v)


def delta(curr: Num, prev: Num) -> Num:
    """당기말 - 전기말"""
    if curr is None or prev is None:
        return None
    return curr - prev


def ratio(a: Num, b: Num) -> Num:
    if a is None or b is None or b == 0:
        return None
    return a / b


def growth_pct(curr: Num, prev: Num) -> Num:
    """증가율(%) = (당기 - 전기) ÷ |전기| × 100"""
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / abs(prev) * 100


def average_balance(prev: Num, curr: Num) -> tuple[Num, str]:
    """평균잔액 = (전기말 + 당기말) ÷ 2. 전기말이 없으면 기말잔액을 쓰고 그 사실을 반환한다."""
    if curr is None:
        return None, "자료 없음"
    if prev is None:
        return curr, END_METHOD
    return (prev + curr) / 2, AVG_METHOD


def sum_codes(values: dict | None, codes: list[str]) -> Num:
    """여러 계정 합계. 하나라도 None이면 None."""
    total = 0.0
    for c in codes:
        v = get(values, c)
        if v is None:
            return None
        total += v
    return total
