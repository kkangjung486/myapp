"""검증 화면에서 사용자가 수정한 내용 반영.

원본 추출값(extracted_won)은 그대로 두고 confirmed_won·표준계정·포함여부만 바뀐다.
바뀐 행은 상태를 '수정됨', 새로 추가한 행은 '수동 추가'로 표시한다.
"""
from __future__ import annotations

import pandas as pd

from account_mapper.mapper import normalize_name
from config.accounts import BY_LABEL
from pdf_parser.models import STATEMENT_NAMES

from .extraction import STATUS_EDITED, STATUS_MANUAL

NAME_TO_STATEMENT = {v: k for k, v in STATEMENT_NAMES.items()}


def apply_edits(base: pd.DataFrame, edited: pd.DataFrame, year: int) -> pd.DataFrame:
    out = edited.copy()
    base_by_id = base.set_index("row_id") if not base.empty else pd.DataFrame()
    for i in out.index:
        rid = out.at[i, "row_id"]
        is_new = not isinstance(rid, str) or rid not in base_by_id.index
        if is_new:
            out.at[i, "row_id"] = f"manual#{year}#{i}"
            out.at[i, "file"] = "(수동 입력)"
            out.at[i, "block"] = -1
            out.at[i, "order"] = 10_000 + i
            out.at[i, "col"] = 0
            out.at[i, "year"] = year
            out.at[i, "role"] = "수동"
            out.at[i, "unit"] = "원"
            out.at[i, "extracted_won"] = None
            out.at[i, "source"] = "수동"
            out.at[i, "confidence"] = "수동"
            out.at[i, "status"] = STATUS_MANUAL
            if pd.isna(out.at[i, "include"]):
                out.at[i, "include"] = True
            if not isinstance(out.at[i, "statement_name"], str):
                out.at[i, "statement_name"] = STATEMENT_NAMES["BS"]
        else:
            b = base_by_id.loc[rid]
            # 표준 계정을 바꿨는데 '분석 포함'은 그대로라면 계정 종류에 맞춰 자동 조정
            # (예: 미분류 → 기타영업유동자산 선택 시 포함, '제외' 선택 시 미포함)
            if out.at[i, "std_label"] != b["std_label"] and bool(out.at[i, "include"]) == bool(b["include"]):
                out.at[i, "include"] = BY_LABEL[out.at[i, "std_label"]].kind != "excluded" \
                    if out.at[i, "std_label"] in BY_LABEL else bool(out.at[i, "include"])
            changed = (
                not _same_num(out.at[i, "confirmed_won"], b["confirmed_won"])
                or out.at[i, "std_label"] != b["std_label"]
                or bool(out.at[i, "include"]) != bool(b["include"])
                or out.at[i, "statement_name"] != b["statement_name"]
                or str(out.at[i, "label"]) != str(b["label"])
            )
            if changed:
                out.at[i, "status"] = STATUS_EDITED
        out.at[i, "statement"] = NAME_TO_STATEMENT.get(out.at[i, "statement_name"], "BS")
        out.at[i, "norm"] = normalize_name(out.at[i, "label"])
    out["include"] = out["include"].fillna(False).astype(bool)
    out["year"] = out["year"].astype("Int64")
    return out


def _same_num(a, b) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(float(a) - float(b)) < 0.5
