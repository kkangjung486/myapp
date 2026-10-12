"""Plotly 차트. 모든 차트는 축 1개, 시리즈 최대 3개, 억원 단위 표시."""
from __future__ import annotations

import plotly.graph_objects as go

from financial_calculations.formatting import eok_man

# 검증된 범주형 팔레트 앞 3색 (blue, orange, aqua) + 증감(극성) 색
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
POSITIVE, NEGATIVE, TOTAL = "#2a78d6", "#e34948", "#1f3a5f"
INK, MUTED, GRID = "#1f2933", "#52514e", "#e6e8eb"
EOK = 100_000_000


def _layout(fig: go.Figure, title: str, y_title: str, height: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0, xanchor="left"),
        template="plotly_white", height=height, margin=dict(l=10, r=70, t=60, b=10),
        font=dict(family="Pretendard, 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif", color=INK, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, font=dict(color=MUTED)),
        hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(type="category", showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, ticksuffix=f" {y_title}" if y_title else "", zerolinecolor="#9aa0a6", tickfont=dict(color=MUTED),
                     automargin=True)
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_traces(cliponaxis=False, selector=dict(type="scatter"))
    return fig


def _x(years):
    return [f"{y}년" for y in years]


def bar_money(years, values, title, names=None, colors=None) -> go.Figure:
    """단일 지표 막대 (억원). 음수는 빨간색."""
    vals = [None if v is None else v / EOK for v in values]
    cols = [NEGATIVE if (v is not None and v < 0) else (colors or SERIES[0]) for v in vals]
    fig = go.Figure(go.Bar(
        x=_x(years), y=vals, marker=dict(color=cols, cornerradius=4), width=0.45,
        text=[eok_man(v) if v is not None else "확인 필요" for v in values], textposition="outside",
        textfont=dict(color=INK), hovertext=[eok_man(v) for v in values], hoverinfo="x+text",
        name=title,
    ))
    return _layout(fig, title, "억원")


def lines_money(years, series: dict[str, list], title) -> go.Figure:
    fig = go.Figure()
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=_x(years), y=[None if v is None else v / EOK for v in values], name=name, mode="lines+markers",
            line=dict(color=SERIES[i % 3], width=2), marker=dict(size=9, line=dict(color="white", width=2)),
            customdata=[eok_man(v) for v in values], hovertemplate=f"{name}: %{{customdata}}<extra></extra>",
        ))
    return _layout(fig, title, "억원")


def grouped_money(years, series: dict[str, list], title) -> go.Figure:
    fig = go.Figure()
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Bar(
            x=_x(years), y=[None if v is None else v / EOK for v in values], name=name,
            marker=dict(color=SERIES[i % 3], cornerradius=4, line=dict(color="white", width=2)),
            customdata=[eok_man(v) for v in values], hovertemplate=f"{name}: %{{customdata}}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.3)
    return _layout(fig, title, "억원")


def lines_days(years, series: dict[str, list], title) -> go.Figure:
    fig = go.Figure()
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=_x(years), y=values, name=name, mode="lines+markers+text",
            line=dict(color=SERIES[i % 3], width=2), marker=dict(size=9, line=dict(color="white", width=2)),
            # 마지막 연도에만 값 표시 (겹침 방지, 나머지는 마우스를 올리면 표시)
            text=[None if (v is None or j < len(values) - 1) else f"{name} {v:.0f}일" for j, v in enumerate(values)],
            textposition="middle right",
            textfont=dict(color=MUTED, size=11),
            hovertemplate=f"{name}: %{{y:.1f}}일<extra></extra>",
        ))
    return _layout(fig, title, "일")


def waterfall(items: list[tuple[str, float]], final_label: str, title: str) -> go.Figure:
    """현금 증감 분해 (+ 현금 유입 / - 현금 유출 → 최종 현금 증감)."""
    labels = [l.split("(")[0].strip().replace(" ", "<br>") for l, _ in items] + [final_label]
    total = sum(v for _, v in items)
    vals = [v / EOK for _, v in items]
    fig = go.Figure(go.Waterfall(
        orientation="v", x=labels, y=vals + [None], measure=["relative"] * len(items) + ["total"],
        increasing=dict(marker=dict(color=POSITIVE)), decreasing=dict(marker=dict(color=NEGATIVE)),
        totals=dict(marker=dict(color=TOTAL)), connector=dict(line=dict(color=GRID, width=1)),
        text=[eok_man(v, signed=True) for _, v in items] + [eok_man(total, signed=True)], textposition="outside",
        textfont=dict(color=INK, size=11), hoverinfo="x+text",
    ))
    fig = _layout(fig, title, "억원", height=440)
    fig.update_layout(hovermode="closest", showlegend=False)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(tickangle=0, tickfont=dict(size=11))
    return fig
