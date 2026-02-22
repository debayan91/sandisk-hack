"""
components/tables.py — Archival candidates table renderer.

Formats the archival recommendation list into a clean Streamlit/Pandas table.
"""

import pandas as pd


def render_archival_table(candidates: list[dict], max_rows: int = 15) -> pd.DataFrame:
    """
    Build and return a formatted DataFrame of archival candidates.

    Args:
        candidates: list of dicts from the /system-summary endpoint
        max_rows:   maximum rows to display

    Returns:
        pd.DataFrame ready for st.dataframe() / st.table()
    """
    if not candidates:
        return pd.DataFrame(columns=["Path", "Size (MB)", "Age (days)", "Extension", "Score"])

    df = pd.DataFrame(candidates[:max_rows])

    display = pd.DataFrame({
        "📄 File Path":    df.get("path", "").apply(lambda p: "…/" + "/".join(str(p).split("/")[-2:])),
        "💾 Size (MB)":    df.get("size_mb", 0).round(1),
        "🕓 Age (days)":   df.get("age_days", 0).round(0).astype(int),
        "🏷️ Extension":    df.get("extension", "").apply(lambda e: f".{e}" if e else "—"),
        "✍️ Write Count":  df.get("write_count", 0).astype(int),
        "📊 Score":        df.get("archive_score", 0).round(4),
    })
    return display
