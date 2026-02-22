"""
components/summary_panel.py — Optimization Impact Summary Panel.

Renders the projected improvements from storage optimization in a
visually clear metric grid.
"""

import streamlit as st


def render_summary_panel(data: dict) -> None:
    """
    Display the optimization impact summary using Streamlit metric widgets.

    Args:
        data: dict from /system-summary endpoint
    """
    st.markdown("### ⚡ Optimization Impact")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        savings_gb = data.get("archival_savings_gb", 0.0)
        st.metric(
            label="🗜️ Archival Savings",
            value=f"{savings_gb:.2f} GB",
            help="Projected storage freed by archiving COLD files",
        )

    with col2:
        proj_cap = data.get("projected_capacity_after_optimization", 0.0)
        st.metric(
            label="💾 Projected Used",
            value=f"{proj_cap:.2f} GB",
            help="Projected disk used (GB) after archival",
        )

    with col3:
        wear_red = data.get("projected_wear_reduction", 0.0)
        st.metric(
            label="🔋 Wear Reduction",
            value=f"{wear_red * 100:.1f}%",
            help="Estimated reduction in write wear from archiving COLD files",
        )

    with col4:
        lifespan = data.get("lifespan_extension_estimate_days", 0)
        years, days_rem = divmod(int(lifespan), 365)
        lifespan_label = f"{years}y {days_rem}d" if years else f"{days_rem}d"
        st.metric(
            label="⏳ Lifespan Extension",
            value=lifespan_label,
            help="Estimated SSD lifespan extension from reduced write intensity",
        )

    # Eligible / candidate counts
    st.caption(
        f"📂 Files tracked: **{data.get('total_tracked_files', 0)}**  |  "
        f"🗃️ Archival eligible: **{data.get('archival_eligible_count', 0)}**  |  "
        f"🗜️ Compression ratio: **{data.get('compression_aggregate_ratio', 1.0):.2f}×**  |  "
        f"📉 Compression savings: **{data.get('compression_savings_bytes', 0) / 1_048_576:.1f} MB**"
    )
