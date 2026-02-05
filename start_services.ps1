# =============================================================================
# SPIS - Start All Services (PowerShell Version)
# =============================================================================
# 
# Prerequisites:
#   1. Docker Desktop running (for PostgreSQL)
#   2. Neo4j Desktop with SPIS instance running
#   3. Run: cd e:\DL_Final_Project\db && docker-compose up -d
#
# Usage: .\start_services.ps1
# =============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SPIS - Starting All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "E:\DL_Final_Project"
$venvActivate = "$projectRoot\.venv\Scripts\Activate.ps1"

# Check if PostgreSQL is running
Write-Host "[CHECK] Checking PostgreSQL..." -ForegroundColor Yellow
$pg = docker ps --filter "name=spis-postgres" --format "{{.Names}}" 2>$null
if ($pg -eq "spis-postgres") {
    Write-Host "  PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL NOT running! Starting..." -ForegroundColor Red
    Set-Location "$projectRoot\db"
    docker-compose up -d
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "[1/5] Starting Auth Service (port 8004)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\services\auth'; & '$venvActivate'; Write-Host 'AUTH SERVICE - Port 8004' -ForegroundColor Green; python -m uvicorn app:app --reload --port 8004"

Start-Sleep -Seconds 3

Write-Host "[2/5] Starting Anomaly Service (port 8002)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\services\anomaly'; & '$venvActivate'; Write-Host 'ANOMALY SERVICE - Port 8002' -ForegroundColor Green; python -m uvicorn app:app --reload --port 8002"

Start-Sleep -Seconds 2

Write-Host "[3/5] Starting Maintenance Service (port 8003)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\services\maintenance'; & '$venvActivate'; Write-Host 'MAINTENANCE SERVICE - Port 8003' -ForegroundColor Green; python -m uvicorn app:app --reload --port 8003"

Start-Sleep -Seconds 2

Write-Host "[4/5] Starting KG Service (port 8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\services\kg'; & '$venvActivate'; Write-Host 'KNOWLEDGE GRAPH SERVICE - Port 8001' -ForegroundColor Green; python -m uvicorn api:app --reload --port 8001"

Start-Sleep -Seconds 2

Write-Host "[5/5] Starting Frontend (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\frontend'; Write-Host 'FRONTEND - Port 3000' -ForegroundColor Green; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All Services Starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  - Frontend:    http://localhost:3000"
Write-Host "  - Auth:        http://localhost:8004"
Write-Host "  - Anomaly:     http://localhost:8002"
Write-Host "  - Maintenance: http://localhost:8003"
Write-Host "  - KG:          http://localhost:8001"
Write-Host ""
Write-Host "Database:" -ForegroundColor Cyan
Write-Host "  - PostgreSQL:  localhost:5432 (Docker)"
Write-Host "  - Neo4j:       localhost:7687 (Neo4j Desktop)"
Write-Host ""
Write-Host "Wait ~30 seconds for all services to initialize, then open:" -ForegroundColor Yellow
Write-Host "  http://localhost:3000" -ForegroundColor White
Write-Host ""
