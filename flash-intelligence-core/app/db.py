"""
db.py — SQLite database layer for the Flash Intelligence Core.

Schema:
  raw_events    → full monitoring payload JSON + timestamp
  disk_history  → time-series of disk used_bytes for growth forecasting
  smart_history → SMART metric snapshots for failure prediction
  file_records  → latest file metadata snapshot (upsert by path)
"""

import sqlite3
import json
import logging
import pathlib
from contextlib import contextmanager
from typing import Any, Generator

from app.settings import get_config

log = logging.getLogger(__name__)


def _db_path() -> pathlib.Path:
    cfg = get_config()
    p = pathlib.Path(cfg["database"]["path"])
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a SQLite connection with row_factory set."""
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist. Called at application startup."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            payload     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS disk_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            total_bytes INTEGER NOT NULL,
            used_bytes  INTEGER NOT NULL,
            free_bytes  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS smart_history (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts                      TEXT    NOT NULL,
            wear_leveling_count     INTEGER,
            reallocated_sector_count INTEGER,
            power_on_hours          INTEGER,
            temperature             REAL,
            media_errors            INTEGER
        );

        CREATE TABLE IF NOT EXISTS io_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ts              TEXT    NOT NULL,
            read_iops       REAL,
            write_iops      REAL,
            burst_write_rate REAL,
            rename_count    INTEGER
        );

        CREATE TABLE IF NOT EXISTS file_records (
            path            TEXT    PRIMARY KEY,
            size            INTEGER,
            last_access     INTEGER,
            last_modified   INTEGER,
            extension       TEXT,
            access_count    INTEGER DEFAULT 0,
            write_count     INTEGER DEFAULT 0,
            rename_count    INTEGER DEFAULT 0,
            updated_ts      TEXT
        );
        """)
    log.info("Database initialized at %s", _db_path())


def ingest_payload(payload: dict) -> None:
    """Persists all fields of a monitoring payload into the appropriate tables."""
    ts = payload.get("timestamp", "")

    with get_conn() as conn:
        # 1. Raw event
        conn.execute(
            "INSERT INTO raw_events (ts, payload) VALUES (?, ?)",
            (ts, json.dumps(payload))
        )

        # 2. Disk history
        dm = payload.get("disk_metrics", {})
        if dm:
            conn.execute(
                "INSERT INTO disk_history (ts, total_bytes, used_bytes, free_bytes) VALUES (?,?,?,?)",
                (ts, dm.get("total_bytes", 0), dm.get("used_bytes", 0), dm.get("free_bytes", 0))
            )

        # 3. SMART history
        sm = payload.get("smart_metrics", {})
        if sm:
            conn.execute(
                """INSERT INTO smart_history
                   (ts, wear_leveling_count, reallocated_sector_count,
                    power_on_hours, temperature, media_errors)
                   VALUES (?,?,?,?,?,?)""",
                (ts, sm.get("wear_leveling_count"), sm.get("reallocated_sector_count"),
                 sm.get("power_on_hours"), sm.get("temperature"), sm.get("media_errors"))
            )

        # 4. I/O history + aggregate rename counts from files
        io = payload.get("io_metrics", {})
        total_renames = sum(f.get("rename_count", 0) for f in payload.get("files", []))
        if io:
            conn.execute(
                """INSERT INTO io_history
                   (ts, read_iops, write_iops, burst_write_rate, rename_count)
                   VALUES (?,?,?,?,?)""",
                (ts, io.get("read_iops"), io.get("write_iops"),
                 io.get("burst_write_rate"), total_renames)
            )

        # 5. File records (upsert — latest wins)
        for f in payload.get("files", []):
            conn.execute(
                """INSERT INTO file_records
                   (path, size, last_access, last_modified, extension,
                    access_count, write_count, rename_count, updated_ts)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(path) DO UPDATE SET
                     size=excluded.size,
                     last_access=excluded.last_access,
                     last_modified=excluded.last_modified,
                     access_count=excluded.access_count,
                     write_count=excluded.write_count,
                     rename_count=excluded.rename_count,
                     updated_ts=excluded.updated_ts""",
                (f["path"], f.get("size", 0), f.get("last_access", 0),
                 f.get("last_modified", 0), f.get("extension", ""),
                 f.get("access_count", 0), f.get("write_count", 0),
                 f.get("rename_count", 0), ts)
            )

    log.debug("Ingested payload ts=%s files=%d", ts, len(payload.get("files", [])))


def query_all(table: str, limit: int = 1000) -> list[dict]:
    """Generic helper: return all rows from a table as dicts."""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def query_recent(table: str, limit: int = 200) -> list[dict]:
    """Return the most recent N rows ordered by id DESC then reversed."""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return list(reversed([dict(r) for r in rows]))
