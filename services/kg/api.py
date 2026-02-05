"""
=============================================================================
Knowledge Graph API Service - Smart Port Intelligence System
=============================================================================

FastAPI backend providing:
- GET /kg/snapshot - Current port state for optimizer/UI
- POST /optimizer/scenario - Input extra vessel scenario
- POST /optimizer/run - Execute optimization
- GET /plans/{plan_id} - Get plan details

Run:
    uvicorn api:app --reload --port 8000

Endpoints:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/kg/snapshot
=============================================================================
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

# Add kg module to path
sys.path.insert(0, os.path.dirname(__file__))

from neo4j_client import Neo4jClient, get_client
from config import get_inventory_summary


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def serialize_neo4j_value(value):
    """Convert Neo4j types to JSON-serializable types."""
    if hasattr(value, 'isoformat'):  # datetime objects
        return value.isoformat()
    if hasattr(value, 'year'):  # Neo4j DateTime/Date
        return str(value)
    return value


def serialize_record(record: dict) -> dict:
    """Serialize a Neo4j record to JSON-safe dict."""
    return {k: serialize_neo4j_value(v) for k, v in record.items()}


def serialize_list(records: list) -> list:
    """Serialize a list of Neo4j records."""
    return [serialize_record(r) if isinstance(r, dict) else r for r in records]

# ---------------------------------------------------------------------------
# PYDANTIC MODELS
# ---------------------------------------------------------------------------

class VesselResponse(BaseModel):
    mmsi: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    sog: Optional[float] = None
    zone: Optional[str] = None
    status: Optional[str] = None
    eta_to_port: Optional[str] = None


class BerthResponse(BaseModel):
    berth_id: str
    terminal: str
    capacity_class: str
    max_vessels: int = 1
    service_rate_base: float


class AssetResponse(BaseModel):
    asset_id: str
    asset_type: str
    operation_state: str
    effective_capacity: float
    health_score: Optional[float] = None


class YardBlockResponse(BaseModel):
    yard_id: str
    terminal: str
    capacity_teu: int
    used_teu: int


class SnapshotResponse(BaseModel):
    snapshot_ts: str
    vessels: dict
    berths: List[dict]
    assets: List[dict]
    yard_blocks: List[dict]
    summary: dict


class ExtraVesselInput(BaseModel):
    mmsi: Optional[str] = Field(None, description="MMSI if known, else generated")
    eta: str = Field(..., description="Expected arrival time (ISO format)")
    containers_est: int = Field(100, description="Estimated container count")
    cargo_priority: str = Field("general", description="Priority: pharma > food > electronics > general")


class ScenarioInput(BaseModel):
    extra_vessel: ExtraVesselInput
    allow_overtime: bool = False
    max_wait_hours: float = 24.0
    risk_tolerance: str = "medium"


class ScenarioResponse(BaseModel):
    scenario_id: str
    created_ts: str
    extra_vessel: dict
    status: str = "pending"


class PlanSummary(BaseModel):
    plan_id: str
    objective_score: float
    total_delay_hours: float
    vessels_impacted: int


class OptimizationResponse(BaseModel):
    scenario_id: str
    plans: List[PlanSummary]
    runtime_seconds: float


# ---------------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Neo4j connection on startup."""
    client = get_client()
    try:
        client.connect()
        print("[OK] Neo4j connected")
        yield
    finally:
        client.close()
        print("Neo4j connection closed")


app = FastAPI(
    title="SPIS Knowledge Graph API",
    description="Smart Port Intelligence System - KG & Optimization APIs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/kg/snapshot", response_model=SnapshotResponse)
async def get_snapshot(window_hours: int = 72):
    """
    Get current Knowledge Graph snapshot.
    
    Returns vessels by status, berths, assets, and yard utilization.
    """
    client = get_client()
    
    try:
        snapshot = client.get_snapshot()
        
        # Calculate summary stats
        vessels = snapshot["vessels"]
        total_vessels = len(vessels.get("approaching", [])) + \
                       len(vessels.get("waiting", [])) + \
                       len(vessels.get("berthed", []))
        
        yard_blocks = snapshot.get("yard_blocks", [])
        total_yard_capacity = sum(y.get("capacity_teu", 0) for y in yard_blocks)
        total_yard_used = sum(y.get("used_teu", 0) for y in yard_blocks)
        
        summary = {
            "vessels_approaching": len(vessels.get("approaching", [])),
            "vessels_waiting": len(vessels.get("waiting", [])),
            "vessels_berthed": len(vessels.get("berthed", [])),
            "total_vessels": total_vessels,
            "berths_total": len(snapshot.get("berths", [])),
            "assets_total": len(snapshot.get("assets", [])),
            "yard_utilization_pct": round(100 * total_yard_used / total_yard_capacity, 1) if total_yard_capacity > 0 else 0,
            "inventory": get_inventory_summary(),
        }
        
        # Serialize Neo4j objects to JSON-safe format
        serialized_vessels = {
            "approaching": serialize_list(vessels.get("approaching", [])),
            "waiting": serialize_list(vessels.get("waiting", [])),
            "berthed": serialize_list(vessels.get("berthed", [])),
            "total": vessels.get("total", 0),
        }
        
        return SnapshotResponse(
            snapshot_ts=snapshot.get("snapshot_ts", datetime.now(timezone.utc).isoformat()),
            vessels=serialized_vessels,
            berths=serialize_list(snapshot.get("berths", [])),
            assets=serialize_list(snapshot.get("assets", [])),
            yard_blocks=serialize_list(yard_blocks),
            summary=summary,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot failed: {str(e)}")


@app.get("/kg/vessels")
async def get_vessels(status: Optional[str] = None):
    """Get all vessels, optionally filtered by status."""
    client = get_client()
    
    if status:
        vessels = client.get_vessels_by_status(status.upper())
    else:
        vessels = client.get_all_vessels()
    
    return {"count": len(vessels), "vessels": vessels}


@app.delete("/kg/vessels/clear-simulated")
async def clear_simulated_vessels():
    """
    Clear old simulated/seeded vessels (MMSI starting with VESSEL_ or WAITING_).
    Keeps real AIS vessels (numeric MMSI).
    """
    client = get_client()
    
    # Delete simulated vessels (non-numeric MMSI patterns)
    query = """
    MATCH (v:Vessel)
    WHERE v.mmsi STARTS WITH 'VESSEL_' OR v.mmsi STARTS WITH 'WAITING_' 
          OR v.mmsi STARTS WITH 'APPROACH_' OR NOT v.mmsi =~ '^[0-9]+$'
    DETACH DELETE v
    RETURN count(v) as deleted_count
    """
    result = client.execute_query(query)
    deleted = result[0]["deleted_count"] if result else 0
    
    return {"message": f"Cleared {deleted} simulated vessels", "deleted_count": deleted}


@app.get("/kg/vessels/recent")
async def get_recent_vessels(minutes: int = 30):
    """
    Get vessels updated within the last N minutes (from live AIS).
    """
    client = get_client()
    
    query = """
    MATCH (v:Vessel)
    WHERE v.last_seen_ts > datetime() - duration({minutes: $minutes})
    RETURN v
    ORDER BY v.last_seen_ts DESC
    """
    results = client.execute_query(query, {"minutes": minutes})
    vessels = [r["v"] for r in results]
    
    return {
        "count": len(vessels),
        "filter": f"last {minutes} minutes",
        "vessels": serialize_list(vessels)
    }


@app.get("/kg/berths")
async def get_berths():
    """Get all berths with their assets."""
    client = get_client()
    berths = client.get_all_berths()
    return {"count": len(berths), "berths": berths}


@app.get("/kg/assets")
async def get_assets():
    """Get all assets (cranes, trucks, etc.)."""
    client = get_client()
    assets = client.get_all_assets()
    return {"count": len(assets), "assets": assets}


# ---------------------------------------------------------------------------
# MODEL INFO ENDPOINT
# ---------------------------------------------------------------------------

@app.get("/kg/model-info")
async def get_model_info():
    """
    Get comprehensive information about KG + CP-SAT optimization.
    """
    return {
        "knowledge_graph": {
            "problem_statement": "Ports manage complex interdependencies: vessels need berths, berths need cranes, cranes need operators, containers need yard space. Traditional databases store these as isolated tables, making it impossible to answer: 'If Crane-1 breaks, which vessels are delayed?' A Knowledge Graph (KG) represents entities as nodes and relationships as edges, enabling intuitive querying and cascading impact analysis.",
            "why_kg": [
                "Captures relationships: Vessel → USES → Berth → HAS → Crane",
                "Enables graph traversal: 'Find all vessels impacted by B1 closure'",
                "Supports real-time updates from AIS stream",
                "Natural fit for 'what-if' scenario modeling"
            ],
            "entities": [
                {"name": "Vessel", "description": "Ships approaching/berthed at port", "properties": ["mmsi", "status", "eta", "zone"]},
                {"name": "Berth", "description": "Docking positions for vessels", "properties": ["berth_id", "terminal", "capacity_class"]},
                {"name": "Asset", "description": "Cranes, trucks, equipment", "properties": ["asset_id", "type", "health_score"]},
                {"name": "YardBlock", "description": "Container storage areas", "properties": ["yard_id", "capacity_teu", "used_teu"]},
                {"name": "Zone", "description": "Geographic areas (Approach, Anchorage, Berth)", "properties": ["zone_id", "type"]}
            ],
            "relationships": [
                "Vessel -[:IN_ZONE]-> Zone",
                "Vessel -[:USES (scheduled)]-> Berth",
                "Berth -[:HAS_ASSET]-> Asset",
                "Berth -[:CONNECTED_TO]-> YardBlock"
            ],
            "business_value": "With KG, port operators can instantly see: 'Show me all vessels that will be affected if Terminal A has a crane failure' - a query that would require complex JOINs across 5+ tables in traditional SQL."
        },
        "cpsat_optimizer": {
            "problem_statement": "Berth Assignment is a combinatorial optimization problem: Given N vessels arriving with different ETAs, cargo types, and service time requirements, assign each to one of M berths to minimize total waiting time while respecting constraints (berth capacity, crane availability, cargo compatibility).",
            "why_cpsat": [
                "Constraint Programming: Naturally expresses 'Vessel can only use Berth if capacity >= vessel size'",
                "SAT Solver: Efficiently finds feasible solutions in large search spaces",
                "Google OR-Tools: Industry-standard, battle-tested optimizer",
                "Handles both hard constraints (must satisfy) and soft constraints (optimize)"
            ],
            "alternatives_considered": {
                "Greedy/Heuristics": "Fast but no optimality guarantee, misses better solutions",
                "MILP (Mixed Integer LP)": "Good for linear problems, but berth assignment has discrete choices",
                "Genetic Algorithms": "Good for exploration, but slower convergence",
                "CP-SAT": "Best of both worlds: constraint expressiveness + SAT efficiency"
            },
            "constraints": {
                "hard": [
                    "Berth capacity: Large vessels only at large berths",
                    "No overlap: One vessel per berth at a time",
                    "Crane availability: Berth must have operational cranes",
                    "Yard space: Sufficient container storage available"
                ],
                "soft": [
                    "Minimize total delay hours",
                    "Prefer berths close to destination yard",
                    "Balance workload across terminals"
                ]
            }
        },
        "objective_score": {
            "description": "A 0-100 score measuring optimization quality. Higher = better.",
            "components": [
                {"name": "Delay Minimization", "weight": 0.40, "description": "Total hours vessels wait beyond their ETA"},
                {"name": "Berth Utilization", "weight": 0.30, "description": "% of berth-hours used vs available"},
                {"name": "Workload Balance", "weight": 0.20, "description": "Even distribution across terminals"},
                {"name": "Priority Compliance", "weight": 0.10, "description": "High-priority cargo (pharma, food) served first"}
            ],
            "formula": "Score = 100 - (DelayPenalty × 0.4) - (IdlePenalty × 0.3) - (ImbalancePenalty × 0.2) - (PriorityPenalty × 0.1)"
        },
        "cascade_impact": {
            "concept": "When one vessel is delayed, it creates a ripple effect. If MEGA CONTAINER takes Berth B1 longer than expected, BALTIC STAR waiting for B1 must wait, which delays NORDIC EXPRESS waiting for B2 (because BALTIC STAR was going to move there).",
            "how_kg_helps": "KG stores the planned schedule as relationships. When a delay occurs, we traverse: Vessel → BLOCKS → Berth → BLOCKS → NextVessel → recursively",
            "visualization": "Cascade is shown as a chain: Original Delay → Impacted Vessel 1 (+1.5h) → Impacted Vessel 2 (+2h) → ..."
        }
    }


# ---------------------------------------------------------------------------
# SCENARIO & OPTIMIZATION (Phase 4)
# ---------------------------------------------------------------------------

# In-memory storage
_scenarios = {}
_plans = {}

logger = logging.getLogger(__name__)


@app.post("/optimizer/scenario", response_model=ScenarioResponse)
async def create_scenario(scenario: ScenarioInput):
    """
    Create an optimization scenario with an extra vessel.
    
    Returns scenario_id for use with /optimizer/run.
    """
    import uuid
    
    scenario_id = str(uuid.uuid4())[:8]
    created_ts = datetime.now(timezone.utc).isoformat()
    
    # Store scenario
    _scenarios[scenario_id] = {
        "scenario_id": scenario_id,
        "created_ts": created_ts,
        "extra_vessel": scenario.extra_vessel.model_dump(),
        "allow_overtime": scenario.allow_overtime,
        "max_wait_hours": scenario.max_wait_hours,
        "risk_tolerance": scenario.risk_tolerance,
        "status": "pending",
    }
    
    return ScenarioResponse(
        scenario_id=scenario_id,
        created_ts=created_ts,
        extra_vessel=scenario.extra_vessel.model_dump(),
        status="pending",
    )


@app.post("/optimizer/run", response_model=OptimizationResponse)
async def run_optimization(scenario_id: str):
    """
    Run CP-SAT optimization for a given scenario.
    
    Returns top 3 plans with KPIs.
    Uses Google OR-Tools CP-SAT solver.
    Includes WAITING + APPROACHING vessels (ETA within 24h).
    """
    import time
    from optimizer import optimize_scenario
    
    if scenario_id not in _scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    
    scenario = _scenarios[scenario_id]
    start_time = time.time()
    
    try:
        # Get current port state from KG
        client = get_client()
        
        # Clean up old plans to avoid clutter in Neo4j
        client.cleanup_old_plans(keep_latest=3)
        
        snapshot = client.get_snapshot()
        
        # Include WAITING + APPROACHING vessels (optimizer handles 24h horizon filter)
        waiting_vessels = snapshot["vessels"].get("waiting", [])
        approaching_vessels = snapshot["vessels"].get("approaching", [])
        all_vessels = waiting_vessels + approaching_vessels
        
        # Get berths with crane count derived from linked assets
        berths = client.get_berths_with_crane_count()
        
        logger.info(f"Optimization input: {len(waiting_vessels)} waiting, {len(approaching_vessels)} approaching, {len(berths)} berths")
        
        # Run CP-SAT optimizer
        plans_data = optimize_scenario(
            vessels=all_vessels,
            berths=berths,
            extra_vessel=scenario["extra_vessel"],
        )
        
        # Convert to response models
        plans = [
            PlanSummary(
                plan_id=p.plan_id,
                objective_score=p.objective_score,
                total_delay_hours=p.total_delay_hours,
                vessels_impacted=p.vessels_impacted,
            )
            for p in plans_data
        ]
        
        # Store full plans for /plans/{plan_id} endpoint (in-memory)
        for p in plans_data:
            _plans[p.plan_id] = p
            
            # Also persist to Neo4j
            plan_dict = {
                "plan_id": p.plan_id,
                "objective_score": p.objective_score,
                "total_delay_hours": p.total_delay_hours,
                "vessels_impacted": p.vessels_impacted,
                "assignments": [
                    {
                        "vessel_mmsi": a.vessel_mmsi,
                        "berth_id": a.berth_id,
                        "start_time": a.start_time,
                        "end_time": a.end_time,
                        "delay_minutes": a.delay_minutes,
                        "is_extra": a.is_extra,
                    }
                    for a in p.assignments
                ],
                "impacts": [
                    {
                        "vessel_mmsi": i.vessel_mmsi,
                        "original_start": i.original_start,
                        "new_start": i.new_start,
                        "delay_minutes": i.delay_minutes,
                        "reason": i.reason,
                    }
                    for i in p.impacts
                ],
            }
            client.save_plan(plan_dict)
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        # Return empty result with error info
        plans = []
    
    runtime = time.time() - start_time
    
    # Update scenario status
    _scenarios[scenario_id]["status"] = "completed"
    
    return OptimizationResponse(
        scenario_id=scenario_id,
        plans=plans,
        runtime_seconds=round(runtime, 3),
    )


@app.get("/plans/{plan_id}")
async def get_plan_detail(plan_id: str):
    """
    Get detailed plan with assignments and impacts.
    Returns full plan data with formatted times (HH:MM).
    """
    from datetime import timedelta
    
    if plan_id not in _plans:
        # Try fetching from Neo4j
        client = get_client()
        kg_plan = client.get_plan_from_kg(plan_id)
        if kg_plan:
            return kg_plan
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    plan = _plans[plan_id]
    now = datetime.now(timezone.utc)
    
    def format_time(minutes: int) -> str:
        """Convert minutes from now to HH:MM format."""
        target = now + timedelta(minutes=minutes)
        return target.strftime("%H:%M")
    
    return {
        "plan_id": plan.plan_id,
        "objective_score": plan.objective_score,
        "total_delay_hours": plan.total_delay_hours,
        "vessels_impacted": plan.vessels_impacted,
        "assignments": [
            {
                "vessel_mmsi": a.vessel_mmsi,
                "berth_id": a.berth_id,
                "start_time_minutes": a.start_time,
                "end_time_minutes": a.end_time,
                "formatted_start": format_time(a.start_time),
                "formatted_end": format_time(a.end_time),
                "delay_minutes": a.delay_minutes,
                "is_extra_vessel": a.is_extra,
            }
            for a in plan.assignments
        ],
        "impacts": [
            {
                "vessel_mmsi": i.vessel_mmsi,
                "original_start_minutes": i.original_start,
                "new_start_minutes": i.new_start,
                "formatted_original": format_time(i.original_start),
                "formatted_new": format_time(i.new_start),
                "delay_minutes": i.delay_minutes,
                "delay_hours": round(i.delay_minutes / 60, 1),
                "reason": i.reason,
            }
            for i in plan.impacts
        ],
    }


@app.get("/kg/cascade/{plan_id}")
async def get_cascade_visualization(plan_id: str):
    """
    Get cascade impact data formatted for UI visualization.
    
    Returns a simplified structure for rendering cascade diagrams.
    """
    from datetime import timedelta
    
    if plan_id not in _plans:
        # Try fetching from Neo4j
        client = get_client()
        kg_plan = client.get_plan_from_kg(plan_id)
        if not kg_plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        # Return simplified cascade from KG data
        return {
            "plan_id": plan_id,
            "cascade_count": len(kg_plan.get("impacts", [])),
            "cascades": [
                {
                    "vessel": i.get("vessel_mmsi", "UNKNOWN"),
                    "delay_hours": round(i.get("delay_minutes", 0) / 60, 1),
                    "reason": i.get("reason", ""),
                }
                for i in kg_plan.get("impacts", [])
            ],
        }
    
    plan = _plans[plan_id]
    now = datetime.now(timezone.utc)
    
    def format_time(minutes: int) -> str:
        target = now + timedelta(minutes=minutes)
        return target.strftime("%H:%M")
    
    # Build berth timeline for visualization
    berth_timeline = {}
    for a in plan.assignments:
        if a.berth_id not in berth_timeline:
            berth_timeline[a.berth_id] = []
        berth_timeline[a.berth_id].append({
            "vessel": a.vessel_mmsi,
            "start": format_time(a.start_time),
            "end": format_time(a.end_time),
            "is_extra": a.is_extra,
            "delay_minutes": a.delay_minutes,
        })
    
    # Sort each berth's timeline by start time
    for berth_id in berth_timeline:
        berth_timeline[berth_id].sort(key=lambda x: x["start"])
    
    return {
        "plan_id": plan.plan_id,
        "objective_score": plan.objective_score,
        "total_delay_hours": plan.total_delay_hours,
        "cascade_count": len(plan.impacts),
        "cascades": [
            {
                "vessel": i.vessel_mmsi,
                "original_time": format_time(i.original_start),
                "new_time": format_time(i.new_start),
                "delay_hours": round(i.delay_minutes / 60, 1),
                "reason": i.reason,
            }
            for i in plan.impacts
        ],
        "berth_timeline": berth_timeline,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
