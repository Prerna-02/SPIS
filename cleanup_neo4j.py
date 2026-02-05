import sys
sys.path.insert(0, "E:/DL_Final_Project/services/kg")
from neo4j_client import Neo4jClient

client = Neo4jClient()
client.connect()

# First, let's see what we have
query = """
MATCH (v:Vessel)
RETURN v.mmsi as mmsi, v.ship_name as name, v.status as status, v.simulated as simulated
ORDER BY v.mmsi
"""
results = client.execute_query(query)
print(f"Total vessel records: {len(results)}")

# Count duplicates
from collections import Counter
mmsi_counts = Counter(r['mmsi'] for r in results)
duplicates = {k: v for k, v in mmsi_counts.items() if v > 1}
print(f"Duplicate MMSIs: {len(duplicates)}")

# Delete non-simulated vessels (keep simulated ones)
print("\nDeleting non-simulated vessels...")
delete_query = """
MATCH (v:Vessel)
WHERE v.simulated IS NULL OR v.simulated = false
DETACH DELETE v
RETURN count(v) as deleted
"""
result = client.execute_write(delete_query)
print(f"Deleted non-simulated vessels")

# Verify remaining
query = """
MATCH (v:Vessel)
RETURN count(v) as count
"""
result = client.execute_query(query)
print(f"Remaining vessels: {result[0]['count']}")

# Check ETA distribution of remaining vessels
query = """
MATCH (v:Vessel)
RETURN v.mmsi as mmsi, v.ship_name as name, v.eta_to_port as eta, v.containers as containers, v.priority as priority
ORDER BY v.eta_to_port
LIMIT 10
"""
results = client.execute_query(query)
print("\nSample vessels:")
for r in results:
    print(f"  {r['mmsi']}: {r['name']}, ETA={r['eta']}, containers={r['containers']}, priority={r['priority']}")

client.close()
