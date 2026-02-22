"""
simulation/engine.py — Simulation Engine.

Computes projected outcomes after applying the recommended archival actions:
  - projected_capacity_after_archive
  - projected_wear_reduction
  - lifespan_extension_estimate

Also accepts overrides (ransomware spike, SSD degradation, growth acceleration)
injected by the Streamlit dashboard simulation controls.
"""

import logging

from app.db import query_recent
from app.settings import get_config

log = logging.getLogger(__name__)


def compute_simulation(
    archival_result: dict,
    disk_info: dict,
    optimizer_result: dict,
    overrides: dict | None = None,
) -> dict:
    """
    Compute projected improvement estimates.

    Args:
        archival_result:   Output of archival_recommendation.recommend_archival()
        disk_info:         Output of growth_forecast.forecast_growth() (for capacity figures)
        optimizer_result:  Output of storage_optimizer.classify_storage()
        overrides:         Optional dict for dashboard simulation:
                           {
                             ransomware_spike: bool,
                             ssd_degradation_factor: float (0–1),
                             growth_acceleration_factor: float (default 1.0)
                           }

    Returns:
        dict with keys:
            projected_capacity_after_archive (int, bytes)
            projected_capacity_after_archive_gb (float)
            projected_wear_reduction (float, 0–1)
            lifespan_extension_estimate_days (int)
            archival_savings_bytes (int)
            archival_savings_gb (float)
    """
    cfg = get_config()["simulation"]
    archive_ratio  = cfg["archive_compression_ratio"]
    wear_reduction = cfg["wear_reduction_factor"]
    lifespan_days_per_unit = cfg["lifespan_days_per_wear_reduction_unit"]

    overrides = overrides or {}

    # Current disk state
    total_bytes   = disk_info.get("total_bytes", 0)
    current_used  = disk_info.get("current_used_bytes", 0)

    # Archival savings
    savings_raw   = archival_result.get("total_projected_space_savings", 0)
    # Files are archived → compressed; actual freed space = savings / ratio
    savings_freed = int(savings_raw / max(archive_ratio, 1.0))

    projected_used = max(0, current_used - savings_freed)
    projected_free = max(0, total_bytes - projected_used)

    # Wear reduction estimate — proportional to COLD write intensity removed
    total_files = optimizer_result.get("total_files", 1)
    cold_files  = optimizer_result.get("distribution", {}).get("COLD", 0)
    cold_fraction = cold_files / max(total_files, 1)
    proj_wear_reduction = round(cold_fraction * wear_reduction, 4)

    # Lifespan extension
    lifespan_ext = int(proj_wear_reduction * lifespan_days_per_unit)

    # Apply simulation overrides
    if overrides.get("ssd_degradation_factor"):
        factor = float(overrides["ssd_degradation_factor"])
        lifespan_ext = int(lifespan_ext * (1.0 - min(factor, 1.0)))

    TB = 1_000_000_000  # bytes per GB

    log.debug("Simulation: projected_used=%d wear_reduction=%.4f lifespan_ext=%d",
              projected_used, proj_wear_reduction, lifespan_ext)

    return {
        "projected_capacity_after_archive":    projected_used,
        "projected_capacity_after_archive_gb": round(projected_used / TB, 3),
        "projected_wear_reduction":            proj_wear_reduction,
        "lifespan_extension_estimate_days":    lifespan_ext,
        "archival_savings_bytes":              savings_freed,
        "archival_savings_gb":                 round(savings_freed / TB, 3),
    }
