# View PostgreSQL data (SPIS database)
# Requires: PostgreSQL bin in path or set $PsqlPath below.

$PsqlPath = "E:\Postgresql\bin\psql.exe"
if (-not (Test-Path $PsqlPath)) {
    Write-Host "psql not found at $PsqlPath. Install PostgreSQL or set PsqlPath in this script." -ForegroundColor Red
    exit 1
}

$env:PGPASSWORD = "spis_dev_password"
$conn = "-h 127.0.0.1 -p 5432 -U spis_user -d spis"

Write-Host "`n=== SPIS PostgreSQL - Connection ===" -ForegroundColor Cyan
Write-Host "  Host: 127.0.0.1  Port: 5432  Database: spis  User: spis_user`n"

Write-Host "=== Tables and row counts ===" -ForegroundColor Cyan
$q1 = "SELECT relname AS table_name, n_live_tup AS row_count FROM pg_stat_user_tables ORDER BY relname;"
& $PsqlPath -h 127.0.0.1 -p 5432 -U spis_user -d spis -c $q1

Write-Host "`n=== Sample: auth_users ===" -ForegroundColor Cyan
& $PsqlPath -h 127.0.0.1 -p 5432 -U spis_user -d spis -c "SELECT user_id, username, role, created_at FROM auth_users LIMIT 10;"

Write-Host "`n=== Sample: auth_login_events (last 5) ===" -ForegroundColor Cyan
& $PsqlPath -h 127.0.0.1 -p 5432 -U spis_user -d spis -c "SELECT id, user_id, timestamp, success, method, ip FROM auth_login_events ORDER BY timestamp DESC LIMIT 5;"

Write-Host "`nTo browse all data in a GUI, use pgAdmin: add server with the connection above. See docs\DATABASE_ACCESS.md" -ForegroundColor Gray
