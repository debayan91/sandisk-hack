"""
modules/compression_estimator.py — File Compression Estimator Module.

Estimates potential space savings using Shannon entropy sampling.

High entropy → file is already compressed or encrypted (ratio ≈ 1.0).
Low entropy  → file has significant redundancy (ratio > 2.0).

All parameters loaded from config.yaml.
"""

import logging
import math
import os
from collections import Counter

from app.db import query_all
from app.settings import get_config

log = logging.getLogger(__name__)


def _shannon_entropy(data: bytes) -> float:
    """Compute Shannon entropy in bits per byte for the given byte sequence."""
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _entropy_to_ratio(entropy: float, mapping: dict) -> float:
    """
    Linearly interpolate the compression ratio from the entropy→ratio map.
    mapping keys are entropy thresholds (ascending), values are ratios.
    """
    keys = sorted(float(k) for k in mapping.keys())
    vals = [float(mapping[k]) for k in sorted(mapping.keys(), key=float)]

    if entropy <= keys[0]:
        return vals[0]
    if entropy >= keys[-1]:
        return vals[-1]

    for i in range(len(keys) - 1):
        if keys[i] <= entropy <= keys[i + 1]:
            t = (entropy - keys[i]) / (keys[i + 1] - keys[i])
            return vals[i] + t * (vals[i + 1] - vals[i])
    return vals[-1]


def estimate_compression() -> dict:
    """
    Estimate compression savings for all tracked files.

    Returns:
        dict with keys:
            enabled                  (bool)
            sampled_files            (int)
            estimated_savings_bytes  (int)
            aggregate_ratio          (float)
            files                   (list of {path, entropy, ratio, savings_bytes})
    """
    cfg = get_config()["compression"]

    if not cfg.get("enabled", True):
        return {"enabled": False, "sampled_files": 0,
                "estimated_savings_bytes": 0, "aggregate_ratio": 1.0, "files": []}

    sample_size = cfg["sample_size"]
    ratio_map   = cfg["entropy_ratio_map"]

    rows = query_all("file_records", limit=2000)

    file_results = []
    total_original  = 0
    total_compressed = 0

    for row in rows:
        path = row.get("path", "")
        size = int(row.get("size", 0))
        if size == 0 or not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                sample = f.read(sample_size)
            entropy = _shannon_entropy(sample)
            ratio   = _entropy_to_ratio(entropy, ratio_map)
            compressed_size = size / ratio
            savings = size - compressed_size

            total_original  += size
            total_compressed += compressed_size

            file_results.append({
                "path":        path,
                "entropy":     round(entropy, 4),
                "ratio":       round(ratio, 3),
                "savings_bytes": int(savings),
            })
        except (OSError, PermissionError) as e:
            log.debug("Cannot read %s: %s", path, e)

    aggregate_ratio = (total_original / max(total_compressed, 1)) if total_compressed else 1.0

    log.debug("Compression: sampled=%d savings=%d bytes",
              len(file_results), total_original - int(total_compressed))

    return {
        "enabled": True,
        "sampled_files": len(file_results),
        "estimated_savings_bytes": int(total_original - total_compressed),
        "aggregate_ratio": round(aggregate_ratio, 3),
        "files": file_results,
    }
