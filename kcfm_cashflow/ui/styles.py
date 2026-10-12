"""화면 스타일 (금융기관 보고서 톤: 네이비·회색, 절제된 강조)."""

CSS = """
<style>
:root { --kc-navy:#1f3a5f; --kc-ink:#1f2933; --kc-muted:#5f6b7a; --kc-line:#dfe3e8; --kc-bg:#f6f8fa; }
.block-container { padding-top: 2.2rem; max-width: 1280px; }
h1, h2, h3 { color: var(--kc-navy); letter-spacing: -0.3px; }
.kc-header { border-bottom: 3px solid var(--kc-navy); padding-bottom: .5rem; margin-bottom: 1rem; }
.kc-header .title { font-size: 1.7rem; font-weight: 800; color: var(--kc-navy); }
.kc-header .sub { color: var(--kc-muted); font-size: .92rem; }
.kc-steps { display:flex; gap:.5rem; margin: .4rem 0 1.2rem 0; flex-wrap: wrap; }
.kc-step { padding:.35rem .8rem; border-radius: 4px; border:1px solid var(--kc-line); color: var(--kc-muted);
           font-size:.88rem; background:#fff; }
.kc-step.on { background: var(--kc-navy); color:#fff; border-color: var(--kc-navy); font-weight:700; }
.kc-step.done { color: var(--kc-navy); border-color: var(--kc-navy); }
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--kc-line); border-left:4px solid var(--kc-navy);
           border-radius:6px; padding: .7rem .9rem; }
div[data-testid="stMetricLabel"] p { font-weight:700; color: var(--kc-muted); }
.kc-badge { display:inline-block; padding: 2px 8px; border-radius: 3px; font-size: .78rem; font-weight: 700;
            margin-right: 6px; border:1px solid; }
.kc-badge.b0 { color:#1f5fa8; border-color:#1f5fa8; background:#eef4fb; }      /* 관찰 */
.kc-badge.b1 { color:#8a5a00; border-color:#c98500; background:#fff7e6; }      /* 주의 */
.kc-badge.b2 { color:#a32020; border-color:#c53030; background:#fdeeee; }      /* 집중점검 */
.kc-badge.est { color:#5f6b7a; border-color:#9aa5b1; background:#f3f4f6; }
.kc-badge.pub { color:#1f3a5f; border-color:#1f3a5f; background:#eef2f7; }
.kc-signal { border:1px solid var(--kc-line); border-radius:6px; padding:.7rem .9rem; margin-bottom:.55rem; background:#fff; }
.kc-signal .t { font-weight:700; color: var(--kc-ink); }
.kc-signal .d { color: var(--kc-ink); font-size:.92rem; margin-top:.25rem; }
.kc-narr { background: var(--kc-bg); border-left: 4px solid var(--kc-navy); padding: .9rem 1.1rem; border-radius: 4px;
           font-size: 1.02rem; line-height: 1.7; color: var(--kc-ink); }
.kc-small { color: var(--kc-muted); font-size: .85rem; }
</style>
"""


def header_html(step: int) -> str:
    names = ["① PDF 업로드", "② 추출 결과 확인", "③ 분석 결과"]
    steps = "".join(
        f'<span class="kc-step {"on" if i == step else ("done" if i < step else "")}">{n}</span>'
        for i, n in enumerate(names)
    )
    return (
        '<div class="kc-header"><div class="title">KCFM 기업 현금흐름 진단</div>'
        '<div class="sub">3개년 재무제표로 현금이 어디에 묶였고, 영업에서 현금이 만들어지고 있는지 확인합니다.</div></div>'
        f'<div class="kc-steps">{steps}</div>'
    )


def badge(level: str) -> str:
    cls = {"관찰": "b0", "주의": "b1", "집중점검": "b2"}.get(level, "b0")
    return f'<span class="kc-badge {cls}">{level}</span>'


def cfo_badge(basis: str | None) -> str:
    if basis == "공시":
        return '<span class="kc-badge pub">공시 영업활동현금흐름</span>'
    if basis == "추정":
        return '<span class="kc-badge est">추정 영업활동현금흐름</span>'
    return '<span class="kc-badge est">확인 필요</span>'
