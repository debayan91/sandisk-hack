"""
main.py — FastAPI application factory for the Flash Intelligence Core.

Startup sequence:
  1. Parse config.yaml
  2. Initialize SQLite database (create tables)
  3. Mount all routers

Endpoints:
  POST /ingest         → receive monitoring payload from Java agent
  GET  /system-summary → return aggregated intelligence report
  GET  /health         → liveness check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import ingest, summary

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    log.info("Flash Intelligence Core starting up…")
    init_db()
    yield
    log.info("Flash Intelligence Core shutting down.")


app = FastAPI(
    title="Flash Intelligence Core",
    description=(
        "Python intelligence engine for SSD analytics: "
        "failure prediction, ransomware detection, layout optimization, "
        "growth forecasting, and archival recommendation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Streamlit dashboard and local browser to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(summary.router)


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe."""
    return {"status": "ok"}
