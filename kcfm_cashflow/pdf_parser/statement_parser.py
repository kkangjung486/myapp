"""재무제표 PDF 레이아웃 해석.

핵심 아이디어
1) 단어 좌표(y)로 줄을 만들고, 제목줄로 재무제표 종류(재무상태표/손익계산서/원가명세서/현금흐름표)를 구분한다.
2) 표 머리글에서 회계기간(제N기, 연도)과 단위를 찾는다.
3) 숫자의 오른쪽 끝 x좌표를 군집화해서 '금액 열'을 찾는다.
   - 한국 재무제표는 연도별로 [세부금액 | 합계금액] 2열 구조(paired)인 경우가 많다.
   - 열 군집을 연도 수(n)만큼 큰 간격 기준으로 묶어 '연도 열그룹'을 만든다.
4) 각 줄의 숫자를 가장 가까운 열에 배정한다. 같은 연도 그룹에 숫자가 2개면
   왼쪽(세부금액, 예: 대손충당금 (3,000))을 그 줄의 금액으로 쓰고 오른쪽(순액)은 참고로 보관한다.

이 모듈은 '숫자를 읽어오는 일'만 한다. 계정 분류·계산은 다른 모듈이 담당한다.
"""
from __future__ import annotations

import re
from collections import Counter

from .models import PageWords, ParsedDocument, ParsedLine, StatementBlock, Word
from .numbers import detect_unit, is_dash, looks_like_amount, parse_amount
from .text_layer import extract_pages

HANGUL_RE = re.compile(r"[가-힣]")

TITLES: list[tuple[str | None, list[str]]] = [
    ("BS", ["재무상태표", "대차대조표"]),
    ("IS", ["포괄손익계산서", "손익계산서"]),
    ("COGS", ["제조원가명세서", "공사원가명세서", "용역원가명세서", "매출원가명세서",
              "분양원가명세서", "원가명세서"]),
    ("CF", ["현금흐름표"]),
    (None, ["이익잉여금처분계산서", "결손금처리계산서", "이익잉여금처분계산서(안)", "자본변동표",
            "재무제표에대한주석", "주석"]),
]
_TITLE_PREFIXES = ("요약", "별첨", "개별", "별도", "첨부")

PERIOD_RE = re.compile(r"제\s*(\d{1,3})\s*(?:\(\s*(당|전전|전)\s*\)\s*)?기")
DATE_RE = re.compile(r"((?:19|20)\d{2})\s*[년.\-/]\s*(\d{1,2})\s*[월.\-/]\s*(\d{1,2})")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
HEADER_WORDS_RE = re.compile(r"부터|까지|현재|단\s*위|회\s*사\s*명")
COLUMN_HEADER_LABELS = {"과목", "계정과목", "구분", "주석", "과목주석"}
FILENAME_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

COMPANY_RE1 = re.compile(r"회\s*사\s*명\s*[:：]\s*(.+?)(?:\s{2,}|\(\s*단\s*위|$)")
COMPANY_RE2 = re.compile(
    r"(주식회사\s*[가-힣A-Za-z0-9&]+|[가-힣A-Za-z0-9&]+\s*주식회사|\(주\)\s*[가-힣A-Za-z0-9&]+|[가-힣A-Za-z0-9&]+\s*\(주\))"
)

CLUSTER_GAP = 15.0       # 같은 열로 볼 오른쪽 끝 x좌표 최대 간격(pt)
ASSIGN_DISTANCE = 28.0   # 숫자를 열에 배정할 때 허용 거리(pt)


# ─────────────────────────────────────────────────────────────────────────────
# 줄 만들기
# ─────────────────────────────────────────────────────────────────────────────
class Line:
    def __init__(self, page: int, words: list[Word]):
        self.page = page
        self.words = sorted(words, key=lambda w: w.x0)
        self.words = _merge_tokens(self.words)
        self.y = sum(w.yc for w in self.words) / len(self.words)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def compact(self) -> str:
        return re.sub(r"\s+", "", self.text)


def _merge_tokens(words: list[Word]) -> list[Word]:
    """'( 15,000 )', '△ 15,000', '1, 234' 처럼 쪼개진 숫자 토큰을 합친다."""
    out: list[Word] = []
    for w in words:
        if out:
            prev = out[-1]
            gap = w.x0 - prev.x1
            joinable = gap < 6
            if joinable and (
                prev.text in ("(", "（", "△", "▲", "-", "－")
                and re.match(r"^[\d,\.]+[\)）]?$", w.text)
                or (w.text in (")", "）") and re.search(r"\d$", prev.text))
                or (prev.text.endswith(",") and re.match(r"^\d{3}", w.text))
            ):
                out[-1] = Word(prev.text + w.text, prev.x0, min(prev.y0, w.y0), w.x1, max(prev.y1, w.y1))
                continue
        out.append(w)
    return out


def build_lines(page: PageWords) -> list[Line]:
    if not page.words:
        return []
    words = sorted(page.words, key=lambda w: (w.yc, w.x0))
    heights = sorted(w.y1 - w.y0 for w in words)
    tol = max(2.5, 0.4 * heights[len(heights) // 2])
    groups: list[list[Word]] = []
    current: list[Word] = []
    cur_y = None
    for w in words:
        if cur_y is None or abs(w.yc - cur_y) <= tol:
            current.append(w)
            cur_y = sum(x.yc for x in current) / len(current)
        else:
            groups.append(current)
            current, cur_y = [w], w.yc
    if current:
        groups.append(current)
    return [Line(page.page_no, g) for g in groups]


# ─────────────────────────────────────────────────────────────────────────────
# 제목 / 기간 / 머리글 인식
# ─────────────────────────────────────────────────────────────────────────────
def detect_title(line: Line) -> tuple[str | None, bool] | None:
    """제목줄이면 (재무제표코드 또는 None(분석 대상 아님), 계속여부) 반환."""
    norm = re.sub(r"[\s\[\]<>【】「」〈〉]", "", line.text)
    for prefix in _TITLE_PREFIXES:
        if norm.startswith(prefix):
            norm = norm[len(prefix):]
    for stmt, names in TITLES:
        for nm in names:
            if not norm.startswith(nm):
                continue
            rest = norm[len(nm):]
            if rest == "" or rest[0] in "(（-–" or rest.startswith(("제", "계속")) or rest[0].isdigit():
                if nm == "주석" and rest and not rest.startswith(("(", "（")):
                    continue
                return stmt, "계속" in rest
    return None


def parse_period_line(text: str) -> list[tuple[int | None, int | None, str | None]]:
    """'제15(당)기 2025년 1월 1일부터 2025년 12월 31일까지' → [(15, 2025, '당')].

    사업연도는 기간의 '종료일' 연도로 정한다 (7월 결산 등 비역년 회계도 처리).
    """
    results: list[tuple[int | None, int | None, str | None]] = []
    matches = list(PERIOD_RE.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            dates = DATE_RE.findall(text[m.end():end])
            year = int(dates[-1][0]) if dates else None
            results.append((int(m.group(1)), year, m.group(2)))
    elif HEADER_WORDS_RE.search(text):
        # '2025년 12월 31일 현재' 처럼 기수 없이 날짜만 있는 줄
        dates = DATE_RE.findall(text)
        if dates and re.search(r"현재|까지", text):
            results.append((None, int(dates[-1][0]), None))
    return results


def _column_header_years(line: Line, periods_by_num: dict[int, int],
                         role_years: dict[str, int]) -> list[tuple[float, int]]:
    """표 머리글 줄에서 (x중심, 연도) 목록을 찾는다. 예: '과목 제15(당)기 제14(전)기'."""
    text, spans, pos = "", [], 0
    for w in line.words:
        spans.append((pos, pos + len(w.text), w))
        text += w.text + " "
        pos += len(w.text) + 1

    def word_at(idx: int) -> Word:
        for s, e, w in spans:
            if s <= idx < e + 1:
                return w
        return spans[-1][2]

    found: list[tuple[float, int]] = []
    for m in PERIOD_RE.finditer(text):
        num = int(m.group(1))
        year = periods_by_num.get(num)
        if year is None and m.group(2):
            year = role_years.get(m.group(2))
        if year:
            a, b = word_at(m.start()), word_at(m.end() - 1)
            found.append(((a.x0 + b.x1) / 2, year))
    if not found:
        for m in YEAR_RE.finditer(text):
            a, b = word_at(m.start()), word_at(m.end() - 1)
            found.append(((a.x0 + b.x1) / 2, int(m.group(1))))
    if not found:
        for m in re.finditer(r"(당|전)\s*기", text):
            year = role_years.get(m.group(1))
            if year:
                a, b = word_at(m.start()), word_at(m.end() - 1)
                found.append(((a.x0 + b.x1) / 2, year))
    return found


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 줄 해석
# ─────────────────────────────────────────────────────────────────────────────
def _split_label_numbers(line: Line) -> tuple[str, list[Word]] | None:
    """줄을 (계정명, 숫자토큰목록)으로 나눈다. 한글 계정명이 없으면 None."""
    first_hangul = next((i for i, w in enumerate(line.words) if HANGUL_RE.search(w.text)), None)
    if first_hangul is None:
        return None
    numbers: list[Word] = []
    label_words: list[Word] = []
    for i, w in enumerate(line.words):
        is_num = parse_amount(w.text) is not None or is_dash(w.text)
        if i > first_hangul and is_num:
            numbers.append(w)
        elif not numbers:
            label_words.append(w)
    label = " ".join(w.text for w in label_words).strip()
    return label, numbers


def _is_header_line(line: Line) -> bool:
    if HEADER_WORDS_RE.search(line.text):
        return True
    if PERIOD_RE.search(line.text) and DATE_RE.search(line.text):
        return True
    compact = line.compact
    return any(compact.startswith(h) for h in ("과목", "계정과목")) and not re.search(r"\d,\d{3}", compact)


def _cluster(xs: list[tuple[float, Word]]) -> list[list[tuple[float, Word]]]:
    xs = sorted(xs, key=lambda t: t[0])
    clusters: list[list[tuple[float, Word]]] = []
    for item in xs:
        if clusters and item[0] - clusters[-1][-1][0] <= CLUSTER_GAP:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


class _Columns:
    """한 페이지 구간의 금액 열 정보."""

    def __init__(self, centers: list[float], group_of: list[int], n_groups: int):
        self.centers = centers          # 각 열의 오른쪽 끝 x (중앙값)
        self.group_of = group_of        # 열 index → 연도 그룹 index
        self.n_groups = n_groups

    @property
    def paired(self) -> bool:
        return len(self.centers) > self.n_groups

    def assign(self, w: Word) -> int | None:
        if not self.centers:
            return None
        dists = [abs(w.x1 - c) for c in self.centers]
        i = min(range(len(dists)), key=dists.__getitem__)
        return i if dists[i] <= ASSIGN_DISTANCE else None


def _detect_columns(numeric_tokens: list[Word], n_groups_hint: int | None,
                    header_xs: list[float]) -> _Columns | None:
    raw = _cluster([(w.x1, w) for w in numeric_tokens])
    kept = []
    for c in raw:
        ratio = sum(looks_like_amount(w.text) for _, w in c) / len(c)
        if ratio >= 0.5:
            xs = sorted(x for x, _ in c)
            kept.append(xs[len(xs) // 2])
    if not kept:
        return None
    k = len(kept)
    if n_groups_hint:
        n = min(n_groups_hint, k)
    elif k >= 4 and k % 2 == 0:
        n = k // 2
    else:
        n = k

    if k == n:
        group_of = list(range(k))
    elif header_xs and len(header_xs) == n:
        # 머리글 위치가 있으면: 가장 가까운 머리글의 연도그룹에 배정
        hx = sorted(header_xs)
        group_of = [min(range(n), key=lambda g: abs(hx[g] - c)) for c in kept]
    else:
        # 큰 간격 n-1개를 기준으로 열을 n개 그룹으로 나눈다
        gaps = sorted(range(k - 1), key=lambda i: kept[i + 1] - kept[i], reverse=True)[: n - 1]
        cut = set(gaps)
        group_of, g = [], 0
        for i in range(k):
            group_of.append(g)
            if i in cut:
                g += 1
    return _Columns(kept, group_of, n)


# ─────────────────────────────────────────────────────────────────────────────
# 문서 전체 해석
# ─────────────────────────────────────────────────────────────────────────────
def parse_pdf(pdf_bytes: bytes, filename: str = "document.pdf", use_ocr: bool = True) -> ParsedDocument:
    pages = extract_pages(pdf_bytes, use_ocr=use_ocr)
    return parse_pages(pages, filename)


def parse_pages(pages: list[PageWords], filename: str = "document.pdf") -> ParsedDocument:
    doc = ParsedDocument(filename=filename)
    doc.page_sources = {p.page_no: p.source for p in pages}
    if doc.unreadable_pages:
        doc.warnings.append(
            f"텍스트를 읽을 수 없는 페이지(스캔본 추정): {doc.unreadable_pages}. "
            "OCR(Tesseract)이 설치되어 있지 않거나 인식에 실패했습니다. 검증 화면에서 수동 입력하세요."
        )
    if doc.ocr_used:
        doc.warnings.append("일부 페이지는 OCR로 읽었습니다. OCR 숫자는 모두 원본과 대조해 주세요.")

    all_lines: list[Line] = []
    for p in pages:
        all_lines.extend(build_lines(p))

    company_votes: Counter[str] = Counter()
    for ln in all_lines[:400]:
        m = COMPANY_RE1.search(ln.text)
        if m:
            company_votes[m.group(1).strip()] += 3
        for m in COMPANY_RE2.finditer(ln.text):
            company_votes[re.sub(r"\s+", " ", m.group(1)).strip()] += 1
        if doc.document_unit is None:
            doc.document_unit = detect_unit(ln.text)
    if company_votes:
        doc.company_name = company_votes.most_common(1)[0][0]

    # 1) 제목 기준으로 블록 나누기
    segments: list[tuple[StatementBlock, list[Line]]] = []
    current: tuple[StatementBlock, list[Line]] | None = None
    for ln in all_lines:
        t = detect_title(ln)
        if t is not None:
            stmt, is_cont = t
            if stmt is None:
                # 주석/자본변동표 등 → 분석 블록 종료 (단, '주석' 열머리글 오인 방지)
                if current and sum(1 for x in current[1] if re.search(r"\d,\d{3}", x.text)) >= 3:
                    current = None
                continue
            if is_cont and current and current[0].statement == stmt:
                continue
            block = StatementBlock(statement=stmt, title=ln.text.strip())
            current = (block, [])
            segments.append(current)
            continue
        if current is not None:
            current[1].append(ln)

    # 2) 블록별 해석
    file_year = None
    fy = FILENAME_YEAR_RE.findall(filename)
    if fy:
        file_year = int(fy[-1])
    for block, lines in segments:
        _parse_block(block, lines, doc, file_year)
        if any(l.amounts for l in block.lines):
            doc.blocks.append(block)

    if not doc.blocks:
        doc.warnings.append(
            "재무상태표·손익계산서 등 재무제표 표를 찾지 못했습니다. 제목(예: '재무상태표')이 "
            "인식되지 않았거나 스캔본일 수 있습니다. 검증 화면에서 직접 입력할 수 있습니다."
        )
    found = {b.statement for b in doc.blocks}
    for code, nm in (("BS", "재무상태표"), ("IS", "손익계산서")):
        if code not in found and doc.blocks:
            doc.warnings.append(f"{nm}를 찾지 못했습니다.")
    return doc


def _parse_block(block: StatementBlock, lines: list[Line], doc: ParsedDocument, file_year: int | None) -> None:
    # (a) 머리글 영역: 첫 데이터 줄 전까지
    block_periods: list[tuple[int | None, int | None, str | None]] = []
    header_cols: list[tuple[float, int]] = []
    first_data_idx = len(lines)
    for i, ln in enumerate(lines):
        if not _is_header_line(ln):
            sp = _split_label_numbers(ln)
            if sp and any(looks_like_amount(w.text) for w in sp[1]):
                first_data_idx = i
                break
    header_lines = lines[:first_data_idx]
    for ln in header_lines:
        u = detect_unit(ln.text)
        if u:
            block.unit, block.unit_source = u, "표에서 인식"
        for num, year, role in parse_period_line(ln.text):
            block_periods.append((num, year, role))
            if num is not None and year is not None:
                doc.periods[num] = year
    # 단위가 머리글이 아닌 곳(표 하단 등)에 있는 경우도 찾는다
    if block.unit_source == "미확인":
        for ln in lines:
            u = detect_unit(ln.text)
            if u:
                block.unit, block.unit_source = u, "표에서 인식"
                break
    if block.unit_source == "미확인" and doc.document_unit:
        block.unit, block.unit_source = doc.document_unit, "문서 내 다른 표"
    if block.unit_source == "미확인":
        block.warnings.append("단위 표기를 찾지 못해 '원'으로 가정했습니다. 반드시 확인하세요.")

    role_years: dict[str, int] = {}
    for num, year, role in block_periods:
        if role and year:
            role_years[role] = year
    for ln in header_lines:
        if HEADER_WORDS_RE.search(ln.text):
            continue
        cols = _column_header_years(ln, doc.periods, role_years)
        if len({y for _, y in cols}) >= 2 or (len(cols) == 1 and not header_cols):
            header_cols = cols

    # (b) 연도 그룹 수 추정
    distinct_header_years = list(dict.fromkeys(y for _, y in sorted(header_cols)))
    period_years = [y for _, y, _ in block_periods if y]
    if len(distinct_header_years) >= 2:
        n_hint = len(distinct_header_years)
    elif len(period_years) >= 1:
        n_hint = len(period_years)
    else:
        n_hint = None

    # (c) 페이지 구간별로 열 인식 후 숫자 배정
    parsed: list[ParsedLine] = []
    order = 0
    last_cols: _Columns | None = None
    pages = sorted({ln.page for ln in lines})
    block.pages = pages
    n_groups_seen = None
    for page in pages:
        page_lines = [ln for i, ln in enumerate(lines) if ln.page == page and i >= first_data_idx]
        splits = []
        numeric_tokens: list[Word] = []
        for ln in page_lines:
            if _is_header_line(ln):
                continue
            sp = _split_label_numbers(ln)
            if sp is None:
                continue
            label, nums = sp
            if re.sub(r"\s", "", label) in COLUMN_HEADER_LABELS:
                continue
            splits.append((ln, label, nums))
            numeric_tokens.extend(nums)
        header_xs = [x for x, _ in header_cols] if page == pages[0] and len(header_cols) == (n_hint or 0) else []
        cols = _detect_columns(numeric_tokens, n_hint, header_xs) if len(numeric_tokens) >= 3 else None
        if cols is None:
            cols = last_cols
        if cols is None:
            continue
        last_cols = cols
        n_groups_seen = max(n_groups_seen or 0, cols.n_groups)
        if cols.paired:
            block.layout = "paired"
        for ln, label, nums in splits:
            pl = ParsedLine(page=page, order=order, label=label)
            order += 1
            per_group: dict[int, list[Word]] = {}
            for w in nums:
                ci = cols.assign(w)
                if ci is None:
                    if looks_like_amount(w.text):
                        pl.issues.append(f"열 위치를 알 수 없는 숫자 무시: {w.text}")
                    continue
                per_group.setdefault(cols.group_of[ci], []).append(w)
            for g, ws in per_group.items():
                ws.sort(key=lambda w: w.x0)
                val = parse_amount(ws[0].text)
                if val is None:
                    continue
                pl.amounts[g] = val
                pl.raw_amounts[g] = ws[0].text
                if cols.paired and len(ws) == 1:
                    group_cols = [i for i, gg in enumerate(cols.group_of) if gg == g]
                    pl.total_col[g] = len(group_cols) > 1 and cols.assign(ws[0]) == group_cols[-1]
                if len(ws) > 1:
                    sec = parse_amount(ws[-1].text)
                    if sec is not None:
                        pl.secondary[g] = sec
                if len(ws) > 2:
                    pl.issues.append("같은 연도 열에 숫자가 3개 이상 – 확인 필요")
            parsed.append(pl)
    block.lines = parsed

    # (d) 연도 그룹 → 사업연도
    n = n_groups_seen or n_hint or 0
    years: list[int | None] = []
    if len(distinct_header_years) == n and n > 0:
        years = [y for _, y in sorted(header_cols)]
        years = list(dict.fromkeys(years))
        block.year_source = "표 머리글"
    elif len(period_years) == n and n > 0:
        years = period_years
        block.year_source = "기수/기간 표기"
    elif doc.periods and len(doc.periods) >= n > 0:
        years = sorted(set(doc.periods.values()), reverse=True)[:n]
        block.year_source = "문서 내 기수 표기(추정)"
        block.warnings.append("표 머리글에서 연도를 직접 찾지 못해 문서의 다른 기수 표기로 추정했습니다.")
    elif file_year and n > 0:
        years = [file_year - i for i in range(n)]
        block.year_source = "파일명(추정)"
        block.warnings.append(f"연도 표기를 찾지 못해 파일명({file_year})으로 당기 연도를 추정했습니다. 확인 필요.")
    else:
        years = [None] * n
        block.warnings.append("사업연도를 인식하지 못했습니다. '파일별 인식 정보'에서 연도를 입력하세요.")
    if len(years) < n:
        years = years + [None] * (n - len(years))
    block.years = years[:n]
    if block.years and len(set(y for y in block.years if y)) != len([y for y in block.years if y]):
        block.warnings.append("열그룹에 같은 연도가 중복 인식되었습니다. 연도를 확인하세요.")
