"""
app.py — Main Streamlit Dashboard for the Flash Intelligence Platform.

Auto-refreshes every N seconds (configurable via config.yaml).
Fetches live data from the Python Intelligence Core REST API.

Panels:
  1. Simulation Controls (sidebar)
  2. Failure Risk Gauge
  3. Ransomware Threat Gauge
  4. HOT/WARM/COLD Pie Chart
  5. Storage Growth Line Chart
  6. Archival Candidates Table
  7. Optimization Impact Summary Panel
"""

import time
import pathlib

import requests
import streamlit as st
import yaml

from components.gauges        import render_failure_gauge, render_ransomware_gauge
from components.charts        import render_hwc_pie, render_growth_line
from components.tables        import render_archival_table
from components.summary_panel import render_summary_panel

# ── Config ────────────────────────────────────────────────────────────────────
_cfg_path = pathlib.Path(__file__).parent / "config.yaml"
with open(_cfg_path) as f:
    _cfg = yaml.safe_load(f)

DASH = _cfg["dashboard"]
UI   = _cfg["ui"]
API  = DASH["api_base_url"]
REFRESH_S = DASH["refresh_interval_seconds"]
MAX_ROWS  = DASH["max_archival_rows"]

st.set_page_config(
    page_title=UI["page_title"],
    page_icon=UI["page_icon"],
    layout=UI["layout"],
)

# ── Dark-theme CSS injection ──────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global dark background */
    .stApp { background-color: #0F0F1A; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #13131F; }
    [data-testid="stMetricValue"] { color: #C084FC; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #AAAAAA; }
    .stDataFrame { background-color: #1A1A2E; }
    h1, h2, h3 { color: #C084FC; }
    .stAlert { background-color: #1E1E2E; border-radius: 8px; }
    div[data-testid="stHorizontalBlock"] > div {
        background: #13131F; border-radius: 12px; padding: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚡ Flash Intelligence Platform")
st.caption("Real-time SSD analytics · Failure prediction · Ransomware detection · Storage optimization")

# ── Sidebar — Simulation Controls ────────────────────────────────────────────
st.sidebar.title("🎛️ Simulation Controls")
st.sidebar.markdown("---")

ransomware_spike = st.sidebar.toggle(
    "🦠 Ransomware Spike",
    value=False,
    help="Simulate a sudden write/rename burst anomaly",
)
ssd_degradation = st.sidebar.slider(
    "🔋 SSD Degradation Factor",
    min_value=0.0, max_value=1.0, value=0.0, step=0.05,
    help="0 = healthy, 1 = critical degradation",
)
growth_acceleration = st.sidebar.slider(
    "📈 Growth Acceleration ×",
    min_value=1.0, max_value=5.0, value=1.0, step=0.5,
    help="Multiply growth speed to see near-future projections",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Auto-refresh**")
auto_refresh = st.sidebar.toggle("🔄 Enable Auto-refresh", value=True)

if REFRESH_S > 0 and auto_refresh:
    st.sidebar.caption(f"Refreshes every {REFRESH_S}s")

st.sidebar.markdown("---")
st.sidebar.markdown("**About**")
st.sidebar.caption("Flash Intelligence Platform v1.0\nmacOS Apple Silicon (M1) optimized\n\nComponents:\n- Java Monitor Agent\n- Python Intelligence Core\n- Streamlit Dashboard")


# ── Data Fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_S if REFRESH_S > 0 else 30, show_spinner=False)
def fetch_summary(ransomware: bool, degradation: float, acceleration: float) -> dict:
    """Fetch the system summary from the Intelligence Core API."""
    params = {
        "ransomware_spike": str(ransomware).lower(),
        "ssd_degradation_factor": degradation,
        "growth_acceleration_factor": acceleration,
    }
    resp = requests.get(f"{API}/system-summary", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# Fetch data
data_placeholder = st.empty()
try:
    with st.spinner("Fetching intelligence data…"):
        data = fetch_summary(ransomware_spike, ssd_degradation, growth_acceleration)
    error = None
except Exception as e:
    data = {}
    error = str(e)

if error:
    st.error(f"⚠️ Cannot reach Intelligence Core at `{API}`: {error}")
    st.info("Make sure the Python Intelligence Core is running:\n```\ncd flash-intelligence-core\nuvicorn app.main:app --reload --port 8000\n```")
    st.stop()

# Simulation active indicator
if data.get("simulation_overrides_active"):
    st.warning("🔬 **Simulation mode active** — values are partially synthetic")

# ── Row 1: Gauges ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    failure_score = data.get("failure_risk_score", 0.0)
    st.plotly_chart(render_failure_gauge(failure_score), use_container_width=True,
                    key="gauge_failure")
    if data.get("failure_anomaly_detected"):
        st.warning("⚡ Anomaly detected in SMART metrics")

with col2:
    threat_score = data.get("ransomware_threat_score", 0.0)
    st.plotly_chart(render_ransomware_gauge(threat_score), use_container_width=True,
                    key="gauge_ransomware")
    flags = []
    if data.get("ransomware_iops_anomaly"):  flags.append("Write IOPS spike")
    if data.get("ransomware_rename_spike"):  flags.append("Rename burst")
    if flags:
        st.warning(f"🚨 {' · '.join(flags)}")

with col3:
    distribution = data.get("hot_warm_cold_distribution", {"HOT": 0, "WARM": 0, "COLD": 0})
    st.plotly_chart(render_hwc_pie(distribution), use_container_width=True,
                    key="pie_hwc")

# ── Row 2: Storage Growth ──────────────────────────────────────────────────────
st.plotly_chart(
    render_growth_line(
        data.get("disk_growth_history", []),
        data.get("projected_days_to_full"),
    ),
    use_container_width=True,
    key="line_growth",
)

# ── Row 3: Archival Candidates Table ──────────────────────────────────────────
st.markdown("### 🗃️ Archival Candidates")
archival = data.get("archival_candidates", [])
if archival:
    df_table = render_archival_table(archival, max_rows=MAX_ROWS)
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
    )
    total_savings = data.get("total_projected_space_savings", 0)
    st.caption(f"Total projected savings: **{total_savings / 1_073_741_824:.2f} GB**  "
               f"({data.get('archival_eligible_count', 0)} files eligible)")
else:
    st.info("No COLD files currently eligible for archival. "
            "Ensure data has been ingested and files have aged past the recency threshold.")

st.markdown("---")

# ── Row 4: Optimization Summary ───────────────────────────────────────────────
render_summary_panel(data)

# ── Last updated timestamp ───────────────────────────────────────────────────
st.caption(f"⏱️ Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}"
           f"  |  Used: {data.get('current_used_pct', 0):.1f}%"
           f"  |  Tracked files: {data.get('total_tracked_files', 0)}")

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if REFRESH_S > 0 and auto_refresh:
    time.sleep(REFRESH_S)
    st.rerun()
