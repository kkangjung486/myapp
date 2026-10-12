"""재무계산 모듈 테스트 — PDF와 무관하게 손으로 검산한 숫자로 검증한다.

가상 제조업체 (단위 백만원 → 원):
            2024(전기말)  2025(당기)
유동자산          500         600
유동부채          300         330
현금               50          55
매출채권          100         150
재고자산           80         100
기타영업유동자산    10          12
매입채무           60          70
기타영업유동부채     5           8
유형자산          400         420
단기차입금        100         150
장기차입금        200         230
퇴직급여충당부채    20          25
2025 손익: 매출 1,000 / 매출원가 700 / 감가상각비 30 / 순이익 50
"""
import pytest

from financial_calculations.cash_bridge import cash_bridge
from financial_calculations.cashflow import ESTIMATE_WARNING, choose_cfo, estimate_cfo
from financial_calculations.ccc import DPO_COGS_PROXY_MSG, compute_ccc
from financial_calculations.common import END_METHOD, average_balance, growth_pct
from financial_calculations.formatting import approx, eok_man
from financial_calculations.summary import analyze
from financial_calculations.working_capital import nwc, owc, owc_change

M = 1_000_000
PREV = {k: v * M for k, v in dict(TOTAL_ASSETS=900, CA_TOTAL=500, CL_TOTAL=300, CASH=50, AR=100, INV=80,
                                   OTHER_OP_CA=10, AP=60, OTHER_OP_CL=5, PPE=400, ST_BORROW=100, LT_BORROW=200,
                                   CURRENT_LTD=0, BONDS=0, RETIREMENT=20, CONTRACT_ASSET=0, CONTRACT_LIAB=0,
                                   REVENUE=900, NET_INCOME=40).items()}
CURR = {k: v * M for k, v in dict(TOTAL_ASSETS=1000, CA_TOTAL=600, CL_TOTAL=330, CASH=55, AR=150, INV=100,
                                   OTHER_OP_CA=12, AP=70, OTHER_OP_CL=8, PPE=420, ST_BORROW=150, LT_BORROW=230,
                                   CURRENT_LTD=0, BONDS=0, RETIREMENT=25, CONTRACT_ASSET=0, CONTRACT_LIAB=0,
                                   REVENUE=1000, COGS=700, DEPRECIATION=30, NET_INCOME=50).items()}


def test_estimated_cfo():
    # 50 + 30 + (25-20) - (150-100) - (100-80) - (12-10) + (70-60) + (8-5) = 26
    est = estimate_cfo(CURR, PREV)
    assert est.value == pytest.approx(26 * M)
    assert est.complete
    assert ESTIMATE_WARNING in est.warnings


def test_cfo_sign_rules():
    """영업자산 증가 = 현금 감소, 영업부채 증가 = 현금 증가."""
    base = estimate_cfo(CURR, PREV).value
    more_ar = dict(CURR, AR=CURR["AR"] + 10 * M)
    assert estimate_cfo(more_ar, PREV).value == pytest.approx(base - 10 * M)
    more_ap = dict(CURR, AP=CURR["AP"] + 10 * M)
    assert estimate_cfo(more_ap, PREV).value == pytest.approx(base + 10 * M)


def test_estimated_cfo_requires_prior_balance_sheet():
    est = estimate_cfo(CURR, None)
    assert est.value is None
    assert any("전기말" in w for w in est.warnings)


def test_missing_depreciation_is_flagged_not_invented():
    cur = dict(CURR)
    del cur["DEPRECIATION"]
    est = estimate_cfo(cur, PREV)
    assert est.value == pytest.approx(-4 * M)
    assert not est.complete
    assert any("감가상각비" in w for w in est.warnings)


def test_disclosed_cfo_has_priority():
    est = estimate_cfo(CURR, PREV)
    assert choose_cfo(99 * M, est) == (99 * M, "공시")
    assert choose_cfo(None, est) == (est.value, "추정")


def test_nwc_and_owc():
    assert nwc(CURR) == 270 * M
    value, breakdown = owc(CURR)
    assert value == pytest.approx(184 * M)          # 150 + 100 + 12 - 70 - 8
    assert breakdown["AP"] == -70 * M
    assert owc(PREV)[0] == pytest.approx(125 * M)    # 100 + 80 + 10 - 60 - 5


def test_owc_change_interpretation():
    d, text = owc_change(184 * M, 125 * M)
    assert d == 59 * M
    assert "묶인" in text
    d, text = owc_change(100 * M, 125 * M)
    assert d == -25 * M and "회수" in text
    assert owc_change(100 * M, None)[0] is None


def test_ccc_with_average_balances_and_cogs_proxy():
    r = compute_ccc(CURR, PREV)
    assert r.dso == pytest.approx(125 / 1000 * 365)   # 평균 매출채권 125
    assert r.dio == pytest.approx(90 / 700 * 365)     # 평균 재고 90
    assert r.dpo == pytest.approx(65 / 700 * 365)     # 평균 매입채무 65, 매출원가 대용
    assert r.ccc == pytest.approx(r.dso + r.dio - r.dpo)
    assert r.ccc == pytest.approx(58.660714, rel=1e-6)
    assert r.purchases_basis == "매출원가 대용"
    assert DPO_COGS_PROXY_MSG in r.notes
    assert r.dpo_ref_purchases == pytest.approx(720 * M)   # 700 + 100 - 80


def test_dpo_uses_actual_purchases_when_available():
    r = compute_ccc(dict(CURR, PURCHASE_MERCH=650 * M), PREV)
    assert r.dpo == pytest.approx(65 / 650 * 365)
    assert r.purchases_basis.startswith("매입액")
    assert DPO_COGS_PROXY_MSG not in r.notes


def test_first_year_uses_ending_balance():
    r = compute_ccc(CURR, None)
    assert r.dso == pytest.approx(150 / 1000 * 365)
    assert r.ar_method == END_METHOD
    assert average_balance(None, 10.0) == (10.0, END_METHOD)


def test_ccc_not_computed_without_cogs():
    cur = dict(CURR)
    del cur["COGS"]
    r = compute_ccc(cur, PREV)
    assert r.dio is None and r.ccc is None


def test_cash_bridge_reconciles():
    b = cash_bridge(CURR, PREV, revenue_growth=11.1)
    amounts = {i.key: i.amount for i in b.items}
    assert amounts["NI"] == 50 * M
    assert amounts["AR"] == -50 * M
    assert amounts["INV"] == -20 * M
    assert amounts["AP"] == 10 * M
    assert amounts["PPE"] == -20 * M
    assert amounts["BORROW"] == 80 * M
    assert b.cash_change == 5 * M
    assert sum(i.amount for i in b.items) == pytest.approx(b.cash_change)   # 기타(잔여)로 정확히 맞춰짐
    assert b.wc_tied == 70 * M
    assert any("묶였습니다" in s for s in b.narrative)


def test_analyze_summary_metrics():
    a = analyze({2024: PREV, 2025: CURR}, [2025])[0]
    assert a.cfo_basis == "추정"
    assert a.ocf_margin == pytest.approx(2.6)
    assert a.cash_conversion == pytest.approx(26 / 50)
    assert a.total_borrowings == 380 * M
    assert a.borrowings_change == 80 * M
    assert a.owc_change == pytest.approx(59 * M)
    assert a.revenue_growth == pytest.approx(100 / 900 * 100)


def test_negative_net_income_conversion_not_interpreted():
    cur = dict(CURR, NET_INCOME=-10 * M)
    a = analyze({2024: PREV, 2025: cur}, [2025])[0]
    assert a.cash_conversion is None and "0 이하" in a.cash_conversion_note


def test_growth_and_formatting():
    assert growth_pct(120, 100) == 20
    assert growth_pct(1, 0) is None
    assert eok_man(1_234_567_890) == "12억 3,457만원"
    assert eok_man(-80_000_000) == "-8,000만원"
    assert approx(130_000_000) == "약 1억 3,000만 원"
