# SPIS - Docker-Free Setup Guide

**No Docker required!** Run everything locally with native installations.

## Benefits
- ✅ No Docker Desktop (saves 2-10 GB on C: drive)
- ✅ Faster startup (no container overhead)
- ✅ Less RAM usage
- ✅ Install databases on D: drive
- ✅ Databases run as Windows services (auto-start)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL INSTALLATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   D:\PostgreSQL\15\                                          │
│   └── data\                    ← PostgreSQL data files       │
│                                                              │
│   D:\Neo4j\                                                  │
│   └── data\                    ← Neo4j graph database        │
│                                                              │
│   E:\DL_Final_Project\                                       │
│   ├── .venv\                   ← Python environment          │
│   ├── services\                ← All Python services         │
│   ├── frontend\                ← Next.js frontend            │
│   └── data\raw\aisstream_logs\ ← AIS data (JSONL files)      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Install PostgreSQL (D: Drive)

### Download
1. Go to: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Download **PostgreSQL 15** for Windows x86-64

### Install
1. Run the installer
2. **IMPORTANT**: When asked for installation directory, change to:
   ```
   D:\PostgreSQL\15
   ```
3. **Data Directory**: 
   ```
   D:\PostgreSQL\15\data
   ```
4. **Password**: Set to `spis_dev_password` (to match your config)
5. **Port**: Keep default `5432`
6. **Locale**: Default

### Post-Install: Create Database & User
Open **pgAdmin** or **SQL Shell (psql)** and run:

```sql
-- Create the database
CREATE DATABASE spis;

-- Create the user
CREATE USER spis_user WITH PASSWORD 'spis_dev_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE spis TO spis_user;

-- Connect to spis database
\c spis

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO spis_user;
```

### Initialize Schema
In pgAdmin or psql, connect to `spis` database and run:
```sql
-- Copy contents from: E:\DL_Final_Project\db\init\01_schema.sql
```

Or use command line:
```powershell
cd E:\DL_Final_Project\db\init
psql -U postgres -d spis -f 01_schema.sql
```

---

## Step 2: Install Neo4j Desktop (D: Drive)

### Download
1. Go to: https://neo4j.com/deployment-center/?desktop-gdb
2. Download **Neo4j Desktop** for Windows
3. You'll need to create a free account

### Install on D: Drive
1. Run the installer
2. When prompted, install to: `D:\Neo4j Desktop`
3. Or set environment variable BEFORE installing:
   ```powershell
   [Environment]::SetEnvironmentVariable("NEO4J_DESKTOP_DATA_PATH", "D:\Neo4j\data", "User")
   ```

### Create Database
1. Open Neo4j Desktop
2. Click "New" → "Create project"
3. Name it "SPIS"
4. Click "Add" → "Local DBMS"
5. **Name**: spis-graph
6. **Password**: `portintel2026` (to match your config)
7. **Version**: 5.x (latest)
8. Click "Create"
9. Click "Start" to run the database

### Verify Connection
- **Bolt URL**: `bolt://localhost:7687`
- **HTTP Browser**: http://localhost:7474
- **Username**: neo4j
- **Password**: portintel2026

---

## Step 3: Remove Docker-Related Files (Optional)

You can delete these Docker files:
```powershell
# Remove Docker compose files (optional - keep for reference)
# rm E:\DL_Final_Project\docker-compose.yml
# rm E:\DL_Final_Project\db\docker-compose.yml
```

---

## Step 4: Verify Configuration

Your services already use the correct connection settings. Verify:

### PostgreSQL Config (`services/auth/config.py`)
```python
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'spis')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'spis_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'spis_dev_password')
```

### Neo4j Config (`services/kg/.env`)
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=portintel2026
```

**No code changes needed!** ✅

---

## Step 5: Create New Startup Script (No Docker)

Save this as `START_LOCAL.ps1`:

```powershell
# =============================================================================
# SPIS - Local Startup (No Docker)
# =============================================================================

$root = "E:\DL_Final_Project"
$venv = "$root\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SPIS - Local Mode (No Docker)" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check PostgreSQL
Write-Host "`n[1/3] Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $pg = Get-Service postgresql* -ErrorAction Stop
    if ($pg.Status -ne 'Running') {
        Start-Service $pg.Name
        Write-Host "      Started PostgreSQL service" -ForegroundColor Green
    } else {
        Write-Host "      PostgreSQL running" -ForegroundColor Green
    }
} catch {
    Write-Host "      WARNING: PostgreSQL service not found. Is it installed?" -ForegroundColor Red
}

# Check Neo4j
Write-Host "[2/3] Checking Neo4j..." -ForegroundColor Yellow
Write-Host "      Make sure Neo4j Desktop is running and database is started!" -ForegroundColor Yellow

# Start services
Write-Host "[3/3] Starting application services..." -ForegroundColor Yellow

# Auth
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\auth'; & '$venv'; python -m uvicorn app:app --reload --port 8004"
Start-Sleep 1

# Forecasting  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\forecasting'; & '$venv'; python -m uvicorn app:app --reload --port 8001"
Start-Sleep 1

# Anomaly
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\anomaly'; & '$venv'; python -m uvicorn app:app --reload --port 8002"
Start-Sleep 1

# Maintenance
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\maintenance'; & '$venv'; python -m uvicorn app:app --reload --port 8003"
Start-Sleep 1

# KG
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\kg'; & '$venv'; python -m uvicorn api:app --reload --port 8000"
Start-Sleep 1

# AIS Ingestion
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\services\ais_ingestion'; & '$venv'; python app.py --mode live --neo4j"
Start-Sleep 1

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  All Services Starting!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open: http://localhost:3000" -ForegroundColor Cyan
```

---

## What About Redpanda?

**You don't need Redpanda!** 

Looking at your code, the AIS ingestion service pushes data **directly to the anomaly service via HTTP**:
- `services/ais_ingestion/app.py` → calls `POST http://localhost:8002/live/ingest`

Redpanda/Kafka was in the original design but is **not being used**. You can safely ignore it.

---

## Storage Summary

| Component | Location | Estimated Size |
|-----------|----------|----------------|
| PostgreSQL | D:\PostgreSQL\15 | ~200 MB + data |
| Neo4j Desktop | D:\Neo4j Desktop | ~500 MB + data |
| Python venv | E:\DL_Final_Project\.venv | ~1-2 GB |
| Node modules | E:\DL_Final_Project\frontend\node_modules | ~300 MB |
| AIS Data | E:\DL_Final_Project\data\raw | Grows over time |

**Total on D: drive**: ~700 MB for databases  
**Total on E: drive**: ~2-3 GB for code/dependencies  
**C: drive**: Minimal (just installers if you choose D:)

---

## Quick Reference

### Start Everything (After Setup)
1. Ensure PostgreSQL service is running (auto-starts with Windows)
2. Start Neo4j database in Neo4j Desktop
3. Run: `.\START_LOCAL.ps1`
4. Open: http://localhost:3000

### Check Services
```powershell
netstat -ano | findstr "LISTENING" | findstr ":3000 :8000 :8001 :8002 :8003 :8004"
```

### Stop Everything
Just close the PowerShell windows, or:
```powershell
Get-Process python | Stop-Process -Force
Get-Process node | Stop-Process -Force
```

---

## Migration Checklist

- [ ] Uninstall Docker Desktop (optional, saves ~2-10 GB on C:)
- [ ] Install PostgreSQL on D: drive
- [ ] Create `spis` database and `spis_user`
- [ ] Run schema initialization script
- [ ] Install Neo4j Desktop (data on D:)
- [ ] Create and start `spis-graph` database
- [ ] Test connections work
- [ ] Run `START_LOCAL.ps1`
- [ ] Verify frontend works at http://localhost:3000

---

## Troubleshooting

### PostgreSQL won't connect
```powershell
# Check if service is running
Get-Service postgresql*

# Start it
Start-Service postgresql-x64-15
```

### Neo4j won't connect
1. Open Neo4j Desktop
2. Make sure the database shows "Running" (green)
3. If stopped, click "Start"

### "Port already in use"
```powershell
# Find what's using the port
netstat -ano | findstr ":8002"

# Kill the process
Stop-Process -Id <PID> -Force
```
