"""
=============================================================================
Seed Optimization Data - Generate Realistic Vessel Queue for Optimizer
=============================================================================

Creates 33 vessels with realistic staggered ETAs for the Port of Tallinn.
This enables the CP-SAT optimizer to compute meaningful berth assignments
and cascade impacts.

Based on Tallinn Port KPIs:
- Average vessel service time: 2-4 hours
- Peak hours: 06:00-10:00, 14:00-18:00
- Container throughput: 25-35 TEU/hour per crane
- Average vessels per day: 15-20

Vessel Types Distribution (Tallinn):
- Cargo: 40%
- Ferry: 25%
- Tanker: 15%
- Container: 10%
- Passenger: 10%
"""

import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import json

# Vessel name prefixes by type
VESSEL_NAMES = {
    'cargo': ['NORDIC', 'BALTIC', 'HANSA', 'MARE', 'NORD', 'SEA', 'OCEAN'],
    'ferry': ['TALLINK', 'VIKING', 'ECKERÖ', 'FINNLINES', 'DFDS'],
    'tanker': ['PETRO', 'OIL', 'FUEL', 'CRUDE', 'BITUMEN'],
    'container': ['MEGA', 'MAERSK', 'MSC', 'HAPAG', 'COSCO', 'EVERGREEN'],
    'passenger': ['PRINCESS', 'QUEEN', 'ROYAL', 'CELEBRITY', 'CRYSTAL'],
}

VESSEL_SUFFIXES = ['STAR', 'EXPRESS', 'CARRIER', 'SPIRIT', 'WIND', 'WAVE', 'SKY', 'SEAS']

# Cargo priorities and their weights
CARGO_TYPES = {
    'pharma': {'weight': 0.05, 'priority': 4, 'containers': (50, 150)},
    'food': {'weight': 0.15, 'priority': 3, 'containers': (100, 300)},
    'electronics': {'weight': 0.20, 'priority': 2, 'containers': (150, 400)},
    'general': {'weight': 0.60, 'priority': 1, 'containers': (100, 500)},
}

# Berth assignments (for simulation)
BERTHS = ['OLDCITY_B1', 'OLDCITY_B2', 'MUUGA_B1', 'MUUGA_B2']


def generate_vessel_name(vessel_type: str) -> str:
    """Generate a realistic vessel name."""
    prefixes = VESSEL_NAMES.get(vessel_type, VESSEL_NAMES['cargo'])
    prefix = random.choice(prefixes)
    suffix = random.choice(VESSEL_SUFFIXES)
    return f"{prefix} {suffix}"


def generate_eta_distribution(num_vessels: int) -> List[int]:
    """
    Generate realistic ETA distribution in minutes from now.
    
    Pattern:
    - 10% already at anchorage (ETA = 0-30 min)
    - 30% arriving soon (ETA = 30-120 min)
    - 40% arriving in medium term (ETA = 2-6 hours)
    - 20% arriving later (ETA = 6-12 hours)
    """
    etas = []
    
    # Already at anchorage
    for _ in range(int(num_vessels * 0.10)):
        etas.append(random.randint(0, 30))
    
    # Arriving soon
    for _ in range(int(num_vessels * 0.30)):
        etas.append(random.randint(30, 120))
    
    # Medium term
    for _ in range(int(num_vessels * 0.40)):
        etas.append(random.randint(120, 360))
    
    # Later arrivals
    remaining = num_vessels - len(etas)
    for _ in range(remaining):
        etas.append(random.randint(360, 720))
    
    random.shuffle(etas)
    return etas


def select_cargo_type() -> Dict:
    """Select cargo type based on weighted distribution."""
    rand = random.random()
    cumulative = 0
    for cargo_type, props in CARGO_TYPES.items():
        cumulative += props['weight']
        if rand <= cumulative:
            return {
                'type': cargo_type,
                'priority': props['priority'],
                'containers': random.randint(*props['containers']),
            }
    return {'type': 'general', 'priority': 1, 'containers': 200}


def generate_vessels(num_vessels: int = 33) -> List[Dict]:
    """Generate a realistic vessel queue."""
    vessels = []
    etas = generate_eta_distribution(num_vessels)
    
    # Vessel type distribution
    type_distribution = ['cargo'] * 13 + ['ferry'] * 8 + ['tanker'] * 5 + ['container'] * 4 + ['passenger'] * 3
    random.shuffle(type_distribution)
    
    for i in range(num_vessels):
        vessel_type = type_distribution[i] if i < len(type_distribution) else 'cargo'
        cargo = select_cargo_type()
        
        # Generate MMSI (9-digit number)
        mmsi = f"27{random.randint(1000000, 9999999)}"
        
        vessel = {
            'mmsi': mmsi,
            'vessel_name': generate_vessel_name(vessel_type),
            'vessel_type': vessel_type,
            'eta_minutes': etas[i],
            'containers': cargo['containers'],
            'cargo_type': cargo['type'],
            'priority': cargo['priority'],
            'status': 'WAITING' if etas[i] < 60 else 'APPROACHING',
            'lat': round(59.45 + random.uniform(-0.05, 0.05), 6),
            'lon': round(24.75 + random.uniform(-0.1, 0.1), 6),
        }
        vessels.append(vessel)
    
    # Sort by ETA
    vessels.sort(key=lambda v: v['eta_minutes'])
    return vessels


def generate_neo4j_cypher(vessels: List[Dict]) -> str:
    """Generate Cypher query to create vessels in Neo4j."""
    cypher_lines = [
        "// Clear old simulated vessels",
        "MATCH (v:Vessel) WHERE v.mmsi STARTS WITH 'SIM_' DETACH DELETE v;",
        "",
        "// Create simulated vessels with realistic ETAs",
    ]
    
    for i, v in enumerate(vessels):
        eta_time = datetime.now(timezone.utc) + timedelta(minutes=v['eta_minutes'])
        cypher = f"""
MERGE (v{i}:Vessel {{mmsi: 'SIM_{v['mmsi']}'}})
SET v{i}.ship_name = '{v['vessel_name']}',
    v{i}.ship_type = '{v['vessel_type']}',
    v{i}.status = '{v['status']}',
    v{i}.eta_to_port = '{v['eta_minutes']} minutes',
    v{i}.eta_timestamp = datetime('{eta_time.isoformat()}'),
    v{i}.containers = {v['containers']},
    v{i}.cargo_type = '{v['cargo_type']}',
    v{i}.priority = {v['priority']},
    v{i}.last_lat = {v['lat']},
    v{i}.last_lon = {v['lon']},
    v{i}.zone = '{'ANCHORAGE' if v['status'] == 'WAITING' else 'APPROACH'}',
    v{i}.simulated = true;
"""
        cypher_lines.append(cypher.strip())
    
    # Link to zones
    cypher_lines.append("""
// Link to zones
MATCH (v:Vessel) WHERE v.simulated = true AND v.status = 'WAITING'
MATCH (z:Zone {zone_id: 'ANCHORAGE'})
MERGE (v)-[:IN_ZONE]->(z);

MATCH (v:Vessel) WHERE v.simulated = true AND v.status = 'APPROACHING'
MATCH (z:Zone {zone_id: 'APPROACH'})
MERGE (v)-[:IN_ZONE]->(z);
""")
    
    return "\n".join(cypher_lines)


def save_for_optimizer(vessels: List[Dict], filepath: str):
    """Save vessel data for optimizer consumption."""
    optimizer_data = []
    for v in vessels:
        optimizer_data.append({
            'mmsi': f"SIM_{v['mmsi']}",
            'vessel_name': v['vessel_name'],
            'vessel_type': v['vessel_type'],
            'eta_minutes': v['eta_minutes'],
            'containers': v['containers'],
            'cargo_type': v['cargo_type'],
            'priority': v['priority'],
            'status': v['status'],
        })
    
    with open(filepath, 'w') as f:
        json.dump(optimizer_data, f, indent=2)
    
    print(f"Saved {len(optimizer_data)} vessels to {filepath}")


def insert_to_neo4j(vessels: List[Dict]):
    """Insert vessels directly into Neo4j."""
    from neo4j_client import Neo4jClient
    
    client = Neo4jClient()
    client.connect()
    
    # Clear old simulated vessels
    client.execute_write(
        "MATCH (v:Vessel) WHERE v.mmsi STARTS WITH 'SIM_' DETACH DELETE v"
    )
    print("Cleared old simulated vessels")
    
    # Insert new vessels
    for v in vessels:
        eta_time = datetime.now(timezone.utc) + timedelta(minutes=v['eta_minutes'])
        
        query = """
        MERGE (v:Vessel {mmsi: $mmsi})
        SET v.ship_name = $ship_name,
            v.ship_type = $ship_type,
            v.status = $status,
            v.eta_to_port = $eta_to_port,
            v.eta_timestamp = datetime($eta_timestamp),
            v.containers = $containers,
            v.cargo_type = $cargo_type,
            v.priority = $priority,
            v.last_lat = $lat,
            v.last_lon = $lon,
            v.zone = $zone,
            v.simulated = true,
            v.last_seen_ts = datetime()
        """
        
        params = {
            'mmsi': f"SIM_{v['mmsi']}",
            'ship_name': v['vessel_name'],
            'ship_type': v['vessel_type'],
            'status': v['status'],
            'eta_to_port': f"{v['eta_minutes']} minutes",
            'eta_timestamp': eta_time.isoformat(),
            'containers': v['containers'],
            'cargo_type': v['cargo_type'],
            'priority': v['priority'],
            'lat': v['lat'],
            'lon': v['lon'],
            'zone': 'ANCHORAGE' if v['status'] == 'WAITING' else 'APPROACH',
        }
        
        client.execute_write(query, params)
    
    # Link to zones
    client.execute_write("""
        MATCH (v:Vessel) WHERE v.simulated = true AND v.status = 'WAITING'
        MATCH (z:Zone {zone_id: 'ANCHORAGE'})
        MERGE (v)-[:IN_ZONE]->(z)
    """)
    
    client.execute_write("""
        MATCH (v:Vessel) WHERE v.simulated = true AND v.status = 'APPROACHING'
        MATCH (z:Zone {zone_id: 'APPROACH'})
        MERGE (v)-[:IN_ZONE]->(z)
    """)
    
    print(f"Inserted {len(vessels)} simulated vessels into Neo4j")
    
    # Print summary
    print("\nVessel Summary:")
    print(f"  - At anchorage (ETA < 1h): {sum(1 for v in vessels if v['eta_minutes'] < 60)}")
    print(f"  - Arriving soon (1-2h): {sum(1 for v in vessels if 60 <= v['eta_minutes'] < 120)}")
    print(f"  - Medium term (2-6h): {sum(1 for v in vessels if 120 <= v['eta_minutes'] < 360)}")
    print(f"  - Later (6-12h): {sum(1 for v in vessels if v['eta_minutes'] >= 360)}")
    
    print("\nPriority Distribution:")
    for cargo_type in ['pharma', 'food', 'electronics', 'general']:
        count = sum(1 for v in vessels if v['cargo_type'] == cargo_type)
        if count > 0:
            print(f"  - {cargo_type}: {count} vessels")
    
    client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Realistic Vessel Queue for Optimizer")
    print("=" * 60)
    
    # Generate vessels
    vessels = generate_vessels(33)
    
    # Print preview
    print("\nGenerated Vessels (first 10):")
    print("-" * 80)
    for v in vessels[:10]:
        print(f"  {v['mmsi']}: {v['vessel_name']:<20} ETA={v['eta_minutes']:>4}min "
              f"({v['status']:<10}) {v['containers']} TEU [{v['cargo_type']}]")
    print("  ...")
    
    # Save to JSON for optimizer
    save_for_optimizer(vessels, "E:/DL_Final_Project/data/processed/simulated_vessels.json")
    
    # Insert to Neo4j
    print("\nInserting to Neo4j...")
    insert_to_neo4j(vessels)
    
    print("\n" + "=" * 60)
    print("Done! Vessels ready for optimization.")
    print("=" * 60)
