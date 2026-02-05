-- ============================================================
-- SPIS - Smart Port Intelligence System
-- PostgreSQL Schema - Docker init script
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- (A) AUTH
-- ============================================================

CREATE TABLE IF NOT EXISTS auth_users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'operator',
    face_embedding DOUBLE PRECISION[],
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS auth_login_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth_users(user_id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ DEFAULT now(),
    success BOOLEAN NOT NULL,
    method TEXT NOT NULL,
    ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_login_events_user ON auth_login_events(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_login_events_ts ON auth_login_events(timestamp);

-- ============================================================
-- (B) FEATURE 1: FORECASTING
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    start_date DATE NOT NULL,
    horizon_days INT DEFAULT 7,
    metrics JSONB
);

CREATE TABLE IF NOT EXISTS forecast_predictions (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES forecast_runs(run_id) ON DELETE CASCADE,
    target_date DATE NOT NULL,
    port_calls_pred DOUBLE PRECISION,
    throughput_pred DOUBLE PRECISION,
    port_calls_p10 DOUBLE PRECISION,
    port_calls_p90 DOUBLE PRECISION,
    throughput_p10 DOUBLE PRECISION,
    throughput_p90 DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_forecast_predictions_run ON forecast_predictions(run_id);
CREATE INDEX IF NOT EXISTS idx_forecast_predictions_date ON forecast_predictions(target_date);

CREATE TABLE IF NOT EXISTS forecast_actuals_daily (
    date DATE PRIMARY KEY,
    port_calls_actual DOUBLE PRECISION,
    throughput_actual DOUBLE PRECISION
);

-- ============================================================
-- (C) FEATURE 2: AIS ANOMALY DETECTION
-- ============================================================

CREATE TABLE IF NOT EXISTS vessel_state (
    mmsi BIGINT PRIMARY KEY,
    last_seen TIMESTAMPTZ,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    sog DOUBLE PRECISION,
    cog DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    source TEXT
);

CREATE TABLE IF NOT EXISTS anomaly_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mmsi BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    anomaly_score DOUBLE PRECISION NOT NULL,
    risk_level TEXT NOT NULL,
    reason TEXT,
    model_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_time ON anomaly_events(event_time);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_mmsi_time ON anomaly_events(mmsi, event_time);

-- ============================================================
-- (D) FEATURE 3: MAINTENANCE PREDICTION
-- ============================================================

CREATE TABLE IF NOT EXISTS asset_state (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    last_seen TIMESTAMPTZ,
    utilization_rate DOUBLE PRECISION,
    motor_temp_c DOUBLE PRECISION,
    vibration_rms DOUBLE PRECISION,
    hydraulic_pressure_bar DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS maintenance_predictions (
    id BIGSERIAL PRIMARY KEY,
    asset_id TEXT REFERENCES asset_state(asset_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    rul_hours DOUBLE PRECISION,
    failure_in_next_72h BOOLEAN,
    failure_prob DOUBLE PRECISION,
    risk_level TEXT,
    model_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_maint_pred_asset_ts ON maintenance_predictions(asset_id, timestamp);

-- ============================================================
-- (E) FEATURE 4: OPTIMIZER
-- ============================================================

CREATE TABLE IF NOT EXISTS optimizer_scenarios (
    scenario_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth_users(user_id) ON DELETE SET NULL,
    extra_vessel_payload JSONB,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS plan_runs (
    plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id UUID REFERENCES optimizer_scenarios(scenario_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    solver_status TEXT,
    runtime_ms INT,
    total_delay_min DOUBLE PRECISION,
    objective_weights JSONB
);

CREATE TABLE IF NOT EXISTS plan_assignments (
    id BIGSERIAL PRIMARY KEY,
    plan_id UUID REFERENCES plan_runs(plan_id) ON DELETE CASCADE,
    mmsi BIGINT,
    berth_id TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    cranes_assigned INT,
    service_minutes INT
);

CREATE INDEX IF NOT EXISTS idx_plan_assignments_plan ON plan_assignments(plan_id);

CREATE TABLE IF NOT EXISTS plan_impacts (
    id BIGSERIAL PRIMARY KEY,
    plan_id UUID REFERENCES plan_runs(plan_id) ON DELETE CASCADE,
    impacted_mmsi BIGINT,
    delay_minutes DOUBLE PRECISION,
    reason TEXT,
    upstream_mmsi BIGINT,
    upstream_berth_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_plan_impacts_plan ON plan_impacts(plan_id);
