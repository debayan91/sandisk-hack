"""
modules/storage_optimizer.py — Storage Layout Optimization Module.

Algorithm:
  1. Load all file_records from DB.
  2. Compute normalized features: recency, frequency, write_intensity, size_norm.
  3. Compute hotness score using configurable weights.
  4. Cluster into 3 groups using KMeans.
  5. Label clusters HOT / WARM / COLD by descending mean hotness.

Returns per-file classifications and aggregate distribution counts.
"""

import logging
import time
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

from app.db import query_all
from app.settings import get_config

log = logging.getLogger(__name__)


def _safe_normalize(series: pd.Series) -> pd.Series:
    """MinMax normalize a series, returning zeros if all values are equal."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mn) / (mx - mn)


def classify_storage() -> dict:
    """
    Run the storage optimizer.

    Returns:
        dict with keys:
            distribution        (dict: {HOT: N, WARM: N, COLD: N})
            files               (list of dicts: {path, cluster, hotness_score})
            total_files         (int)
    """
    cfg = get_config()["storage_optimizer"]
    w = cfg["weights"]
    n_clusters = cfg["n_clusters"]
    labels_cfg = cfg["cluster_labels"]

    rows = query_all("file_records", limit=10000)

    if not rows:
        log.info("No file records found; returning empty classification")
        return {
            "distribution": {"HOT": 0, "WARM": 0, "COLD": 0},
            "files": [],
            "total_files": 0,
        }

    df = pd.DataFrame(rows)
    now_ms = int(time.time() * 1000)

    # Ensure numeric types
    df["size"] = pd.to_numeric(df["size"], errors="coerce").fillna(0)
    df["last_access"] = pd.to_numeric(df["last_access"], errors="coerce").fillna(0)
    df["access_count"] = pd.to_numeric(df["access_count"], errors="coerce").fillna(0)
    df["write_count"] = pd.to_numeric(df["write_count"], errors="coerce").fillna(0)

    # ── Feature engineering ───────────────────────────────────────────
    age_ms = now_ms - df["last_access"]
    df["recency_raw"] = age_ms.clip(lower=0)            # higher = older = colder
    df["recency"] = _safe_normalize(df["recency_raw"])  # 0=very recent, 1=ancient
    df["frequency"] = _safe_normalize(df["access_count"])
    df["write_intensity"] = _safe_normalize(df["write_count"])
    df["size_norm"] = _safe_normalize(df["size"])

    # ── Hotness score ─────────────────────────────────────────────────
    df["hotness"] = (
        w["frequency"]      * df["frequency"]
        + w["recency"]      * (1.0 - df["recency"])   # invert: high recency = low hotness
        + w["write_intensity"] * df["write_intensity"]
        + w["size"]         * df["size_norm"]
    )

    # ── KMeans clustering ─────────────────────────────────────────────
    n_actual = min(n_clusters, len(df))
    if n_actual < 2:
        df["cluster_id"] = 0
    else:
        X = df[["hotness"]].values
        km = KMeans(n_clusters=n_actual, random_state=42, n_init=10)
        df["cluster_id"] = km.fit_predict(X)

    # ── Label clusters by descending mean hotness ─────────────────────
    cluster_means = df.groupby("cluster_id")["hotness"].mean().sort_values(ascending=False)
    cluster_to_label = {
        cid: labels_cfg[i] if i < len(labels_cfg) else "COLD"
        for i, cid in enumerate(cluster_means.index)
    }
    df["cluster"] = df["cluster_id"].map(cluster_to_label)

    distribution = df["cluster"].value_counts().to_dict()
    # Ensure all expected labels present
    for label in labels_cfg:
        distribution.setdefault(label, 0)

    results = df[["path", "cluster", "hotness"]].rename(
        columns={"hotness": "hotness_score"}
    ).to_dict(orient="records")

    # Round hotness scores
    for r in results:
        r["hotness_score"] = round(r["hotness_score"], 4)

    log.debug("Storage classification: %s", distribution)
    return {
        "distribution": distribution,
        "files": results,
        "total_files": len(df),
    }
