import sys
sys.path.insert(0, "E:/DL_Final_Project/services/kg")
from neo4j_client import Neo4jClient

client = Neo4jClient()
client.connect()

# Check berths with crane count
berths = client.get_berths_with_crane_count()
print("Berths with crane count:")
for b in berths:
    print(f"  {b.get('berth_id')}: crane_count={b.get('crane_count')}, service_rate={b.get('service_rate_base')}")

# Check asset relationships
query = """
MATCH (b:Berth)
OPTIONAL MATCH (b)-[r:HAS_ASSET]->(a:Asset)
RETURN b.berth_id as berth, type(r) as rel_type, a.asset_id as asset, a.asset_type as asset_type, a.operation_state as state
"""
results = client.execute_query(query)
print("\nBerth-Asset relationships:")
for r in results:
    print(f"  {r}")

client.close()
