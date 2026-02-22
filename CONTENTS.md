# Flash Intelligence Platform — File Contents Reference

This document describes every source file in the repository, grouped by component.

---

## Root

| File | Description |
|------|-------------|
| `README.md` | Quick-start guide, configuration reference, API docs, and macOS M1 notes |
| `ARCHITECTURE.md` | Mermaid system diagram, data flow, configuration hierarchy, and SQLite schema |
| `CONTENTS.md` | This file — per-file descriptions for every source file in the repository |

---

## flash-monitor-agent (Java 17 · Spring Boot 3 · Maven)

### Build & Configuration

| File | Description |
|------|-------------|
| `pom.xml` | Maven build descriptor. Declares Spring Boot 3.2 parent, Java 17, and dependencies: `spring-boot-starter-web`, `spring-boot-starter`, Jackson (`jackson-databind`, `jackson-datatype-jsr310`), `spring-boot-configuration-processor`, and test scope starters. Produces a self-contained fat JAR. |
| `src/main/resources/application.yml` | Fully commented YAML configuration. All agent parameters live here: scan root directory, max traversal depth, disk-collection interval (`monitor.disk.interval-ms`), I/O simulation toggle and base values, SMART device path and `smartctl` binary path, HTTP sender endpoint and timeouts, and logging levels. No magic numbers exist in source code. |

### Source — Root Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/FlashMonitorAgentApplication.java` | Spring Boot entry point. Enables `@EnableScheduling` for periodic tasks and `@EnableAsync` for non-blocking HTTP sends. Starts the embedded Tomcat server and all Spring beans. |

### Source — config Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/config/MonitorConfig.java` | Strongly-typed configuration class annotated with `@ConfigurationProperties(prefix = "monitor")`. Binds every `application.yml` key into nested static classes: `Scan`, `Disk`, `Io`, `Smart`, `Send`. Eliminates all string-key lookups from business logic. |

### Source — domain Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/domain/FileMetadata.java` | POJO representing a single file's snapshot. Fields: `path`, `size` (bytes), `lastAccessTime` (epoch ms), `lastModifiedTime` (epoch ms), `extension`, `accessCount`, `writeCount`, `renameCount`. Jackson `@JsonProperty` annotations map to the snake_case JSON sent to the Python core. |
| `src/main/java/com/flashintel/agent/domain/SmartMetrics.java` | POJO for SMART health fields: `wearLevelingCount`, `reallocatedSectorCount`, `powerOnHours`, `temperature`, `mediaErrors`. All fields default to `-1` to safely represent "not available". |
| `src/main/java/com/flashintel/agent/domain/DiskMetrics.java` | POJO for disk capacity: `totalBytes`, `usedBytes`, `freeBytes` — all in bytes. |
| `src/main/java/com/flashintel/agent/domain/IoMetrics.java` | POJO for I/O throughput: `readIOPS`, `writeIOPS`, `burstWriteRate`, and a `simulated` boolean flag indicating whether values are synthetic. |
| `src/main/java/com/flashintel/agent/domain/MonitorPayload.java` | Root payload assembled every 15 seconds. Contains `timestamp` (ISO-8601), `diskMetrics`, `smartMetrics`, `ioMetrics`, and `files` (list of `FileMetadata`). This is the exact JSON structure POSTed to `/ingest`. |

### Source — scanner Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/scanner/FileScanner.java` | Recursive file scanner using `Files.walkFileTree`. Reads `BasicFileAttributes` for size, lastAccess, lastModified. Detects file extension via simple dot-split. Optionally filters by configured extension list. Enriches each `FileMetadata` with live counters from `AccessFrequencyTracker`. Skips unreadable paths gracefully. |

### Source — tracker Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/tracker/FileStats.java` | Per-file event counters using `AtomicLong` for thread safety. Three counters: `accessCount`, `writeCount`, `renameCount`. Exposed via `increment*()` and `get*()` methods. |
| `src/main/java/com/flashintel/agent/tracker/AccessFrequencyTracker.java` | Java NIO `WatchService` implementation. Registers all subdirectories of the scan root (respecting max depth). Maps events: `ENTRY_MODIFY` → `writeCount++` + `accessCount++`; `ENTRY_CREATE` within 500ms of a `ENTRY_DELETE` → `renameCount++`. New subdirectories are registered dynamically. Runs on a dedicated daemon thread (`fip-watch-thread`). |

### Source — metrics Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/metrics/DiskMetricsCollector.java` | Uses `Files.getFileStore(scanRoot)` to obtain `totalSpace`, `usableSpace`. Computes `usedBytes = total - free`. Result stored in `AtomicReference<DiskMetrics>` for lock-free reads. Exposes `collect()` (called by sender) and `getLatest()`. |
| `src/main/java/com/flashintel/agent/metrics/SmartMetricsCollector.java` | Runs `smartctl -j -a <device>` via `ProcessBuilder`. Parses JSON output safely: `findSmartAttribute()` searches the `ata_smart_attributes.table` array by SMART ID (177 = wear leveling, 5 = reallocated sectors). Separate helpers `longAt()` and `doubleAt()` safely navigate nested JSON paths. All missing values default to `-1`. Warns on failure and returns safe defaults. |
| `src/main/java/com/flashintel/agent/metrics/IoMetricsCollector.java` | Dual-mode collector. **Simulation mode** (default on M1): applies configurable jitter (±N%) to baseline IOPS values using `Random`. **Real mode**: parses `iostat -d 1 1` third line for TPS value, derives read/write IOPS. Falls back to simulation on any parse failure. |

### Source — sender Package

| File | Description |
|------|-------------|
| `src/main/java/com/flashintel/agent/sender/JsonPayloadSender.java` | Orchestrates the full collection-and-send cycle as a `@Scheduled` + `@Async` Spring bean. On each tick: triggers all three collectors, calls `FileScanner.scan()`, assembles a `MonitorPayload`, serializes with Jackson, and sends via Java 11 `HttpClient.send()`. HTTP timeouts are configurable. Logs success (status code, file count) or failure without re-throwing. |

---

## flash-intelligence-core (Python 3.11 · FastAPI · scikit-learn · SQLite)

### Project Root

| File | Description |
|------|-------------|
| `requirements.txt` | Python dependencies: `fastapi`, `uvicorn[standard]`, `scikit-learn`, `pandas`, `numpy`, `statsmodels`, `pyyaml`, `aiofiles`, `httpx`. Pin-versioned for reproducibility. |
| `config.yaml` | Single source of truth for all Python-side parameters. Sections: `database` (SQLite path), `server`, `failure_prediction` (contamination, min_records, max_life_days), `ransomware` (std multiplier, spike thresholds, component weights), `storage_optimizer` (KMeans clusters, hotness weights), `growth_forecast` (full threshold %), `compression` (enable toggle, sample size, entropy→ratio mapping table), `archival` (recency threshold days, min size bytes, penalty weight, max candidates), `simulation` (compression ratio, wear reduction factor, lifespan factor). |

### app Package

| File | Description |
|------|-------------|
| `app/__init__.py` | Empty package marker. |
| `app/settings.py` | Parses `config.yaml` once via `@lru_cache`. All modules call `get_config()` to retrieve the config dict; no module opens the YAML file directly. |
| `app/db.py` | SQLite layer. `get_conn()` context manager handles commit/rollback. `init_db()` creates 5 tables: `raw_events`, `disk_history`, `smart_history`, `io_history`, `file_records`. `ingest_payload()` distributes one monitoring payload into all appropriate tables and performs an UPSERT for file records keyed on `path`. `query_all()` and `query_recent()` are generic helpers returning `list[dict]`. |
| `app/main.py` | FastAPI application factory. Uses `lifespan` context manager to call `init_db()` on startup. Adds `CORSMiddleware` allowing all origins (for dashboard and browser). Mounts `ingest` and `summary` routers. Provides a `/health` liveness probe. |

### app/routers Package

| File | Description |
|------|-------------|
| `app/routers/__init__.py` | Empty package marker. |
| `app/routers/ingest.py` | `POST /ingest` endpoint. Validates that `timestamp` is present in the payload. Calls `db.ingest_payload()`. Returns `{"status": "accepted", "timestamp": ..., "file_count": ...}` with HTTP 202. On error returns HTTP 500 with the exception message. |
| `app/routers/summary.py` | `GET /system-summary` endpoint. Accepts three optional query parameters for simulation overrides (`ransomware_spike`, `ssd_degradation_factor`, `growth_acceleration_factor`). Calls all six intelligence modules and the simulation engine, applies overrides in-place, and returns a flat JSON dict covering all intelligence outputs. |

### app/modules Package

| File | Description |
|------|-------------|
| `app/modules/__init__.py` | Empty package marker. |
| `app/modules/failure_prediction.py` | **SSD Failure Prediction.** Loads up to 500 recent SMART records. Replaces sentinel `-1` values with column medians. Fits `sklearn.linear_model.LinearRegression` on `wear_leveling_count` over time to compute slope. Fits `IsolationForest` on all 5 SMART features to compute anomaly fraction. Combines both into `failure_risk_score` (60% slope-based, 40% anomaly-based). Extrapolates remaining life assuming slope continues to a wear ceiling of 100. Returns `failure_risk_score`, `predicted_remaining_life_days`, `anomaly_detected`, `trend_slope`. |
| `app/modules/ransomware_detection.py` | **Ransomware Detection.** Loads recent I/O history. Computes `baseline_mean` and `baseline_std` of `write_iops` from all rows except the latest. Compares current `write_iops` against `baseline_mean + N*std`. Checks `rename_count` against spike threshold. Checks `burst_write_rate` against high threshold. Computes weighted `threat_score` from three normalized component scores. Returns `threat_score`, `iops_anomaly`, `rename_spike`, `burst_write_high`, `current_write_iops`, `baseline_write_iops`. |
| `app/modules/storage_optimizer.py` | **Storage Layout Optimization.** Loads all file records. Computes normalized features: `recency` (0=just accessed, 1=ancient), `frequency`, `write_intensity`, `size_norm`. Computes `hotness = 0.4×freq + 0.3×(1−recency) + 0.2×write_intensity + 0.1×size_norm`. Applies `KMeans(n_clusters=3)`. Labels clusters HOT/WARM/COLD by descending mean hotness. Returns `distribution` dict and per-file classifications. |
| `app/modules/growth_forecast.py` | **Storage Growth Forecast.** Loads disk history. Fits `LinearRegression` on time index → `used_bytes`. Extrapolates index when `used_bytes` reaches 90% of total capacity. Converts interval count to days (assuming 10-second collection intervals → 8640 intervals/day). Returns `days_to_full`, `history`, `current_used_pct`, `regression_slope_bytes_per_interval`. |
| `app/modules/compression_estimator.py` | **Compression Estimator.** Reads up to 64 KB from each tracked file. Computes Shannon entropy (bits per byte). Maps entropy to estimated compression ratio via a linear interpolation table from `config.yaml`. Aggregates total estimated savings. Returns `estimated_savings_bytes`, `aggregate_ratio`, and per-file `{entropy, ratio, savings_bytes}`. Skips files that don't exist or can't be read. |
| `app/modules/archival_recommendation.py` | **Archival Recommendation.** Calls `classify_storage()` to get cluster labels. Filters file records to COLD cluster + age > `recency_threshold_days` + size > `min_size_bytes`. Normalizes `size` and `write_count` within the eligible set. Computes `archive_score = size_norm - penalty_weight × write_intensity_norm`. Returns top N candidates sorted by score, plus `total_projected_space_savings`. |

### app/simulation Package

| File | Description |
|------|-------------|
| `app/simulation/__init__.py` | Empty package marker. |
| `app/simulation/engine.py` | **Simulation Engine.** Computes three projected outcomes: (1) `projected_capacity_after_archive` — current used minus archival savings divided by compression ratio; (2) `projected_wear_reduction` — fraction of COLD files × wear reduction factor from config; (3) `lifespan_extension_estimate_days` — wear reduction × lifespan days per unit. Accepts optional overrides dict to apply dashboard simulation factors. |
| `app/simulation/demo_generator.py` | **Demo Data Generator.** CLI tool (`python -m app.simulation.demo_generator`). Generates N synthetic monitoring payloads with realistic gradients (disk usage growing 180→210 GB, wear leveling slowly increasing, simulated file tree with varied access ages). `--ransomware N` injects extreme write and rename anomalies from record N onward. `--degradation` boosts wear and media error counts. Inserts directly into SQLite via `db.ingest_payload()`. |

---

## flash-dashboard (Python 3.11 · Streamlit · Plotly)

### Project Root

| File | Description |
|------|-------------|
| `requirements.txt` | Dashboard dependencies: `streamlit`, `plotly`, `requests`, `pandas`, `pyyaml`. |
| `config.yaml` | Dashboard settings: `api_base_url` (Intelligence Core URL), `refresh_interval_seconds`, `max_archival_rows`, and `ui` colors for HOT/WARM/COLD and risk gauges. |
| `app.py` | Main Streamlit application. Reads `config.yaml` on startup. Sidebar provides three simulation controls: ransomware spike toggle, SSD degradation slider (0–1), and growth acceleration slider (1–5×). Fetches `GET /system-summary` with query params matching slider state; result is cached via `@st.cache_data(ttl=refresh_interval_seconds)`. Renders all panels in order. Shows error block with restart instructions if the API is unreachable. Calls `st.rerun()` after `refresh_interval_seconds` sleep to auto-refresh. Injects dark CSS for premium aesthetics. |

### components Package

| File | Description |
|------|-------------|
| `components/__init__.py` | Empty package marker. |
| `components/gauges.py` | Two Plotly `go.Indicator` gauge figures, both built by a shared `_base_gauge()` factory. Gauge uses three color bands (green/amber/red) in `steps`, a white pointer bar, and a threshold line at the current value. Background is `#0F0F1A`. `render_failure_gauge(score)` and `render_ransomware_gauge(score)` are the public API. |
| `components/charts.py` | Two Plotly charts. `render_hwc_pie(distribution)` builds a donut chart with HOT/WARM/COLD slices colored `#FF4B4B`, `#FFA500`, `#00B4D8`. `render_growth_line(history, days_to_full)` draws a filled area chart of `used_pct` over time with a dashed 90% threshold line; the title embeds the `days_to_full` projection. Both charts use the dark `#0F0F1A` theme. |
| `components/tables.py` | `render_archival_table(candidates, max_rows)` converts the archival candidate list to a display `pd.DataFrame` with emoji-prefixed column names, truncated file paths (`…/dir/file`), rounded sizes, and integer counts. Ready for `st.dataframe()` with `hide_index=True`. |
| `components/summary_panel.py` | `render_summary_panel(data)` renders a 4-column metric row: archival savings (GB), projected used capacity (GB), wear reduction (%), lifespan extension (years+days friendly format). Below the metrics a `st.caption()` line shows tracked file count, eligible count, compression ratio, and compression savings in MB. |
