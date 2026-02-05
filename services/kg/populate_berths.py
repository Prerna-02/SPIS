"""Populate berths and assets in Neo4j."""
from neo4j_client import Neo4jClient

client = Neo4jClient()
client.connect()

# Create berths
BERTHS = [
    {'berth_id': 'OLDCITY_B1', 'terminal': 'Old City Harbor', 'capacity_class': 'large', 'max_vessels': 1, 'service_rate_base': 30.0},
    {'berth_id': 'OLDCITY_B2', 'terminal': 'Old City Harbor', 'capacity_class': 'medium', 'max_vessels': 1, 'service_rate_base': 25.0},
    {'berth_id': 'MUUGA_B1', 'terminal': 'Muuga Container Terminal', 'capacity_class': 'large', 'max_vessels': 1, 'service_rate_base': 35.0},
    {'berth_id': 'MUUGA_B2', 'terminal': 'Muuga Container Terminal', 'capacity_class': 'medium', 'max_vessels': 1, 'service_rate_base': 28.0},
]

for b in BERTHS:
    client.upsert_berth(
        berth_id=b['berth_id'],
        terminal=b['terminal'],
        capacity_class=b['capacity_class'],
        max_vessels=b['max_vessels'],
        service_rate_base=b.get('service_rate_base', 25.0)
    )
    print(f"Created berth: {b['berth_id']} at {b['terminal']}")

# Create assets and link to berths
ASSETS = [
    {'asset_id': 'CRANE_OC1', 'berth_id': 'OLDCITY_B1', 'health_score': 0.92},
    {'asset_id': 'CRANE_OC2', 'berth_id': 'OLDCITY_B1', 'health_score': 0.88},
    {'asset_id': 'CRANE_OC3', 'berth_id': 'OLDCITY_B2', 'health_score': 0.95},
    {'asset_id': 'CRANE_M1', 'berth_id': 'MUUGA_B1', 'health_score': 0.90},
    {'asset_id': 'CRANE_M2', 'berth_id': 'MUUGA_B1', 'health_score': 0.85},
    {'asset_id': 'CRANE_M3', 'berth_id': 'MUUGA_B2', 'health_score': 0.91},
]

for a in ASSETS:
    # Create asset
    client.upsert_asset(
        asset_id=a['asset_id'],
        asset_type='STS_CRANE',
        operation_state='ACTIVE',
        effective_capacity=100.0,
        health_score=a.get('health_score', 0.9)
    )
    
    # Link to berth
    link_query = """
    MATCH (asset:Asset {asset_id: $asset_id})
    MATCH (berth:Berth {berth_id: $berth_id})
    MERGE (berth)-[:HAS_ASSET]->(asset)
    """
    client.execute_write(link_query, {'asset_id': a['asset_id'], 'berth_id': a['berth_id']})
    print(f"Created asset: {a['asset_id']} linked to {a['berth_id']}")

client.close()
print("\nDone! 4 berths and 6 cranes populated.")
