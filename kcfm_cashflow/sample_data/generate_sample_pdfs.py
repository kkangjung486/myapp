"""가상 제조업체 재무제표 PDF 생성기 (테스트·체험용).

생성 파일 (sample_data/pdfs/)
  2023년_재무제표_케이씨정밀.pdf  : 2023(당기)·2022(전기), 단위 천원, 재무상태표·손익계산서·제조원가명세서
  2024년_재무제표_케이씨정밀.pdf  : 2024·2023, 단위 천원
  2025년_재무제표_케이씨정밀.pdf  : 2025·2024, 단위 '원', 현금흐름표 포함
  3개년_통합_재무제표_케이씨정밀.pdf : 한 파일에 2025·2024·2023 3개 열 (단위 원, 단일열 형식)

실행:  python -m sample_data.generate_sample_pdfs
"""
from __future__ import annotations

import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from .sample_company import COMPANY, PERIOD_NO, build

FONT = "HYGothic-Medium"
OUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")

PAGE_W, PAGE_H = A4
TOP, BOTTOM, ROW_H = PAGE_H - 50, 50, 13.5
# 연도별 2열(세부/합계) 형식의 오른쪽 끝 x좌표
PAIRED_X = [(318, 393), (478, 553)]


def fmt(v: float | None) -> str:
    if v is None:
        return ""
    v = int(round(v))
    if v == 0:
        return "-"
    return f"({abs(v):,})" if v < 0 else f"{v:,}"


# 행 정의: (계정명, 종류, 들여쓰기, {연도: 값})
# 종류: head(숫자 없음) / total(합계열) / detail(세부열) / contra((차감액, 순액))
def bs_rows(d: dict) -> list:
    return [
        ("자 산", "head", 0, None),
        ("Ⅰ. 유동자산", "total", 0, d["ca"]),
        ("(1) 당좌자산", "total", 1, d["quick"]),
        ("1. 현금및현금성자산", "detail", 2, d["cash"]),
        ("2. 단기금융상품", "detail", 2, d["st_fin"]),
        ("3. 매출채권", "detail", 2, d["ar_gross"]),
        ("대손충당금", "contra", 3, (-d["allowance"], d["ar_net"])),
        ("4. 미수금", "detail", 2, d["misc_recv"]),
        ("5. 선급금", "detail", 2, d["advances"]),
        ("6. 선급비용", "detail", 2, d["prepaid"]),
        ("(2) 재고자산", "total", 1, d["inv"]),
        ("1. 상품", "detail", 2, d["merch_inv"]),
        ("2. 제품", "detail", 2, d["fg_inv"]),
        ("3. 재공품", "detail", 2, d["wip_inv"]),
        ("4. 원재료", "detail", 2, d["raw_inv"]),
        ("Ⅱ. 비유동자산", "total", 0, d["nca"]),
        ("(1) 유형자산", "total", 1, d["ppe"]),
        ("1. 토지", "detail", 2, 800_000),
        ("2. 건물", "detail", 2, 1_200_000),
        ("감가상각누계액", "contra", 3, (-d["acc_building"], 1_200_000 - d["acc_building"])),
        ("3. 기계장치", "detail", 2, d["machine_gross"]),
        ("감가상각누계액", "contra", 3, (-d["acc_machine"], d["machine_gross"] - d["acc_machine"])),
        ("4. 차량운반구", "detail", 2, 120_000),
        ("감가상각누계액", "contra", 3, (-d["acc_vehicle"], 120_000 - d["acc_vehicle"])),
        ("(2) 무형자산", "total", 1, 30_000),
        ("1. 소프트웨어", "detail", 2, 30_000),
        ("(3) 기타비유동자산", "total", 1, 50_000),
        ("1. 임차보증금", "detail", 2, 50_000),
        ("자 산 총 계", "total", 0, d["assets"]),
        ("부 채", "head", 0, None),
        ("Ⅰ. 유동부채", "total", 0, d["cl"]),
        ("1. 매입채무", "detail", 1, d["ap"]),
        ("2. 미지급금", "detail", 1, d["misc_pay"]),
        ("3. 미지급비용", "detail", 1, d["accrued"]),
        ("4. 예수금", "detail", 1, d["withholding"]),
        ("5. 선수금", "detail", 1, d["cust_adv"]),
        ("6. 미지급법인세", "detail", 1, d["tax_payable"]),
        ("7. 단기차입금", "detail", 1, d["st_borrow"]),
        ("8. 유동성장기부채", "detail", 1, d["cur_ltd"]),
        ("Ⅱ. 비유동부채", "total", 0, d["ncl"]),
        ("1. 장기차입금", "detail", 1, d["lt_borrow"]),
        ("2. 퇴직급여충당부채", "detail", 1, d["retire"]),
        ("퇴직연금운용자산", "contra", 2, (-d["pension"], d["retire_net"])),
        ("부 채 총 계", "total", 0, d["liab"]),
        ("자 본", "head", 0, None),
        ("Ⅰ. 자본금", "total", 0, d["capital"]),
        ("Ⅱ. 이익잉여금", "total", 0, d["retained"]),
        ("1. 미처분이익잉여금", "detail", 1, d["retained"]),
        ("자 본 총 계", "total", 0, d["equity"]),
        ("부 채 와 자 본 총 계", "total", 0, d["liab"] + d["equity"]),
    ]


def is_rows(d: dict, p_fg: int, p_merch: int) -> list:
    return [
        ("Ⅰ. 매출액", "total", 0, d["revenue"]),
        ("1. 제품매출", "detail", 1, d["rev_product"]),
        ("2. 상품매출", "detail", 1, d["rev_merch"]),
        ("Ⅱ. 매출원가", "total", 0, d["cogs"]),
        ("1. 상품매출원가", "detail", 1, d["merch_cogs"]),
        ("기초상품재고액", "detail", 2, p_merch),
        ("당기상품매입액", "detail", 2, d["merch_purchase"]),
        ("기말상품재고액", "detail", 2, -d["merch_inv"]),
        ("2. 제품매출원가", "detail", 1, d["product_cogs"]),
        ("기초제품재고액", "detail", 2, p_fg),
        ("당기제품제조원가", "detail", 2, d["cogm"]),
        ("기말제품재고액", "detail", 2, -d["fg_inv"]),
        ("Ⅲ. 매출총이익", "total", 0, d["gross"]),
        ("Ⅳ. 판매비와관리비", "total", 0, d["sga"]),
        ("1. 급여", "detail", 1, d["salary"]),
        ("2. 퇴직급여", "detail", 1, d["retire_exp"]),
        ("3. 복리후생비", "detail", 1, d["welfare"]),
        ("4. 감가상각비", "detail", 1, d["dep_sga"]),
        ("5. 지급수수료", "detail", 1, d["fees"]),
        ("6. 대손상각비", "detail", 1, d["bad_debt"]),
        ("7. 기타판매관리비", "detail", 1, d["other_sga"]),
        ("Ⅴ. 영업이익", "total", 0, d["op"]),
        ("Ⅵ. 영업외수익", "total", 0, d["interest_income"]),
        ("1. 이자수익", "detail", 1, d["interest_income"]),
        ("Ⅶ. 영업외비용", "total", 0, d["interest_exp"]),
        ("1. 이자비용", "detail", 1, d["interest_exp"]),
        ("Ⅷ. 법인세비용차감전순이익", "total", 0, d["pretax"]),
        ("Ⅸ. 법인세비용", "total", 0, d["tax"]),
        ("Ⅹ. 당기순이익", "total", 0, d["ni"]),
    ]


def cogs_rows(d: dict, p_raw: int, p_wip: int) -> list:
    return [
        ("Ⅰ. 재료비", "total", 0, d["material"]),
        ("1. 기초원재료재고액", "detail", 1, p_raw),
        ("2. 당기원재료매입액", "detail", 1, d["raw_purchase"]),
        ("3. 기말원재료재고액", "detail", 1, -d["raw_inv"]),
        ("Ⅱ. 노무비", "total", 0, d["labor"]),
        ("Ⅲ. 경비", "total", 0, d["overhead"]),
        ("1. 감가상각비", "detail", 1, d["dep_mfg"]),
        ("2. 전력비", "detail", 1, d["power"]),
        ("3. 외주가공비", "detail", 1, d["outsource"]),
        ("4. 기타경비", "detail", 1, d["other_mfg"]),
        ("Ⅳ. 당기총제조비용", "total", 0, d["total_mfg"]),
        ("Ⅴ. 기초재공품재고액", "total", 0, p_wip),
        ("Ⅵ. 기말재공품재고액", "total", 0, -d["wip_inv"]),
        ("Ⅶ. 당기제품제조원가", "total", 0, d["cogm"]),
    ]


def cf_rows(d: dict) -> list:
    cf = d["cf"]
    rows = [("Ⅰ. 영업활동으로 인한 현금흐름", "total", 0, cf["cfo"])]
    rows += [(f"{i + 1}. {nm}" if i == 0 else nm, "detail", 1, v) for i, (nm, v) in enumerate(cf["items"])]
    rows.append(("Ⅱ. 투자활동으로 인한 현금흐름", "total", 0, cf["cfi"]))
    rows += [(nm, "detail", 1, v) for nm, v in cf["cfi_items"]]
    rows.append(("Ⅲ. 재무활동으로 인한 현금흐름", "total", 0, cf["cff"]))
    rows += [(nm, "detail", 1, v) for nm, v in cf["cff_items"]]
    rows += [
        ("Ⅳ. 현금의 증가(감소)", "total", 0, cf["net"]),
        ("Ⅴ. 기초의 현금", "total", 0, cf["begin"]),
        ("Ⅵ. 기말의 현금", "total", 0, cf["end"]),
    ]
    return rows


class StatementWriter:
    def __init__(self, path: str):
        pdfmetrics.registerFont(UnicodeCIDFont(FONT))
        self.c = canvas.Canvas(path, pagesize=A4)
        self.y = TOP

    def text(self, x, s, size=8.5, align="left"):
        self.c.setFont(FONT, size)
        if align == "right":
            self.c.drawRightString(x, self.y, s)
        elif align == "center":
            self.c.drawCentredString(x, self.y, s)
        else:
            self.c.drawString(x, self.y, s)

    def newline(self, h=ROW_H):
        self.y -= h

    def new_page(self):
        self.c.showPage()
        self.y = TOP

    def statement(self, title: str, period_lines: list[str], unit: str, col_labels: list[str],
                  rows_by_col: list[list], paired: bool = True, col_x: list | None = None):
        self.text(PAGE_W / 2, title, size=14, align="center")
        self.newline(22)
        for pl in period_lines:
            self.text(PAGE_W / 2, pl, size=8.5, align="center")
            self.newline(12)
        self.newline(4)
        self.text(40, f"회사명 : {COMPANY}")
        self.text(555, f"(단위 : {unit})", align="right")
        self.newline(16)
        self._header(col_labels, paired, col_x)
        n_rows = len(rows_by_col[0])
        for i in range(n_rows):
            if self.y < BOTTOM:
                self.new_page()
                self._header(col_labels, paired, col_x)
            label, kind, indent, _ = rows_by_col[0][i]
            self.text(40 + indent * 10, label)
            for ci, rows in enumerate(rows_by_col):
                val = rows[i][3]
                if kind == "head" or val is None:
                    continue
                if paired:
                    xd, xt = PAIRED_X[ci]
                    if kind == "total":
                        self.text(xt, fmt(val), align="right")
                    elif kind == "detail":
                        self.text(xd, fmt(val), align="right")
                    elif kind == "contra":
                        self.text(xd, fmt(val[0]), align="right")
                        self.text(xt, fmt(val[1]), align="right")
                else:
                    v = val[0] if kind == "contra" else val  # 단일열: 차감계정은 차감액 표시
                    self.text(col_x[ci], fmt(v), align="right")
            self.newline()
        self.newline(10)
        self.text(PAGE_W / 2, "별첨 주석은 본 재무제표의 일부입니다.", size=8, align="center")
        self.new_page()

    def _header(self, col_labels, paired, col_x):
        self.c.line(35, self.y + 10, 560, self.y + 10)
        self.text(110, "과 목", align="center")
        for ci, lab in enumerate(col_labels):
            x = (PAIRED_X[ci][0] + PAIRED_X[ci][1]) / 2 - 30 if paired else col_x[ci] - 35
            self.text(x, lab, align="center")
        self.newline(6)
        self.c.line(35, self.y, 560, self.y)
        self.newline(12)

    def save(self):
        self.c.save()


def _scale(rows: list, k: int) -> list:
    out = []
    for label, kind, indent, v in rows:
        if v is None:
            out.append((label, kind, indent, v))
        elif kind == "contra":
            out.append((label, kind, indent, (v[0] * k, v[1] * k)))
        else:
            out.append((label, kind, indent, v * k))
    return out


def two_year_pdf(path: str, year: int, data: dict, unit: str, include_cf: bool):
    k = 1 if unit == "천원" else 1000
    cur, prev = data[year], data[year - 1] if year - 1 in data else None
    no_c, no_p = PERIOD_NO[year], PERIOD_NO[year] - 1
    from .sample_company import END  # 기초 재고 (2021) 참조
    def prev_end(key, y):
        return data[y - 1][key] if (y - 1) in data else END[key][y - 1]

    w = StatementWriter(path)
    labels = [f"제 {no_c}(당) 기", f"제 {no_p}(전) 기"]
    w.statement(
        "재 무 상 태 표",
        [f"제 {no_c}(당) 기 {year}년 12월 31일 현재", f"제 {no_p}(전) 기 {year - 1}년 12월 31일 현재"],
        unit, labels, [_scale(bs_rows(cur), k), _scale(bs_rows(prev), k)],
    )
    period = [f"제 {no_c}(당) 기 {year}년 1월 1일부터 {year}년 12월 31일까지",
              f"제 {no_p}(전) 기 {year - 1}년 1월 1일부터 {year - 1}년 12월 31일까지"]
    w.statement(
        "손 익 계 산 서", period, unit, labels,
        [_scale(is_rows(cur, prev_end("fg_inv", year), prev_end("merch_inv", year)), k),
         _scale(is_rows(prev, prev_end("fg_inv", year - 1), prev_end("merch_inv", year - 1)), k)],
    )
    w.statement(
        "제 조 원 가 명 세 서", period, unit, labels,
        [_scale(cogs_rows(cur, prev_end("raw_inv", year), prev_end("wip_inv", year)), k),
         _scale(cogs_rows(prev, prev_end("raw_inv", year - 1), prev_end("wip_inv", year - 1)), k)],
    )
    if include_cf:
        w.statement("현 금 흐 름 표", period, unit, labels, [_scale(cf_rows(cur), k), _scale(cf_rows(prev), k)])
    w.save()


def three_year_single_pdf(path: str, data: dict):
    """한 파일에 3개년 (단일열 형식, 단위 원). 재무상태표·손익계산서만."""
    from .sample_company import END
    years = [2025, 2024, 2023]
    col_x = [330, 445, 555]
    w = StatementWriter(path)
    labels = [f"{y}년" for y in years]
    w.statement("재 무 상 태 표", [], "원", labels,
                [_scale(bs_rows(data[y]), 1000) for y in years], paired=False, col_x=col_x)
    w.statement("손 익 계 산 서", [], "원", labels,
                [_scale(is_rows(data[y], data[y - 1]["fg_inv"] if y - 1 in data else END["fg_inv"][y - 1],
                                data[y - 1]["merch_inv"] if y - 1 in data else END["merch_inv"][y - 1]), 1000)
                 for y in years], paired=False, col_x=col_x)
    w.save()


def generate(out_dir: str = OUT_DIR) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    data = build()
    files = []
    for year, unit, cf in ((2023, "천원", False), (2024, "천원", False), (2025, "원", True)):
        path = os.path.join(out_dir, f"{year}년_재무제표_케이씨정밀.pdf")
        two_year_pdf(path, year, data, unit, cf)
        files.append(path)
    path = os.path.join(out_dir, "3개년_통합_재무제표_케이씨정밀.pdf")
    three_year_single_pdf(path, data)
    files.append(path)
    return files


if __name__ == "__main__":
    for f in generate():
        print("생성:", f)
