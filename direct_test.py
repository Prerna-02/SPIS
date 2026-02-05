import sys
import logging
logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, "E:/DL_Final_Project/services/kg")
from neo4j_client import Neo4jClient
from optimizer import VesselData, BerthData, greedy_schedule, PRIORITY_MAP

client = Neo4jClient()
client.connect()

# Get berths with crane count
berths_raw = client.get_berths_with_crane_count()
print("RAW BERTHS FROM NEO4J:")
for b in berths_raw:
    print(f"  {b}")

# Convert to BerthData
berths = [
    BerthData(
        berth_id=b.get("berth_id", f"B{i}"),
        terminal=b.get("terminal", "UNKNOWN"),
        service_rate=b.get("service_rate_base") or 25.0,
        crane_count=b.get("crane_count") or 2,
    )
    for i, b in enumerate(berths_raw)
]

print("\nCONVERTED BERTHS:")
for b in berths:
    print(f"  {b.berth_id}: rate={b.service_rate}, cranes={b.crane_count}")

# Get vessels
snapshot = client.get_snapshot()
vessels_raw = snapshot["vessels"].get("waiting", []) + snapshot["vessels"].get("approaching", [])
print(f"\nVESSELS: {len(vessels_raw)} total")

# Convert to VesselData (simplified)
vessels = []
for v in vessels_raw[:5]:  # Just first 5 for testing
    mmsi = str(v.get("mmsi", "UNKNOWN"))
    containers = v.get("containers") or 150
    eta_str = str(v.get("eta_to_port", "0"))
    if "minutes" in eta_str.lower():
        eta_minutes = int(eta_str.split()[0])
    else:
        eta_minutes = 0
    priority = v.get("priority") or 1
    
    vessels.append(VesselData(
        mmsi=mmsi,
        eta_minutes=eta_minutes,
        containers=containers,
        priority_score=priority,
    ))
    print(f"  {mmsi}: containers={containers}, eta={eta_minutes}, priority={priority}")

# Add pharma vessel
vessels.append(VesselData(
    mmsi="PHARMA_001",
    eta_minutes=0,
    containers=150,
    priority_score=4,
    is_extra=True,
))
print(f"  PHARMA_001: containers=150, eta=0, priority=4 (EXTRA)")

# Run greedy scheduler
print("\n" + "="*60)
print("RUNNING GREEDY SCHEDULER")
print("="*60)

# Test service time calculation manually
print("\nSERVICE TIME CALCULATIONS:")
for v in vessels[:2]:
    for b in berths[:2]:
        containers_per_hour = b.service_rate * b.crane_count
        hours = v.containers / max(containers_per_hour, 1)
        service_min = max(int(hours * 60), 60)
        print(f"  {v.mmsi} ({v.containers} TEU) at {b.berth_id} (rate={b.service_rate}, cranes={b.crane_count}): {service_min} min")

plan = greedy_schedule(vessels, berths)
print(f"\nRESULT: score={plan.objective_score}, delay={plan.total_delay_hours}h, impacted={plan.vessels_impacted}")

print("\nASSIGNMENTS:")
for a in plan.assignments:
    service = a.end_time - a.start_time
    print(f"  {a.vessel_mmsi}: {a.berth_id}, start={a.start_time}, service={service}min")

client.close()
