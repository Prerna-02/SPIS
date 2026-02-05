import sys
sys.path.insert(0, "E:/DL_Final_Project/services/kg")
from optimizer import VesselData, BerthData, greedy_schedule

# Create test data
vessels = [
    VesselData(mmsi="V1", eta_minutes=0, containers=100, priority_score=1),
    VesselData(mmsi="V2", eta_minutes=30, containers=100, priority_score=1),
    VesselData(mmsi="V3", eta_minutes=60, containers=100, priority_score=1),
    VesselData(mmsi="PHARMA_001", eta_minutes=0, containers=200, priority_score=4, is_extra=True),
]

berths = [
    BerthData(berth_id="MUUGA_B1", terminal="Muuga", service_rate=35.0, crane_count=2),
    BerthData(berth_id="MUUGA_B2", terminal="Muuga", service_rate=28.0, crane_count=1),
    BerthData(berth_id="OLDCITY_B1", terminal="Old City", service_rate=30.0, crane_count=2),
    BerthData(berth_id="OLDCITY_B2", terminal="Old City", service_rate=25.0, crane_count=1),
]

# Test service time calculation
def calc_service_time(vessel, berth):
    containers_per_hour = berth.service_rate * berth.crane_count
    hours = vessel.containers / max(containers_per_hour, 1)
    return max(int(hours * 60), 60)

print("Service time calculations:")
for v in vessels:
    for b in berths:
        st = calc_service_time(v, b)
        print(f"  {v.mmsi} ({v.containers} TEU) at {b.berth_id} (rate={b.service_rate}, cranes={b.crane_count}): {st} min")

print("\nRunning greedy scheduler...")
plan = greedy_schedule(vessels, berths)

print(f"\nPlan ID: {plan.plan_id}")
print(f"Objective Score: {plan.objective_score}")
print(f"Total Delay: {plan.total_delay_hours} hours")
print(f"Vessels Impacted: {plan.vessels_impacted}")
print("\nAssignments:")
for a in plan.assignments:
    print(f"  {a.vessel_mmsi}: {a.berth_id}, start={a.start_time}min, end={a.end_time}min, delay={a.delay_minutes}min, is_extra={a.is_extra}")
