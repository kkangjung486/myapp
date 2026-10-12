"""숫자·단위 해석.

재무제표 숫자 표기 규칙
  1,234,567   → 1234567
  (15,000)    → -15000     (괄호 = 음수)
  △15,000 / ▲15,000 / -15,000 → -15000
  -, –, —     → 0          (재무제표에서 '-'는 0을 의미)
"""
from __future__ import annotations

import re

UNIT_MULTIPLIERS: dict[str, int] = {
    "원": 1,
    "천원": 1_000,
    "백만원": 1_000_000,
    "억원": 100_000_000,
}

_DASHES = {"-", "–", "—", "－", "―", "‐"}
_NEG_PREFIX = ("△", "▲", "-", "－", "−", "(", "（")

# 천 단위 쉼표가 올바른 숫자 또는 쉼표 없는 숫자 (소수점 허용)
_NUM_BODY = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_AMOUNT_RE = re.compile(
    rf"^(?P<neg>[△▲\-－−])?\s*(?P<open>[\(（])?\s*(?P<neg2>[△▲\-－−])?\s*(?P<body>{_NUM_BODY})\s*(?P<close>[\)）])?$"
)


def is_dash(token: str) -> bool:
    return token.strip() in _DASHES


def parse_amount(token: str) -> float | None:
    """재무제표 숫자 문자열 → float. 숫자가 아니면 None.

    공백은 제거하고 해석한다. 괄호는 열고 닫는 짝이 맞아야 음수로 인정한다.
    """
    if token is None:
        return None
    t = str(token).strip().replace(" ", "").replace(" ", "")
    if not t:
        return None
    if t in _DASHES:
        return 0.0
    m = _AMOUNT_RE.match(t)
    if not m:
        return None
    has_open, has_close = bool(m.group("open")), bool(m.group("close"))
    if has_open != has_close:
        return None  # 괄호 짝이 맞지 않으면 숫자로 보지 않음 (예: "(1" 같은 번호)
    value = float(m.group("body").replace(",", ""))
    negative = has_open or bool(m.group("neg")) or bool(m.group("neg2"))
    return -value if negative else value


def looks_like_amount(token: str) -> bool:
    """금액 열에 들어가는 숫자인지(주석번호·항목번호와 구분하기 위한 힌트)."""
    t = token.strip()
    if is_dash(t):
        return True
    if parse_amount(t) is None:
        return False
    digits = re.sub(r"\D", "", t)
    return "," in t or len(digits) >= 4 or t.startswith(("(", "（", "△", "▲"))


_UNIT_RE = re.compile(r"단\s*위\s*[:：]?\s*(?:\(?\s*)?(백\s*만\s*원|천\s*원|억\s*원|원)")


def detect_unit(text: str) -> str | None:
    """'(단위: 천원)' 같은 표기에서 단위를 찾는다. 없으면 None."""
    m = _UNIT_RE.search(text)
    if not m:
        return None
    return m.group(1).replace(" ", "")


def to_won(amount: float | None, unit: str) -> float | None:
    if amount is None:
        return None
    return amount * UNIT_MULTIPLIERS[unit]
