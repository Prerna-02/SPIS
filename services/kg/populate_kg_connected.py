"""
=============================================================================
KNOWLEDGE GRAPH POPULATOR - Properly Connected Graph from AIS Data
=============================================================================

This script rebuilds the Knowledge Graph with properly connected nodes:
- Vessels from real AIS stream data (JSONL file)
- Zones (BERTH, ANCHORAGE, APPROACH)
- Berths with crane assets
- Relationships: IN_ZONE, HAS_ASSET, etc.

Usage:
    python populate_kg_connected.py

Result: A connected graph visible in Neo4j Browser.
=============================================================================
"""

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neo4j_client import Neo4jClient
from zones import classify_zone

# ---------------------------------------------------------------------------
# PORT CONFIGURATION - Tallinn
# ---------------------------------------------------------------------------

# Zone definitions (approximate lat/lon for Tallinn port)
ZONES = [
    {"zone_id": "BERTH_ZONE", "type": "BERTH", "lat_min": 59.453, "lat_max": 59.465, "lon_min": 24.70, "lon_max": 24.75},
    {"zone_id": "ANCHORAGE_ZONE", "type": "ANCHORAGE", "lat_min": 59.44, "lat_max": 59.47, "lon_min": 24.75, "lon_max": 24.80},
    {"zone_id": "APPROACH_ZONE", "type": "APPROACH", "lat_min": 59.48, "lat_max": 59.60, "lon_min": 24.68, "lon_max": 24.80},
]

# Berth definitions
BERTHS = [
    {"berth_id": "OLDCITY_B1", "terminal": "Old City Harbor", "capacity_class": "large", "max_vessels": 1},
    {"berth_id": "OLDCITY_B2", "terminal": "Old City Harbor", "capacity_class": "medium", "max_vessels": 1},
    {"berth_id": "MUUGA_B1", "terminal": "Muuga Container Terminal", "capacity_class": "large", "max_vessels": 1},
    {"berth_id": "MUUGA_B2", "terminal": "Muuga Container Terminal", "capacity_class": "medium", "max_vessels": 1},
]

# Asset definitions (cranes per berth)
ASSETS = [
    {"asset_id": "CRANE_OC1", "berth_id": "OLDCITY_B1", "asset_type": "STS_CRANE", "health_score": 0.92},
    {"asset_id": "CRANE_OC2", "berth_id": "OLDCITY_B1", "asset_type": "STS_CRANE", "health_score": 0.88},
    {"asset_id": "CRANE_OC3", "berth_id": "OLDCITY_B2", "asset_type": "STS_CRANE", "health_score": 0.95},
    {"asset_id": "CRANE_M1", "berth_id": "MUUGA_B1", "asset_type": "STS_CRANE", "health_score": 0.90},
    {"asset_id": "CRANE_M2", "berth_id": "MUUGA_B1", "asset_type": "STS_CRANE", "health_score": 0.85},
    {"asset_id": "CRANE_M3", "berth_id": "MUUGA_B2", "asset_type": "STS_CRANE", "health_score": 0.91},
]


def determine_zone(lat: float, lon: float) -> Tuple[str, str]:
    """
    Determine which zone a vessel is in based on coordinates.
    Returns (zone_id, zone_type).
    """
    for zone in ZONES:
        if (zone["lat_min"] <= lat <= zone["lat_max"] and 
            zone["lon_min"] <= lon <= zone["lon_max"]):
            return zone["zone_id"], zone["type"]
    
    # Default to APPROACH for vessels outside defined zones
    return "APPROACH_ZONE", "APPROACH"


def determine_vessel_status(lat: float, lon: float, sog: float) -> str:
    """
    Determine vessel status based on position and speed.
    """
    zone_id, zone_type = determine_zone(lat, lon)
    
    if zone_type == "BERTH" and sog < 0.5:
        return "BERTHED"
    elif zone_type == "ANCHORAGE" and sog < 0.5:
        return "WAITING"
    elif zone_type == "APPROACH" or sog > 1.0:
        return "APPROACHING"
    else:
        return "WAITING"


def load_ais_data(jsonl_path: str) -> List[Dict]:
    """
    Load AIS data from JSONL file and deduplicate by MMSI (keep latest).
    """
    vessels_by_mmsi = {}
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                mmsi = str(record.get("mmsi", ""))
                if mmsi and mmsi != "299999999":  # Skip test MMSI
                    vessels_by_mmsi[mmsi] = record  # Last record wins
            except json.JSONDecodeError:
                continue
    
    return list(vessels_by_mmsi.values())


def main():
    print("=" * 70)
    print("KNOWLEDGE GRAPH POPULATOR - Creating Connected Graph")
    print("=" * 70)
    
    # Find AIS data file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    ais_data_dir = os.path.join(project_root, "data", "raw", "aisstream_logs")
    
    # Find latest JSONL file
    jsonl_files = [f for f in os.listdir(ais_data_dir) if f.endswith('.jsonl')]
    if not jsonl_files:
        print(f"❌ No JSONL files found in {ais_data_dir}")
        return
    
    latest_file = sorted(jsonl_files)[-1]
    jsonl_path = os.path.join(ais_data_dir, latest_file)
    print(f"\n📂 Loading AIS data from: {latest_file}")
    
    # Load AIS data
    vessels_data = load_ais_data(jsonl_path)
    print(f"   Found {len(vessels_data)} unique vessels")
    
    # Connect to Neo4j
    client = Neo4jClient()
    
    try:
        # Step 1: Clear existing data (keep schema)
        print("\n🗑️  Clearing existing data...")
        client.execute_write("MATCH (n) DETACH DELETE n", {})
        print("   Done - all nodes and relationships cleared")
        
        # Step 2: Create Zones
        print("\n🗺️  Creating Zones...")
        for zone in ZONES:
            client.create_zone(zone["zone_id"], zone["type"])
            print(f"   ✓ Zone: {zone['zone_id']} ({zone['type']})")
        
        # Step 3: Create Berths with zone relationships
        print("\n🚢 Creating Berths...")
        for berth in BERTHS:
            client.upsert_berth(
                berth_id=berth["berth_id"],
                terminal=berth["terminal"],
                capacity_class=berth["capacity_class"],
                max_vessels=berth["max_vessels"]
            )
            # Link berth to BERTH_ZONE
            query = """
            MATCH (b:Berth {berth_id: $berth_id})
            MATCH (z:Zone {zone_id: 'BERTH_ZONE'})
            MERGE (b)-[:IN_ZONE]->(z)
            """
            client.execute_write(query, {"berth_id": berth["berth_id"]})
            print(f"   ✓ Berth: {berth['berth_id']} -> BERTH_ZONE")
        
        # Step 4: Create Assets and link to Berths
        print("\n🏗️  Creating Assets (Cranes)...")
        for asset in ASSETS:
            client.upsert_asset(
                asset_id=asset["asset_id"],
                asset_type=asset["asset_type"],
                operation_state="ACTIVE",
                health_score=asset["health_score"],
                effective_capacity=25.0
            )
            # Link asset to berth
            client.link_berth_to_asset(asset["berth_id"], asset["asset_id"])
            print(f"   ✓ Asset: {asset['asset_id']} -> {asset['berth_id']}")
        
        # Step 5: Create Vessels from AIS data with zone relationships
        print("\n⚓ Creating Vessels from AIS data...")
        status_counts = {"BERTHED": 0, "WAITING": 0, "APPROACHING": 0}
        
        for record in vessels_data:
            mmsi = str(record.get("mmsi", ""))
            lat = record.get("lat", 0)
            lon = record.get("lon", 0)
            sog = record.get("sog", 0) or 0
            cog = record.get("cog", 0) or 0
            
            # Determine zone and status
            zone_id, zone_type = determine_zone(lat, lon)
            status = determine_vessel_status(lat, lon, sog)
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Create vessel
            client.upsert_vessel(
                mmsi=mmsi,
                lat=lat,
                lon=lon,
                sog=sog,
                cog=cog,
                status=status,
                zone=zone_type
            )
            
            # Link vessel to zone
            client.link_vessel_to_zone(mmsi, zone_id)
        
        print(f"   ✓ Created {len(vessels_data)} vessels:")
        print(f"     - BERTHED: {status_counts.get('BERTHED', 0)}")
        print(f"     - WAITING: {status_counts.get('WAITING', 0)}")
        print(f"     - APPROACHING: {status_counts.get('APPROACHING', 0)}")
        
        # Step 6: Assign some vessels to berths (for demo)
        print("\n📍 Assigning vessels to berths (demo)...")
        berthed_vessels = [v for v in vessels_data 
                          if determine_vessel_status(v.get("lat", 0), v.get("lon", 0), v.get("sog", 0) or 0) == "BERTHED"]
        
        for i, berth in enumerate(BERTHS):
            if i < len(berthed_vessels):
                vessel = berthed_vessels[i]
                mmsi = str(vessel.get("mmsi", ""))
                query = """
                MATCH (v:Vessel {mmsi: $mmsi})
                MATCH (b:Berth {berth_id: $berth_id})
                MERGE (v)-[:BERTHED_AT]->(b)
                """
                client.execute_write(query, {"mmsi": mmsi, "berth_id": berth["berth_id"]})
                print(f"   ✓ Vessel {mmsi} -> {berth['berth_id']}")
        
        # Step 7: Create YardBlocks
        print("\n📦 Creating YardBlocks...")
        yard_blocks = [
            {"yard_id": "YB_A1", "terminal": "Old City Harbor", "capacity_teu": 500},
            {"yard_id": "YB_A2", "terminal": "Old City Harbor", "capacity_teu": 400},
            {"yard_id": "YB_B1", "terminal": "Muuga Container Terminal", "capacity_teu": 600},
        ]
        for yb in yard_blocks:
            client.upsert_yard_block(yb["yard_id"], yb["terminal"], yb["capacity_teu"])
            # Link yard block to BERTH_ZONE
            query = """
            MATCH (y:YardBlock {yard_id: $yard_id})
            MATCH (z:Zone {zone_id: 'BERTH_ZONE'})
            MERGE (y)-[:IN_ZONE]->(z)
            """
            client.execute_write(query, {"yard_id": yb["yard_id"]})
            print(f"   ✓ YardBlock: {yb['yard_id']} -> BERTH_ZONE")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ Knowledge Graph Created Successfully!")
        print("=" * 70)
        
        # Count nodes and relationships
        node_count = client.execute_query("MATCH (n) RETURN count(n) as count", {})[0]["count"]
        rel_count = client.execute_query("MATCH ()-[r]->() RETURN count(r) as count", {})[0]["count"]
        
        print(f"\n📊 Graph Statistics:")
        print(f"   - Total Nodes: {node_count}")
        print(f"   - Total Relationships: {rel_count}")
        
        print("\n🔍 To visualize in Neo4j Browser, run:")
        print("   MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 100")
        print("")
        
    finally:
        client.close()


if __name__ == "__main__":
    main()
