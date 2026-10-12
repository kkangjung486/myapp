"""데이터 정확성 검증.

결과 상태: 통과 / 정보 / 경고 / 실패 / 확인불가
'실패'가 하나라도 있으면 결과 화면 상단에 '숫자를 확정적으로 사용하지 말 것' 경고를 띄운다.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from account_mapper.mapper import is_contra_name
from config.accounts import BY_CODE, CURRENT_ASSET_CODES, CURRENT_LIAB_CODES, code_of, label_of

from .common import get
from .formatting import won

PASS, INFO, WARN, FAIL, NA = "통과", "정보", "경고", "실패", "확인불가"


@dataclass
class Check:
    year: int | None
    category: str
    item: str
    status: str
    detail: str


def _tol(mult: int) -> float:
    """반올림 오차 허용: 표시단위 3단위 (천원 표시면 3,000원)"""
    return 3 * max(mult, 1)


def _compare(year, cat, item, left, right, tol, left_name, right_name, fail_status=FAIL) -> Check:
    if left is None or right is None:
        return Check(year, cat, item, NA, f"{left_name} 또는 {right_name} 값이 없어 검증할 수 없습니다.")
    diff = left - right
    if abs(diff) <= tol:
        return Check(year, cat, item, PASS, f"{left_name} {won(left)} = {right_name} {won(right)}")
    return Check(year, cat, item, fail_status,
                 f"{left_name} {won(left)} ≠ {right_name} {won(right)} (차이 {won(diff)})")


def run_checks(std: dict, selected: pd.DataFrame, analysis_years: list[int], block_metas: list) -> list[Check]:
    """std: {연도: StandardYear}. selected: 확인 화면의 최종 행. block_metas: 파일·표별 인식 정보."""
    checks: list[Check] = []

    # 연도 순서
    ys = sorted(analysis_years)
    if len(ys) < 2:
        checks.append(Check(None, "연도", "분석 연도 수", WARN, f"분석 연도가 {len(ys)}개입니다. 추이 분석에는 3개년이 필요합니다."))
    elif any(b - a != 1 for a, b in zip(ys, ys[1:])):
        checks.append(Check(None, "연도", "연도 연속성", WARN, f"분석 연도가 연속되지 않습니다: {ys}"))
    else:
        checks.append(Check(None, "연도", "연도 순서·연속성", PASS, f"{ys[0]}~{ys[-1]} 연속"))

    # 단위
    for m in block_metas:
        if m.unit_source == "미확인":
            checks.append(Check(None, "단위", f"{m.file} / {m.statement}", WARN,
                                "단위 표기를 찾지 못해 '원'으로 가정했습니다. 원본을 보고 단위를 확인하세요."))
    units = {m.file: set() for m in block_metas}
    for m in block_metas:
        units[m.file].add(m.unit)
    for f, us in units.items():
        if len(us) > 1:
            checks.append(Check(None, "단위", f, INFO, f"한 파일 안에 서로 다른 단위가 있습니다: {sorted(us)} (표별로 각각 환산함)"))

    for y in ys:
        sy = std.get(y)
        if sy is None:
            checks.append(Check(y, "자료", "재무제표", FAIL, "해당 연도 자료가 없습니다."))
            continue
        v, tol = sy.values, _tol(sy.unit_multiplier)
        # 재무상태표
        if "BS" not in sy.statements:
            checks.append(Check(y, "재무상태표", "자료 존재", FAIL, "재무상태표가 없습니다."))
        else:
            liab, eq = get(v, "TOTAL_LIAB"), get(v, "TOTAL_EQUITY")
            checks.append(_compare(y, "재무상태표", "자산총계 = 부채총계 + 자본총계", get(v, "TOTAL_ASSETS"),
                                   None if liab is None or eq is None else liab + eq, tol, "자산총계", "부채+자본"))
            if get(v, "LIAB_EQUITY_TOTAL") is not None:
                checks.append(_compare(y, "재무상태표", "자산총계 = 부채와자본총계", get(v, "TOTAL_ASSETS"),
                                       get(v, "LIAB_EQUITY_TOTAL"), tol, "자산총계", "부채와자본총계"))
            if get(v, "NCA_TOTAL") is not None:
                checks.append(_compare(y, "재무상태표", "유동자산 + 비유동자산 = 자산총계",
                                       (get(v, "CA_TOTAL") or 0) + get(v, "NCA_TOTAL"), get(v, "TOTAL_ASSETS"),
                                       tol, "유동+비유동자산", "자산총계"))
            ca_sum = sum(get(v, c) or 0 for c in CURRENT_ASSET_CODES)
            checks.append(_compare(y, "재무상태표", "유동자산 구성항목 합계 = 유동자산합계", ca_sum, get(v, "CA_TOTAL"),
                                   tol, "분류된 유동자산 합계", "유동자산합계", fail_status=WARN))
            if checks[-1].status == WARN:
                checks[-1].detail += " – 미분류·제외된 계정이나 누락·중복 추출이 있는지 확인하세요."
            cl_sum = sum(get(v, c) or 0 for c in CURRENT_LIAB_CODES)
            checks.append(_compare(y, "재무상태표", "유동부채 구성항목 합계 = 유동부채합계", cl_sum, get(v, "CL_TOTAL"),
                                   tol, "분류된 유동부채 합계", "유동부채합계", fail_status=WARN))
            if checks[-1].status == WARN:
                checks[-1].detail += " – 미분류·제외된 계정이나 누락·중복 추출이 있는지 확인하세요."
        # 손익계산서
        if "IS" not in sy.statements:
            checks.append(Check(y, "손익계산서", "자료 존재", FAIL, "손익계산서가 없습니다."))
        else:
            rev, cogs, gp = get(v, "REVENUE"), get(v, "COGS"), get(v, "GROSS_PROFIT")
            if gp is not None:
                checks.append(_compare(y, "손익계산서", "매출액 - 매출원가 = 매출총이익",
                                       None if rev is None or cogs is None else rev - cogs, gp, tol,
                                       "매출액-매출원가", "매출총이익"))
            sga, op = get(v, "SGA"), get(v, "OP_INCOME")
            if gp is not None and sga is not None:
                checks.append(_compare(y, "손익계산서", "매출총이익 - 판매비와관리비 = 영업이익", gp - sga, op, tol,
                                       "매출총이익-판관비", "영업이익"))
            pre, tax, ni = get(v, "PRETAX_INCOME"), get(v, "INCOME_TAX"), get(v, "NET_INCOME")
            if pre is not None and tax is not None:
                checks.append(_compare(y, "손익계산서", "법인세차감전순이익 - 법인세비용 = 당기순이익", pre - tax, ni, tol,
                                       "세전이익-법인세", "당기순이익"))
            if rev is None:
                checks.append(Check(y, "손익계산서", "매출액", FAIL, "매출액을 찾지 못했습니다."))
            elif rev < 10_000_000 or rev > 500_000_000_000:
                checks.append(Check(y, "단위", "매출액 규모", WARN,
                                    f"매출액이 {won(rev)}입니다. 대상 기업 규모(5억~100억)와 크게 달라 단위 오류일 수 있습니다."))
            if ni is None:
                checks.append(Check(y, "손익계산서", "당기순이익", FAIL, "당기순이익을 찾지 못했습니다."))
        # 현금흐름표
        if "CF" in sy.statements:
            b, n, e = get(v, "CF_BEGIN_CASH"), get(v, "CF_NET_CHANGE"), get(v, "CF_END_CASH")
            if b is not None and n is not None:
                checks.append(_compare(y, "현금흐름표", "기초현금 + 현금증감 = 기말현금", b + n, e, tol, "기초+증감", "기말현금"))
            o, i, f = get(v, "CFO"), get(v, "CFI"), get(v, "CFF")
            if None not in (o, i, f, n):
                checks.append(_compare(y, "현금흐름표", "영업+투자+재무 = 현금증감", o + i + f, n, tol * 3,
                                       "활동별 합계", "현금증감", fail_status=WARN))
            if e is not None and get(v, "CASH") is not None:
                checks.append(_compare(y, "현금흐름표", "기말현금 = 재무상태표 현금", e, get(v, "CASH"), tol,
                                       "현금흐름표 기말현금", "재무상태표 현금", fail_status=WARN))
        # 기타 주석
        for code, notes in sy.notes.items():
            for n in notes:
                if "중복" in n:
                    checks.append(Check(y, "중복", label_of(code), WARN, n))

    # 행 단위 검증 (중복 추출, 미분류, 확인 필요, 사용자 수정)
    if not selected.empty:
        sel = selected[selected["year"].isin(ys)].copy()
        sel["code"] = sel["std_label"].map(code_of)
        key_rows = sel[sel["include"].astype(bool) & sel["code"].map(lambda c: BY_CODE[c].kind in ("sum", "total"))]
        # 차감계정(감가상각누계액 등)은 여러 자산 아래 반복되는 것이 정상이므로 제외
        key_rows = key_rows[(key_rows["norm"] != "") & ~key_rows["norm"].map(is_contra_name)]
        dup = key_rows.groupby(["year", "statement", "norm", "std_label"]).size()
        for (y, st, nm, lab), cnt in dup[dup > 1].items():
            checks.append(Check(int(y), "중복", f"{nm} → {lab}", WARN, f"같은 계정명이 {cnt}번 추출되어 모두 합산됩니다. 중복인지 확인하세요."))
        for y, g in sel.groupby("year"):
            unm = g[g["code"] == "UNMAPPED"]
            if len(unm):
                names = ", ".join(unm["label"].astype(str).head(8))
                checks.append(Check(int(y), "분류", "미분류 계정", WARN,
                                    f"{len(unm)}개 계정이 미분류 상태로 분석에서 빠져 있습니다: {names}"))
            edited = g[g["status"].isin(["수정됨", "수동 추가"])]
            if len(edited):
                checks.append(Check(int(y), "수정", "사용자 수정", INFO, f"사용자가 수정·추가한 행 {len(edited)}개 (원본 추출값은 별도 보관)"))
            missing_amount = g[g["include"].astype(bool) & g["confirmed_won"].isna() & (g["code"] != "UNMAPPED")]
            if len(missing_amount):
                checks.append(Check(int(y), "자료", "금액 없음", WARN, f"금액이 비어 있는 행 {len(missing_amount)}개"))
    return checks


def has_failure(checks: list[Check]) -> bool:
    return any(c.status == FAIL for c in checks)


def checks_frame(checks: list[Check]) -> pd.DataFrame:
    return pd.DataFrame([{"연도": str(c.year) if c.year else "전체", "구분": c.category, "검증 항목": c.item,
                          "결과": c.status, "내용": c.detail} for c in checks])
