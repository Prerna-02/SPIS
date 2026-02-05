# Database Access Guide

## Neo4j Browser

- **URL**: http://localhost:7474
- **Username**: `neo4j`
- **Password**: `portintel2026` (note: **intel**, not "line")

If you typed `portline2026`, use `portintel2026` instead.

---

## PostgreSQL – Where to See the Data

You can view PostgreSQL data in any of these ways:

### Option 1: pgAdmin (GUI – recommended)

If you have PostgreSQL installed (e.g. at `E:\Postgresql`), pgAdmin is usually included.

1. Open **pgAdmin 4** (from Start Menu or `E:\Postgresql\pgAdmin 4\runtime\pgAdmin4.exe`).
2. Add a server:
   - **Host**: `127.0.0.1` (or `localhost`)
   - **Port**: `5432`
   - **Database**: `spis`
   - **Username**: `spis_user`
   - **Password**: `spis_dev_password`
3. In the left tree: **Servers** → your server → **Databases** → **spis** → **Schemas** → **public** → **Tables**.
4. Right‑click a table → **View/Edit Data** → **All Rows** to see the data.

### Option 2: Command line (psql)

From a terminal (use your actual path to `psql` if different):

```powershell
$env:PGPASSWORD = "spis_dev_password"
& "E:\Postgresql\bin\psql.exe" -h 127.0.0.1 -p 5432 -U spis_user -d spis -c "\dt"
```

List tables and row counts:

```powershell
& "E:\Postgresql\bin\psql.exe" -h 127.0.0.1 -p 5432 -U spis_user -d spis -c "
SELECT relname AS table_name, n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY relname;
"
```

### Option 3: Run the project’s “view data” script

From the project root:

```powershell
.\scripts\view_postgres_data.ps1
```

(If that script exists; see below.)

---

## PostgreSQL connection summary

| Setting   | Value              |
|----------|--------------------|
| Host     | `127.0.0.1`        |
| Port     | `5432`             |
| Database | `spis`             |
| Username | `spis_user`        |
| Password | `spis_dev_password`|

## Main tables (SPIS schema)

- **auth_users** – user accounts
- **auth_login_events** – login history
- **forecast_runs**, **forecast_predictions**, **forecast_actuals_daily** – forecasting
- **vessel_state**, **anomaly_events** – AIS/anomaly
- **maintenance_predictions** – maintenance predictions
- **asset_state** – asset state
- **optimizer_scenarios**, **plan_runs**, **plan_assignments**, **plan_impacts** – KG/optimizer
