# 🚢 Smart Port Intelligence System (SPIS)
## AI-Powered Port Operations Optimization Platform

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [System Architecture](#system-architecture)
5. [Feature 1: Port Demand Forecasting](#feature-1-port-demand-forecasting)
6. [Feature 2: Maritime Anomaly Detection](#feature-2-maritime-anomaly-detection)
7. [Feature 3: Smart Equipment Maintenance](#feature-3-smart-equipment-maintenance)
8. [Technology Stack](#technology-stack)
9. [Data Pipeline](#data-pipeline)
10. [Deployment Architecture](#deployment-architecture)
11. [Expected Outcomes](#expected-outcomes)
12. [Future Roadmap](#future-roadmap)

---

## Executive Summary

**Smart Port Intelligence System (SPIS)** is an AI-powered platform that transforms port operations through predictive analytics and real-time monitoring. The system addresses three critical challenges in modern port management:

| Challenge | Solution | Impact |
|-----------|----------|--------|
| Demand Uncertainty | AI-based demand forecasting | 20-30% better resource allocation |
| Security Threats | Real-time vessel anomaly detection | Early threat identification |
| Equipment Downtime | Predictive maintenance | 40% reduction in unplanned failures |

---

## Problem Statement

### The Port Operations Challenge

Modern ports face unprecedented challenges:

```
┌─────────────────────────────────────────────────────────────────┐
│                    GLOBAL PORT CHALLENGES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📦 DEMAND VOLATILITY                                           │
│     • 15-25% daily throughput variance                          │
│     • Seasonal spikes (holidays, trade cycles)                  │
│     • Supply chain disruptions (COVID, geopolitics)             │
│                                                                  │
│  🚢 SECURITY CONCERNS                                            │
│     • 60,000+ commercial vessels globally                       │
│     • Illegal fishing, smuggling, terrorism risks               │
│     • Manual AIS monitoring is impossible at scale              │
│                                                                  │
│  ⚙️ EQUIPMENT FAILURES                                           │
│     • Average crane downtime: $50,000/hour                      │
│     • Unplanned failures cause cascading delays                 │
│     • Reactive maintenance is 3x more expensive                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Matters

| Statistic | Impact |
|-----------|--------|
| $12B+ | Annual losses from port congestion globally |
| 30% | Equipment lifetime lost due to poor maintenance |
| 72 hours | Average delay from unexpected equipment failure |
| $4.5B | Annual maritime security threat costs |

---

## Solution Overview

### What We Built

SPIS is a **unified AI platform** with three integrated modules:

```
                    ┌─────────────────────────────────────┐
                    │   SMART PORT INTELLIGENCE SYSTEM    │
                    │          (SPIS Platform)            │
                    └─────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   FEATURE 1     │       │   FEATURE 2     │       │   FEATURE 3     │
│                 │       │                 │       │                 │
│  📊 DEMAND      │       │  🚨 ANOMALY     │       │  🔧 PREDICTIVE  │
│  FORECASTING    │       │  DETECTION      │       │  MAINTENANCE    │
│                 │       │                 │       │                 │
│  LSTM + TFT     │       │  Autoencoder    │       │  BiLSTM + Attn  │
│  + LightGBM     │       │  + Redpanda     │       │  + Risk Class   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         UNIFIED DASHBOARD           │
                    │         (React/Next.js)             │
                    └─────────────────────────────────────┘
```

### Key Innovations

| Innovation | Description |
|------------|-------------|
| **Vessel-Level Detection** | Aggregates multiple AIS points per vessel for robust anomaly scoring |
| **Dynamic Thresholding** | Thresholds computed from data, not hardcoded |
| **Real-Time Streaming** | Redpanda-based pipeline for millisecond latency |
| **Interpretable AI** | TFT provides feature importance for decision support |
| **Multi-Task Learning** | Shared representations across maintenance targets |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPIS ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │  DATA LAYER  │     │   ML LAYER   │     │  API LAYER   │                 │
│  ├──────────────┤     ├──────────────┤     ├──────────────┤                 │
│  │              │     │              │     │              │                 │
│  │ • AIS CSV    │────▶│ • LSTM       │────▶│ • FastAPI    │                 │
│  │ • Sensor CSV │     │ • TFT        │     │ • REST APIs  │                 │
│  │ • Supply CSV │     │ • Autoencoder│     │ • WebSocket  │                 │
│  │              │     │ • BiLSTM     │     │              │                 │
│  └──────────────┘     └──────────────┘     └──────────────┘                 │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │                    STREAMING LAYER (Redpanda)                 │           │
│  │  Topics: ais_raw → ais_scored | sensor_raw → alerts          │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │                    PRESENTATION LAYER                         │           │
│  │                                                               │           │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │           │
│  │   │  Demand     │  │  Anomaly    │  │ Maintenance │          │           │
│  │   │  Dashboard  │  │  Monitor    │  │  Dashboard  │          │           │
│  │   └─────────────┘  └─────────────┘  └─────────────┘          │           │
│  │                                                               │           │
│  │                    React/Next.js Frontend                     │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Microservices Architecture

| Service | Port | Responsibility |
|---------|------|----------------|
| `demand-api` | 8001 | Demand forecasting inference |
| `anomaly-api` | 8002 | Vessel anomaly detection |
| `maintenance-api` | 8003 | RUL & failure prediction |
| `redpanda` | 9092 | Event streaming broker |
| `frontend` | 3000 | Unified dashboard |

---

## Feature 1: Port Demand Forecasting

### Problem
> "How many containers will arrive in the next 7 days?"

Port operators need accurate demand forecasts to:
- Allocate crane operators and equipment
- Plan warehouse capacity
- Schedule vessel berths
- Coordinate trucking

### Data

| Dataset | Records | Date Range |
|---------|---------|------------|
| `port_throughput_synthetic.csv` | 1,127 days | Jan 2021 - Mar 2023 |

**Features:**
| Feature | Description | Range |
|---------|-------------|-------|
| `port_congestion_level` | Current congestion score | 0-10 |
| `warehouse_inventory_level` | Warehouse utilization | 400-900 |
| `handling_equipment_availability` | Equipment uptime % | 0.6-1.0 |
| `loading_unloading_time` | Avg operation hours | 1.5-4.5 |
| `weather_condition_severity` | Weather impact score | 0-1 |
| `delay_probability` | Delay likelihood | 0.2-0.8 |
| `historical_demand` | **TARGET** - daily containers | 800-6,500 |

### Models

#### Model 1: LSTM (Baseline)
```
Architecture:
Input (7 days × 6 features)
    → LSTM(64, return_sequences=True)
    → Dropout(0.2)
    → LSTM(32)
    → Dropout(0.2)
    → Dense(16, relu)
    → Dense(7)  # 7-day forecast

Training:
- Optimizer: Adam (lr=0.001)
- Loss: MSE
- Epochs: 100 with EarlyStopping
```

#### Model 2: Temporal Fusion Transformer (TFT)
```
Why TFT?
✅ Variable Selection Network → Shows which features matter
✅ Multi-Head Attention → Focuses on relevant timesteps
✅ Quantile Outputs → Prediction intervals (P10, P50, P90)
✅ 15-25% improvement over LSTM typically

Architecture:
Static Covariates + Known Future + Observed Past
    → Variable Selection Networks
    → LSTM Encoder/Decoder
    → Interpretable Multi-Head Attention
    → Quantile Dense Layers
```

#### Model 3: LightGBM (Complementary)
```
Why include trees?
✅ Handles tabular features naturally
✅ Built-in feature importance
✅ Fast training on small datasets
✅ Often wins on <10K samples

Feature Engineering:
- Lag features (t-1, t-7, t-14, t-30)
- Rolling statistics (mean, std, min, max)
- Calendar features (day of week, month, quarter)
```

### Ensemble Strategy
```python
final_prediction = (
    0.3 * lstm_pred +     # Baseline
    0.5 * tft_pred +      # Primary (best interpretability)
    0.2 * lgbm_pred       # Complementary
)
```

### Expected Metrics

| Model | MAE | MAPE | RMSE |
|-------|-----|------|------|
| LSTM (Baseline) | ~900 | ~18% | ~1200 |
| TFT | ~650 | ~12% | ~850 |
| LightGBM | ~700 | ~14% | ~900 |
| **Ensemble** | ~550 | ~10% | ~750 |

---

## Feature 2: Maritime Anomaly Detection

### Problem
> "Which vessels are behaving suspiciously in our port area?"

Port security teams need to identify:
- Vessels deviating from normal routes
- Unusual speed/course patterns
- Potential smuggling or illegal activity
- AIS spoofing or tampering

### Data

| Dataset | Description |
|---------|-------------|
| `ais_copenhagen_filtered.csv` | AIS data filtered to Danish waters |
| Bounding Box | Lat: 54.5-58.5, Lon: 7.0-16.0 |

**Features:**
| Feature | Description |
|---------|-------------|
| `Timestamp` | UTC datetime of AIS transmission |
| `MMSI` | Unique vessel identifier |
| `Latitude` | Vessel position |
| `Longitude` | Vessel position |
| `SOG` | Speed Over Ground (knots) |
| `COG` | Course Over Ground (degrees) |
| `Heading` | Vessel heading (degrees) |

### Model: Autoencoder

```
Why Autoencoder?
✅ Unsupervised learning (no labeled anomalies needed)
✅ Learns "normal" patterns automatically
✅ Anomaly = high reconstruction error

Architecture:
Input (7 features)
    → Dense(32, relu)
    → Dense(16, relu)
    → LATENT SPACE (8 dimensions)
    → Dense(16, relu)
    → Dense(32, relu)
    → Dense(7)  # Reconstruction

Training:
- Loss: MSE reconstruction error
- Epochs: 100 with EarlyStopping
- Threshold: 95th percentile of validation errors
```

### Key Innovation: Vessel-Level Detection

```
Traditional (Row-Level):
  Each AIS point scored independently
  Problem: One noisy reading = false alert

Our Approach (Vessel-Level):
  1. Collect all AIS points for a vessel (MMSI)
  2. Score each point
  3. Vessel Score = MAX(all point scores)
  4. Compare vessel score to threshold

Benefit: More robust, fewer false positives
```

### Real-Time Pipeline

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────┐
│ AIS Source  │────▶│ Redpanda │────▶│ Anomaly API  │────▶│ Dashboard │
│ (CSV/Live)  │     │ ais_raw  │     │ (Scoring)    │     │ (Alerts)  │
└─────────────┘     └──────────┘     └──────────────┘     └───────────┘
                         │                  │
                         │                  ▼
                         │           ┌──────────────┐
                         └──────────▶│ ais_scored   │
                                     │ (Results)    │
                                     └──────────────┘
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/detect` | POST | Manual single-point check |
| `/detect-vessel` | POST | Vessel-level check (multiple points) |
| `/live/vessels` | GET | All tracked vessels with status |
| `/live/alerts` | GET | Recent anomalies (last 50) |
| `/live/stats` | GET | Dashboard statistics |

### Risk Classification

| Risk Level | Condition | Action |
|------------|-----------|--------|
| LOW | Score < 0.5 × threshold | Normal monitoring |
| MEDIUM | 0.5 × threshold ≤ Score < threshold | Enhanced monitoring |
| HIGH | threshold ≤ Score < 1.5 × threshold | Investigate |
| CRITICAL | Score ≥ 1.5 × threshold | Immediate alert |

---

## Feature 3: Smart Equipment Maintenance

### Problem
> "When will this crane fail, and what will cause it?"

Port equipment failures cause:
- Average $50,000/hour downtime cost
- Cascading delays across operations
- Safety hazards for workers
- Customer dissatisfaction

### Data

| Dataset | Records |
|---------|---------|
| `port_maintenance_synthetic_3months.csv` | 3 months sensor data |

**Features:**
| Category | Features |
|----------|----------|
| **Sensor** | Temperature, Vibration, Pressure, Current, Voltage |
| **Operational** | Hours Since Maintenance, Operating Hours, Load% |
| **Categorical** | Asset Type (Crane/Forklift/Conveyor), Shift |

**Targets:**
| Target | Description |
|--------|-------------|
| `RUL` | Remaining Useful Life (hours) |
| `Failure_Within_72h` | Binary classification |
| `Risk_Classification` | Low/Medium/High/Critical |

### Models

#### Model 1: BiLSTM + Attention (RUL Prediction)
```
Why BiLSTM + Attention?
✅ Bidirectional: learns from past AND future context
✅ Attention: focuses on critical sensor readings
✅ Regression output: hours until failure

Architecture:
Input Sequence (24 timesteps × features)
    → Bidirectional LSTM(64)
    → Attention Layer
    → Bidirectional LSTM(32)
    → Dense(16, relu)
    → Dense(1)  # RUL in hours
```

#### Model 2: Multi-Task Learning
```
Why Multi-Task?
✅ Shared representations across related tasks
✅ Regularization effect improves generalization
✅ One model serves multiple purposes

Architecture:
Input → Shared LSTM Layers → Task-Specific Heads
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   RUL Head            Failure Head           Risk Head
   (Regression)        (Binary)               (Multi-class)
```

### Maintenance Strategy

| Prediction | Recommended Action |
|------------|-------------------|
| RUL > 500 hours | Normal operation |
| 100 < RUL ≤ 500 | Schedule maintenance |
| RUL ≤ 100 hours | Urgent maintenance |
| Failure within 72h = True | Immediate inspection |
| Risk = Critical | Stop equipment |

---

## Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **Python 3.10+** | Core language |
| **FastAPI** | REST API framework |
| **TensorFlow/Keras** | Deep learning models |
| **PyTorch** | TFT implementation |
| **scikit-learn** | Preprocessing, metrics |
| **pandas/numpy** | Data manipulation |
| **Redpanda** | Event streaming (Kafka-compatible) |

### Frontend

| Technology | Purpose |
|------------|---------|
| **Next.js 14** | React framework |
| **TypeScript** | Type safety |
| **CSS** | Styling (dark theme) |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **Redpanda Console** | Streaming monitoring |

---

## Data Pipeline

### Training Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Raw CSV    │────▶│  Filter &   │────▶│  Feature    │────▶│   Train     │
│  Data       │     │  Clean      │     │  Engineer   │     │   Model     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
                                                            ┌─────────────┐
                                                            │   Save      │
                                                            │   Artifacts │
                                                            │             │
                                                            │ • model.keras│
                                                            │ • scaler.pkl │
                                                            │ • threshold.json
                                                            └─────────────┘
```

### Inference Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  New Data   │────▶│  Preprocess │────▶│  Model      │────▶│  API        │
│  (API/Stream)│     │  (Scale)    │     │  Inference  │     │  Response   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Deployment Architecture

### Docker Compose Services

```yaml
services:
  # Event Streaming
  redpanda:
    image: redpandadata/redpanda
    ports: ["9092:9092"]
  
  # Feature 1: Demand Forecasting
  demand-api:
    build: ./services/demand
    ports: ["8001:8001"]
  
  # Feature 2: Anomaly Detection
  anomaly-api:
    build: ./services/anomaly
    ports: ["8002:8002"]
  
  # Feature 3: Maintenance Prediction
  maintenance-api:
    build: ./services/maintenance
    ports: ["8003:8003"]
  
  # Unified Frontend
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  # Monitoring
  redpanda-console:
    image: redpandadata/console
    ports: ["8080:8080"]
```

### Running the System

```bash
# Start all services
docker-compose up --build

# Access points
# http://localhost:3000   - Dashboard
# http://localhost:8001   - Demand API
# http://localhost:8002   - Anomaly API
# http://localhost:8003   - Maintenance API
# http://localhost:8080   - Redpanda Console
```

---

## Expected Outcomes

### Quantitative Benefits

| Metric | Current | With SPIS | Improvement |
|--------|---------|-----------|-------------|
| **Demand Forecast Accuracy** | ±30% | ±10% | **3x better** |
| **Anomaly Detection Time** | Hours | Seconds | **Real-time** |
| **Unplanned Downtime** | 15% | 5% | **67% reduction** |
| **Maintenance Costs** | $X | $0.6X | **40% savings** |

### Qualitative Benefits

```
┌────────────────────────────────────────────────────────────┐
│                    SPIS VALUE PROPOSITION                   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  👁️ VISIBILITY                                              │
│     • Real-time dashboards for all operations              │
│     • Early warning alerts before problems occur           │
│     • Historical trend analysis                            │
│                                                             │
│  🎯 DECISION SUPPORT                                        │
│     • AI-powered recommendations                           │
│     • Feature importance for interpretability              │
│     • Confidence intervals for risk assessment             │
│                                                             │
│  💰 COST REDUCTION                                          │
│     • Optimized resource allocation                        │
│     • Predictive vs reactive maintenance                   │
│     • Reduced equipment downtime                           │
│                                                             │
│  🔒 SECURITY                                                │
│     • Automated vessel behavior monitoring                 │
│     • Anomaly detection at scale                           │
│     • Risk-based alert prioritization                      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Future Roadmap

### Phase 2 Enhancements

| Feature | Description | Priority |
|---------|-------------|----------|
| **Chronos Integration** | Zero-shot forecasting baseline | High |
| **N-HiTS Model** | State-of-the-art long-horizon | High |
| **WebSocket Streaming** | Real-time dashboard updates | Medium |
| **LLM Recommendations** | Natural language insights | Medium |
| **Multi-Port Support** | Scale to multiple locations | Low |

### Model Improvements

```
Current → Future

LSTM → TFT + N-HiTS + LightGBM Ensemble
Autoencoder → Variational Autoencoder + Isolation Forest
BiLSTM → Transformer-based RUL prediction
```

### Infrastructure Scaling

```
Current (Single Node)                Future (Distributed)
┌──────────────┐                    ┌──────────────────────┐
│   Docker     │                    │   Kubernetes         │
│   Compose    │       ───▶         │   + Horizontal       │
│              │                    │   Auto-Scaling       │
└──────────────┘                    └──────────────────────┘
```

---

## Project Structure

```
DL_Final_Project/
├── PROJECT_DOCUMENTATION.md    # This file
├── README.md                   # Quick start guide
├── requirements.txt            # Python dependencies
│
├── data/
│   ├── raw/                    # Original datasets
│   │   ├── port_throughput_synthetic.csv
│   │   ├── port_maintenance_synthetic_3months.csv
│   │   └── dynamic_supply_chain_logistics_dataset.csv
│   └── processed/              # Cleaned data
│
├── models/                     # Saved model artifacts
│   ├── throughput_lstm_best.keras
│   ├── autoencoder_model.keras
│   ├── rul_bilstm_best.keras
│   ├── scaler.pkl
│   └── threshold.json
│
├── src/
│   ├── models/                 # Model architectures
│   │   ├── throughput_lstm.py
│   │   ├── rul_bilstm.py
│   │   └── multitask_lstm.py
│   └── data/                   # Preprocessors
│       └── throughput_preprocessor.py
│
├── services/
│   ├── anomaly/                # Feature 2 microservice
│   │   ├── app.py             # FastAPI application
│   │   ├── training/          # Training scripts
│   │   ├── models/            # Saved artifacts
│   │   ├── docker-compose.yml # Container orchestration
│   │   └── frontend/          # Next.js dashboard
│   │
│   ├── demand/                 # Feature 1 (to be added)
│   └── maintenance/            # Feature 3 (to be added)
│
└── notebooks/                  # Exploration & EDA
```

---

## Authors & Acknowledgments

**Smart Port Intelligence System (SPIS)**  
Deep Learning Final Project

---

*This documentation reflects the system design as of January 2026. For the latest updates, refer to the repository README.*
