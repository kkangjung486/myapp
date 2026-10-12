"""확인된 추출표 → 연도별 표준 재무데이터.

규칙
- '분석 포함'이 체크된 행만 사용한다.
- 합산형 계정(재고자산 등)은 합산, 합계형 계정(자산총계 등)은 단일 값.
  합계형 계정에 서로 다른 값이 2개 이상 있으면 '중복 추출' 경고를 남기고 첫 번째 값을 쓴다.
- 값이 없는 계정은 0이 아니라 None(확인 필요)으로 둔다.
  단, 재무상태표가 있는데 매출채권·재고 같은 계정 행이 아예 없으면 0으로 간주하고 그 사실을 기록한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config.accounts import (
    BY_CODE,
    CURRENT_ASSET_CODES,
    CURRENT_LIAB_CODES,
    ZERO_IF_ABSENT_CODES,
    code_of,
)


@dataclass
class StandardYear:
    year: int
    values: dict[str, float | None] = field(default_factory=dict)
    notes: dict[str, list[str]] = field(default_factory=dict)
    statements: set[str] = field(default_factory=set)
    unit_multiplier: int = 1

    def get(self, code: str) -> float | None:
        return self.values.get(code)

    def note(self, code: str, text: str) -> None:
        self.notes.setdefault(code, []).append(text)


def aggregate(df: pd.DataFrame) -> dict[int, StandardYear]:
    out: dict[int, StandardYear] = {}
    if df.empty:
        return out
    df = df[df["year"].notna()].copy()
    df["code"] = df["std_label"].map(code_of)
    for year, g in df.groupby("year"):
        sy = StandardYear(int(year))
        sy.statements = set(g["statement"])
        units = g["unit"].dropna().map({"원": 1, "천원": 1_000, "백만원": 1_000_000, "억원": 100_000_000})
        sy.unit_multiplier = int(units.max()) if len(units) else 1
        used = g[g["include"].astype(bool) & g["confirmed_won"].notna()]
        for code, rows in used.groupby("code", sort=False):
            acc = BY_CODE.get(code)
            if acc is None or acc.kind == "excluded":
                continue
            vals = [float(v) for v in rows["confirmed_won"]]
            if acc.kind == "total":
                distinct = sorted(set(round(v) for v in vals))
                if len(distinct) > 1:
                    sy.note(code, f"동일 계정 중복 추출(서로 다른 값 {len(distinct)}개) – 첫 번째 값 사용, 확인 필요")
                sy.values[code] = vals[0]
            else:
                sy.values[code] = sum(vals)
        _fallbacks(sy)
        out[int(year)] = sy
    return out


def _fallbacks(sy: StandardYear) -> None:
    v = sy.values
    if v.get("REVENUE") is None and v.get("REVENUE_ITEM") is not None:
        v["REVENUE"] = v["REVENUE_ITEM"]
        sy.note("REVENUE", "매출액 합계 행이 없어 매출 구성항목 합계로 계산")
    if v.get("COGS") is None and v.get("COGS_ITEM") is not None:
        v["COGS"] = v["COGS_ITEM"]
        sy.note("COGS", "매출원가 합계 행이 없어 매출원가 구성항목 합계로 계산")
    if "BS" in sy.statements:
        for code in ZERO_IF_ABSENT_CODES:
            if v.get(code) is None:
                v[code] = 0.0
                sy.note(code, "재무상태표에 해당 계정이 없어 0으로 간주")
        if v.get("CA_TOTAL") is None:
            v["CA_TOTAL"] = sum(v.get(c) or 0 for c in CURRENT_ASSET_CODES)
            sy.note("CA_TOTAL", "유동자산 합계 행이 없어 구성항목 합계로 계산 (확인 필요)")
        if v.get("CL_TOTAL") is None:
            v["CL_TOTAL"] = sum(v.get(c) or 0 for c in CURRENT_LIAB_CODES)
            sy.note("CL_TOTAL", "유동부채 합계 행이 없어 구성항목 합계로 계산 (확인 필요)")
        if v.get("TOTAL_LIAB") is None and v.get("CL_TOTAL") is not None and v.get("NCL_TOTAL") is not None:
            v["TOTAL_LIAB"] = v["CL_TOTAL"] + v["NCL_TOTAL"]
            sy.note("TOTAL_LIAB", "부채총계 행이 없어 유동+비유동부채로 계산")


def to_values(data: dict[int, StandardYear]) -> dict[int, dict[str, float | None]]:
    """계산 모듈 입력 형식(연도 → {표준코드: 금액})으로 변환."""
    return {y: dict(sy.values) for y, sy in data.items()}
