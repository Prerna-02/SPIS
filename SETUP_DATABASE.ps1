# =============================================================================
# SPIS - PostgreSQL Database Setup
# =============================================================================
# Run this script to create the SPIS database and user
# =============================================================================

Write-Host @"
============================================
     SPIS PostgreSQL Database Setup
============================================
"@ -ForegroundColor Cyan

$psql = "E:\Postgresql\bin\psql.exe"

if (-not (Test-Path $psql)) {
    Write-Host "ERROR: psql not found at $psql" -ForegroundColor Red
    Write-Host "Please update the path in this script" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nThis script will create:" -ForegroundColor Yellow
Write-Host "  - User: spis_user (password: spis_dev_password)" -ForegroundColor White
Write-Host "  - Database: spis" -ForegroundColor White
Write-Host "  - Tables from schema.sql" -ForegroundColor White

Write-Host "`nEnter your PostgreSQL 'postgres' superuser password:" -ForegroundColor Magenta
$securePassword = Read-Host -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$pgPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
$env:PGPASSWORD = $pgPassword

Write-Host "`nConnecting to PostgreSQL..." -ForegroundColor Cyan

# Test connection
$test = & $psql -U postgres -p 5433 -h localhost -c "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to connect to PostgreSQL" -ForegroundColor Red
    Write-Host $test -ForegroundColor Red
    exit 1
}

Write-Host "Connected successfully!" -ForegroundColor Green

# Create user
Write-Host "`n1. Creating user spis_user..." -ForegroundColor Yellow
& $psql -U postgres -p 5433 -h localhost -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'spis_user') THEN CREATE USER spis_user WITH PASSWORD 'spis_dev_password'; END IF; END `$`$;"

# Create database
Write-Host "2. Creating database spis..." -ForegroundColor Yellow
& $psql -U postgres -p 5433 -h localhost -c "SELECT 1 FROM pg_database WHERE datname = 'spis'" | Out-Null
$dbExists = & $psql -U postgres -p 5433 -h localhost -t -c "SELECT COUNT(*) FROM pg_database WHERE datname = 'spis'"
if ($dbExists.Trim() -eq "0") {
    & $psql -U postgres -p 5433 -h localhost -c "CREATE DATABASE spis OWNER spis_user;"
} else {
    Write-Host "   Database 'spis' already exists" -ForegroundColor Gray
}

# Grant privileges
Write-Host "3. Granting privileges..." -ForegroundColor Yellow
& $psql -U postgres -p 5433 -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE spis TO spis_user;"

# Run schema
Write-Host "4. Creating tables from schema.sql..." -ForegroundColor Yellow
$schemaPath = "E:\DL_Final_Project\db\init\01_schema.sql"
if (Test-Path $schemaPath) {
    $env:PGPASSWORD = "spis_dev_password"
    & $psql -U spis_user -p 5433 -h localhost -d spis -f $schemaPath 2>&1 | Out-Null
    Write-Host "   Schema applied!" -ForegroundColor Green
} else {
    Write-Host "   WARNING: Schema file not found at $schemaPath" -ForegroundColor Yellow
}

# Test connection with new user
Write-Host "`n5. Testing connection with spis_user..." -ForegroundColor Yellow
$env:PGPASSWORD = "spis_dev_password"
$test = & $psql -U spis_user -p 5433 -h localhost -d spis -c "SELECT 'Connection successful!' as status" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   SUCCESS! Database is ready." -ForegroundColor Green
} else {
    Write-Host "   ERROR: $test" -ForegroundColor Red
}

Write-Host @"

============================================
     Setup Complete!
============================================
Now restart the Auth service:
1. Close the Auth PowerShell window
2. Run START_LOCAL.ps1 again

Or manually start Auth:
cd E:\DL_Final_Project\services\auth
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --port 8004
============================================
"@ -ForegroundColor Cyan
