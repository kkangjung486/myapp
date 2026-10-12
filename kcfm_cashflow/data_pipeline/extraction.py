"""PDF 파싱 결과 → '재무제표 추출 결과 확인' 표(DataFrame).

- 모든 숫자는 '원' 단위로 환산하여 저장한다 (원본 표기 숫자·단위도 함께 보관).
- extracted_won(원본 추출값)은 절대 수정하지 않고, 사용자가 고치는 값은 confirmed_won에 저장한다.
- 같은 연도가 여러 PDF에 있으면(예: 2024년이 2024년 PDF의 당기, 2025년 PDF의 전기) 당기 자료를 우선 사용하고
  두 자료의 주요 합계를 서로 대조한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from account_mapper.mapper import (
    Mapping,
    apply_sign_rules,
    contra_target,
    detect_subtotals,
    is_contra_name,
    map_account,
    normalize_name,
    section_of,
)
from config.accounts import BY_CODE, label_of
from pdf_parser.models import STATEMENT_NAMES, ParsedDocument, StatementBlock
from pdf_parser.numbers import UNIT_MULTIPLIERS

COLUMNS = [
    "row_id", "file", "block", "statement", "statement_name", "page", "order", "col", "year", "role",
    "label", "norm", "raw_text", "unit", "extracted_won", "confirmed_won", "std_label", "include",
    "status", "note", "confidence", "source",
]

STATUS_AUTO = "자동 인식"
STATUS_SIMILAR = "자동(유사 명칭)"
STATUS_REVIEW = "확인 필요"
STATUS_SUBTOTAL = "소계 제외"
STATUS_EDITED = "수정됨"
STATUS_MANUAL = "수동 추가"

KEY_TOTALS = {"BS": ["TOTAL_ASSETS", "TOTAL_LIAB", "TOTAL_EQUITY"], "IS": ["REVENUE", "NET_INCOME"],
              "COGS": ["PURCHASE_RAW"], "CF": ["CFO"]}


@dataclass
class BlockMeta:
    """파일·표별 인식 정보 (사용자가 단위·연도를 수정할 수 있음)."""
    file: str
    block: int
    statement: str
    unit: str
    unit_source: str
    years: list[int | None]
    year_source: str
    layout: str
    pages: list[int]
    warnings: list[str] = field(default_factory=list)


def block_metas(docs: list[ParsedDocument]) -> list[BlockMeta]:
    metas = []
    for doc in docs:
        for i, b in enumerate(doc.blocks):
            metas.append(BlockMeta(doc.filename, i, b.statement, b.unit, b.unit_source, list(b.years),
                                   b.year_source, b.layout, b.pages, list(b.warnings)))
    return metas


def build_rows(docs: list[ParsedDocument], metas: list[BlockMeta], industry: str) -> pd.DataFrame:
    meta_by_key = {(m.file, m.block): m for m in metas}
    rows: list[dict] = []
    for doc in docs:
        for b_idx, block in enumerate(doc.blocks):
            meta = meta_by_key[(doc.filename, b_idx)]
            ocr_pages = {p for p, s in doc.page_sources.items() if s == "ocr"}
            rows.extend(_block_rows(doc.filename, b_idx, block, meta, industry, ocr_pages))
    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df["year"] = df["year"].astype("Int64")
    return df


def _block_rows(file: str, b_idx: int, block: StatementBlock, meta: BlockMeta, industry: str,
                ocr_pages: set[int]) -> list[dict]:
    mult = UNIT_MULTIPLIERS[meta.unit]
    section = None
    anchor: tuple[str, str, str | None] | None = None   # (code, label, suggestion)
    mapped = []
    for line in block.lines:
        norm = normalize_name(line.label)
        if block.statement == "BS":
            section = section_of(norm) or section
        m = map_account(norm, block.statement, section, industry)
        contra = False
        if block.statement == "BS" and is_contra_name(norm) and anchor is not None:
            tgt = contra_target(norm, anchor[0])
            if tgt:
                contra = True
                m = Mapping(tgt, "중간", tgt == "UNMAPPED", anchor[2],
                            [f"차감계정 – 바로 위 '{anchor[1]}'에서 차감"])
        if line.amounts and not contra:
            anchor = (m.code, line.label, m.suggestion)
        mapped.append((line, norm, m, contra))

    out: list[dict] = []
    for g, year in enumerate(meta.years):
        seq: list[dict] = []
        for line, norm, m, contra in mapped:
            if g not in line.amounts:
                continue
            notes = list(m.notes) + list(line.issues)
            if m.code == "UNMAPPED" and m.suggestion and not any("제안" in n for n in notes):
                notes.append(f"제안: {label_of(m.suggestion)}")
            r = {
                "norm": norm, "label": line.label, "amount": line.amounts[g], "code": m.code,
                "confidence": m.confidence, "needs_review": m.needs_review, "notes": notes,
                "is_contra": contra, "total_col": line.total_col.get(g, False), "is_subtotal": False,
                "page": line.page, "order": line.order, "raw": line.raw_amounts.get(g, ""),
            }
            if line.page in ocr_pages:
                r["needs_review"] = True
                r["confidence"] = "낮음"
                r["notes"].append("OCR 인식값 – 원본 대조 필요")
            apply_sign_rules(r)
            seq.append(r)
        detect_subtotals(seq, tolerance=2.0)
        for r in seq:
            code = "SUBTOTAL" if r["is_subtotal"] else r["code"]
            kind = BY_CODE[code].kind
            if r["is_subtotal"]:
                status = STATUS_SUBTOTAL if not r["needs_review"] else STATUS_REVIEW
            elif r["needs_review"]:
                status = STATUS_REVIEW
            elif r["confidence"] == "중간":
                status = STATUS_SIMILAR
            else:
                status = STATUS_AUTO
            won = r["amount"] * mult
            out.append({
                "row_id": f"{file}#{b_idx}#{r['order']}#{g}",
                "file": file, "block": b_idx, "statement": block.statement,
                "statement_name": STATEMENT_NAMES[block.statement], "page": r["page"], "order": r["order"],
                "col": g, "year": year, "role": "당기" if g == 0 else f"비교{g}",
                "label": r["label"], "norm": r["norm"], "raw_text": r["raw"], "unit": meta.unit,
                "extracted_won": won, "confirmed_won": won, "std_label": label_of(code),
                "include": kind != "excluded", "status": status, "note": "; ".join(r["notes"]),
                "confidence": r["confidence"], "source": "PDF",
            })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 연도별 자료 선택 (같은 연도가 여러 PDF에 있을 때)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SourceChoice:
    statement: str
    year: int
    file: str
    block: int
    col: int
    alternatives: list[tuple[str, int, int]]


def select_sources(df: pd.DataFrame) -> tuple[pd.DataFrame, list[SourceChoice], list[str]]:
    """(재무제표, 연도)마다 하나의 출처를 고른다. 당기(가장 왼쪽 열) 자료를 우선한다."""
    warnings: list[str] = []
    if df.empty:
        return df, [], warnings
    known = df[df["year"].notna()]
    if len(known) < len(df):
        warnings.append("연도를 인식하지 못한 표가 있어 제외했습니다. '파일별 인식 정보'에서 연도를 입력하세요.")
    file_order = {f: i for i, f in enumerate(dict.fromkeys(df["file"]))}
    choices: list[SourceChoice] = []
    keep_ids: list[pd.Index] = []
    cand = (known.groupby(["statement", "year", "file", "block", "col"]).size().reset_index()
            .drop(columns=0))
    for (stmt, year), g in cand.groupby(["statement", "year"]):
        g = g.assign(fo=g["file"].map(file_order)).sort_values(["col", "fo"])
        best = g.iloc[0]
        alts = [(r.file, int(r.block), int(r.col)) for r in g.iloc[1:].itertuples()]
        if len(g) > 1 and int(g.iloc[1]["col"]) == int(best["col"]):
            warnings.append(
                f"{int(year)}년 {STATEMENT_NAMES[stmt]}가 같은 위치(당기/전기)로 여러 파일에 있습니다 "
                f"({best['file']}, {g.iloc[1]['file']}). 첫 번째 파일을 사용합니다 – 중복 업로드인지 확인하세요."
            )
        choices.append(SourceChoice(stmt, int(year), best["file"], int(best["block"]), int(best["col"]), alts))
        sel = known[(known["statement"] == stmt) & (known["year"] == year) & (known["file"] == best["file"])
                    & (known["block"] == best["block"]) & (known["col"] == best["col"])]
        keep_ids.append(sel.index)
        warnings.extend(_cross_check(known, stmt, int(year), best, alts))
    idx = keep_ids[0].append(keep_ids[1:]) if keep_ids else pd.Index([])
    selected = df.loc[idx].sort_values(["year", "statement", "file", "block", "order"])
    return selected.reset_index(drop=True), choices, warnings


def _cross_check(df: pd.DataFrame, stmt: str, year: int, best, alts) -> list[str]:
    out = []
    for code in KEY_TOTALS.get(stmt, []):
        label = label_of(code)

        def value(file, block, col):
            r = df[(df["file"] == file) & (df["block"] == block) & (df["col"] == col) & (df["std_label"] == label)]
            return None if r.empty else float(r.iloc[0]["extracted_won"])

        base = value(best["file"], best["block"], best["col"])
        for f, b, c in alts:
            other = value(f, b, c)
            if base is None or other is None:
                continue
            tol = max(abs(base) * 0.0005, 3_000)
            if abs(base - other) > tol:
                out.append(
                    f"[대조 불일치] {year}년 {label}: '{best['file']}' {base:,.0f}원 vs '{f}' {other:,.0f}원 "
                    "– 전기 재작성(수정)이거나 추출 오류일 수 있습니다."
                )
    return out


def default_analysis_years(selected: pd.DataFrame, n: int = 3) -> list[int]:
    if selected.empty:
        return []
    is_years = sorted({int(y) for y in selected.loc[selected["statement"] == "IS", "year"].dropna()})
    years = is_years or sorted({int(y) for y in selected["year"].dropna()})
    return years[-n:]


def new_manual_row(year: int, statement: str = "BS") -> dict:
    return {
        "row_id": f"manual#{year}#{pd.Timestamp.now().value}", "file": "(수동 입력)", "block": -1,
        "statement": statement, "statement_name": STATEMENT_NAMES.get(statement, statement), "page": None,
        "order": 9999, "col": 0, "year": year, "role": "수동", "label": "", "norm": "", "raw_text": "",
        "unit": "원", "extracted_won": None, "confirmed_won": None, "std_label": label_of("UNMAPPED"),
        "include": True, "status": STATUS_MANUAL, "note": "", "confidence": "수동", "source": "수동",
    }
