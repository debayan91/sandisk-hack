"""
modules/archival_recommendation.py — Archival Recommendation Module.

Eligibility criteria (all configurable in config.yaml):
  - Cluster == COLD
  - Time since last_access > recency_threshold_days
  - size >= min_size_bytes

Scoring:
  archive_score = size_norm - (performance_penalty_weight * write_intensity_norm)

Returns ranked candidates and projected total space savings.
"""

import logging
import time
import numpy as np
import pandas as pd

from app.db import query_all
from app.settings import get_config
from app.modules.storage_optimizer import classify_storage

log = logging.getLogger(__name__)

SECONDS_PER_DAY = 86_400
MS_PER_DAY      = SECONDS_PER_DAY * 1000


def recommend_archival() -> dict:
    """
    Identify and rank COLD files eligible for archival.

    Returns:
        dict with keys:
            recommended_files            (list of dicts)
            total_projected_space_savings (int, bytes)
            eligible_count               (int)
    """
    cfg = get_config()["archival"]
    recency_thresh = cfg["recency_threshold_days"]
    min_size       = cfg["min_size_bytes"]
    max_candidates = cfg["max_candidates"]
    penalty_weight = cfg["performance_penalty_weight"]

    now_ms = int(time.time() * 1000)
    threshold_ms = recency_thresh * MS_PER_DAY

    # Get cluster classification
    classification = classify_storage()
    cluster_map = {f["path"]: f["cluster"] for f in classification.get("files", [])}

    rows = query_all("file_records", limit=10000)
    if not rows:
        return {"recommended_files": [], "total_projected_space_savings": 0, "eligible_count": 0}

    df = pd.DataFrame(rows)
    df["size"]         = pd.to_numeric(df["size"], errors="coerce").fillna(0)
    df["last_access"]  = pd.to_numeric(df["last_access"], errors="coerce").fillna(0)
    df["write_count"]  = pd.to_numeric(df["write_count"], errors="coerce").fillna(0)
    df["access_count"] = pd.to_numeric(df["access_count"], errors="coerce").fillna(0)

    # Attach cluster labels
    df["cluster"] = df["path"].map(cluster_map).fillna("UNKNOWN")

    # ── Filter eligible files ─────────────────────────────────────────
    age_ms = now_ms - df["last_access"]
    df["age_days"] = age_ms / MS_PER_DAY

    eligible = df[
        (df["cluster"] == "COLD")
        & (age_ms >= threshold_ms)
        & (df["size"] >= min_size)
    ].copy()

    if eligible.empty:
        return {"recommended_files": [], "total_projected_space_savings": 0, "eligible_count": 0}

    # ── Compute archive_score ─────────────────────────────────────────
    def safe_norm(series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - mn) / (mx - mn)

    eligible["size_norm"]  = safe_norm(eligible["size"])
    eligible["write_norm"] = safe_norm(eligible["write_count"])
    eligible["archive_score"] = (
        eligible["size_norm"] - penalty_weight * eligible["write_norm"]
    )

    # ── Rank and cap ──────────────────────────────────────────────────
    top = eligible.nlargest(max_candidates, "archive_score")

    results = []
    for _, row in top.iterrows():
        results.append({
            "path":          row["path"],
            "size_bytes":    int(row["size"]),
            "size_mb":       round(row["size"] / (1024 * 1024), 2),
            "age_days":      round(row["age_days"], 1),
            "write_count":   int(row["write_count"]),
            "archive_score": round(row["archive_score"], 4),
            "extension":     row.get("extension", ""),
        })

    total_savings = int(top["size"].sum())

    log.debug("Archival: eligible=%d recommended=%d savings=%d bytes",
              len(eligible), len(results), total_savings)

    return {
        "recommended_files":             results,
        "total_projected_space_savings": total_savings,
        "eligible_count":                len(eligible),
    }
