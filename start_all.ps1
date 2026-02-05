# =============================================================================
# SPIS - Start All Services
# =============================================================================
# This script starts all backend services and the frontend in separate windows.
# Run with: .\start_all.ps1
# =============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SPIS - Starting All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$projectRoot = "E:\DL_Final_Project"
$venvActivate = "$projectRoot\.venv\Scripts\Activate.ps1"

# Start Auth Service (Port 8004)
Write-Host "`n[1/5] Starting Auth Service (port 8004)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\services\auth'; & '$venvActivate'; python -m uvicorn app:app --reload --port 8004"

Start-Sleep -Seconds 2

# Start Anomaly Service (Port 8002)
Write-Host "[2/5] Starting Anomaly Service (port 8002)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\services\anomaly'; & '$venvActivate'; python -m uvicorn app:app --reload --port 8002"

Start-Sleep -Seconds 2

# Start Maintenance Service (Port 8003)
Write-Host "[3/5] Starting Maintenance Service (port 8003)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\services\maintenance'; & '$venvActivate'; python -m uvicorn app:app --reload --port 8003"

Start-Sleep -Seconds 2

# Start KG Service (Port 8001)
Write-Host "[4/5] Starting KG Service (port 8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\services\kg'; & '$venvActivate'; python -m uvicorn api:app --reload --port 8001"

Start-Sleep -Seconds 2

# Start Frontend (Port 3000)
Write-Host "[5/5] Starting Frontend (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\frontend'; npm run dev"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nServices running at:"
Write-Host "  - Frontend:    http://localhost:3000" -ForegroundColor Cyan
Write-Host "  - Auth:        http://localhost:8004" -ForegroundColor Cyan
Write-Host "  - Anomaly:     http://localhost:8002" -ForegroundColor Cyan
Write-Host "  - Maintenance: http://localhost:8003" -ForegroundColor Cyan
Write-Host "  - KG:          http://localhost:8001" -ForegroundColor Cyan
Write-Host "`nNote: Make sure Neo4j (SPIS) is running before using KG features!"
Write-Host "`nTo stop all services, close the PowerShell windows or run: .\stop_all.ps1"
