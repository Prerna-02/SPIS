# Smart Port Intelligence System - Project Status

**Last Updated:** 2026-01-31  
**Port:** Tallinn, Estonia

---

## Overview

The Smart Port Intelligence System (SPIS) consists of 4 deep learning features:

| Feature | Name | Purpose |
|---------|------|---------|
| 1 | Port Throughput Forecasting | Predict port demand 7 days ahead |
| 2 | Anomaly Detection | Detect unusual patterns in operations |
| 3 | Smart Maintenance | Predictive equipment maintenance |
| 4 | Knowledge Graph + Optimization | Real-time berth optimization |

---

## Completed Work

### Feature 1: Port Throughput Forecasting ✅
| Component | Status | Notes |
|-----------|--------|-------|
| TCN Model | ✅ Done | Temporal Convolutional Network for 7-day forecast |
| LightGBM Baseline | ✅ Done | Horizon-specific models for comparison |
| Data Pipeline | ✅ Done | `tallinn_feature1_daily_v2.csv` (4,167 records) |
| Model Training | ✅ Done | 56-day input window, 7-day output |
| Evaluation | ✅ Done | sMAPE ~6%, R² 0.75 for throughput |

**Best Model:** TCN (outperforms LightGBM on both port_calls and throughput_containers)

---

### Feature 2: Anomaly Detection ✅
| Component | Status | Notes |
|-----------|--------|-------|
| Anomaly Model | ✅ Done | Detects unusual operational patterns |
| Data Processing | ✅ Done | Historical operational data |
| Services | ✅ Done | Located in `services/anomaly/` |

---

### Feature 3: Smart Maintenance ✅
| Component | Status | Notes |
|-----------|--------|-------|
| Predictive Model | ✅ Done | Equipment failure prediction |
| RUL Estimation | ✅ Done | Remaining Useful Life in hours |
| Equipment Data | ✅ Done | Sensors: motor_temp, vibration, pressure, etc. |
| Integration with F4 | ✅ Done | Feeds equipment health to KG |

**Key Outputs:** `failure_in_next_72h`, `rul_hours`, `health_score`

---

### Feature 4: Knowledge Graph + Optimization ✅
| Component | Status | Notes |
|-----------|--------|-------|
| Neo4j KG | ✅ Done | Vessel, Berth, Zone, Asset nodes |
| AIS Stream Integration | ✅ Done | Live vessel tracking (Tallinn area) |
| Zone Classification | ✅ Done | APPROACH → ANCHORAGE → BERTH |
| CP-SAT Optimizer | ✅ Done | Constraint-based berth assignment |
| Cascade Explanation | ✅ Done | Shows downstream delay impacts |
| API Endpoints | ✅ Done | `/optimizer/run`, `/plans/{id}`, `/kg/cascade/{id}` |

**Key Deliverables:**
- Real-time port state from AIS
- Optimized berth assignments (minimize delay + congestion)
- Cascade explanations with berth context

---

## Pending Work

### Frontend Integration 🔄

| Task | Priority | Details |
|------|----------|---------|
| Feature 1 Dashboard | High | 7-day forecast charts, horizon accuracy |
| Feature 4 UI | High | Berth timeline, cascade visualization |
| Connect to KG APIs | High | `/optimizer/run`, `/kg/cascade/{id}` |
| Real-time Vessel Map | Medium | Display vessel positions from AIS |

### Docker Deployment 🔄

| Service | Status | Location |
|---------|--------|----------|
| Neo4j | ✅ Ready | Use `neo4j:5.15.0` image |
| KG API (FastAPI) | ❌ Needs Dockerfile | `services/kg/` |
| AIS Ingestion | ❌ Needs Dockerfile | `services/ais_ingestion/` |
| Anomaly Service | ❌ Needs Dockerfile | `services/anomaly/` |
| Frontend (Next.js) | ❌ Needs Dockerfile | TBD |

### Recommended Docker Compose

```yaml
services:
  neo4j:
    image: neo4j:5.15.0
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/portintel2026

  kg-api:
    build: ./services/kg
    ports: ["8000:8000"]
    depends_on: [neo4j]

  ais-ingestion:
    build: ./services/ais_ingestion
    depends_on: [neo4j]

  anomaly-service:
    build: ./services/anomaly
    ports: ["8001:8001"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [kg-api]
```

---

## Environment Variables

```env
# AIS Stream
AISSTREAM_API_KEY=your_key_here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=portintel2026
```

---

## Running Locally

```bash
# 1. Start Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/portintel2026 neo4j:5.15.0

# 2. Initialize KG schema
cd services/kg && python schema.py

# 3. Start KG API
cd services/kg && uvicorn api:app --reload --port 8000

# 4. Start AIS ingestion (with Neo4j)
cd services/ais_ingestion && python app.py --mode live --neo4j

# 5. Access Swagger UI
http://localhost:8000/docs
```

---

## Documentation

| File | Description |
|------|-------------|
| [FEATURE1_DOCUMENTATION.md](file:///e:/DL_Final_Project/docs/FEATURE1_DOCUMENTATION.md) | Detailed Feature 1 documentation |
| [Feature4_KG_Optimization.md](file:///e:/DL_Final_Project/docs/Feature4_KG_Optimization.md) | Feature 4 phases + CP-SAT explanation |
| [TRD_v2.md](file:///e:/DL_Final_Project/docs/TRD_v2.md) | Technical Requirements Document |
