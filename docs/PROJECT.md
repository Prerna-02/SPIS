# SPIS - Smart Port Intelligence System
## End-to-End Project Documentation

**Port:** Tallinn, Estonia  
**Last Updated:** February 2026  
**Version:** 1.0

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Feature 1: Port Throughput Forecasting](#feature-1-port-throughput-forecasting)
4. [Feature 2: Maritime Anomaly Detection](#feature-2-maritime-anomaly-detection)
5. [Feature 3: Smart Maintenance](#feature-3-smart-maintenance)
6. [Feature 4: Knowledge Graph + Optimization](#feature-4-knowledge-graph--optimization)
7. [Frontend Dashboard](#frontend-dashboard)
8. [Project Structure](#project-structure)
9. [Running the System](#running-the-system)

---

## Executive Summary

SPIS is an AI-powered port intelligence system for the **Port of Tallinn, Estonia**, implementing 4 deep learning features to optimize maritime operations:

| Feature | Purpose | Deep Learning Model | Port |
|---------|---------|---------------------|------|
| 1 | Demand Forecasting | TCN + LightGBM | 8000 |
| 2 | Anomaly Detection | Autoencoder | 8002 |
| 3 | Predictive Maintenance | BiLSTM | 8003 |
| 4 | Berth Optimization | CP-SAT + Neo4j | 8000 |

### Key Achievements
- **7-day demand forecasting** with sMAPE ~6%
- **Real-time anomaly detection** with 92% recall
- **RUL prediction** for equipment health
- **Optimal berth assignments** with cascade impact analysis

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                            │
│                         http://localhost:3000                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Landing Page │ Forecasting │ Anomaly │ Maintenance │ Optimization      │
└───────┬───────┴──────┬──────┴────┬────┴──────┬──────┴────────┬──────────┘
        │              │           │           │               │
        ▼              ▼           ▼           ▼               ▼
┌───────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────────┐
│    Weather    │ │Feature 1 │ │Feature 2│ │Feature 3 │ │   Feature 4     │
│  Open-Meteo   │ │   TCN    │ │Autoenc. │ │ BiLSTM   │ │ Neo4j + CP-SAT  │
│     API       │ │LightGBM  │ │ :8002   │ │  :8003   │ │     :8000       │
└───────────────┘ └──────────┘ └─────────┘ └──────────┘ └─────────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────┐
                                                        │   Neo4j     │
                                                        │   :7687     │
                                                        └─────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────┐
                                                        │ AIS Stream  │
                                                        │   Live      │
                                                        └─────────────┘
```

---

## Feature 1: Port Throughput Forecasting

### Purpose
Predict **port demand (port calls & container throughput)** for the next 7 days to enable resource planning.

### Deep Learning Model: TCN (Temporal Convolutional Network)

```
Input (56 days × 16 features) → TCN Encoder → Dense Layers → Output (7 days × 2 targets)
```

| Component | Details |
|-----------|---------|
| **Architecture** | TCN with dilated convolutions |
| **Input Window** | 56 days of historical data |
| **Output Horizon** | 7-day forecast |
| **Features** | 16 (weather, operations, cargo mix, calendar) |
| **Targets** | `port_calls`, `throughput_containers` |

### Model Comparison

| Model | Target | sMAPE | R² | MAE |
|-------|--------|-------|-----|-----|
| **TCN** | port_calls | **5.76%** | -0.002 | 11.0 |
| **TCN** | throughput_containers | **6.24%** | **0.749** | 1,688 |
| LightGBM | port_calls | 6.16% | 0.161 | 11.5 |
| LightGBM | throughput_containers | 6.52% | 0.598 | 1,761 |

**Winner:** TCN outperforms LightGBM on both targets.

### Data Pipeline
- **Dataset:** `tallinn_feature1_daily_v2.csv` (4,167 records)
- **Date Range:** January 2014 - May 2025
- **Train/Val/Test:** 70% / 15% / 15% chronological split

### Files
| File | Purpose |
|------|---------|
| `services/forecasting/tcn_model.py` | TCN model definition |
| `services/forecasting/training.ipynb` | Model training notebook |
| `data/processed/tallinn_feature1_daily_v2.csv` | Training data |

---

## Feature 2: Maritime Anomaly Detection

### Purpose
Detect **unusual vessel behavior** in real-time using AIS data to identify potential security threats.

### Deep Learning Model: Denoising Autoencoder

```
Input (7 features) → Encoder [64→32→16→8] → Decoder [16→32→64] → Output (7 features)
```

| Component | Details |
|-----------|---------|
| **Architecture** | Deep Denoising Autoencoder |
| **Latent Dimension** | 8 |
| **Loss Function** | Mean Squared Error (MSE) |
| **Threshold** | 95th percentile (0.3179) |
| **Noise Factor** | 0.1 (denoising) |

### How It Works
1. **Train on normal data only** - learns to reconstruct typical vessel patterns
2. **Reconstruction error** = anomaly score
3. If error > threshold → flag as anomaly

### Input Features
| Feature | Description |
|---------|-------------|
| timestamp | Unix epoch seconds |
| MMSI | Vessel identifier |
| latitude | Decimal degrees |
| longitude | Decimal degrees |
| SOG | Speed Over Ground (knots) |
| COG | Course Over Ground (degrees) |
| heading | Vessel heading (degrees) |

### Performance Metrics
| Metric | Value |
|--------|-------|
| Precision | 89% |
| Recall | 92% |
| F1 Score | 0.90 |
| AUC-ROC | 0.94 |
| False Positive Rate | 8% |

### Risk Levels
| Level | Condition | Action |
|-------|-----------|--------|
| LOW | score < threshold×0.5 | Normal monitoring |
| MEDIUM | score < threshold | Enhanced monitoring |
| HIGH | score < threshold×1.5 | Investigate |
| CRITICAL | score ≥ threshold×1.5 | Alert security |

### Files
| File | Purpose |
|------|---------|
| `services/anomaly/app.py` | FastAPI service (port 8002) |
| `services/anomaly/models/autoencoder_model.keras` | Trained model |
| `services/anomaly/models/threshold.json` | Threshold config |

### API Endpoints
```bash
GET  /health              # Health check
GET  /simulate?count=10   # Demo vessel data
GET  /timeseries?hours=24 # Hourly anomaly data
POST /detect              # Single point detection
GET  /model-info          # Model architecture
```

---

## Feature 3: Smart Maintenance

### Purpose
Predict **equipment failures** and estimate **Remaining Useful Life (RUL)** for port equipment.

### Deep Learning Model: BiLSTM (Bidirectional LSTM)

```
Input (Sensor Time Series) → BiLSTM Layers → Multi-Task Head → [Failure Prob, RUL]
```

| Component | Details |
|-----------|---------|
| **Architecture** | Bidirectional LSTM |
| **Task 1** | Binary classification (failure in 72h) |
| **Task 2** | RUL regression (hours remaining) |
| **Equipment Types** | Cranes, Forklifts, Conveyor Belts |

### Sensor Inputs
| Sensor | Description |
|--------|-------------|
| motor_temperature | Motor temp (°C) |
| vibration_level | Vibration (mm/s) |
| pressure | Hydraulic pressure (bar) |
| load_capacity | Current load (%) |
| operating_hours | Cumulative hours |
| last_maintenance | Hours since service |

### Outputs
| Output | Description |
|--------|-------------|
| `failure_in_next_72h` | Binary (0/1) |
| `rul_hours` | Remaining useful life |
| `health_score` | 0-100 equipment health |

### Equipment Inventory
| Type | Count | Sensors |
|------|-------|---------|
| Crane | 6 | temp, vibration, load |
| Forklift | 12 | temp, pressure, hours |
| Conveyor Belt | 8 | vibration, speed |

### Files
| File | Purpose |
|------|---------|
| `services/maintenance/app.py` | FastAPI service (port 8003) |
| `services/maintenance/models/` | Trained BiLSTM model |
| `data/processed/maintenance_records.csv` | Training data |

### API Endpoints
```bash
GET  /health              # Health check
GET  /stream?count=5      # Live equipment data
GET  /stats               # Operational statistics
POST /predict             # RUL prediction
GET  /model-info          # Model metrics
```

---

## Feature 4: Knowledge Graph + Optimization

### Purpose
**Optimize berth assignments** using constraint programming and visualize cascade impacts.

### Technology Stack
| Component | Technology |
|-----------|------------|
| Graph Database | Neo4j 5.15 |
| Optimizer | Google OR-Tools CP-SAT |
| Live Data | AISStream WebSocket |
| API | FastAPI (port 8000) |

### Knowledge Graph Schema

```
(:Vessel)-[:APPROACHING]->(:Zone)-[:ADJACENT]->(:Berth)
(:Vessel)-[:ASSIGNED_TO]->(:Berth)
(:Berth)-[:HAS_EQUIPMENT]->(:Asset)
(:Plan)-[:CONTAINS]->(:Assignment)
```

### Zone Flow
```
APPROACH (>5nm) → ANCHORAGE (1-5nm) → BERTH (<1nm)
```

### CP-SAT Optimization Model

**Decision Variables:**
```python
assign[v, b]  # Binary: vessel v assigned to berth b
start[v]      # Start time (minutes)
end[v]        # End time (minutes)
delay[v]      # Delay from ETA
```

**Constraints:**
| Constraint | Description |
|------------|-------------|
| One Berth | Each vessel → exactly one berth |
| No Overlap | Same berth vessels don't overlap |
| Service Time | end = start + (containers ÷ rate) |
| ETA Respect | start ≥ arrival time |

**Objective Function:**
```
Minimize: 0.40 × Total Delay
        + 0.25 × Congestion Penalty
        + 0.20 × Operating Cost
        + 0.15 × Priority Violation
```

### Cascade Explanation
Shows downstream impacts when inserting extra vessels:
```
Berth B3 occupied by MMSI 276482000 until 14:30 → your start pushed to 15:00
```

### Port Inventory
| Asset | Count | Details |
|-------|-------|---------|
| Berths | 4 | B1-B2 (Old City), B3-B4 (Muuga) |
| Cranes | 6 | 2 per container berth |
| Yard Blocks | 3 | 10,000 TEU capacity |

### Files
| File | Purpose |
|------|---------|
| `services/kg/api.py` | FastAPI service (port 8000) |
| `services/kg/optimizer.py` | CP-SAT model |
| `services/kg/neo4j_client.py` | Graph operations |
| `services/kg/zones.py` | Zone classification |
| `services/ais_ingestion/app.py` | Live AIS feed |

### API Endpoints
```bash
GET  /health                    # Health check
GET  /kg/snapshot               # Current port state
POST /optimizer/scenario        # Create scenario
POST /optimizer/run             # Run optimization
GET  /plans/{plan_id}           # Get plan details
GET  /kg/cascade/{plan_id}      # Cascade impacts
```

---

## Frontend Dashboard

### Technology
- **Framework:** Next.js 14
- **Styling:** Tailwind CSS + Glassmorphic Theme
- **Charts:** Recharts

### Pages
| Route | Description |
|-------|-------------|
| `/` | Landing page with weather, vessel count, feature cards |
| `/details` | Company and terminal information |
| `/map` | Port Tallinn 3D map |
| `/forecasting` | 7-day demand forecast |
| `/anomaly` | Real-time anomaly detection |
| `/maintenance` | Equipment health monitoring |
| `/optimization` | Berth assignment optimization |

### Design
- **Theme:** Dark glassmorphic with backdrop blur
- **Background:** Port image with slate overlay
- **Navigation:** Home → Details → Map + Feature tabs

---

## Project Structure

```
e:\DL_Final_Project\
├── frontend/                    # Next.js frontend
│   ├── app/
│   │   ├── page.tsx            # Landing page
│   │   ├── forecasting/        # Feature 1 UI
│   │   ├── anomaly/            # Feature 2 UI
│   │   ├── maintenance/        # Feature 3 UI
│   │   ├── optimization/       # Feature 4 UI
│   │   ├── details/            # About page
│   │   ├── map/                # Port map
│   │   └── components/         # Shared components
│   └── public/                 # Static assets
├── services/
│   ├── forecasting/            # Feature 1 backend
│   ├── anomaly/                # Feature 2 backend (port 8002)
│   ├── maintenance/            # Feature 3 backend (port 8003)
│   ├── kg/                     # Feature 4 backend (port 8000)
│   └── ais_ingestion/          # Live AIS data
├── data/
│   ├── raw/                    # Raw datasets
│   └── processed/              # Cleaned datasets
├── models/                     # Trained model artifacts
├── notebooks/                  # Training notebooks
└── docs/                       # Documentation
```

---

## Running the System

### Prerequisites
- Python 3.10+
- Node.js 18+
- Neo4j Desktop or Docker
- Docker (optional)

### Quick Start (5 Terminals)

```powershell
# Terminal 1: Neo4j
cd e:\DL_Final_Project\services\kg
docker-compose up -d

# Terminal 2: KG API (port 8000)
cd e:\DL_Final_Project\services\kg
python -m uvicorn api:app --reload --port 8000

# Terminal 3: Anomaly API (port 8002)
cd e:\DL_Final_Project\services\anomaly
python -m uvicorn app:app --reload --port 8002

# Terminal 4: Maintenance API (port 8003)
cd e:\DL_Final_Project\services\maintenance
python -m uvicorn app:app --reload --port 8003

# Terminal 5: Frontend (port 3000)
cd e:\DL_Final_Project\frontend
npm run dev
```

### Access URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| KG API Docs | http://localhost:8000/docs |
| Anomaly API Docs | http://localhost:8002/docs |
| Maintenance API Docs | http://localhost:8003/docs |
| Neo4j Browser | http://localhost:7474 |

---

## Environment Variables

Create `.env` file:
```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=portintel2026

# AIS Stream
AISSTREAM_API_KEY=your_key_here
```

---

## Summary

| Feature | Model | Input | Output | Status |
|---------|-------|-------|--------|--------|
| 1. Forecasting | TCN | 56-day history | 7-day forecast | ✅ Complete |
| 2. Anomaly | Autoencoder | AIS data | Anomaly score | ✅ Complete |
| 3. Maintenance | BiLSTM | Sensor data | RUL, health | ✅ Complete |
| 4. Optimization | CP-SAT | Port state | Berth assignments | ✅ Complete |
| Frontend | Next.js | - | Dashboard | ✅ Complete |

---

**End of Documentation**
