# =============================================================================
# SPIS - Stop All Services
# =============================================================================
# This script stops all running Python/Node services.
# Run with: .\stop_all.ps1
# =============================================================================

Write-Host "Stopping all SPIS services..." -ForegroundColor Yellow

# Kill Python processes (uvicorn servers)
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  - Stopped Python/Uvicorn services" -ForegroundColor Green

# Kill Node processes (Next.js)
Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  - Stopped Node/Next.js services" -ForegroundColor Green

Write-Host "`nAll services stopped!" -ForegroundColor Green
