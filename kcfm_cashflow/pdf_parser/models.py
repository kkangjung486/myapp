"""PDF 파싱 결과 데이터 구조. (계산 모듈과 완전히 분리)"""
from __future__ import annotations

from dataclasses import dataclass, field

STATEMENT_NAMES = {
    "BS": "재무상태표",
    "IS": "손익계산서",
    "COGS": "원가명세서",
    "CF": "현금흐름표",
}


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class PageWords:
    page_no: int            # 1부터 시작
    width: float
    words: list[Word]
    source: str             # "text"(텍스트 레이어) | "ocr" | "none"(추출 불가)


@dataclass
class ParsedLine:
    page: int
    order: int                          # 블록 안에서의 순서
    label: str                          # 원본 계정명 (번호 포함)
    amounts: dict[int, float] = field(default_factory=dict)       # 열그룹 → 금액(문서 단위)
    raw_amounts: dict[int, str] = field(default_factory=dict)     # 열그룹 → 원문 숫자
    secondary: dict[int, float] = field(default_factory=dict)     # 같은 열그룹 오른쪽 숫자(소계열)
    total_col: dict[int, bool] = field(default_factory=dict)      # 2열 형식에서 합계열(오른쪽)에만 숫자가 있는지
    issues: list[str] = field(default_factory=list)


@dataclass
class StatementBlock:
    statement: str                      # BS / IS / COGS / CF
    title: str
    unit: str = "원"
    unit_source: str = "미확인"          # "표에서 인식" | "문서 내 다른 표" | "미확인"
    years: list[int | None] = field(default_factory=list)   # 열그룹 순서(왼→오른쪽)별 사업연도
    year_source: str = "미확인"
    layout: str = "single"              # single(연도별 1열) | paired(연도별 2열: 세부/합계)
    lines: list[ParsedLine] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return STATEMENT_NAMES.get(self.statement, self.statement)


@dataclass
class ParsedDocument:
    filename: str
    company_name: str | None = None
    periods: dict[int, int] = field(default_factory=dict)   # 기수 → 사업연도
    blocks: list[StatementBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    page_sources: dict[int, str] = field(default_factory=dict)
    document_unit: str | None = None

    @property
    def ocr_used(self) -> bool:
        return any(s == "ocr" for s in self.page_sources.values())

    @property
    def unreadable_pages(self) -> list[int]:
        return [p for p, s in self.page_sources.items() if s == "none"]
