"""Quick script to check vessels in Neo4j"""
import sys
sys.path.insert(0, '../kg')
from neo4j_client import get_client

c = get_client()
c.connect()

vessels = c.get_all_vessels()
print(f"\nVessels in KG: {len(vessels)}")
print("-" * 50)

for v in vessels[:10]:
    print(f"  {v['mmsi']}: {v.get('zone')} → {v.get('status')}")

if len(vessels) > 10:
    print(f"  ... and {len(vessels) - 10} more")

# Get snapshot
snapshot = c.get_snapshot()
print(f"\nSnapshot:")
print(f"  Approaching: {len(snapshot['vessels']['approaching'])}")
print(f"  Waiting: {len(snapshot['vessels']['waiting'])}")
print(f"  Berthed: {len(snapshot['vessels']['berthed'])}")

c.close()
