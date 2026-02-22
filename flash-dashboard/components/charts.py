"""
components/charts.py — Plotly chart components for the dashboard.

Provides:
  - render_hwc_pie(distribution)    → HOT/WARM/COLD pie chart
  - render_growth_line(history)     → storage usage line chart
"""

import pandas as pd
import plotly.graph_objects as go


def render_hwc_pie(distribution: dict) -> go.Figure:
    """
    Render a donut pie chart of the HOT/WARM/COLD file distribution.

    Args:
        distribution: dict like {"HOT": 120, "WARM": 400, "COLD": 200}
    """
    labels = ["HOT", "WARM", "COLD"]
    values = [distribution.get(l, 0) for l in labels]
    colors = ["#FF4B4B", "#FFA500", "#00B4D8"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker={"colors": colors, "line": {"color": "#0F0F1A", "width": 2}},
        textfont={"size": 14, "color": "#FFFFFF"},
        hovertemplate="<b>%{label}</b><br>Files: %{value}<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title={"text": "📊 Storage Temperature Distribution",
               "font": {"size": 15, "color": "#E0E0E0"}, "x": 0.5},
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font={"color": "#CCCCCC"},
        legend={"font": {"color": "#CCCCCC"}, "bgcolor": "#0F0F1A"},
        margin={"t": 60, "b": 20, "l": 10, "r": 10},
        height=300,
    )
    return fig


def render_growth_line(history: list[dict], days_to_full: float | None) -> go.Figure:
    """
    Render a line chart of storage usage over time.

    Args:
        history:      list of {"ts": str, "used_bytes": int, "used_pct": float}
        days_to_full: projected days until 90% capacity, or None
    """
    if not history:
        fig = go.Figure()
        fig.update_layout(
            title={"text": "📈 Storage Growth (no data yet)", "x": 0.5},
            paper_bgcolor="#0F0F1A",
            height=300,
        )
        return fig

    df = pd.DataFrame(history)
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    label = (f"Days to 90% Full: <b>{days_to_full:.0f}d</b>" if days_to_full
             else "Growth: Stable")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["ts"],
        y=df["used_pct"],
        mode="lines+markers",
        name="Used %",
        line={"color": "#7B61FF", "width": 2.5},
        marker={"size": 5, "color": "#7B61FF"},
        fill="tozeroy",
        fillcolor="rgba(123,97,255,0.15)",
        hovertemplate="%{x|%b %d %H:%M}<br>Used: %{y:.1f}%<extra></extra>",
    ))

    # 90% threshold line
    fig.add_hline(
        y=90, line_dash="dash", line_color="#FF4B4B", line_width=1.5,
        annotation_text="90% threshold", annotation_position="top left",
        annotation_font_color="#FF4B4B",
    )

    fig.update_layout(
        title={"text": f"📈 Storage Growth — {label}", "x": 0.5,
               "font": {"color": "#E0E0E0", "size": 15}},
        xaxis={"title": "", "color": "#999", "gridcolor": "#222"},
        yaxis={"title": "Used (%)", "color": "#999", "gridcolor": "#222",
               "range": [0, 105]},
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font={"color": "#CCCCCC"},
        margin={"t": 60, "b": 40, "l": 50, "r": 20},
        height=300,
    )
    return fig
