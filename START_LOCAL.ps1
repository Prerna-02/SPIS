# =============================================================================
# SPIS - Local Startup (NO DOCKER REQUIRED)
# =============================================================================
#
# Prerequisites:
#   1. PostgreSQL installed locally (service running)
#   2. Neo4j Desktop installed, database started
#
# Usage: .\START_LOCAL.ps1
# =============================================================================

$ErrorActionPreference = "Continue"
$root = "E:\DL_Final_Project"
$venv = "$root\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SPIS - Local Mode (No Docker)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# CHECK POSTGRESQL
# =============================================================================

Write-Host "[1/3] Checking PostgreSQL..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue

if ($pgService) {
    if ($pgService.Status -eq 'Running') {
        Write-Host "      PostgreSQL is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "      Starting PostgreSQL service..." -ForegroundColor Yellow
        Start-Service $pgService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        Write-Host "      PostgreSQL started" -ForegroundColor Green
    }
} else {
    Write-Host "      WARNING: PostgreSQL service not found!" -ForegroundColor Red
    Write-Host "      Make sure PostgreSQL is installed and the service exists." -ForegroundColor Red
    Write-Host "      Continuing anyway..." -ForegroundColor Yellow
}

# =============================================================================
# CHECK NEO4J
# =============================================================================

Write-Host "[2/3] Checking Neo4j..." -ForegroundColor Yellow
try {
    $neo4jCheck = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "      Neo4j is RUNNING (port 7474)" -ForegroundColor Green
} catch {
    Write-Host "      WARNING: Neo4j not responding on port 7474" -ForegroundColor Yellow
    Write-Host "      Please start Neo4j Desktop and start your database!" -ForegroundColor Yellow
    Write-Host "      Continuing anyway..." -ForegroundColor Yellow
}

# =============================================================================
# START APPLICATION SERVICES
# =============================================================================

Write-Host "[3/3] Starting application services..." -ForegroundColor Yellow
Write-Host ""

# Auth Service (8004)
Write-Host "      Starting Auth Service (8004)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - Auth (8004)'; cd '$root\services\auth'; & '$venv'; python -m uvicorn app:app --reload --port 8004"
)
Start-Sleep -Seconds 1

# Forecasting Service (8001)
Write-Host "      Starting Forecasting Service (8001)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - Forecasting (8001)'; cd '$root\services\forecasting'; & '$venv'; python -m uvicorn app:app --reload --port 8001"
)
Start-Sleep -Seconds 1

# Anomaly Service (8002)
Write-Host "      Starting Anomaly Service (8002)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - Anomaly (8002)'; cd '$root\services\anomaly'; & '$venv'; python -m uvicorn app:app --reload --port 8002"
)
Start-Sleep -Seconds 1

# Maintenance Service (8003)
Write-Host "      Starting Maintenance Service (8003)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - Maintenance (8003)'; cd '$root\services\maintenance'; & '$venv'; python -m uvicorn app:app --reload --port 8003"
)
Start-Sleep -Seconds 1

# KG Service (8000)
Write-Host "      Starting KG Service (8000)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - KG (8000)'; cd '$root\services\kg'; & '$venv'; python -m uvicorn api:app --reload --port 8000"
)
Start-Sleep -Seconds 1

# AIS Ingestion (Live Stream)
Write-Host "      Starting AIS Ingestion (Live)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - AIS Stream'; cd '$root\services\ais_ingestion'; & '$venv'; python app.py --mode live --neo4j"
)
Start-Sleep -Seconds 1

# Frontend (3000)
Write-Host "      Starting Frontend (3000)..." -ForegroundColor Gray
Start-Process powershell -ArgumentList @(
    "-NoExit"
    "-Command"
    "`$Host.UI.RawUI.WindowTitle = 'SPIS - Frontend (3000)'; cd '$root\frontend'; npm run dev"
)

# =============================================================================
# DONE
# =============================================================================

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  All Services Starting!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor White
Write-Host "  - Auth:        http://localhost:8004" -ForegroundColor Cyan
Write-Host "  - Forecasting: http://localhost:8001" -ForegroundColor Cyan
Write-Host "  - Anomaly:     http://localhost:8002" -ForegroundColor Cyan
Write-Host "  - Maintenance: http://localhost:8003" -ForegroundColor Cyan
Write-Host "  - KG:          http://localhost:8000" -ForegroundColor Cyan
Write-Host "  - Frontend:    http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Databases (must be running separately):" -ForegroundColor White
Write-Host "  - PostgreSQL:  localhost:5432" -ForegroundColor Magenta
Write-Host "  - Neo4j:       localhost:7687 (browser: 7474)" -ForegroundColor Magenta
Write-Host ""
Write-Host "Wait 20-30 seconds, then open: http://localhost:3000" -ForegroundColor Yellow
Write-Host ""
