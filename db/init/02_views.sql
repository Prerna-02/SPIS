-- ============================================================
-- SPIS - Smart Port Intelligence System
-- PostgreSQL Views - Docker init script
-- ============================================================

-- ============================================================
-- View 1: Anomalies in last 24 hours
-- ============================================================

CREATE OR REPLACE VIEW v_anomalies_last_24h AS
SELECT 
    mmsi,
    event_time,
    anomaly_score,
    risk_level,
    lat,
    lon,
    reason
FROM anomaly_events
WHERE event_time >= now() - INTERVAL '24 hours'
ORDER BY event_time DESC;

-- ============================================================
-- View 2: High-risk assets in last 7 days
-- ============================================================

CREATE OR REPLACE VIEW v_assets_high_risk_last_7d AS
SELECT 
    a.asset_id,
    a.asset_type,
    m.timestamp,
    m.rul_hours,
    m.failure_prob,
    m.failure_in_next_72h,
    m.risk_level
FROM maintenance_predictions m
JOIN asset_state a ON m.asset_id = a.asset_id
WHERE m.timestamp >= now() - INTERVAL '7 days'
  AND (m.risk_level IN ('HIGH', 'CRITICAL') OR m.failure_in_next_72h = true)
ORDER BY m.timestamp DESC;

-- ============================================================
-- View 3: Latest forecast run with predictions
-- ============================================================

CREATE OR REPLACE VIEW v_latest_forecast AS
SELECT 
    r.run_id,
    r.model_name,
    r.created_at,
    r.start_date,
    r.horizon_days,
    r.metrics,
    p.target_date,
    p.port_calls_pred,
    p.throughput_pred,
    p.port_calls_p10,
    p.port_calls_p90,
    p.throughput_p10,
    p.throughput_p90
FROM forecast_runs r
JOIN forecast_predictions p ON r.run_id = p.run_id
WHERE r.created_at = (SELECT MAX(created_at) FROM forecast_runs)
ORDER BY p.target_date;

-- ============================================================
-- View 4: Latest plan assignments
-- ============================================================

CREATE OR REPLACE VIEW v_latest_plan_assignments AS
SELECT 
    pa.mmsi,
    pa.berth_id,
    pa.start_time,
    pa.end_time,
    pa.cranes_assigned,
    pa.service_minutes,
    pr.solver_status,
    pr.total_delay_min
FROM plan_assignments pa
JOIN plan_runs pr ON pa.plan_id = pr.plan_id
WHERE pr.created_at = (SELECT MAX(created_at) FROM plan_runs)
ORDER BY pa.start_time;

-- ============================================================
-- View 5: Latest plan impacts
-- ============================================================

CREATE OR REPLACE VIEW v_latest_plan_impacts AS
SELECT 
    pi.impacted_mmsi,
    pi.delay_minutes,
    pi.reason,
    pi.upstream_mmsi,
    pi.upstream_berth_id,
    pr.solver_status,
    pr.total_delay_min
FROM plan_impacts pi
JOIN plan_runs pr ON pi.plan_id = pr.plan_id
WHERE pr.created_at = (SELECT MAX(created_at) FROM plan_runs)
ORDER BY pi.delay_minutes DESC;
