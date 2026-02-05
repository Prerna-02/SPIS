# =============================================================================
# SPIS - Development Stop Script
# =============================================================================
# 
# Stops all SPIS services (Docker and local processes)
#
# Usage: .\stop_dev.ps1
# =============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SPIS - Stopping All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop local Python/Node processes
Write-Host "[1/2] Stopping local services..." -ForegroundColor Yellow

# Kill uvicorn processes (Auth, KG services)
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*SPIS*" -or $_.CommandLine -like "*uvicorn*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill node processes (Frontend)
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*SPIS*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "      Local processes stopped" -ForegroundColor Green

# Stop Docker containers
Write-Host "[2/2] Stopping Docker containers..." -ForegroundColor Yellow

Push-Location "E:\DL_Final_Project\db"
docker-compose down
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All Services Stopped" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
