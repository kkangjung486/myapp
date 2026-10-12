"""계정 매핑 테스트."""
from account_mapper.mapper import apply_sign_rules, detect_subtotals, map_account, normalize_name


def test_normalize_name():
    assert normalize_name("Ⅴ. 영업이익(손실)") == "영업이익"
    assert normalize_name("(1) 당좌자산") == "당좌자산"
    assert normalize_name("자 산 총 계") == "자산총계"
    assert normalize_name("1. 현금및현금성자산(주석3)") == "현금및현금성자산"
    assert normalize_name("가. 외상매출금") == "외상매출금"
    assert normalize_name("현금") == "현금"   # 한 글자 번호로 오인하지 않음


def test_exact_mapping():
    assert map_account("외상매출금", "BS", "CA").code == "AR"
    assert map_account("공사미수금", "BS", "CA").code == "AR"
    assert map_account("미청구공사", "BS", "CA").code == "CONTRACT_ASSET"
    assert map_account("초과청구공사", "BS", "CL").code == "CONTRACT_LIAB"
    assert map_account("원재료", "BS", "CA").code == "INV"
    assert map_account("지급어음", "BS", "CL").code == "AP"
    assert map_account("유동성장기부채", "BS", "CL").code == "CURRENT_LTD"
    assert map_account("기계장치", "BS", "NCA").code == "PPE"
    assert map_account("당기순이익", "IS").code == "NET_INCOME"
    assert map_account("영업활동으로인한현금흐름", "CF").code == "CFO"


def test_ambiguous_accounts_are_not_auto_classified():
    m = map_account("선급금", "BS", "CA")
    assert m.code == "UNMAPPED" and m.needs_review and m.suggestion == "OTHER_OP_CA"
    m = map_account("선수금", "BS", "CL", industry="건설업")
    assert m.code == "UNMAPPED" and m.suggestion == "CONTRACT_LIAB"


def test_section_remap_noncurrent():
    assert map_account("차입금", "BS", "NCL").code == "LT_BORROW"
    assert map_account("알수없는계정", "BS", "NCA").suggestion == "OTHER_NCA"


def test_statement_specific_mapping_avoids_double_count():
    # 현금흐름표 안의 '당기순이익', '감가상각비'는 손익 계정으로 매핑하지 않는다
    assert map_account("당기순이익", "CF").code == "CF_ITEM"
    assert map_account("감가상각비", "CF").code == "CF_ITEM"
    assert map_account("감가상각비", "COGS").code == "DEPRECIATION"


def _row(norm, amount, code, **kw):
    return {"norm": norm, "label": kw.pop("label", norm), "amount": amount, "code": code, "notes": [],
            "needs_review": False, "is_contra": kw.pop("is_contra", False), "total_col": kw.pop("total_col", False),
            "is_subtotal": False}


def test_subtotal_detection():
    rows = [_row("재고자산", 300, "INV"), _row("상품", 100, "INV"), _row("제품", 200, "INV")]
    detect_subtotals(rows)
    assert rows[0]["is_subtotal"] and not rows[1]["is_subtotal"]


def test_receivable_with_allowance_is_not_subtotal():
    rows = [_row("매출채권", 300, "AR"), _row("대손충당금", -3, "AR", is_contra=True)]
    detect_subtotals(rows)
    assert not rows[0]["is_subtotal"]


def test_sign_rules():
    r = _row("대손충당금", 3000, "AR", is_contra=True)
    apply_sign_rules(r)
    assert r["amount"] == -3000
    r = _row("영업손실", 500, "OP_INCOME", label="영업손실")
    apply_sign_rules(r)
    assert r["amount"] == -500 and r["needs_review"]
    r = _row("매출원가", -800, "COGS")
    apply_sign_rules(r)
    assert r["amount"] == 800
