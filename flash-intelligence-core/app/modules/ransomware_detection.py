"""
modules/ransomware_detection.py — Ransomware Anomaly Detection Module.

Detection logic:
  1. Load recent I/O history.
  2. Compute rolling baseline (mean ± N*std) for writeIOPS.
  3. Check for rename count spikes and high burst write rates.
  4. Compute weighted threat_score (0–100).

All thresholds loaded from config.yaml (no hardcoded magic numbers).
"""

import logging
import numpy as np
import pandas as pd

from app.db import query_recent
from app.settings import get_config

log = logging.getLogger(__name__)


def detect_ransomware() -> dict:
    """
    Run the ransomware detection pipeline.

    Returns:
        dict with keys:
            threat_score          (float, 0–100)
            iops_anomaly          (bool)
            rename_spike          (bool)
            burst_write_high      (bool)
            current_write_iops    (float)
            baseline_write_iops   (float)
    """
    cfg = get_config()["ransomware"]
    min_records = cfg["min_history_records"]
    std_mult = cfg["write_iops_std_multiplier"]
    rename_thresh = cfg["rename_spike_threshold"]
    burst_thresh = cfg["burst_write_high_threshold"]
    w = cfg["weights"]

    rows = query_recent("io_history", limit=200)

    # Default safe values
    defaults = {
        "threat_score": 0.0,
        "iops_anomaly": False,
        "rename_spike": False,
        "burst_write_high": False,
        "current_write_iops": 0.0,
        "baseline_write_iops": 0.0,
    }

    if len(rows) < min_records:
        log.info("Insufficient IO history (%d records) for ransomware baseline", len(rows))
        return defaults

    df = pd.DataFrame(rows)
    df["write_iops"] = pd.to_numeric(df["write_iops"], errors="coerce").fillna(0.0)
    df["burst_write_rate"] = pd.to_numeric(df["burst_write_rate"], errors="coerce").fillna(0.0)
    df["rename_count"] = pd.to_numeric(df["rename_count"], errors="coerce").fillna(0.0)

    # ── 1. WriteIOPS baseline ─────────────────────────────────────────
    baseline_vals = df["write_iops"].iloc[:-1]   # Exclude latest for baseline
    baseline_mean = float(baseline_vals.mean())
    baseline_std  = float(baseline_vals.std())
    current_iops  = float(df["write_iops"].iloc[-1])
    threshold     = baseline_mean + std_mult * baseline_std

    iops_anomaly = current_iops > threshold
    # Normalize IOPS score: 0 at threshold, 100 at 5× threshold
    iops_excess = max(0.0, current_iops - threshold)
    iops_range  = max(threshold * 4.0, 1.0)
    iops_score  = min(100.0, (iops_excess / iops_range) * 100.0)

    # ── 2. Rename spike ───────────────────────────────────────────────
    latest_renames = float(df["rename_count"].iloc[-1])
    rename_spike = latest_renames > rename_thresh
    rename_score = min(100.0, (latest_renames / max(rename_thresh, 1)) * 100.0)

    # ── 3. Burst write rate ───────────────────────────────────────────
    current_burst = float(df["burst_write_rate"].iloc[-1])
    burst_write_high = current_burst > burst_thresh
    burst_score = min(100.0, (current_burst / max(burst_thresh, 1)) * 100.0)

    # ── 4. Composite threat score ─────────────────────────────────────
    threat_score = (
        w["iops_weight"] * iops_score
        + w["rename_weight"] * rename_score
        + w["burst_weight"] * burst_score
    )

    log.debug("Ransomware: threat=%.1f iops_anom=%s rename=%s burst=%s",
              threat_score, iops_anomaly, rename_spike, burst_write_high)

    return {
        "threat_score": round(min(100.0, threat_score), 1),
        "iops_anomaly": iops_anomaly,
        "rename_spike": rename_spike,
        "burst_write_high": burst_write_high,
        "current_write_iops": round(current_iops, 2),
        "baseline_write_iops": round(baseline_mean, 2),
    }
