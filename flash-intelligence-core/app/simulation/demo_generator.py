"""
simulation/demo_generator.py — Synthetic Data Generator for Demo Mode.

Generates realistic monitoring payloads and inserts them directly into
the SQLite database so the Intelligence Core can run without the Java agent.

Usage:
    python -m app.simulation.demo_generator
    python -m app.simulation.demo_generator --records 100

Generates configurable number of records spanning the past N days.
"""

import argparse
import logging
import math
import os
import random
import sys
import time
from datetime import datetime, timezone, timedelta

# Make the app importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import init_db, ingest_payload
from app.settings import get_config

log = logging.getLogger("demo_generator")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# ── Simulated filesystem ──────────────────────────────────────────────────────
FAKE_FILES = [
    ("/Users/demo/Documents/report_q1_2024.pdf",   50_485_760,  ".pdf"),
    ("/Users/demo/Documents/thesis_draft.docx",    12_345_678,  ".docx"),
    ("/Users/demo/Videos/demo_recording.mp4",    4_294_967_296, ".mp4"),
    ("/Users/demo/Pictures/vacation_album.zip",  1_073_741_824, ".zip"),
    ("/Users/demo/Music/playlist.flac",            523_456_789, ".flac"),
    ("/Users/demo/Downloads/installer.dmg",        892_345_678, ".dmg"),
    ("/Users/demo/Projects/data.csv",               25_000_000, ".csv"),
    ("/Users/demo/Desktop/notes.txt",                   15_000, ".txt"),
    ("/Users/demo/Library/logs/system.log",          8_400_000, ".log"),
    ("/Users/demo/.config/settings.json",               45_000, ".json"),
    ("/Users/demo/Projects/model_weights.pkl",     234_567_890, ".pkl"),
    ("/Users/demo/Documents/archive_old_proj.tar", 678_901_234, ".tar"),
]

TOTAL_BYTES = 500 * 1_000_000_000  # 500 GB simulated SSD


def _ts(dt: datetime) -> str:
    return dt.isoformat()


def generate_payload(
    ts: datetime,
    used_bytes: int,
    record_num: int,
    inject_ransomware: bool = False,
    inject_degradation: bool = False,
) -> dict:
    """Build a single monitoring payload dict."""

    # Simulate wear leveling: increases slowly over all records
    wear = 50 + int(record_num * 0.05) + random.randint(0, 2)
    if inject_degradation:
        wear = min(100, wear + 20)

    power_on_hours = 1200 + record_num  # increases per record

    io_write = random.uniform(700, 900)
    burst = io_write * random.uniform(1.8, 2.5)
    if inject_ransomware:
        io_write = random.uniform(5000, 8000)
        burst = io_write * random.uniform(3.0, 5.0)

    files = []
    now_ms = int(ts.timestamp() * 1000)
    for (path, size, ext) in FAKE_FILES:
        # Older access times for COLD detection
        age_days = random.choice([1, 3, 7, 30, 90, 180, 365])
        last_access = now_ms - age_days * 86_400_000
        last_modified = last_access - random.randint(0, 86_400_000)
        acc = max(0, 100 - age_days) + random.randint(0, 10)
        wrt = max(0, 20 - age_days // 10) + random.randint(0, 5)
        ren = 1 if inject_ransomware and random.random() < 0.4 else 0
        files.append({
            "path": path,
            "size": size,
            "last_access": last_access,
            "last_modified": last_modified,
            "access_count": acc,
            "write_count": wrt,
            "rename_count": ren,
            "extension": ext.lstrip("."),
        })

    return {
        "timestamp": _ts(ts),
        "disk_metrics": {
            "total_bytes": TOTAL_BYTES,
            "used_bytes":  used_bytes,
            "free_bytes":  TOTAL_BYTES - used_bytes,
        },
        "smart_metrics": {
            "wear_leveling_count":      wear,
            "reallocated_sector_count": random.randint(0, 3) if not inject_degradation else random.randint(5, 20),
            "power_on_hours":           power_on_hours,
            "temperature":              random.uniform(35.0, 50.0),
            "media_errors":             random.randint(0, 2) if not inject_degradation else random.randint(10, 50),
        },
        "io_metrics": {
            "read_iops":       random.uniform(1000, 1400),
            "write_iops":      io_write,
            "burst_write_rate": burst,
            "simulated":       True,
        },
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description="Flash Intelligence Platform — Demo Data Generator")
    parser.add_argument("--records",     type=int,  default=60,    help="Number of records to generate (default: 60)")
    parser.add_argument("--days",        type=float, default=7.0,  help="Time span in days (default: 7)")
    parser.add_argument("--ransomware",  type=int,  default=0,     help="Inject ransomware spike at record N (0=disabled)")
    parser.add_argument("--degradation", action="store_true",      help="Simulate SSD degradation pattern")
    args = parser.parse_args()

    init_db()

    start_used = 180 * 1_000_000_000  # 180 GB used at start
    end_used   = 210 * 1_000_000_000  # growing to 210 GB
    now = datetime.now(timezone.utc)
    span = timedelta(days=args.days)
    start_ts = now - span

    log.info("Generating %d records over %.1f days…", args.records, args.days)

    for i in range(args.records):
        frac = i / max(args.records - 1, 1)
        ts = start_ts + frac * span
        used = int(start_used + frac * (end_used - start_used))
        inject_r = (args.ransomware > 0 and i >= args.ransomware)
        payload  = generate_payload(ts, used, i, inject_r, args.degradation)
        ingest_payload(payload)
        sys.stdout.write(f"\r  Inserted record {i+1}/{args.records}")
        sys.stdout.flush()

    print(f"\nDone. {args.records} records inserted.")


if __name__ == "__main__":
    main()
