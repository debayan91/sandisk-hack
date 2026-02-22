"""
routers/ingest.py — POST /ingest endpoint.

Receives monitoring payloads from the Java agent, validates structure,
and delegates persistence to db.ingest_payload().
"""

import logging
from fastapi import APIRouter, HTTPException

from app.db import ingest_payload

log = logging.getLogger(__name__)
router = APIRouter(tags=["Ingest"])


@router.post("/ingest", status_code=202)
def ingest(payload: dict):
    """
    Accept a monitoring payload from the Java Flash Monitor Agent.

    Expected payload shape:
    {
        "timestamp": "...",
        "disk_metrics": {...},
        "smart_metrics": {...},
        "io_metrics": {...},
        "files": [...]
    }
    """
    if "timestamp" not in payload:
        raise HTTPException(status_code=400, detail="Missing required field: timestamp")

    try:
        ingest_payload(payload)
        return {
            "status": "accepted",
            "timestamp": payload["timestamp"],
            "file_count": len(payload.get("files", [])),
        }
    except Exception as e:
        log.error("Ingest failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
