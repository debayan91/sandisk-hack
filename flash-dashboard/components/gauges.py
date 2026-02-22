"""
components/gauges.py — Plotly gauge charts.

Provides:
  - render_failure_gauge(score)      → Failure Risk gauge
  - render_ransomware_gauge(score)   → Ransomware Threat gauge
"""

import plotly.graph_objects as go


def _base_gauge(title: str, value: float, color_low: str, color_high: str) -> go.Figure:
    """Create a Plotly indicator gauge with a gradient from safe to danger."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={"text": title, "font": {"size": 16, "color": "#E0E0E0"}},
        number={"suffix": "/100", "font": {"size": 24, "color": "#FFFFFF"}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#555",
                "tickfont": {"color": "#999"},
            },
            "bar": {"color": "#FFFFFF", "thickness": 0.25},
            "bgcolor": "#1E1E2E",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 33],   "color": "#1A3A2A"},
                {"range": [33, 66],  "color": "#3A3A1A"},
                {"range": [66, 100], "color": "#3A1A1A"},
            ],
            "threshold": {
                "line": {"color": "#FF4B4B", "width": 3},
                "thickness": 0.75,
                "value": value,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="#0F0F1A",
        font={"color": "#CCCCCC"},
        margin={"t": 60, "b": 20, "l": 30, "r": 30},
        height=220,
    )
    return fig


def render_failure_gauge(score: float) -> go.Figure:
    """Failure Risk gauge (0–100)."""
    return _base_gauge("🔴 SSD Failure Risk", score, "#00CC66", "#FF4B4B")


def render_ransomware_gauge(score: float) -> go.Figure:
    """Ransomware Threat gauge (0–100)."""
    return _base_gauge("🛡️ Ransomware Threat", score, "#00CC66", "#FF4B4B")
