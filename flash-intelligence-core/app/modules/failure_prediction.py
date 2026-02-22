"""
modules/failure_prediction.py — SSD Failure Prediction Module.

Algorithm:
  1. Load SMART history from DB.
  2. Compute linear slope of wear_leveling_count over time (trend analysis).
  3. Fit IsolationForest on all SMART numeric features to detect anomaly.
  4. Combine slope severity and anomaly score into failure_risk_score (0–100).
  5. Extrapolate remaining life days using slope.

All hyperparameters are loaded from config.yaml.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

from app.db import query_recent
from app.settings import get_config

log = logging.getLogger(__name__)
FEATURES = ["wear_leveling_count", "reallocated_sector_count",
            "power_on_hours", "temperature", "media_errors"]


def predict_failure() -> dict:
    """
    Run the failure prediction pipeline.

    Returns:
        dict with keys:
            failure_risk_score         (float, 0–100)
            predicted_remaining_life_days (float)
            anomaly_detected           (bool)
            trend_slope                (float)
    """
    cfg = get_config()["failure_prediction"]
    min_records = cfg["min_history_records"]
    contamination = cfg["contamination"]
    max_life = cfg["max_life_days"]

    rows = query_recent("smart_history", limit=500)

    # Insufficient data — return safe defaults
    if len(rows) < min_records:
        log.info("Insufficient SMART history (%d records), returning defaults", len(rows))
        return {
            "failure_risk_score": 0.0,
            "predicted_remaining_life_days": float(max_life),
            "anomaly_detected": False,
            "trend_slope": 0.0,
        }

    df = pd.DataFrame(rows)

    # Replace sentinel -1 values with NaN, then fill with column mean
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].replace(-1, np.nan).fillna(df[col].median())
        else:
            df[col] = 0.0

    # ── 1. Wear leveling trend slope ─────────────────────────────────
    wlc = df["wear_leveling_count"].values.reshape(-1, 1)
    time_idx = np.arange(len(wlc)).reshape(-1, 1)
    lr = LinearRegression().fit(time_idx, wlc)
    slope = float(lr.coef_[0][0])

    # ── 2. IsolationForest anomaly detection ─────────────────────────
    X = df[FEATURES].values
    iso = IsolationForest(contamination=contamination, random_state=42)
    preds = iso.fit_predict(X)
    anomaly_score = float(np.mean(preds == -1))   # fraction of anomalous rows
    anomaly_detected = bool(preds[-1] == -1)       # is the latest point anomalous?

    # ── 3. Composite risk score ───────────────────────────────────────
    # Normalize slope: slope > 0 means wear is increasing (bad)
    slope_score = min(100.0, max(0.0, slope * 10.0))
    anomaly_component = anomaly_score * 100.0
    risk_score = min(100.0, 0.6 * slope_score + 0.4 * anomaly_component)

    # ── 4. Remaining life estimate ────────────────────────────────────
    current_wlc = float(df["wear_leveling_count"].iloc[-1])
    if slope > 0:
        # Extrapolate when wear reaches 100 (normalized units)
        remaining_increments = max(0.0, (100.0 - current_wlc) / slope)
        # Each increment ≈ one collection interval (~10 min); convert to days
        remaining_days = min(float(max_life), remaining_increments * (10 / 1440))
    else:
        remaining_days = float(max_life)

    log.debug("Failure prediction: risk=%.1f slope=%.4f anomaly=%s",
              risk_score, slope, anomaly_detected)

    return {
        "failure_risk_score": round(risk_score, 1),
        "predicted_remaining_life_days": round(remaining_days, 0),
        "anomaly_detected": anomaly_detected,
        "trend_slope": round(slope, 6),
    }
