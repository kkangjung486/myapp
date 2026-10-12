"""숫자·단위 해석 테스트 (음수 괄호, 쉼표, 공백, 단위 변환)."""
import pytest

from pdf_parser.numbers import detect_unit, looks_like_amount, parse_amount, to_won


@pytest.mark.parametrize("text, expected", [
    ("1,234,567", 1234567),
    ("(15,000)", -15000),
    ("（15,000）", -15000),
    ("( 15,000 )", -15000),
    ("△15,000", -15000),
    ("▲ 2,500", -2500),
    ("-15,000", -15000),
    ("1, 234, 567", 1234567),   # 공백 제거
    ("0", 0),
    ("-", 0),                    # 재무제표의 '-'는 0
    ("–", 0),
    ("1,234.5", 1234.5),
    ("850", 850),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["매출액", "(15,000", "15,000)", "1,23", "제15기", "", None, "2025년"])
def test_parse_amount_rejects_non_numbers(text):
    assert parse_amount(text) is None


def test_looks_like_amount_distinguishes_note_numbers():
    assert looks_like_amount("1,234")
    assert looks_like_amount("(512)")
    assert looks_like_amount("-")
    assert not looks_like_amount("3")     # 주석 번호
    assert not looks_like_amount("12")


@pytest.mark.parametrize("text, unit", [
    ("(단위: 원)", "원"), ("(단위 : 천원)", "천원"), ("단위:백만원", "백만원"), ("(단위 : 백 만 원)", "백만원"),
    ("회사명 : (주)케이씨   (단위: 천 원)", "천원"), ("재무상태표", None),
])
def test_detect_unit(text, unit):
    assert detect_unit(text) == unit


def test_unit_conversion():
    assert to_won(1_234, "천원") == 1_234_000
    assert to_won(-15, "백만원") == -15_000_000
    assert to_won(7, "원") == 7
    assert to_won(None, "천원") is None
