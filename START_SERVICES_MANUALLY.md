# Manual Service Startup Guide - SPIS

**Use this guide to start all services manually in separate PowerShell windows.**  
This gives you full visibility into each service's output and makes debugging easier.

---

## Prerequisites

1. **Databases Running** (should already be running):
   ```powershell
   cd E:\DL_Final_Project\db
   docker-compose up -d
   ```
   Wait 10 seconds, then verify:
   ```powershell
   docker ps
   ```
   You should see `spis-postgres` and `spis-neo4j` as healthy.

---

## Start Each Service (Open 6 Separate PowerShell Windows)

### Window 1: Auth Service (Port 8004)
```powershell
cd E:\DL_Final_Project\services\auth
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --port 8004
```
**Wait for**: `INFO: Application startup complete`

---

### Window 2: Forecasting Service (Port 8001)
```powershell
cd E:\DL_Final_Project\services\forecasting
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --port 8001
```
**Wait for**: `INFO: Application startup complete`

---

### Window 3: Anomaly Service (Port 8002) ⭐ WATCH THIS ONE
```powershell
cd E:\DL_Final_Project\services\anomaly
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --port 8002
```
**Wait for**: `INFO: Application startup complete`
**You'll see**: `[STARTUP] Maritime Anomaly Detection service ready!`

**IMPORTANT**: Keep this window visible! You'll see debug output here when AIS data comes in.

---

### Window 4: Maintenance Service (Port 8003)
```powershell
cd E:\DL_Final_Project\services\maintenance
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --port 8003
```
**Wait for**: `INFO: Application startup complete`

---

### Window 5: KG Service (Port 8000)
```powershell
cd E:\DL_Final_Project\services\kg
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn api:app --reload --port 8000
```
**Wait for**: `INFO: Application startup complete`

---

### Window 6: AIS Ingestion (Live Stream) ⭐ WATCH THIS ONE TOO
```powershell
cd E:\DL_Final_Project\services\ais_ingestion
..\..\.venv\Scripts\Activate.ps1
python app.py --mode live --neo4j
```
**You'll see**: Real-time vessel updates like:
```
NAFTA | MMSI=276260000 | Lat=59.4579 Lon=24.7081 sog=0 cog=332.8° | ANCHORAGE → WAITING
```

**IMPORTANT**: This window will show if vessels are being sent to the anomaly service!

---

### Window 7: Frontend (Port 3000)
```powershell
cd E:\DL_Final_Project\frontend
npm run dev
```
**Wait for**: `Ready started server on 0.0.0.0:3000`

Then open: **http://localhost:3000**

---

## Verification Steps

Once all windows are running:

1. **Check all ports**:
   ```powershell
   netstat -ano | findstr "LISTENING" | findstr ":3000 :8000 :8001 :8002 :8003 :8004"
   ```
   Should show 6 listening ports.

2. **Test live vessels**:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8002/live/vessels"
   ```
   Should return vessel data (not empty).

3. **Open frontend**: http://localhost:3000/anomaly
   - Should show real vessel names (NAFTA, HABE-3, SEKTORI, etc.)
   - Badge should say "🛰️ Live AISStream Data"

---

## Debugging the Pipeline

If you STILL see simulated data:

1. **Check AIS Ingestion window** (Window 6):
   - Should show "[ANOMALY] Ingested X vessels, Y anomalies detected"
   - If you DON'T see this, the AIS→Anomaly connection is broken

2. **Check Anomaly Service window** (Window 3):
   - Should show "[INGEST] Received X vessels"
   - Should show "[INGEST DEBUG] Processing: <vessel name>..."
   - If you see "In port area: False", that's the problem!

3. **Manual data injection** (if nothing else works):
   ```powershell
   cd E:\DL_Final_Project
   
   # Read latest AIS data
   $logFile = Get-ChildItem "data\raw\aisstream_logs\*.jsonl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
   $vessels = Get-Content $logFile.FullName -Tail 10 | ConvertFrom-Json | Where-Object { $_.message_type -eq 'PositionReport' }
   
   # Format for anomaly service
   $formatted = $vessels | ForEach-Object {
       [PSCustomObject]@{
           mmsi = [string]$_.mmsi
           lat = [double]$_.lat
           lon = [double]$_.lon
           sog = if ($_.sog) { [double]$_.sog } else { 0.0 }
           cog = if ($_.cog) { [double]$_.cog } else { 0.0 }
           heading = if ($_.heading) { [double]$_.heading } else { 0.0 }
           ship_name = if ($_.ship_name) { $_.ship_name } else { "" }
           ship_type = if ($_.ship_type) { $_.ship_type } else { "unknown" }
       }
   }
   
   # Send to anomaly service
   $json = $formatted | ConvertTo-Json -Depth 3
   Invoke-RestMethod -Uri "http://localhost:8002/live/ingest" -Method POST -Body $json -ContentType "application/json"
   
   # Verify
   Invoke-RestMethod -Uri "http://localhost:8002/live/vessels"
   ```

---

## Quick Status Check

To check if everything is working:
```powershell
# Should return 6 ports
netstat -ano | findstr "LISTENING" | findstr ":3000 :8000 :8001 :8002 :8003 :8004"

# Should return vessel data
Invoke-RestMethod -Uri "http://localhost:8002/live/vessels" | Select-Object -ExpandProperty vessels | Select-Object vessel_name, score, is_anomaly
```

---

**TIP**: Keep all 7 PowerShell windows arranged on your screen so you can see the output from each service. This makes debugging much easier!
