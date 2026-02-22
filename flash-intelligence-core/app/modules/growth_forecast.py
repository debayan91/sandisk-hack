"""
modules/growth_forecast.py — Storage Growth Forecast Module.

Algorithm:
  1. Load disk usage history from DB.
  2. Fit LinearRegression on (time_index → used_bytes).
  3. Extrapolate to find when used_bytes reaches 90% of total capacity.
  4. Return days_to_full and historical data for charting.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from app.db import query_recent
from app.settings import get_config

log = logging.getLogger(__name__)


def forecast_growth() -> dict:
    """
    Forecast storage growth.

    Returns:
        dict with keys:
            days_to_full            (float | None)
            full_threshold_pct      (float)
            current_used_bytes      (int)
            total_bytes             (int)
            current_used_pct        (float)
            history                 (list of {ts, used_bytes, used_pct})
            regression_slope_bytes_per_interval (float)
    """
    cfg = get_config()["growth_forecast"]
    full_pct = cfg["full_threshold_pct"] / 100.0
    min_records = cfg["min_history_records"]

    rows = query_recent("disk_history", limit=1000)

    defaults = {
        "days_to_full": None,
        "full_threshold_pct": cfg["full_threshold_pct"],
        "current_used_bytes": 0,
        "total_bytes": 0,
        "current_used_pct": 0.0,
        "history": [],
        "regression_slope_bytes_per_interval": 0.0,
    }

    if len(rows) < min_records:
        log.info("Insufficient disk history (%d records)", len(rows))
        return defaults

    df = pd.DataFrame(rows)
    df["used_bytes"] = pd.to_numeric(df["used_bytes"], errors="coerce").fillna(0)
    df["total_bytes"] = pd.to_numeric(df["total_bytes"], errors="coerce").fillna(1)

    latest_total = int(df["total_bytes"].iloc[-1])
    latest_used  = int(df["used_bytes"].iloc[-1])
    full_bytes   = latest_total * full_pct

    # ── Linear regression ─────────────────────────────────────────────
    X = np.arange(len(df)).reshape(-1, 1)
    y = df["used_bytes"].values
    lr = LinearRegression().fit(X, y)
    slope = float(lr.coef_[0])

    # Find intervals until used_bytes == full_bytes
    if slope <= 0:
        days_to_full = None
    else:
        intervals_to_full = (full_bytes - float(lr.intercept_)) / slope
        current_interval  = float(len(df) - 1)
        remaining_intervals = max(0.0, intervals_to_full - current_interval)
        # Assume collection every 10 seconds → intervals per day = 8640
        INTERVALS_PER_DAY = 8640
        days_to_full = remaining_intervals / INTERVALS_PER_DAY

    # ── Build history list ────────────────────────────────────────────
    history = []
    for _, row in df.iterrows():
        total = max(row["total_bytes"], 1)
        history.append({
            "ts": row.get("ts", ""),
            "used_bytes": int(row["used_bytes"]),
            "used_pct": round(row["used_bytes"] / total * 100.0, 2),
        })

    log.debug("Growth forecast: slope=%.0f days_to_full=%s", slope, days_to_full)

    return {
        "days_to_full": round(days_to_full, 1) if days_to_full is not None else None,
        "full_threshold_pct": cfg["full_threshold_pct"],
        "current_used_bytes": latest_used,
        "total_bytes": latest_total,
        "current_used_pct": round(latest_used / max(latest_total, 1) * 100.0, 2),
        "history": history,
        "regression_slope_bytes_per_interval": round(slope, 0),
    }
