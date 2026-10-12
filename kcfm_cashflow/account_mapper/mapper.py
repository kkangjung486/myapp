"""계정과목 → 표준계정 매핑 (규칙 기반).

매핑은 '제안'일 뿐이며, 최종 분류는 검증 화면에서 사용자가 확인·수정한다.
애매한 계정은 자동 분류하지 않고 '미분류(확인 필요)'로 둔다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from config.accounts import BY_CODE
from config.mapping_rules import (
    AMBIGUOUS_RULES,
    CONTAINS_RULES,
    CONTRA_RULES,
    EXACT_RULES,
    GROUP_HEADER_NAMES,
    INDUSTRY_SUGGESTION_OVERRIDES,
    LOSS_SIGN_CODES,
    NONCURRENT_SECTION_REMAP,
    SECTION_HEADERS,
)

_PREFIX_RE = re.compile(
    r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+\s*[\.\)]?|[IVX]{1,4}\s*\.|\d{1,2}\s*[\.\)]|\(\s*\d{1,2}\s*\)"
    r"|\(\s*[가-하]\s*\)|[가-하]\s*[\.\)]|[①-⑳])\s*"
)
_PAREN_RE = re.compile(r"[\(（][^\)）]*[\)）]")
_TOTAL_SUFFIX_RE = re.compile(r"(합계|소계|총계|총액)$")

BS_ASSET_CODES = {"CASH", "ST_FIN", "AR", "CONTRACT_ASSET", "INV", "OTHER_OP_CA", "OTHER_CA",
                  "PPE", "INTANGIBLE", "OTHER_NCA"}
SECTION_DEFAULT_SUGGESTION = {"CA": "OTHER_CA", "NCA": "OTHER_NCA", "CL": "OTHER_CL", "NCL": "OTHER_NCL"}


def normalize_name(label: str) -> str:
    """'Ⅴ. 영업이익(손실)' → '영업이익',  '(1) 당좌자산' → '당좌자산',  '자 산 총 계' → '자산총계'."""
    s = str(label or "").strip()
    while True:
        new = _PREFIX_RE.sub("", s, count=1)
        if new == s:
            break
        s = new
    s = _PAREN_RE.sub("", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[·ㆍ:：<>\[\]\"'※*]", "", s)
    return s


@dataclass
class Mapping:
    code: str
    confidence: str                 # 높음 / 중간 / 낮음
    needs_review: bool = False
    suggestion: str | None = None   # 미분류일 때 제안 표준코드
    notes: list[str] = field(default_factory=list)


def map_account(norm: str, statement: str, section: str | None = None, industry: str = "기타") -> Mapping:
    m = _map_base(norm, statement, industry)
    if statement == "BS" and section in NONCURRENT_SECTION_REMAP:
        remap = NONCURRENT_SECTION_REMAP[section]
        if m.code in remap:
            m.notes.append(f"비유동 구간에 위치하여 '{BY_CODE[remap[m.code]].label}'(으)로 분류")
            m.code = remap[m.code]
        if m.suggestion in remap:
            m.suggestion = remap[m.suggestion]
    if m.code == "UNMAPPED" and m.suggestion is None and statement == "BS":
        m.suggestion = SECTION_DEFAULT_SUGGESTION.get(section or "")
    return m


def _map_base(norm: str, statement: str, industry: str) -> Mapping:
    for code, names in EXACT_RULES.get(statement, {}).items():
        if norm in names:
            return Mapping(code, "높음")

    ambiguous = dict(AMBIGUOUS_RULES.get(statement, {}))
    if statement == "BS":
        for k, v in INDUSTRY_SUGGESTION_OVERRIDES.get(industry, {}).items():
            ambiguous[k] = v
    if norm in ambiguous:
        sugg, reason = ambiguous[norm]
        return Mapping("UNMAPPED", "낮음", True, sugg,
                       [f"판단 필요: {reason} (제안: {BY_CODE[sugg].label})"])

    for st, pattern, code in CONTAINS_RULES:
        if st == statement and re.search(pattern, norm):
            if statement in ("CF", "IS"):
                return Mapping(code, "높음")  # 활동별 합계·이익 항목은 표기 변형만 있는 경우가 대부분
            return Mapping(code, "중간", notes=["유사 명칭으로 자동 분류"])

    # '○○합계/소계' → 기초 계정명으로 다시 매핑
    if _TOTAL_SUFFIX_RE.search(norm):
        base = _TOTAL_SUFFIX_RE.sub("", norm)
        if base and base != norm:
            m = _map_base(base, statement, industry)
            if m.code != "UNMAPPED" and BY_CODE[m.code].kind == "sum":
                m.notes.append("합계 표기 행")
            return m

    if statement == "BS":
        return Mapping("UNMAPPED", "낮음", True, None, ["자동 분류 규칙에 없는 계정 – 분류 선택 필요"])
    if statement == "CF":
        return Mapping("CF_ITEM", "높음")
    return Mapping("OTHER_INFO", "높음")


def section_of(norm: str) -> str | None:
    return SECTION_HEADERS.get(norm)


def contra_target(norm: str, anchor_code: str | None) -> str | None:
    """차감계정이면 바로 위 계정(anchor)의 표준코드를 반환. 아니면 None."""
    if anchor_code is None:
        return None
    for pattern, allowed in CONTRA_RULES:
        if re.search(pattern, norm):
            if allowed is None:
                ok = anchor_code in BS_ASSET_CODES or anchor_code == "UNMAPPED"
            else:
                ok = anchor_code in allowed
            return anchor_code if ok else None
    return None


def is_contra_name(norm: str) -> bool:
    return any(re.search(p, norm) for p, _ in CONTRA_RULES)


# ─────────────────────────────────────────────────────────────────────────────
# 블록 단위 구조 규칙: 차감계정 / 부호 / 소계
# rows: 같은 재무제표 블록, 같은 연도 열의 행 목록(순서대로). 각 행은 dict:
#   norm, label, amount(문서단위), code, confidence, needs_review, suggestion, notes(list),
#   is_contra(bool), total_col(bool), is_subtotal(bool)
# ─────────────────────────────────────────────────────────────────────────────
def apply_sign_rules(row: dict) -> None:
    code, amt = row["code"], row["amount"]
    if amt is None:
        return
    if row.get("is_contra") and amt > 0:
        row["amount"] = -amt
        row["notes"].append("차감계정: 양수로 표기되어 음수로 변환")
        row["needs_review"] = True
    if code in LOSS_SIGN_CODES and "손실" in row["label"] and "이익" not in row["label"] and amt > 0:
        row["amount"] = -amt
        row["notes"].append("'손실' 표기 계정: 음수로 변환 (확인 필요)")
        row["needs_review"] = True
    acc = BY_CODE.get(code)
    if acc and acc.expense and amt < 0:
        row["amount"] = -amt
        row["notes"].append("비용 항목이 괄호(음수)로 표기되어 양수로 변환 (확인 필요)")
        row["needs_review"] = True


def detect_subtotals(rows: list[dict], tolerance: float = 2.0) -> None:
    """그룹 헤더(예: '(2) 재고자산 1,430')가 바로 아래 세부항목 합계와 같으면 '소계'로 표시한다.

    - 헤더 아래(또는 '합계' 행 위)의 같은 표준계정 연속 행 합계와 비교한다.
    - 차감계정(대손충당금 등)만 이어지는 경우는 소계로 보지 않는다 (예: 매출채권 + 대손충당금).
    - 합계가 다르더라도 2열 형식에서 헤더가 합계열에 있으면 소계로 보되 '확인 필요'.
    """
    n = len(rows)
    for i, r in enumerate(rows):
        acc = BY_CODE.get(r["code"])
        if not acc or acc.kind != "sum" or r["amount"] is None or r.get("is_contra"):
            continue
        is_header = r["norm"] in GROUP_HEADER_NAMES
        is_total_row = bool(_TOTAL_SUFFIX_RE.search(r["norm"]))
        if not (is_header or is_total_row):
            continue
        if is_total_row:
            seq = []
            j = i - 1
            while j >= 0 and rows[j]["code"] == r["code"]:
                seq.append(rows[j])
                j -= 1
        else:
            seq = []
            j = i + 1
            while j < n and rows[j]["code"] == r["code"]:
                seq.append(rows[j])
                j += 1
        if not any(not s.get("is_contra") for s in seq):
            continue
        total = sum(s["amount"] or 0 for s in seq)
        if abs(total - r["amount"]) <= tolerance:
            r["is_subtotal"] = True
            r["notes"].append("하위 항목 합계와 같아 소계로 판단 – 중복 방지를 위해 제외")
        elif r.get("total_col") and not any(s.get("total_col") for s in seq):
            r["is_subtotal"] = True
            r["needs_review"] = True
            r["notes"].append(
                f"소계로 판단했으나 하위 항목 합계({total:,.0f})와 다름 – 누락된 세부 항목이 있는지 확인"
            )
        else:
            r["needs_review"] = True
            r["notes"].append("같은 계정의 세부 항목이 이어짐 – 소계(중복) 여부 확인 필요")
