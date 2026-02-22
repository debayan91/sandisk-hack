"""
routers/summary.py — GET /system-summary endpoint.

Orchestrates all intelligence modules and the simulation engine,
then returns the unified system summary JSON.

Also accepts optional query parameters for simulation overrides:
  ?ransomware_spike=true
  ?ssd_degradation_factor=0.5
  ?growth_acceleration_factor=1.5
"""

import logging
from fastapi import APIRouter, Query

from app.modules.failure_prediction    import predict_failure
from app.modules.ransomware_detection  import detect_ransomware
from app.modules.storage_optimizer     import classify_storage
from app.modules.growth_forecast       import forecast_growth
from app.modules.compression_estimator import estimate_compression
from app.modules.archival_recommendation import recommend_archival
from app.simulation.engine             import compute_simulation

log = logging.getLogger(__name__)
router = APIRouter(tags=["Summary"])


@router.get("/system-summary")
def system_summary(
    ransomware_spike: bool = Query(False, description="Simulate ransomware spike"),
    ssd_degradation_factor: float = Query(0.0, ge=0.0, le=1.0,
                                          description="SSD degradation override (0–1)"),
    growth_acceleration_factor: float = Query(1.0, ge=0.5, le=5.0,
                                              description="Growth acceleration multiplier"),
):
    """
    Return the full intelligence summary.

    All six analytical modules run per request (results are fast since
    DB queries are small and models operate on in-memory DataFrames).
    """
    overrides = {
        "ransomware_spike":           ransomware_spike,
        "ssd_degradation_factor":     ssd_degradation_factor,
        "growth_acceleration_factor": growth_acceleration_factor,
    }

    try:
        failure   = predict_failure()
        ransomware_result = detect_ransomware()

        # Apply ransomware spike simulation override
        if ransomware_spike:
            ransomware_result["threat_score"] = min(100.0,
                ransomware_result["threat_score"] + 60.0)
            ransomware_result["iops_anomaly"]  = True

        # Apply SSD degradation override to failure score
        if ssd_degradation_factor > 0:
            failure["failure_risk_score"] = min(100.0,
                failure["failure_risk_score"] + ssd_degradation_factor * 50.0)
            failure["predicted_remaining_life_days"] = max(0.0,
                failure["predicted_remaining_life_days"] * (1.0 - ssd_degradation_factor * 0.5))

        optimizer = classify_storage()
        growth    = forecast_growth()

        # Apply growth acceleration override
        if growth_acceleration_factor != 1.0 and growth["days_to_full"]:
            growth["days_to_full"] = round(
                growth["days_to_full"] / growth_acceleration_factor, 1)

        compression = estimate_compression()
        archival    = recommend_archival()
        simulation  = compute_simulation(archival, growth, optimizer, overrides)

        return {
            "failure_risk_score":             failure["failure_risk_score"],
            "predicted_remaining_life_days":  failure["predicted_remaining_life_days"],
            "failure_anomaly_detected":       failure["anomaly_detected"],

            "ransomware_threat_score":        ransomware_result["threat_score"],
            "ransomware_iops_anomaly":        ransomware_result["iops_anomaly"],
            "ransomware_rename_spike":        ransomware_result["rename_spike"],

            "hot_warm_cold_distribution":     optimizer["distribution"],
            "total_tracked_files":            optimizer["total_files"],
            "file_classifications":           optimizer["files"],

            "projected_days_to_full":         growth["days_to_full"],
            "current_used_pct":               growth["current_used_pct"],
            "disk_growth_history":            growth["history"],

            "compression_savings_bytes":      compression["estimated_savings_bytes"],
            "compression_aggregate_ratio":    compression["aggregate_ratio"],

            "archival_candidates":            archival["recommended_files"],
            "archival_eligible_count":        archival["eligible_count"],
            "total_projected_space_savings":  archival["total_projected_space_savings"],

            "projected_capacity_after_optimization": simulation["projected_capacity_after_archive_gb"],
            "projected_wear_reduction":              simulation["projected_wear_reduction"],
            "lifespan_extension_estimate_days":      simulation["lifespan_extension_estimate_days"],
            "archival_savings_gb":                   simulation["archival_savings_gb"],

            "simulation_overrides_active": any([
                ransomware_spike,
                ssd_degradation_factor > 0,
                growth_acceleration_factor != 1.0,
            ]),
        }

    except Exception as e:
        log.exception("System summary failed")
        return {"error": str(e)}
