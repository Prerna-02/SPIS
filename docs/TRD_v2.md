# TRD — Feature 4: Knowledge Graph + Optimization (SPIS | Port of Tallinn)

**Module name:** Feature 4 — KG + Optimization  
**System:** Smart Port Intelligence System (SPIS)  
**Port:** Tallinn (live vessel traffic via AISStream; equipment data via Feature 3 maintenance dataset)  
**Frontend:** React + Next.js + Tailwind  
**Graph DB:** Neo4j  
**Date:** January 2026

---

## 1) Purpose

Build a real-time decision-support module that:
- Ingests **live AIS vessel positions** (AISStream WebSocket) to maintain the current port traffic state.
- Ingests **equipment availability/health** (Feature 3 maintenance CSV / model outputs).
- Maintains an operational **Knowledge Graph (KG)** of vessels, zones, berths, yard capacity, and equipment.
- Runs an **optimizer** when an “extra vessel / ETA shift” event occurs.
- Produces:
  - an **action plan** (berth reassignment, hold at anchorage, add crane/truck, yard allocation),
  - **expected impact** (delay hours, congestion risk, cost score),
  - a **cascade explanation** (who gets delayed and why).

---

## 2) Scope

### 2.1 In scope
- Live AIS ingestion (WebSocket) → near real-time vessel updates.
- Replay fallback for AIS (replay saved JSONL logs) for reliability.
- Equipment ingestion (Feature 3 CSV / inference outputs) → resource availability + risk.
- KG storage and querying in Neo4j.
- Optimization engine (2 algorithms for comparison).
- Backend APIs to drive UI pages.
- UI pages for scenario simulation, plan results, and cascade explanation.

### 2.2 Out of scope
- Official berth assignment / terminal operating system (TOS) integration (we approximate using zones + schedule).
- Full container-level yard operations (we model yard at an aggregate block level).

---

## 3) High-Level Architecture

### 3.1 Services (containerizable)
1) **ais-ingestion-service**
   - Connects to AISStream WebSocket and receives PositionReport messages.
   - Writes raw/minimal events to `data/raw/aisstream_logs/*.jsonl`.
   - Updates vessel state in Neo4j (upsert).
   - Supports **Replay mode** for demos.

2) **equipment-service** (Feature 3 integration)
   - Reads Feature 3 maintenance CSV / model outputs.
   - Updates Neo4j with equipment state + risk indicators.

3) **kg-service**
   - Neo4j driver + query layer.
   - Provides “KG snapshot” queries for optimizer + UI.

4) **optimizer-service**
   - Pulls snapshot from Neo4j.
   - Runs optimization (CP-SAT primary + MILP baseline).
   - Writes plan + impacts back to Neo4j.

5) **frontend (Next.js)**
   - Scenario input (extra vessel / ETA shift).
   - Displays live status (vessels/resources), plan options, and cascade impacts.

---

## 4) Data Inputs

### 4.1 AISStream (live) fields — minimum set
From JSONL logs / payload:
- `ingest_ts_utc`
- `mmsi`
- `lat`, `lon`
- `sog`, `cog`, `heading`

Derived fields:
- `zone` (APPROACH / ANCHORAGE / BERTH) based on geofence/polygons or bounding boxes
- `status`:
  - **APPROACHING** if in approach zone and/or `sog >= 0.5`
  - **WAITING** if in anchorage zone and `sog < 0.5`
  - **BERTHED** if in berth zone and `sog < 0.5`
- `eta_to_port` (optional): estimated using distance-to-port / speed smoothing

### 4.2 Feature 3 equipment fields (maintenance CSV)
Available columns (sample):
- `asset_id`, `asset_type`, `timestamp`
- `operation_state`, `utilization_rate`
- `maintenance_age_days`
- `load_tons`, `lift_cycles_per_hour`
- sensors: `motor_temp_c`, `gearbox_temp_c`, `hydraulic_pressure_bar`, `vibration_rms`, `current_amp`, `rpm`
- `rul_hours`, `failure_mode`, `failure_in_next_72h`

Derived (recommended):
- `availability_flag` (0/1)
- `health_score` (0–1)
- `effective_capacity` (0–1), e.g. `availability_flag * health_score * (1 - utilization_rate)`

---

## 5) Knowledge Graph (Neo4j) Design

### 5.1 Node labels + key properties
**Vessel**
- `:Vessel {mmsi, last_lat, last_lon, last_sog, last_cog, last_seen_ts, status, eta_to_port}`

**Zone**
- `:Zone {zone_id, type: "BERTH_ZONE"|"ANCHORAGE_ZONE"|"APPROACH_ZONE"}`

**Berth**
- `:Berth {berth_id, max_vessels=1, capacity_class}`

**Asset (equipment)**
- `:Asset {asset_id, asset_type, operation_state, utilization_rate, rul_hours, failure_in_next_72h, health_score, effective_capacity, last_ts}`

**YardBlock**
- `:YardBlock {yard_id, capacity_teu, used_teu}`

**PortCall** (optional entity; created when needed for scheduling)
- `:PortCall {portcall_id, mmsi, eta, etd, cargo_priority, containers_est, status}`

**Plan**
- `:Plan {plan_id, created_ts, scenario_id, objective_score, status}`

**Assignment**
- `:Assignment {assignment_id, vessel_mmsi, berth_id, start_ts, end_ts}`

**Impact**
- `:Impact {impact_id, vessel_mmsi, delay_hours, reason}`

> Performance note: keep KG “light” (store only latest vessel state + minimal recent history if required).

### 5.2 Relationships
- `(Vessel)-[:IN_ZONE]->(Zone)`
- `(PortCall)-[:FOR_VESSEL]->(Vessel)`
- `(PortCall)-[:ASSIGNED_TO]->(Berth)`
- `(Berth)-[:HAS_ASSET]->(Asset)`
- `(PortCall)-[:USES_YARD]->(YardBlock)`
- `(Plan)-[:HAS_ASSIGNMENT]->(Assignment)`
- `(Plan)-[:CAUSES_IMPACT]->(Impact)`
- `(Impact)-[:IMPACTS]->(Vessel)`

---

## 6) Event Triggers (when the optimizer runs)

Optimizer executes on any of the following:
1) **Extra vessel event**: new `mmsi` appears in APPROACH zone not in “expected list”, or user manual scenario.
2) **ETA shift**: derived ETA changes by > X minutes (recommended: 60 minutes).
3) **Congestion threshold**: anchorage queue > N vessels, or yard utilization > Y% (e.g., 85%).
4) **Equipment degradation**: critical asset DOWN or `failure_in_next_72h=1` for cranes.

---

## 7) Optimization Problem Definition

### 7.1 Decision variables
- Assign each vessel/portcall to berth or anchorage wait, with start/end time windows.
- Allocate equipment per berth/time window (abstracted by `effective_capacity`).
- Yard block allocation (optional).

### 7.2 Constraints
- One berth handles max one vessel at a time.
- Limited equipment available per time window.
- Unavailable assets cannot be used.
- Yard capacity cannot exceed maximum.
- Priority cargo penalties (pharma > food > electronics > other).

### 7.3 Objective (weighted)
Minimize:
- total waiting time (sum of vessel delays),
- congestion risk,
- resource cost,
- priority delay penalties.

---

## 8) Algorithms (2 for comparison)

### A) CP-SAT scheduling (primary)
- Best for discrete constraints (assignment + sequencing).

### B) MILP (baseline)
- Linear benchmark; often easier to explain; may be slower with complex constraints.

---

## 9) Expected Impact Computation

### 9.1 Service time estimate
Concept: `service_time_hours = base_time(containers_est) / sum(effective_capacity_of_allocated_assets)`.

### 9.2 Delay computation
`delay_hours = max(0, berth_start_time - eta_to_port)`; cascades via shifted berth occupancy.

### 9.3 Congestion risk score
Combine anchorage queue length + berth occupancy + yard utilization (+ optional forecast pressure).

### 9.4 Cost score
Overtime usage + extra allocations + rerouting penalties.

---

## 10) Backend API Contracts

### 10.1 Snapshot (KG → optimizer/UI)
`GET /kg/snapshot?window_hours=72`

Returns:
- vessels by status, ETA estimates,
- berth schedule/occupancy,
- assets availability + effective_capacity,
- yard utilization.

### 10.2 Scenario input (UI → optimizer)
`POST /optimizer/scenario`

Body:
- `extra_vessel`: `{mmsi(optional), eta, containers_est, cargo_priority}`
- toggles: `{allow_overtime, max_wait_hours, risk_tolerance}`

### 10.3 Run optimization
`POST /optimizer/run` → returns top K plans (recommend 3) + KPIs.

### 10.4 Plan detail
`GET /plans/{plan_id}` → assignments, allocations, impacts with reasons.

---

## 11) Frontend Requirements (Next.js + Tailwind)

### Pages
1) **Live Port View**: KPIs + tables (approach/anchorage/berth).  
2) **Extra Vessel Planner**: scenario form + “Simulate & Optimize”.  
3) **Plan Results**: top 3 plan cards + KPI summary.  
4) **Cascade Explanation**: impacted vessels + delay + “because” reasons.

### Refresh
- Poll every 2–5 seconds or backend WebSocket.

---

## 12) Evaluation Metrics

### Optimization quality
- Total delay hours, priority delay (weighted), congestion risk, cost score, runtime.

### Reliability
- reconnect success rate, replay availability, ingestion throughput (msgs/sec).

---

## 13) Deployment Notes
- Dockerize Neo4j + services + frontend.
- Env vars: `AISSTREAM_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

---

## 14) Neo4j “Sign-in” requirement

- **Neo4j Desktop (local):** no online sign-in required; set local DB username/password.
- **Neo4j Docker (local):** no online sign-in required; set credentials via env vars.
- **Neo4j Aura (cloud):** requires online Neo4j account to provision; still accessed via URI + user/pass.

**Recommended for your project:** Neo4j Desktop or Docker (stable + simple).

---

## 15) Data retention & fallback

- Store live stream to JSONL (`data/raw/aisstream_logs/`).
- Auto-reconnect with exponential backoff.
- Replay mode for demo continuity.

---

## 16) Security notes
- Never expose AISStream API key to frontend.
- Keep `.env` out of version control.
---

# TRD v2 Addendum — Closing the 4 Critical Gaps

This addendum resolves the gaps identified in the review:
1) Zone boundary definitions (APPROACH / ANCHORAGE / BERTH)
2) ETA estimation algorithm
3) Port inventory model (berths, cranes, yard blocks)
4) “Expected vessel list” definition (how we know a vessel is “extra”)

> Note: The zone coordinates below are **starter geofences** intended for prototyping and demo stability. You should refine them empirically by plotting AIS points (heatmap) and tightening polygons based on observed traffic density.

---

## A) Zone Definitions (Geofencing)

We classify each incoming AIS point into one of the following zones. Zones are stored in Neo4j as `:Zone` nodes and used to derive `Vessel.status`.

### A1) Approach Zone (Tallinn approaches)
Purpose: identify vessels that are “incoming soon” and should be considered in the scheduling horizon.

**Bounding Box (starter):**
- `lat: 59.65 → 59.30`
- `lon: 24.45 → 25.20`

### A2) Anchorage Zone (waiting area)
Purpose: detect vessels waiting (low SOG) for berth allocation.

**Bounding Box (starter):**
- `lat: 59.56 → 59.45`
- `lon: 24.55 → 24.88`

### A3) Berth Zones (two sub-zones)
Purpose: identify vessels at/near terminals (used for berth occupancy approximation).

**Old City Harbour (starter):**
- `lat: 59.46 → 59.43`
- `lon: 24.72 → 24.80`

**Muuga terminal (starter):**
- `lat: 59.56 → 59.48`
- `lon: 24.88 → 25.07`

### A4) Zone classification rule
Given an AIS point `(lat, lon)`:
1) If inside any BERTH zone → `zone=BERTH`
2) Else if inside ANCHORAGE zone → `zone=ANCHORAGE`
3) Else if inside APPROACH zone → `zone=APPROACH`
4) Else → ignore (outside region of interest)

### A5) Status derivation rule
Given `(zone, sog)`:
- If `zone=BERTH` and `sog < 0.5` → `status=BERTHED`
- If `zone=ANCHORAGE` and `sog < 0.5` → `status=WAITING`
- If `zone=APPROACH` and `sog >= 0.5` → `status=APPROACHING`
- Else → `status=IN_TRANSIT` (optional)

---

## B) ETA Estimation (from AIS)

We estimate ETA to a **reference port point** (one coordinate) to keep the prototype simple.
- Reference point (starter): `PortRef = (59.45, 24.75)`  (near central Tallinn harbor)

### B1) Distance calculation
- Compute great-circle distance using Haversine: `distance_km(lat, lon, PortRef)`
- Convert to nautical miles if you prefer: `distance_nm = distance_km / 1.852`

### B2) Speed smoothing
AIS `sog` can be noisy or 0 for stationary ships. Use a smoothed speed:
- `sog_smooth = EMA(sog, alpha=0.3)` per vessel MMSI

### B3) ETA formula
- If `sog_smooth >= 0.5` knots:
  - `eta_hours = distance_nm / sog_smooth`
  - `eta_ts = now_ts + eta_hours`
- Else:
  - If in anchorage/berth: `eta_ts = None` (already arrived/waiting)
  - If in approach but sog low: clamp to minimum speed:
    - `eta_hours = distance_nm / 0.5`

### B4) Store in KG
Update `:Vessel` node:
- `v.eta_to_port = eta_ts`
- `v.eta_confidence = "high/medium/low"` (optional heuristic based on sog stability)

---

## C) Port Inventory Model (not hardcoded actions; configurable parameters)

We need a configurable inventory for berths, equipment, and yard blocks. This can be synthetic while still realistic.

### C1) Inventory tables (recommended)
Create a simple config (CSV/JSON) that is loaded on service start and upserted to Neo4j:

**Berths**
- `berth_id`
- `terminal` (OldCity / Muuga)
- `max_vessels=1`
- `service_rate_base` (containers/hour baseline)

**Assets**
- `asset_id`
- `asset_type` (CRANE/TRUCK/…)
- `home_berth_id`
- `operation_state`

**YardBlocks**
- `yard_id`
- `terminal`
- `capacity_teu`
- `used_teu`

### C2) Suggested starter inventory (demo-friendly)
- **Berths:** 4 total (2 OldCity, 2 Muuga)
- **Cranes:** 6 total mapped across berths
- **Yard blocks:** 3 total, each with capacity TEU and current utilization

> Important: This is NOT hardcoding “plans”. It is defining the resource constraints (reality). The optimizer still decides allocations dynamically.

---

## D) “Expected Vessel List” (how we detect “extra”)

To decide whether a vessel is “extra”, we need an expected set for the next horizon.

### D1) Practical prototype approach (recommended)
Maintain a rolling expected set derived from recent AIS history:
- “Expected” = vessels that have appeared in the APPROACH zone within the last **N days** at similar time-of-day (or simply last N days).
- Update expected list daily (batch) or hourly (rolling).

### D2) Alternative (manual + forecast hybrid)
- Use Feature 1 forecast to estimate *how many* port calls are expected in the next 7 days.
- Use AIS-derived list to identify *which* vessels are actually approaching.
- If approaching vessel count exceeds forecasted expected count (beyond tolerance), flag “extra load pressure”.

### D3) Definition used by optimizer trigger
- Trigger “extra vessel scenario” when:
  - new MMSI appears in APPROACH and not in expected set, OR
  - queue length / yard utilization spikes beyond thresholds

Store on a `:Scenario` or directly on `:Plan`:
- `scenario_type = EXTRA_VESSEL | ETA_SHIFT | CONGESTION`
- `trigger_reason`

---

## E) Cascade Explanation Logic (why X delayed because of Y)

### E1) Core idea
The cascade is explained using resource dependencies:
- Berths are scarce resources. If a berth is occupied longer, the next vessel assigned to that berth is delayed.

### E2) Computation steps (per plan)
1) Build a schedule per berth from assignments: ordered by start time
2) For each vessel i on berth b:
   - `delay_i = max(0, start_i - eta_i)`
3) For vessel i+1, if vessel i end time shifts:
   - propagate: `start_{i+1} = max(start_{i+1}, end_i)`
4) For each delay, create an `:Impact` node with:
   - `delay_hours`
   - `reason` (human-readable): “Berth B2 occupied by MMSI X until 14:00 → pushed MMSI Y start to 15:30”

### E3) Store in KG for UI
- `(Plan)-[:CAUSES_IMPACT]->(Impact)-[:IMPACTS]->(Vessel)`
- Each `Impact` includes a short reason string + optional chain pointer to the upstream vessel/berth.

---

## F) Implementation priority (confirmed)
1) Zone classification (APPROACH/ANCHORAGE/BERTH)
2) Neo4j setup + schema init
3) AIS ingestion → KG vessel upserts
4) Equipment ingestion → KG asset upserts (Feature 3)
5) Snapshot API
6) CP-SAT optimizer + write plan/impact back
7) Cascade explanation in UI
8) MILP baseline (comparison)

---
