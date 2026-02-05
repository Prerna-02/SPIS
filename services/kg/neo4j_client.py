"""
=============================================================================
Neo4j Client - Smart Port Intelligence System
=============================================================================

Provides a connection wrapper and CRUD operations for the Knowledge Graph.
Handles vessel upserts, asset updates, and snapshot queries.
=============================================================================
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NEO4J CLIENT
# ---------------------------------------------------------------------------

class Neo4jClient:
    """
    Neo4j database client with connection pooling and helper methods.
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize Neo4j client.
        
        Args:
            uri: Neo4j bolt URI (default from NEO4J_URI env var)
            user: Database user (default from NEO4J_USER env var)
            password: Database password (default from NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        
        self._driver: Optional[Driver] = None
    
    def connect(self) -> None:
        """Establish connection to Neo4j."""
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.uri}...")
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            self._driver.verify_connectivity()
            logger.info("✅ Connected to Neo4j")
    
    def close(self) -> None:
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    @contextmanager
    def session(self):
        """Get a session context manager."""
        if self._driver is None:
            self.connect()
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a Cypher query and return results as list of dicts.
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> None:
        """
        Execute a write query (CREATE, MERGE, DELETE, etc.).
        """
        with self.session() as session:
            session.run(query, parameters or {})
    
    # -----------------------------------------------------------------------
    # VESSEL OPERATIONS
    # -----------------------------------------------------------------------
    
    def upsert_vessel(
        self,
        mmsi: str,
        lat: float,
        lon: float,
        sog: Optional[float] = None,
        cog: Optional[float] = None,
        heading: Optional[float] = None,
        zone: Optional[str] = None,
        status: Optional[str] = None,
        eta_to_port: Optional[str] = None,
        ship_type: Optional[str] = None,
        ship_name: Optional[str] = None,
    ) -> None:
        """
        Upsert a vessel node with latest position data.
        
        Creates the vessel if it doesn't exist, updates if it does.
        Includes ship_type (ITU category) and ship_name from AIS metadata.
        """
        query = """
        MERGE (v:Vessel {mmsi: $mmsi})
        SET v.last_lat = $lat,
            v.last_lon = $lon,
            v.last_sog = $sog,
            v.last_cog = $cog,
            v.last_heading = $heading,
            v.zone = $zone,
            v.status = $status,
            v.eta_to_port = $eta_to_port,
            v.ship_type = $ship_type,
            v.ship_name = $ship_name,
            v.last_seen_ts = datetime()
        """
        self.execute_write(query, {
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "sog": sog,
            "cog": cog,
            "heading": heading,
            "zone": zone,
            "status": status,
            "eta_to_port": eta_to_port,
            "ship_type": ship_type,
            "ship_name": ship_name,
        })
    
    def get_vessel(self, mmsi: str) -> Optional[Dict]:
        """Get a vessel by MMSI."""
        query = "MATCH (v:Vessel {mmsi: $mmsi}) RETURN v"
        results = self.execute_query(query, {"mmsi": mmsi})
        if results:
            return results[0]["v"]
        return None
    
    def get_vessels_by_status(self, status: str) -> List[Dict]:
        """Get all vessels with a specific status."""
        query = "MATCH (v:Vessel {status: $status}) RETURN v ORDER BY v.eta_to_port"
        return [r["v"] for r in self.execute_query(query, {"status": status})]
    
    def get_all_vessels(self) -> List[Dict]:
        """Get all vessels in the KG."""
        query = "MATCH (v:Vessel) RETURN v ORDER BY v.last_seen_ts DESC"
        return [r["v"] for r in self.execute_query(query)]
    
    # -----------------------------------------------------------------------
    # ASSET OPERATIONS
    # -----------------------------------------------------------------------
    
    def upsert_asset(
        self,
        asset_id: str,
        asset_type: str,
        operation_state: str = "OPERATIONAL",
        utilization_rate: float = 0.0,
        rul_hours: Optional[float] = None,
        failure_in_next_72h: bool = False,
        health_score: float = 1.0,
        effective_capacity: float = 1.0,
    ) -> None:
        """Upsert an asset (crane, truck, etc.) node."""
        query = """
        MERGE (a:Asset {asset_id: $asset_id})
        SET a.asset_type = $asset_type,
            a.operation_state = $operation_state,
            a.utilization_rate = $utilization_rate,
            a.rul_hours = $rul_hours,
            a.failure_in_next_72h = $failure_in_next_72h,
            a.health_score = $health_score,
            a.effective_capacity = $effective_capacity,
            a.last_ts = datetime()
        """
        self.execute_write(query, {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "operation_state": operation_state,
            "utilization_rate": utilization_rate,
            "rul_hours": rul_hours,
            "failure_in_next_72h": failure_in_next_72h,
            "health_score": health_score,
            "effective_capacity": effective_capacity,
        })
    
    def get_all_assets(self) -> List[Dict]:
        """Get all assets."""
        query = "MATCH (a:Asset) RETURN a ORDER BY a.asset_id"
        return [r["a"] for r in self.execute_query(query)]
    
    # -----------------------------------------------------------------------
    # BERTH OPERATIONS
    # -----------------------------------------------------------------------
    
    def upsert_berth(
        self,
        berth_id: str,
        terminal: str,
        capacity_class: str,
        max_vessels: int = 1,
        service_rate_base: float = 25.0,
    ) -> None:
        """Upsert a berth node."""
        query = """
        MERGE (b:Berth {berth_id: $berth_id})
        SET b.terminal = $terminal,
            b.capacity_class = $capacity_class,
            b.max_vessels = $max_vessels,
            b.service_rate_base = $service_rate_base
        """
        self.execute_write(query, {
            "berth_id": berth_id,
            "terminal": terminal,
            "capacity_class": capacity_class,
            "max_vessels": max_vessels,
            "service_rate_base": service_rate_base,
        })
    
    def get_all_berths(self) -> List[Dict]:
        """Get all berths."""
        query = "MATCH (b:Berth) RETURN b ORDER BY b.berth_id"
        return [r["b"] for r in self.execute_query(query)]
    
    # -----------------------------------------------------------------------
    # YARD BLOCK OPERATIONS
    # -----------------------------------------------------------------------
    
    def upsert_yard_block(
        self,
        yard_id: str,
        terminal: str,
        capacity_teu: int,
        used_teu: int = 0,
    ) -> None:
        """Upsert a yard block node."""
        query = """
        MERGE (y:YardBlock {yard_id: $yard_id})
        SET y.terminal = $terminal,
            y.capacity_teu = $capacity_teu,
            y.used_teu = $used_teu
        """
        self.execute_write(query, {
            "yard_id": yard_id,
            "terminal": terminal,
            "capacity_teu": capacity_teu,
            "used_teu": used_teu,
        })
    
    def get_all_yard_blocks(self) -> List[Dict]:
        """Get all yard blocks."""
        query = "MATCH (y:YardBlock) RETURN y ORDER BY y.yard_id"
        return [r["y"] for r in self.execute_query(query)]
    
    # -----------------------------------------------------------------------
    # ZONE OPERATIONS
    # -----------------------------------------------------------------------
    
    def create_zone(self, zone_id: str, zone_type: str) -> None:
        """Create a zone node."""
        query = """
        MERGE (z:Zone {zone_id: $zone_id})
        SET z.type = $zone_type
        """
        self.execute_write(query, {"zone_id": zone_id, "zone_type": zone_type})
    
    def link_vessel_to_zone(self, mmsi: str, zone_id: str) -> None:
        """Create IN_ZONE relationship between vessel and zone."""
        query = """
        MATCH (v:Vessel {mmsi: $mmsi})
        MATCH (z:Zone {zone_id: $zone_id})
        MERGE (v)-[:IN_ZONE]->(z)
        """
        self.execute_write(query, {"mmsi": mmsi, "zone_id": zone_id})
    
    # -----------------------------------------------------------------------
    # RELATIONSHIP OPERATIONS
    # -----------------------------------------------------------------------
    
    def link_berth_to_asset(self, berth_id: str, asset_id: str) -> None:
        """Create HAS_ASSET relationship between berth and asset."""
        query = """
        MATCH (b:Berth {berth_id: $berth_id})
        MATCH (a:Asset {asset_id: $asset_id})
        MERGE (b)-[:HAS_ASSET]->(a)
        """
        self.execute_write(query, {"berth_id": berth_id, "asset_id": asset_id})
    
    # -----------------------------------------------------------------------
    # SNAPSHOT QUERY
    # -----------------------------------------------------------------------
    
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a full snapshot of the current KG state for optimizer/UI.
        
        Returns dict with vessels, berths, assets, yard_blocks categorized.
        """
        return {
            "vessels": {
                "approaching": self.get_vessels_by_status("APPROACHING"),
                "waiting": self.get_vessels_by_status("WAITING"),
                "berthed": self.get_vessels_by_status("BERTHED"),
                "total": len(self.get_all_vessels()),
            },
            "berths": self.get_all_berths(),
            "assets": self.get_all_assets(),
            "yard_blocks": self.get_all_yard_blocks(),
            "snapshot_ts": datetime.now(timezone.utc).isoformat(),
        }
    
    # -----------------------------------------------------------------------
    # PLAN PERSISTENCE (TRD Schema)
    # -----------------------------------------------------------------------
    
    def cleanup_old_plans(self, keep_latest: int = 3) -> int:
        """
        Clean up old optimization plans, keeping only the latest N.
        
        Args:
            keep_latest: Number of recent plans to keep
            
        Returns:
            Number of plans deleted
        """
        # Get plan IDs to keep (most recent)
        keep_query = """
        MATCH (p:Plan)
        RETURN p.plan_id as plan_id
        ORDER BY p.created_ts DESC
        LIMIT $keep
        """
        keep_results = self.execute_query(keep_query, {"keep": keep_latest})
        keep_ids = [r["plan_id"] for r in keep_results]
        
        # Delete old plans and their relationships
        delete_query = """
        MATCH (p:Plan)
        WHERE NOT p.plan_id IN $keep_ids
        OPTIONAL MATCH (p)-[:HAS_ASSIGNMENT]->(a:Assignment)
        OPTIONAL MATCH (p)-[:CAUSES_IMPACT]->(i:Impact)
        DETACH DELETE p, a, i
        RETURN count(DISTINCT p) as deleted
        """
        result = self.execute_write(delete_query, {"keep_ids": keep_ids})
        deleted = result[0]["deleted"] if result else 0
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old plans")
        
        return deleted
    
    def save_plan(self, plan: Dict[str, Any]) -> None:
        """
        Save an optimization plan with assignments and impacts to Neo4j.
        
        Creates:
        - (Plan) node
        - (Assignment) nodes with (Plan)-[:HAS_ASSIGNMENT]->(Assignment)
        - (Impact) nodes with (Plan)-[:CAUSES_IMPACT]->(Impact)
        - (Impact)-[:IMPACTS]->(Vessel) relationships
        
        Args:
            plan: Dict with plan_id, objective_score, assignments, impacts
        """
        plan_id = plan.get("plan_id", "unknown")
        
        # 1. Create Plan node
        plan_query = """
        MERGE (p:Plan {plan_id: $plan_id})
        SET p.objective_score = $objective_score,
            p.total_delay_hours = $total_delay_hours,
            p.vessels_impacted = $vessels_impacted,
            p.created_ts = datetime(),
            p.status = 'generated'
        """
        self.execute_write(plan_query, {
            "plan_id": plan_id,
            "objective_score": plan.get("objective_score", 0.0),
            "total_delay_hours": plan.get("total_delay_hours", 0.0),
            "vessels_impacted": plan.get("vessels_impacted", 0),
        })
        
        # 2. Create Assignment nodes and link to Plan
        for i, assignment in enumerate(plan.get("assignments", [])):
            assign_id = f"{plan_id}_assign_{i}"
            assign_query = """
            MERGE (a:Assignment {assignment_id: $assign_id})
            SET a.vessel_mmsi = $vessel_mmsi,
                a.berth_id = $berth_id,
                a.start_time = $start_time,
                a.end_time = $end_time,
                a.delay_minutes = $delay_minutes,
                a.is_extra = $is_extra
            WITH a
            MATCH (p:Plan {plan_id: $plan_id})
            MERGE (p)-[:HAS_ASSIGNMENT]->(a)
            """
            self.execute_write(assign_query, {
                "assign_id": assign_id,
                "plan_id": plan_id,
                "vessel_mmsi": assignment.get("vessel_mmsi", "UNKNOWN"),
                "berth_id": assignment.get("berth_id", "UNKNOWN"),
                "start_time": assignment.get("start_time", 0),
                "end_time": assignment.get("end_time", 0),
                "delay_minutes": assignment.get("delay_minutes", 0),
                "is_extra": assignment.get("is_extra", False),
            })
        
        # 3. Create Impact nodes and link to Plan and Vessel
        for i, impact in enumerate(plan.get("impacts", [])):
            impact_id = f"{plan_id}_impact_{i}"
            impact_query = """
            MERGE (i:Impact {impact_id: $impact_id})
            SET i.vessel_mmsi = $vessel_mmsi,
                i.original_start = $original_start,
                i.new_start = $new_start,
                i.delay_minutes = $delay_minutes,
                i.reason = $reason
            WITH i
            MATCH (p:Plan {plan_id: $plan_id})
            MERGE (p)-[:CAUSES_IMPACT]->(i)
            WITH i
            OPTIONAL MATCH (v:Vessel {mmsi: $vessel_mmsi})
            FOREACH (_ IN CASE WHEN v IS NOT NULL THEN [1] ELSE [] END |
                MERGE (i)-[:IMPACTS]->(v)
            )
            """
            self.execute_write(impact_query, {
                "impact_id": impact_id,
                "plan_id": plan_id,
                "vessel_mmsi": impact.get("vessel_mmsi", "UNKNOWN"),
                "original_start": impact.get("original_start", 0),
                "new_start": impact.get("new_start", 0),
                "delay_minutes": impact.get("delay_minutes", 0),
                "reason": impact.get("reason", ""),
            })
        
        logger.info(f"✅ Saved plan {plan_id} with {len(plan.get('assignments', []))} assignments, {len(plan.get('impacts', []))} impacts")
    
    def get_plan_from_kg(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a plan with assignments and impacts from Neo4j.
        
        Args:
            plan_id: Unique plan identifier
            
        Returns:
            Dict with plan data, or None if not found
        """
        # Get plan node
        plan_query = """
        MATCH (p:Plan {plan_id: $plan_id})
        RETURN p
        """
        plan_results = self.execute_query(plan_query, {"plan_id": plan_id})
        if not plan_results:
            return None
        
        plan_data = plan_results[0]["p"]
        
        # Get assignments
        assign_query = """
        MATCH (p:Plan {plan_id: $plan_id})-[:HAS_ASSIGNMENT]->(a:Assignment)
        RETURN a ORDER BY a.start_time
        """
        assignments = [r["a"] for r in self.execute_query(assign_query, {"plan_id": plan_id})]
        
        # Get impacts
        impact_query = """
        MATCH (p:Plan {plan_id: $plan_id})-[:CAUSES_IMPACT]->(i:Impact)
        RETURN i ORDER BY i.delay_minutes DESC
        """
        impacts = [r["i"] for r in self.execute_query(impact_query, {"plan_id": plan_id})]
        
        return {
            "plan_id": plan_id,
            "objective_score": plan_data.get("objective_score", 0.0),
            "total_delay_hours": plan_data.get("total_delay_hours", 0.0),
            "vessels_impacted": plan_data.get("vessels_impacted", 0),
            "created_ts": str(plan_data.get("created_ts", "")),
            "status": plan_data.get("status", "unknown"),
            "assignments": assignments,
            "impacts": impacts,
        }
    
    def get_berths_with_crane_count(self) -> List[Dict]:
        """
        Get all berths with crane count derived from linked CRANE assets.
        
        Counts cranes with operation_state in ['ACTIVE', 'OPERATIONAL'].
        """
        query = """
        MATCH (b:Berth)
        OPTIONAL MATCH (b)-[:HAS_ASSET]->(a:Asset)
        WHERE (a.asset_type = 'CRANE' OR a.asset_type = 'STS_CRANE')
              AND a.operation_state IN ['ACTIVE', 'OPERATIONAL']
        WITH b, count(a) as crane_count
        RETURN b.berth_id as berth_id, 
               b.terminal as terminal, 
               b.capacity_class as capacity_class,
               b.max_vessels as max_vessels,
               b.service_rate_base as service_rate_base,
               CASE WHEN crane_count > 0 THEN crane_count ELSE 2 END as crane_count
        ORDER BY b.berth_id
        """
        return self.execute_query(query)


# ---------------------------------------------------------------------------
# SINGLETON INSTANCE
# ---------------------------------------------------------------------------

_client: Optional[Neo4jClient] = None


def get_client() -> Neo4jClient:
    """Get the singleton Neo4j client instance."""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


# ---------------------------------------------------------------------------
# TESTING
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client = get_client()
    try:
        client.connect()
        print("[OK] Neo4j connection successful!")
        
        # Test basic query
        result = client.execute_query("RETURN 1 as test")
        print(f"Test query result: {result}")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
    finally:
        client.close()
