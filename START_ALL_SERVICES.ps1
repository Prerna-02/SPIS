# =============================================================================
# SPIS - Complete Service Startup (All in Separate Windows)
# =============================================================================

$ErrorActionPreference = "Continue"
$root = "E:\DL_Final_Project"
$venv = "$root\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SPIS - Starting All Services" -ForegroundColor Cyan  
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# 1. DATABASES (Docker)
# =============================================================================

Write-Host "[1/8] Starting Databases (Docker)..." -ForegroundColor Yellow
Push-Location "$root\db"
docker-compose up -d
Pop-Location
Start-Sleep -Seconds 8
Write-Host "      Databases starting..." -ForegroundColor Green

# =============================================================================
# 2. AUTH SERVICE (8004)
# =============================================================================

Write-Host "[2/8] Auth Service (8004)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - Auth (8004)'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Auth Service - Port 8004' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\auth'
& '$venv'
python -m uvicorn app:app --reload --port 8004
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 3. FORECASTING SERVICE (8001)
# =============================================================================

Write-Host "[3/8] Forecasting Service (8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - Forecasting (8001)'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Forecasting - Port 8001' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\forecasting'
& '$venv'
python -m uvicorn app:app --reload --port 8001
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 4. ANOMALY SERVICE (8002) - WATCH THIS WINDOW
# =============================================================================

Write-Host "[4/8] Anomaly Service (8002) - WATCH FOR DEBUG OUTPUT..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - Anomaly (8002) ⭐ WATCH THIS'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Anomaly Detection - Port 8002' -ForegroundColor Cyan
Write-Host '  ⭐ WATCH FOR DEBUG OUTPUT' -ForegroundColor Yellow
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\anomaly'
& '$venv'
python -m uvicorn app:app --reload --port 8002
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 5. MAINTENANCE SERVICE (8003)
# =============================================================================

Write-Host "[5/8] Maintenance Service (8003)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - Maintenance (8003)'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Maintenance - Port 8003' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\maintenance'
& '$venv'
python -m uvicorn app:app --reload --port 8003
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 6. KG SERVICE (8000)
# =============================================================================

Write-Host "[6/8] KG Service (8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - KG (8000)'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Knowledge Graph - Port 8000' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\kg'
& '$venv'
python -m uvicorn api:app --reload --port 8000
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 7. AIS INGESTION (Live Stream) - WATCH THIS TOO
# =============================================================================

Write-Host "[7/8] AIS Ingestion (Live)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - AIS Stream ⭐ WATCH THIS'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  AIS Live Stream (Tallinn Port)' -ForegroundColor Cyan
Write-Host '  ⭐ WATCH FOR ANOMALY MESSAGES' -ForegroundColor Yellow
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\services\ais_ingestion'
& '$venv'
python app.py --mode live --neo4j
"@
)
Start-Sleep -Seconds 2

# =============================================================================
# 8. FRONTEND (3000)
# =============================================================================

Write-Host "[8/8] Frontend (3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    @"
`$Host.UI.RawUI.WindowTitle = 'SPIS - Frontend (3000)'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Frontend - Port 3000' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
cd '$root\frontend'
npm run dev
"@
)

# =============================================================================
# DONE
# =============================================================================

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  ALL SERVICES STARTING!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "You should see 8 PowerShell windows opening..." -ForegroundColor White
Write-Host ""
Write-Host "⭐ IMPORTANT: Watch these windows:" -ForegroundColor Yellow
Write-Host "   - Anomaly (8002): Look for debug output" -ForegroundColor Cyan
Write-Host "   - AIS Stream: Look for '[ANOMALY] Ingested...' messages" -ForegroundColor Cyan
Write-Host ""
Write-Host "Wait 30 seconds, then open: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "To check status:" -ForegroundColor Gray
Write-Host '  netstat -ano | findstr "LISTENING" | findstr ":3000 :8000 :8001 :8002 :8003 :8004"' -ForegroundColor Gray
Write-Host ""
