import sys
sys.path.insert(0, "E:/DL_Final_Project/services/kg")
from neo4j_client import Neo4jClient

client = Neo4jClient()
client.connect()

# Get berths with crane count
berths = client.get_berths_with_crane_count()
print("Berths with crane count:")
for b in berths:
    print(f"  {b}")

# Calculate expected service time for 150 containers
print("\nExpected service times for 150 containers:")
for b in berths:
    rate = b.get('service_rate_base', 25)
    cranes = b.get('crane_count', 2)
    containers_per_hour = rate * cranes
    service_minutes = int(150 / containers_per_hour * 60)
    print(f"  {b.get('berth_id')}: rate={rate}, cranes={cranes}, service={service_minutes} min")

client.close()
