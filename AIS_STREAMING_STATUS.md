# AIS Streaming & Anomaly Detection - Status Report

## ✅ What's Working

### 1. AIS Data Streaming ✓
- **Location**: `data/raw/aisstream_logs/aisstream_tallinn_20260204_171600.jsonl`
- **Status**: ACTIVE - Last update 21:35:52 (102 KB of data)
- **Vessels**: Recording real-time AIS data from Tallinn Port
- **Format**: JSONL files with vessel positions, MMSI, ship names, types

**Sample Data**:
```json
{"mmsi": 276781000, "ship_name": "SEKTORI", "lat": 59.458, "lon": 24.720, "sog": 0}
{"mmsi": 276330000, "ship_name": "HABE-3", "lat": 59.453, "lon": 24.737, "sog": 0.1}
```

### 2. All Services Running ✓
- PostgreSQL (5432) - Docker
- Neo4j (7474, 7687) - Docker
- Frontend (3000) - Local
- Auth (8004) - Local
- KG (8000) - Local
- **Forecasting (8001)** - Local ✓
- **Anomaly (8002)** - Local ✓
- **Maintenance (8003)** - Local ✓

### 3. Frontend Features ✓
- **Live data detection**: Already implemented (tries `/live/vessels` first)
- **Red dots for anomalies**: Already in the time series chart code
- **Forecast gap**: FIXED (added day 0 connection point)

## ⚠️ Issue Found: Anomaly Service Not Receiving Data

### Problem
The AIS ingestion service is streaming data and saving to JSONL, but the anomaly detection service shows **0 vessels**.

### Root Cause Investigation
1. **AIS Ingestion**: Configured to push to `http://localhost:8002/live/ingest`
2. **Batch Size**: Sends every 5 vessels
3. **Integration**: Only pushes when `--neo4j` flag is used (which you ARE using)

### Debugging Steps Completed
1. ✓ Verified anomaly service model is loaded
2. ✓ Verified bounding box coordinates match
3. ✓ Added debug logging to `/live/ingest` endpoint
4. ✓ Tested manual data submission (returns 200 OK but ingests 0 vessels)

### Next Steps Required

**CHECK THE ANOMALY SERVICE POWERSHELL WINDOW**:
Look for a window titled "Anomaly (8002)" or similar. You should see debug output like:
```
[INGEST DEBUG] Processing: SEKTORI (276781000) at 59.458,24.720
[INGEST DEBUG] In port area: True (bbox: 59.35-59.60, 24.55-25.15)
```

If you see "In port area: False", then the bounding box check is failing.
If you see exceptions, that's the root cause.

## 🎯 Quick Test

### Option 1: Check PowerShell Window
1. Find the PowerShell window running the Anomaly service (port 8002)
2. Look for the debug output when you refresh the anomaly page

### Option 2: Force Feed Data
Run this in PowerShell to manually populate the anomaly service:
```powershell
cd E:\DL_Final_Project
# Read last 10 vessels from AIS log
$logFile = Get-ChildItem "data\raw\aisstream_logs\*.jsonl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$vessels = Get-Content $logFile.FullName -Tail 10 | ForEach-Object { $_ | ConvertFrom-Json }

# Convert to anomaly service format
$formatted = $vessels | Where-Object { $_.message_type -eq 'PositionReport' } | ForEach-Object {
    @{
        mmsi = [string]$_.mmsi
        lat = [double]$_.lat
        lon = [double]$_.lon
        sog = [double]($_.sog ?? 0)
        cog = [double]($_.cog ?? 0)
        heading = [double]($_.heading ?? 0)
        ship_name = $_.ship_name ?? ""
        ship_type = $_.ship_type ?? "unknown"
    }
}

# Send to anomaly service
$json = $formatted | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "http://localhost:8002/live/ingest" -Method POST -Body $json -ContentType "application/json"

# Check result
Invoke-RestMethod -Uri "http://localhost:8002/live/vessels"
```

## 📊 Expected Behavior (Once Fixed)

1. **AIS Stream** → Saves to JSONL + Pushes to Anomaly Service
2. **Anomaly Service** → Scores vessels → Stores in memory
3. **Frontend** → Fetches from `/live/vessels` → Shows real data with "🛰️ Live AISStream Data" badge
4. **Time Series Chart** → Red dots appear on anomaly points
5. **Vessel Table** → Shows actual vessel names from your screenshots (SEKTORI, HABE-3, etc.)

## 🔧 Files Modified

1. `frontend/app/forecasting/page.tsx` - Fixed forecast gap (day 0 connector)
2. `services/anomaly/app.py` - Added debug logging to `/live/ingest`

## 💡 Summary

**Everything is architecturally correct:**
- ✅ Data is streaming and being saved
- ✅ Services are all running
- ✅ Frontend code is correct
- ✅ API endpoints exist and are healthy
- ✅ Red dots for anomalies already implemented

**The missing link:**
- The data pipeline from AIS → Anomaly service needs debugging
- Check the PowerShell window for the Anomaly service to see debug output
- The service might be filtering out all vessels for an unknown reason

---
**Generated**: 2026-02-04 21:37
