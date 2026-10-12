"""가상 제조업체 '주식회사 케이씨정밀'의 재무제표 원천 데이터 (단위: 천원).

※ 실존 회사가 아닌 테스트용 가상 데이터다.
- 매출은 성장하지만 매출채권·재고가 더 빠르게 늘고, 차입금이 증가하는 전형적인 '흑자인데 돈이 없는' 구조.
- 재무상태표 대차, 손익계산서 합계, 원가 흐름, 현금흐름표가 모두 서로 맞도록 계산해서 만든다.
- 이 모듈의 결과를 '정답'으로 삼아 PDF 파싱·계산 결과를 테스트한다.
"""
from __future__ import annotations

COMPANY = "주식회사 케이씨정밀"
YEARS = [2022, 2023, 2024, 2025]
PERIOD_NO = {2022: 12, 2023: 13, 2024: 14, 2025: 15}

# 기말 잔액 드라이버 (2021 = 기초값)
END = {
    "cash":        {2021: 300_000, 2022: 320_000, 2023: 280_000, 2024: 250_000, 2025: 260_000},
    "st_fin":      {2021: 100_000, 2022: 100_000, 2023: 100_000, 2024: 50_000, 2025: 50_000},
    "ar_gross":    {2021: 600_000, 2022: 650_000, 2023: 800_000, 2024: 1_100_000, 2025: 1_450_000},
    "misc_recv":   {2021: 20_000, 2022: 25_000, 2023: 30_000, 2024: 28_000, 2025: 35_000},
    "advances":    {2021: 30_000, 2022: 35_000, 2023: 40_000, 2024: 60_000, 2025: 55_000},
    "prepaid":     {2021: 5_000, 2022: 6_000, 2023: 7_000, 2024: 8_000, 2025: 9_000},
    "merch_inv":   {2021: 150_000, 2022: 160_000, 2023: 180_000, 2024: 230_000, 2025: 300_000},
    "fg_inv":      {2021: 300_000, 2022: 320_000, 2023: 350_000, 2024: 430_000, 2025: 560_000},
    "wip_inv":     {2021: 100_000, 2022: 110_000, 2023: 120_000, 2024: 150_000, 2025: 190_000},
    "raw_inv":     {2021: 200_000, 2022: 210_000, 2023: 240_000, 2024: 300_000, 2025: 380_000},
    "ap":          {2021: 380_000, 2022: 400_000, 2023: 450_000, 2024: 520_000, 2025: 560_000},
    "misc_pay":    {2021: 40_000, 2022: 45_000, 2023: 50_000, 2024: 55_000, 2025: 60_000},
    "accrued":     {2021: 25_000, 2022: 28_000, 2023: 30_000, 2024: 35_000, 2025: 40_000},
    "withholding": {2021: 10_000, 2022: 11_000, 2023: 12_000, 2024: 13_000, 2025: 14_000},
    "cust_adv":    {2021: 20_000, 2022: 25_000, 2023: 15_000, 2024: 30_000, 2025: 20_000},
    "cur_ltd":     {2021: 100_000, 2022: 100_000, 2023: 100_000, 2024: 100_000, 2025: 100_000},
    "lt_borrow":   {2021: 500_000, 2022: 500_000, 2023: 550_000, 2024: 650_000, 2025: 700_000},
}
LAND = 800_000
BUILDING_GROSS = 1_200_000
VEHICLE_GROSS = 120_000
SOFTWARE = 30_000
DEPOSIT = 50_000
CAPITAL = 500_000
MACHINE_GROSS_2021 = 900_000
ACC_DEP_2021 = {"building": 300_000, "machine": 400_000, "vehicle": 60_000}
CAPEX = {2022: 100_000, 2023: 150_000, 2024: 400_000, 2025: 250_000}  # 기계장치 취득
RETIRE_2021 = 200_000
PENSION_ASSET_2021 = 100_000
RETIRE_EXPENSE = {2022: 40_000, 2023: 45_000, 2024: 50_000, 2025: 55_000}
RETIRE_PAID = 15_000
PENSION_DEPOSIT = 20_000
TAX_2021 = 20_000
ST_BORROW_2021 = 600_000

REVENUE = {
    2022: {"product": 3_600_000, "merch": 600_000},
    2023: {"product": 4_100_000, "merch": 700_000},
    2024: {"product": 4_750_000, "merch": 850_000},
    2025: {"product": 5_300_000, "merch": 1_000_000},
}
LABOR = {2022: 520_000, 2023: 590_000, 2024: 690_000, 2025: 760_000}
POWER = {2022: 90_000, 2023: 100_000, 2024: 115_000, 2025: 125_000}
OUTSOURCE = {2022: 150_000, 2023: 170_000, 2024: 200_000, 2025: 230_000}
OTHER_MFG = {2022: 60_000, 2023: 65_000, 2024: 75_000, 2025: 80_000}
SALARY = {2022: 380_000, 2023: 420_000, 2024: 480_000, 2025: 540_000}
WELFARE = {2022: 45_000, 2023: 50_000, 2024: 57_000, 2025: 63_000}
FEES = {2022: 60_000, 2023: 70_000, 2024: 82_000, 2025: 95_000}
OTHER_SGA = {2022: 80_000, 2023: 88_000, 2024: 99_000, 2025: 110_000}
INTEREST_INCOME = {2022: 3_000, 2023: 3_000, 2024: 2_000, 2025: 1_500}
INTEREST_RATE = 0.05
MERCH_COGS_RATIO = 0.85
PRODUCT_COGS_RATIO = 0.80


def _r(x: float) -> int:
    return int(round(x))


def build() -> dict[int, dict]:
    """연도별 재무제표 원천 데이터를 계산한다 (단위: 천원)."""
    data: dict[int, dict] = {}
    machine_gross = MACHINE_GROSS_2021
    acc = dict(ACC_DEP_2021)
    retire, pension, tax_prev = RETIRE_2021, PENSION_ASSET_2021, TAX_2021
    re_prev = _opening_retained_earnings()
    for y in YEARS:
        p = y - 1
        d: dict = {"year": y}
        # ── 유형자산 / 감가상각 ──
        machine_gross += CAPEX[y]
        dep_building, dep_vehicle = 40_000, 10_000
        dep_machine = _r(machine_gross * 0.10)
        acc["building"] += dep_building
        acc["machine"] += dep_machine
        acc["vehicle"] += dep_vehicle
        dep_mfg = _r(dep_building * 0.7) + dep_machine
        dep_sga = dep_building - _r(dep_building * 0.7) + dep_vehicle
        d.update(machine_gross=machine_gross, acc_building=acc["building"], acc_machine=acc["machine"],
                 acc_vehicle=acc["vehicle"], dep_mfg=dep_mfg, dep_sga=dep_sga, dep_total=dep_mfg + dep_sga)
        # ── 매출 / 매출원가 / 원가명세 ──
        rev_p, rev_m = REVENUE[y]["product"], REVENUE[y]["merch"]
        merch_cogs = _r(rev_m * MERCH_COGS_RATIO)
        merch_purchase = merch_cogs - END["merch_inv"][p] + END["merch_inv"][y]
        product_cogs = _r(rev_p * PRODUCT_COGS_RATIO)
        cogm = product_cogs - END["fg_inv"][p] + END["fg_inv"][y]
        total_mfg = cogm - END["wip_inv"][p] + END["wip_inv"][y]
        overhead = dep_mfg + POWER[y] + OUTSOURCE[y] + OTHER_MFG[y]
        material = total_mfg - LABOR[y] - overhead
        raw_purchase = material - END["raw_inv"][p] + END["raw_inv"][y]
        d.update(rev_product=rev_p, rev_merch=rev_m, revenue=rev_p + rev_m, merch_cogs=merch_cogs,
                 merch_purchase=merch_purchase, product_cogs=product_cogs, cogm=cogm, total_mfg=total_mfg,
                 material=material, raw_purchase=raw_purchase, labor=LABOR[y], power=POWER[y],
                 outsource=OUTSOURCE[y], other_mfg=OTHER_MFG[y], overhead=overhead,
                 cogs=merch_cogs + product_cogs)
        # ── 판관비 ──
        allowance = _r(END["ar_gross"][y] * 0.01)
        bad_debt = allowance - _r(END["ar_gross"][p] * 0.01)
        sga = SALARY[y] + RETIRE_EXPENSE[y] + WELFARE[y] + dep_sga + FEES[y] + bad_debt + OTHER_SGA[y]
        d.update(allowance=allowance, bad_debt=bad_debt, salary=SALARY[y], retire_exp=RETIRE_EXPENSE[y],
                 welfare=WELFARE[y], fees=FEES[y], other_sga=OTHER_SGA[y], sga=sga)
        gross = d["revenue"] - d["cogs"]
        op = gross - sga
        interest = _r((END["cur_ltd"][p] + END["lt_borrow"][p]) * INTEREST_RATE + 0)  # 장기 이자
        pretax_tmp = op + INTEREST_INCOME[y]
        d.update(gross=gross, op=op, interest_income=INTEREST_INCOME[y])
        # 단기차입금 이자는 기초 단기차입금 기준 (plug 계산 뒤 확정)
        d["_interest_lt"] = interest
        d["_pretax_wo_st"] = pretax_tmp
        data[y] = d

    # 단기차입금(plug)과 이자·법인세·이익잉여금을 연도순으로 확정
    st_prev = None
    for y in YEARS:
        d = data[y]
        p = y - 1
        if st_prev is None:
            st_prev = ST_BORROW_2021
        interest = d["_interest_lt"] + _r(st_prev * INTEREST_RATE)
        pretax = d["_pretax_wo_st"] - interest
        tax = _r(pretax * 0.10)
        ni = pretax - tax
        retire = retire + RETIRE_EXPENSE[y] - RETIRE_PAID
        pension = pension + PENSION_DEPOSIT
        re_end = re_prev + ni
        d.update(interest_exp=interest, pretax=pretax, tax=tax, ni=ni, retire=retire, pension=pension,
                 retained=re_end, capital=CAPITAL, tax_payable=tax)
        # 자산
        ppe = (LAND + BUILDING_GROSS - d["acc_building"] + d["machine_gross"] - d["acc_machine"]
               + VEHICLE_GROSS - d["acc_vehicle"])
        inv = END["merch_inv"][y] + END["fg_inv"][y] + END["wip_inv"][y] + END["raw_inv"][y]
        ar_net = END["ar_gross"][y] - d["allowance"]
        quick = (END["cash"][y] + END["st_fin"][y] + ar_net + END["misc_recv"][y]
                 + END["advances"][y] + END["prepaid"][y])
        ca = quick + inv
        nca = ppe + SOFTWARE + DEPOSIT
        assets = ca + nca
        # 부채 (단기차입금 = plug)
        retire_net = retire - pension
        ncl = END["lt_borrow"][y] + retire_net
        equity = CAPITAL + re_end
        cl_ex_st = (END["ap"][y] + END["misc_pay"][y] + END["accrued"][y] + END["withholding"][y]
                    + END["cust_adv"][y] + tax + END["cur_ltd"][y])
        st = assets - equity - ncl - cl_ex_st
        assert st > 0, (y, st)
        cl = cl_ex_st + st
        d.update(ppe=ppe, inv=inv, ar_net=ar_net, quick=quick, ca=ca, nca=nca, assets=assets,
                 st_borrow=st, cl=cl, ncl=ncl, liab=cl + ncl, equity=equity, retire_net=retire_net)
        for k, v in END.items():
            d[k] = v[y]
        # 현금흐름표 (간접법)
        prev = data.get(p)
        prev_vals = prev if prev else _opening(st_prev, tax_prev)
        d["cf"] = _cash_flow(d, prev_vals)
        st_prev, tax_prev, re_prev = st, tax, re_end
    return data


def _opening_retained_earnings() -> int:
    """2021년말(기초) 재무상태표가 대차일치하도록 이익잉여금을 역산한다."""
    e = {k: v[2021] for k, v in END.items()}
    ppe = (LAND + BUILDING_GROSS - ACC_DEP_2021["building"] + MACHINE_GROSS_2021 - ACC_DEP_2021["machine"]
           + VEHICLE_GROSS - ACC_DEP_2021["vehicle"])
    assets = (e["cash"] + e["st_fin"] + e["ar_gross"] - _r(e["ar_gross"] * 0.01) + e["misc_recv"]
              + e["advances"] + e["prepaid"] + e["merch_inv"] + e["fg_inv"] + e["wip_inv"] + e["raw_inv"]
              + ppe + SOFTWARE + DEPOSIT)
    liab = (e["ap"] + e["misc_pay"] + e["accrued"] + e["withholding"] + e["cust_adv"] + TAX_2021
            + e["cur_ltd"] + ST_BORROW_2021 + e["lt_borrow"] + RETIRE_2021 - PENSION_ASSET_2021)
    return assets - liab - CAPITAL


def _opening(st_2021: int, tax_2021: int) -> dict:
    o = {k: v[2021] for k, v in END.items()}
    o.update(st_borrow=st_2021, tax_payable=tax_2021, ar_net=END["ar_gross"][2021] - _r(END["ar_gross"][2021] * 0.01),
             inv=END["merch_inv"][2021] + END["fg_inv"][2021] + END["wip_inv"][2021] + END["raw_inv"][2021])
    return o


def _cash_flow(d: dict, p: dict) -> dict:
    items = [
        ("당기순이익", d["ni"]),
        ("감가상각비", d["dep_total"]),
        ("퇴직급여", d["retire_exp"]),
        ("매출채권의 감소(증가)", -(d["ar_net"] - p["ar_net"])),
        ("미수금의 감소(증가)", -(d["misc_recv"] - p["misc_recv"])),
        ("선급금의 감소(증가)", -(d["advances"] - p["advances"])),
        ("선급비용의 감소(증가)", -(d["prepaid"] - p["prepaid"])),
        ("재고자산의 감소(증가)", -(d["inv"] - p["inv"])),
        ("매입채무의 증가(감소)", d["ap"] - p["ap"]),
        ("미지급금의 증가(감소)", d["misc_pay"] - p["misc_pay"]),
        ("미지급비용의 증가(감소)", d["accrued"] - p["accrued"]),
        ("예수금의 증가(감소)", d["withholding"] - p["withholding"]),
        ("선수금의 증가(감소)", d["cust_adv"] - p["cust_adv"]),
        ("미지급법인세의 증가(감소)", d["tax_payable"] - p["tax_payable"]),
        ("퇴직금의 지급", -RETIRE_PAID),
    ]
    cfo = sum(v for _, v in items)
    capex = CAPEX[d["year"]]
    cfi_items = [
        ("단기금융상품의 감소(증가)", -(d["st_fin"] - p["st_fin"])),
        ("기계장치의 취득", -capex),
        ("퇴직연금운용자산의 증가", -PENSION_DEPOSIT),
    ]
    cfi = sum(v for _, v in cfi_items)
    cff_items = [
        ("단기차입금의 증가(감소)", d["st_borrow"] - p["st_borrow"]),
        ("장기차입금의 증가(감소)", (d["lt_borrow"] + d["cur_ltd"]) - (p["lt_borrow"] + p["cur_ltd"])),
    ]
    cff = sum(v for _, v in cff_items)
    net = cfo + cfi + cff
    assert net == d["cash"] - p["cash"], (d["year"], net, d["cash"] - p["cash"])
    return {"items": items, "cfo": cfo, "cfi_items": cfi_items, "cfi": cfi, "cff_items": cff_items,
            "cff": cff, "net": net, "begin": p["cash"], "end": d["cash"]}


if __name__ == "__main__":
    for y, d in build().items():
        print(y, "매출", d["revenue"], "순이익", d["ni"], "자산", d["assets"], "단기차입금", d["st_borrow"],
              "CFO", d["cf"]["cfo"])
