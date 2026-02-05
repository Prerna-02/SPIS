# =============================================================================
# SPIS - Development Startup Script
# =============================================================================
# 
# This script starts:
#   1. PostgreSQL + Neo4j in Docker (databases only)
#   2. Auth Service locally (port 8004)
#   3. Frontend locally (port 3000)
#   4. AIS Ingestion with Neo4j integration (real-time vessel data)
#
# Usage: .\start_dev.ps1
# Stop:  .\stop_dev.ps1 or close the PowerShell windows
# =============================================================================

param(
    [switch]$SkipDatabases,
    [switch]$SkipAIS
)

$ErrorActionPreference = "Continue"
$projectRoot = "E:\DL_Final_Project"
$venvActivate = "$projectRoot\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SPIS - Development Mode Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# STEP 1: Start Databases in Docker
# =============================================================================

if (-not $SkipDatabases) {
    Write-Host "[1/5] Starting PostgreSQL + Neo4j in Docker..." -ForegroundColor Yellow
    
    Push-Location "$projectRoot\db"
    docker-compose up -d
    Pop-Location
    
    Write-Host "      Waiting for databases to be healthy..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Check PostgreSQL
    $pgReady = $false
    for ($i = 0; $i -lt 10; $i++) {
        $result = docker exec spis-postgres pg_isready -U spis_user -d spis 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pgReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    
    if ($pgReady) {
        Write-Host "      PostgreSQL is ready!" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: PostgreSQL may not be ready yet" -ForegroundColor Yellow
    }
    
    # Check Neo4j
    $neo4jReady = $false
    for ($i = 0; $i -lt 15; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $neo4jReady = $true
                break
            }
        } catch {}
        Start-Sleep -Seconds 2
    }
    
    if ($neo4jReady) {
        Write-Host "      Neo4j is ready!" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: Neo4j may not be ready yet (it takes ~30s to start)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[1/5] Skipping database startup (--SkipDatabases)" -ForegroundColor Gray
}

Write-Host ""

# =============================================================================
# STEP 2: Start Auth Service
# =============================================================================

Write-Host "[2/5] Starting Auth Service (port 8004)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'SPIS - Auth Service (8004)'
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  Auth Service - Port 8004' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    cd '$projectRoot\services\auth'
    & '$venvActivate'
    python -m uvicorn app:app --reload --port 8004
"@

Start-Sleep -Seconds 2

# =============================================================================
# STEP 3: Start Feature 4 (KG + Optimizer) - Needs Neo4j
# =============================================================================

Write-Host "[3/5] Starting Feature 4 - KG Service (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'SPIS - KG Service (8000)'
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  KG + Optimizer Service - Port 8000' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    cd '$projectRoot\services\kg'
    & '$venvActivate'
    python -m uvicorn api:app --reload --port 8000
"@

Start-Sleep -Seconds 2

# =============================================================================
# STEP 4: Start AIS Ingestion (Real-time vessel data)
# =============================================================================

if (-not $SkipAIS) {
    Write-Host "[4/5] Starting AIS Ingestion (live mode with Neo4j)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        `$host.UI.RawUI.WindowTitle = 'SPIS - AIS Live Stream'
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host '  AIS Live Stream (Tallinn Port)' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host 'Streaming real-time vessel data to Neo4j...' -ForegroundColor Gray
        Write-Host 'Press Ctrl+C to stop' -ForegroundColor Gray
        Write-Host ''
        cd '$projectRoot\services\ais_ingestion'
        & '$venvActivate'
        python app.py --mode live --neo4j
"@
} else {
    Write-Host "[4/5] Skipping AIS Ingestion (--SkipAIS)" -ForegroundColor Gray
}

Start-Sleep -Seconds 2

# =============================================================================
# STEP 5: Start Frontend
# =============================================================================

Write-Host "[5/5] Starting Frontend (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'SPIS - Frontend (3000)'
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  Frontend - Port 3000' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    cd '$projectRoot\frontend'
    npm run dev
"@

# =============================================================================
# DONE
# =============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All Services Starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor White
Write-Host "  [Docker]" -ForegroundColor Magenta
Write-Host "    - PostgreSQL:  localhost:5432" -ForegroundColor Cyan
Write-Host "    - Neo4j:       localhost:7474 (browser) / :7687 (bolt)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [Local]" -ForegroundColor Magenta
Write-Host "    - Frontend:    http://localhost:3000" -ForegroundColor Cyan
Write-Host "    - Auth API:    http://localhost:8004" -ForegroundColor Cyan
Write-Host "    - KG API:      http://localhost:8000" -ForegroundColor Cyan
Write-Host "    - AIS Stream:  Running (pushing to Neo4j)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Neo4j Browser: http://localhost:7474" -ForegroundColor Yellow
Write-Host "  Username: neo4j" -ForegroundColor Gray
Write-Host "  Password: portintel2026" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop: Close the PowerShell windows or run .\stop_dev.ps1" -ForegroundColor Gray
Write-Host ""
