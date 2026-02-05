# SPIS - Smart Port Intelligence System
## Startup & Recovery Guide

This guide explains how to start all services and recover if the system fails.

---

## 📋 Prerequisites

Before starting, ensure you have:
- **Python 3.10+** installed
- **Node.js 18+** installed
- **Neo4j Desktop** running (for KG + Optimization feature)
- **Docker** (optional, for Redpanda/Kafka)

---

## 🚀 Quick Start - All Services

Open **5 separate terminals** and run these commands:

### Terminal 1: Neo4j (Required for KG)
```powershell
# Start Neo4j Desktop manually, or use Docker:
cd e:\DL_Final_Project\services\kg
docker-compose up -d
```

### Terminal 2: KG + Optimization API (Port 8000)
```powershell
cd e:\DL_Final_Project\services\kg
python -m uvicorn api:app --reload --port 8000
```

### Terminal 3: Anomaly Detection API (Port 8002)
```powershell
cd e:\DL_Final_Project\services\anomaly
python -m uvicorn app:app --reload --port 8002
```

### Terminal 4: Maintenance API (Port 8003)
```powershell
cd e:\DL_Final_Project\services\maintenance
python -m uvicorn app:app --reload --port 8003
```

### Terminal 5: Frontend (Port 3000)
```powershell
cd e:\DL_Final_Project\frontend
npm run dev
```

### Optional: AIS Ingestion (Live Data)
```powershell
cd e:\DL_Final_Project\services\ais_ingestion
python app.py
```

---

## 🔍 Service Overview

| Feature | Service | Port | API Endpoint |
|---------|---------|------|--------------|
| KG + Optimization | `services/kg/api.py` | 8000 | http://localhost:8000 |
| Anomaly Detection | `services/anomaly/app.py` | 8002 | http://localhost:8002 |
| Smart Maintenance | `services/maintenance/app.py` | 8003 | http://localhost:8003 |
| Frontend | `frontend/` | 3000 | http://localhost:3000 |
| AIS Ingestion | `services/ais_ingestion/app.py` | - | Background service |

---

## 🛠️ Recovery Commands

### If a service crashes:
Re-run the command for that specific service from the table above.

### If Neo4j connection fails:
```powershell
# Check Neo4j is running
cd e:\DL_Final_Project\services\kg
docker-compose ps

# Restart Neo4j
docker-compose restart neo4j
```

### If frontend fails:
```powershell
cd e:\DL_Final_Project\frontend
npm install  # Reinstall dependencies if needed
npm run dev
```

### If Python APIs fail with module errors:
```powershell
# Install dependencies for each service
cd e:\DL_Final_Project\services\kg
pip install -r requirements.txt

cd e:\DL_Final_Project\services\anomaly
pip install -r requirements.txt

cd e:\DL_Final_Project\services\maintenance
pip install -r requirements.txt
```

---

## ✅ Health Check

After starting all services, verify they're running:

| Service | Test URL | Expected |
|---------|----------|----------|
| Frontend | http://localhost:3000 | Landing page loads |
| KG API | http://localhost:8000/health | `{"status": "ok"}` |
| Anomaly API | http://localhost:8002/health | `{"status": "ok"}` |
| Maintenance API | http://localhost:8003/health | `{"status": "ok"}` |

---

## 📁 Project Structure

```
e:\DL_Final_Project\
├── frontend/               # Next.js frontend (port 3000)
├── services/
│   ├── kg/                 # Knowledge Graph + Optimization (port 8000)
│   ├── anomaly/            # Anomaly Detection (port 8002)
│   ├── maintenance/        # Smart Maintenance (port 8003)
│   ├── forecasting/        # Demand Forecasting (embedded)
│   └── ais_ingestion/      # Live AIS data ingestion
├── data/                   # Datasets and models
└── docs/                   # Documentation
```

---

## 🔧 Troubleshooting

### Port already in use
```powershell
# Find and kill process on port
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Neo4j authentication error
Edit `services/kg/config.py`:
```python
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"
```

### Frontend build errors
```powershell
cd e:\DL_Final_Project\frontend
rm -rf node_modules .next
npm install
npm run dev
```

---

## 📞 Contact

For issues, check the logs in each terminal window for error messages.
