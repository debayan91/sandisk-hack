# Flash Intelligence Platform

> **Modular hybrid system for real-time SSD health analytics, ransomware detection, and storage optimization.**
> Designed for macOS Apple Silicon (M1). All components run locally.

---

## Architecture

```
Java Monitor Agent ──POST /ingest──▶ Python Intelligence Core ──GET /system-summary──▶ Streamlit Dashboard
        │                                       │
   (Spring Boot)                           (FastAPI + SQLite)
```

---

## Components

| Directory                   | Tech                    | Role                              |
|-----------------------------|-------------------------|-----------------------------------|
| `flash-monitor-agent/`      | Java 17, Spring Boot 3  | File scan, SMART, IOPS collection |
| `flash-intelligence-core/`  | Python 3.11, FastAPI    | AI analytics, SQLite, REST API    |
| `flash-dashboard/`          | Python 3.11, Streamlit  | Live dashboard with simulation UI |

---

## Quick Start

### 1. Python Intelligence Core

```bash
cd flash-intelligence-core
pip install -r requirements.txt

# Seed demo data (no Java agent needed for demo)
python -m app.simulation.demo_generator --records 80

# Start server
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/docs

### 2. Streamlit Dashboard

```bash
cd flash-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Open: http://localhost:8501

### 3. Java Monitoring Agent *(requires Java 17 + Maven)*

```bash
cd flash-monitor-agent
mvn spring-boot:run
```

The agent sends a payload every 15 seconds to `http://localhost:8000/ingest`.

---

## Configuration

| File | Purpose |
|------|---------|
| `flash-monitor-agent/src/main/resources/application.yml` | Java agent: scan root, intervals, device paths |
| `flash-intelligence-core/config.yaml` | Python: all ML weights, thresholds, archival rules |
| `flash-dashboard/config.yaml` | Dashboard: API URL, refresh interval, colors |

> ⚠️ The Java agent uses `monitor.io.simulate=true` by default — required on macOS M1.
> ⚠️ `smartctl` must be installed via Homebrew for real SMART data: `brew install smartmontools`.

---

## Demo Simulation Scenarios

| Scenario | Command |
|----------|---------|
| Normal 7-day growth | `python -m app.simulation.demo_generator` |
| Ransomware spike at record 50 | `python -m app.simulation.demo_generator --ransomware 50` |
| SSD degradation pattern | `python -m app.simulation.demo_generator --degradation` |
| Combined, 200 records | `python -m app.simulation.demo_generator --records 200 --ransomware 150 --degradation` |

Dashboard simulation toggles (sidebar) apply on top of real or demo data in real time.

---

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Ingest a monitoring payload |
| `/system-summary` | GET | Full intelligence report |
| `/health` | GET | Liveness check |

### Simulation Query Params for `/system-summary`

| Param | Type | Default | Effect |
|-------|------|---------|--------|
| `ransomware_spike` | bool | false | Boosts threat score +60 |
| `ssd_degradation_factor` | float 0–1 | 0 | Increases failure risk, reduces life estimate |
| `growth_acceleration_factor` | float 0.5–5 | 1.0 | Compresses days_to_full |

---

## Intelligence Modules

| Module | Algorithm | Output |
|--------|-----------|--------|
| Failure Prediction | Linear slope + IsolationForest | `failure_risk_score`, `predicted_remaining_life_days` |
| Ransomware Detection | Baseline ± 3σ + rename/burst | `ransomware_threat_score` |
| Storage Optimizer | KMeans n=3 on hotness features | HOT / WARM / COLD labels |
| Growth Forecast | LinearRegression on disk history | `days_to_full` |
| Compression Estimator | Shannon entropy → ratio mapping | estimated savings bytes |
| Archival Recommendation | COLD filter + archive_score rank | ranked candidate list |

---

## macOS M1 Notes

- **SMART data**: Real data requires Homebrew `smartmontools`. Without it, the agent returns safe defaults (-1).
- **IOPS**: Apple Silicon does not expose raw IOPS in userspace. Set `monitor.io.simulate=true` (default).
- **WatchService**: macOS uses `kqueue` under the hood. Some system directories may require Full Disk Access in System Preferences for the Java agent.
