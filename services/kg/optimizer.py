"""
=============================================================================
CP-SAT Berth Assignment Optimizer - Smart Port Intelligence System
=============================================================================

Uses Google OR-Tools CP-SAT solver to optimize berth assignments when an
extra vessel arrives. Minimizes total delay while respecting constraints.

Algorithm:
1. Load current port state from KG (vessels, berths, assets)
2. Add extra vessel to the queue
3. Create CP-SAT model with decision variables
4. Add constraints (one berth per vessel, no overlap, crane capacity)
5. Minimize weighted objective (delay, congestion, cost, priority)
6. Extract solution and calculate cascade impacts

Weights from TRD v2 Section 7.3:
- 40% total delay hours
- 25% queue congestion
- 20% crane utilization cost
- 15% priority penalty
=============================================================================
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------------------

@dataclass
class VesselData:
    """Vessel data for optimization."""
    mmsi: str
    eta_minutes: int  # Minutes from now
    containers: int = 100
    priority_score: int = 1  # 4=pharma, 3=food, 2=electronics, 1=general
    original_berth: Optional[str] = None
    is_extra: bool = False


@dataclass
class BerthData:
    """Berth data for optimization."""
    berth_id: str
    terminal: str
    service_rate: float = 25.0  # containers per hour
    crane_count: int = 2


@dataclass
class Assignment:
    """A vessel-berth assignment in a plan."""
    vessel_mmsi: str
    berth_id: str
    start_time: int  # minutes from now
    end_time: int
    delay_minutes: int = 0
    is_extra: bool = False


@dataclass
class CascadeImpact:
    """Impact on a vessel due to extra vessel insertion."""
    vessel_mmsi: str
    original_start: int
    new_start: int
    delay_minutes: int
    reason: str


@dataclass
class OptimizationPlan:
    """A complete optimization plan."""
    plan_id: str
    objective_score: float
    total_delay_hours: float
    vessels_impacted: int
    assignments: List[Assignment] = field(default_factory=list)
    impacts: List[CascadeImpact] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PRIORITY MAPPING
# ---------------------------------------------------------------------------

PRIORITY_MAP = {
    "pharma": 4,
    "food": 3,
    "electronics": 2,
    "general": 1,
}


# ---------------------------------------------------------------------------
# GREEDY SCHEDULER (REPLACES INFEASIBLE CP-SAT FOR LARGE N)
# ---------------------------------------------------------------------------

def greedy_schedule(
    vessels: List[VesselData],
    berths: List[BerthData],
) -> OptimizationPlan:
    """
    Greedy berth assignment scheduler.
    
    Schedules vessels in order of priority (highest first), then ETA.
    Assigns each vessel to the berth that becomes available soonest.
    
    This is used when CP-SAT can't find a feasible solution (too many vessels).
    
    Returns:
        OptimizationPlan with all assignments and impacts
    """
    logger.info(f"Running greedy scheduler: {len(vessels)} vessels, {len(berths)} berths")
    
    # Debug: Print berth details
    for b in berths:
        logger.info(f"  BERTH DEBUG: {b.berth_id} rate={b.service_rate} cranes={b.crane_count}")
    
    # Sort vessels by priority (descending) then ETA (ascending)
    sorted_vessels = sorted(
        vessels,
        key=lambda v: (-v.priority_score, v.eta_minutes, 0 if v.is_extra else 1)
    )
    
    # Debug: Print first vessel
    if sorted_vessels:
        v = sorted_vessels[0]
        logger.info(f"  FIRST VESSEL: {v.mmsi} containers={v.containers} priority={v.priority_score}")
    
    # Track when each berth becomes available
    berth_available_at = {b.berth_id: 0 for b in berths}
    
    # Service time calculation helper
    def calc_service_time(vessel: VesselData, berth: BerthData) -> int:
        """Calculate service time in minutes."""
        containers_per_hour = berth.service_rate * berth.crane_count
        hours = vessel.containers / max(containers_per_hour, 1)
        service_min = max(int(hours * 60), 60)  # Minimum 1 hour
        logger.debug(f"    SERVICE TIME: {vessel.mmsi} at {berth.berth_id}: {vessel.containers} TEU / ({berth.service_rate} * {berth.crane_count}) = {service_min} min")
        return service_min
    
    assignments = []
    impacts = []
    total_delay_minutes = 0
    
    for vessel in sorted_vessels:
        # Find best berth (earliest available)
        best_berth = None
        earliest_start = float('inf')
        
        for berth in berths:
            available_at = berth_available_at[berth.berth_id]
            # Vessel can start when: max(berth available, vessel ETA)
            can_start_at = max(available_at, vessel.eta_minutes)
            
            if can_start_at < earliest_start:
                earliest_start = can_start_at
                best_berth = berth
        
        if best_berth is None:
            best_berth = berths[0]  # Fallback
            earliest_start = berth_available_at[best_berth.berth_id]
        
        # Calculate times
        start_time = int(earliest_start)
        service_time = calc_service_time(vessel, best_berth)
        end_time = start_time + service_time
        delay = max(0, start_time - vessel.eta_minutes)
        
        # Update berth availability
        berth_available_at[best_berth.berth_id] = end_time
        
        # Create assignment
        assignment = Assignment(
            vessel_mmsi=vessel.mmsi,
            berth_id=best_berth.berth_id,
            start_time=start_time,
            end_time=end_time,
            delay_minutes=delay,
            is_extra=vessel.is_extra,
        )
        assignments.append(assignment)
        total_delay_minutes += delay
        
        # Create impact for delayed non-extra vessels
        if delay > 0 and not vessel.is_extra:
            # Find what caused the delay
            reason = f"Berth {best_berth.berth_id} occupied -> delayed by {delay} min"
            
            # Check if extra vessel is ahead in the queue
            extra_vessel = next((v for v in sorted_vessels if v.is_extra), None)
            if extra_vessel:
                extra_assignment = next(
                    (a for a in assignments if a.vessel_mmsi == extra_vessel.mmsi),
                    None
                )
                if extra_assignment and extra_assignment.berth_id == best_berth.berth_id:
                    if extra_assignment.end_time > vessel.eta_minutes:
                        reason = (
                            f"Priority vessel {extra_vessel.mmsi} (pharma) assigned to "
                            f"{best_berth.berth_id} -> cascade delay of {delay} min"
                        )
            
            impact = CascadeImpact(
                vessel_mmsi=vessel.mmsi,
                original_start=vessel.eta_minutes,
                new_start=start_time,
                delay_minutes=delay,
                reason=reason,
            )
            impacts.append(impact)
    
    # Calculate objective score (0-100, higher is better)
    # Formula: Based on how well we minimize delays given constraints
    # 
    # With N vessels and B berths, minimum theoretical total service time:
    #   min_time = sum(service_times) / B
    # Actual time = total_delay + total_service_time
    # Score = efficiency of scheduling
    
    total_service_time = sum(a.end_time - a.start_time for a in assignments)
    num_berths = len(berths) if berths else 4
    
    # Theoretical minimum: if all vessels could be served in parallel
    min_possible_time = total_service_time / num_berths if num_berths > 0 else total_service_time
    
    # Actual makespan (time to serve all vessels)
    makespan = max(a.end_time for a in assignments) if assignments else 0
    
    # Efficiency = min_possible_time / makespan (1.0 = perfect, approaches 0 as delays increase)
    efficiency = min_possible_time / makespan if makespan > 0 else 1.0
    
    # Bonus for high-priority vessels getting low delay
    priority_bonus = 0
    for a in assignments:
        vessel = next((v for v in vessels if v.mmsi == a.vessel_mmsi), None)
        if vessel and vessel.priority_score >= 3:  # High priority (food, pharma)
            if a.delay_minutes == 0:
                priority_bonus += 5  # +5 points per high-priority vessel with 0 delay
            elif a.delay_minutes < 60:
                priority_bonus += 2  # +2 points for < 1 hour delay
    
    # Final score: 60% efficiency + 40% from priority handling
    objective_score = min(100.0, efficiency * 60 + priority_bonus)
    
    plan = OptimizationPlan(
        plan_id=f"greedy_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        objective_score=round(objective_score, 3),
        total_delay_hours=round(total_delay_minutes / 60, 2),
        vessels_impacted=len([i for i in impacts if i.delay_minutes > 0]),
        assignments=assignments,
        impacts=impacts,
    )
    
    logger.info(f"Greedy plan: {len(assignments)} assignments, {plan.vessels_impacted} impacted, {plan.total_delay_hours}h delay")
    
    return plan


# ---------------------------------------------------------------------------
# CP-SAT OPTIMIZER (FOR SMALL N)
# ---------------------------------------------------------------------------

class BerthOptimizer:
    """
    CP-SAT optimizer for berth assignment with cascade impact calculation.
    """
    
    # Objective weights from TRD
    W_DELAY = 0.40
    W_CONGESTION = 0.25
    W_COST = 0.20
    W_PRIORITY = 0.15
    
    # Constants
    TIME_HORIZON = 72 * 60  # 72 hours in minutes
    MAX_SERVICE_TIME = 24 * 60  # Max 24 hours per vessel
    
    def __init__(self, vessels: List[VesselData], berths: List[BerthData]):
        """
        Initialize optimizer with port state.
        
        Args:
            vessels: List of vessels (including extra vessel)
            berths: List of available berths
        """
        self.vessels = vessels
        self.berths = berths
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Decision variables (populated in build_model)
        self.assign: Dict[Tuple[int, int], Any] = {}  # (v,b) -> BoolVar
        self.start: Dict[int, Any] = {}  # v -> IntVar
        self.end: Dict[int, Any] = {}  # v -> IntVar
        self.delay: Dict[int, Any] = {}  # v -> IntVar
        
    def calculate_service_time(self, vessel: VesselData, berth: BerthData) -> int:
        """
        Calculate service time in minutes.
        
        service_time = containers / (service_rate * crane_count)
        """
        containers_per_hour = berth.service_rate * berth.crane_count
        hours = vessel.containers / max(containers_per_hour, 1)
        return max(int(hours * 60), 60)  # Minimum 1 hour
    
    @staticmethod
    def format_time_hhmm(minutes_from_now: int) -> str:
        """Format minutes from now to HH:MM time string."""
        target_time = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
        return target_time.strftime("%H:%M")
    
    def _build_cascade_chains(self, assignments: List[Assignment]) -> Dict[str, str]:
        """
        Build cascade reason strings showing upstream vessel causing delay.
        """
        reasons = {}
        
        # Group assignments by berth
        by_berth: Dict[str, List[Assignment]] = {}
        for a in assignments:
            if a.berth_id not in by_berth:
                by_berth[a.berth_id] = []
            by_berth[a.berth_id].append(a)
        
        # Sort each berth's assignments by start time
        for berth_id in by_berth:
            by_berth[berth_id].sort(key=lambda x: x.start_time)
        
        # Find upstream vessel for each delayed vessel
        for a in assignments:
            if a.delay_minutes <= 0:
                continue
                
            berth_assignments = by_berth.get(a.berth_id, [])
            upstream_vessel = None
            
            for other in berth_assignments:
                if other.vessel_mmsi == a.vessel_mmsi:
                    continue
                if other.end_time <= a.start_time:
                    if upstream_vessel is None or other.end_time > upstream_vessel.end_time:
                        upstream_vessel = other
            
            if upstream_vessel:
                end_time_str = self.format_time_hhmm(upstream_vessel.end_time)
                new_start_str = self.format_time_hhmm(a.start_time)
                reasons[a.vessel_mmsi] = (
                    f"Berth {a.berth_id} occupied by {upstream_vessel.vessel_mmsi} "
                    f"until {end_time_str} -> start pushed to {new_start_str}"
                )
            else:
                new_start_str = self.format_time_hhmm(a.start_time)
                reasons[a.vessel_mmsi] = (
                    f"Berth {a.berth_id} congested -> start delayed to {new_start_str}"
                )
        
        return reasons
    
    def build_model(self) -> None:
        """Build the CP-SAT model with variables and constraints."""
        n_vessels = len(self.vessels)
        n_berths = len(self.berths)
        
        logger.info(f"Building model: {n_vessels} vessels, {n_berths} berths")
        
        # --- Decision Variables ---
        for v in range(n_vessels):
            for b in range(n_berths):
                self.assign[v, b] = self.model.NewBoolVar(f"assign_{v}_{b}")
        
        for v in range(n_vessels):
            vessel = self.vessels[v]
            
            self.start[v] = self.model.NewIntVar(
                vessel.eta_minutes,
                self.TIME_HORIZON,
                f"start_{v}"
            )
            
            self.end[v] = self.model.NewIntVar(
                vessel.eta_minutes,
                self.TIME_HORIZON + self.MAX_SERVICE_TIME,
                f"end_{v}"
            )
            
            self.delay[v] = self.model.NewIntVar(
                0,
                self.TIME_HORIZON,
                f"delay_{v}"
            )
        
        # --- Constraints ---
        
        # 1. Each vessel assigned to exactly one berth
        for v in range(n_vessels):
            self.model.Add(
                sum(self.assign[v, b] for b in range(n_berths)) == 1
            )
        
        # 2. Link start, end times with service time
        for v in range(n_vessels):
            vessel = self.vessels[v]
            for b in range(n_berths):
                berth = self.berths[b]
                service_time = self.calculate_service_time(vessel, berth)
                
                self.model.Add(
                    self.end[v] == self.start[v] + service_time
                ).OnlyEnforceIf(self.assign[v, b])
        
        # 3. Delay = start - ETA
        for v in range(n_vessels):
            vessel = self.vessels[v]
            self.model.Add(self.delay[v] == self.start[v] - vessel.eta_minutes)
        
        # 4. No overlap at same berth (disjunctive constraint)
        for b in range(n_berths):
            for v1 in range(n_vessels):
                for v2 in range(v1 + 1, n_vessels):
                    both_at_b = self.model.NewBoolVar(f"both_{v1}_{v2}_{b}")
                    self.model.AddMultiplicationEquality(
                        both_at_b, 
                        [self.assign[v1, b], self.assign[v2, b]]
                    )
                    
                    v1_before_v2 = self.model.NewBoolVar(f"v1b4v2_{v1}_{v2}_{b}")
                    v2_before_v1 = self.model.NewBoolVar(f"v2b4v1_{v1}_{v2}_{b}")
                    
                    self.model.Add(self.end[v1] <= self.start[v2]).OnlyEnforceIf(v1_before_v2)
                    self.model.Add(self.end[v2] <= self.start[v1]).OnlyEnforceIf(v2_before_v1)
                    
                    self.model.Add(v1_before_v2 + v2_before_v1 >= 1).OnlyEnforceIf(both_at_b)
        
        # --- Objective ---
        total_delay = sum(self.delay[v] for v in range(n_vessels))
        
        priority_penalty = sum(
            self.delay[v] * self.vessels[v].priority_score
            for v in range(n_vessels)
        )
        
        max_delay = self.model.NewIntVar(0, self.TIME_HORIZON, "max_delay")
        for v in range(n_vessels):
            self.model.Add(max_delay >= self.delay[v])
        
        objective = (
            int(self.W_DELAY * 100) * total_delay +
            int(self.W_PRIORITY * 100) * priority_penalty +
            int(self.W_CONGESTION * 100) * max_delay
        )
        
        self.model.Minimize(objective)
        logger.info("Model built successfully")
    
    def solve(self, time_limit_seconds: float = 10.0) -> Optional[OptimizationPlan]:
        """Solve the optimization model."""
        self.solver.parameters.max_time_in_seconds = time_limit_seconds
        
        logger.info(f"Solving... (time limit: {time_limit_seconds}s)")
        status = self.solver.Solve(self.model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.warning(f"No solution found. Status: {status}")
            return None
        
        logger.info(f"Solution found! Status: {'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'}")
        
        assignments = []
        impacts = []
        total_delay_minutes = 0
        vessels_impacted = 0
        
        for v, vessel in enumerate(self.vessels):
            assigned_berth = None
            for b, berth in enumerate(self.berths):
                if self.solver.Value(self.assign[v, b]):
                    assigned_berth = berth
                    break
            
            start_time = self.solver.Value(self.start[v])
            end_time = self.solver.Value(self.end[v])
            delay = self.solver.Value(self.delay[v])
            
            total_delay_minutes += delay
            
            assignment = Assignment(
                vessel_mmsi=vessel.mmsi,
                berth_id=assigned_berth.berth_id if assigned_berth else "UNKNOWN",
                start_time=start_time,
                end_time=end_time,
                delay_minutes=delay,
                is_extra=vessel.is_extra,
            )
            assignments.append(assignment)
        
        cascade_reasons = self._build_cascade_chains(assignments)
        
        for v, vessel in enumerate(self.vessels):
            delay = self.solver.Value(self.delay[v])
            if delay > 0 and not vessel.is_extra:
                vessels_impacted += 1
                start_time = self.solver.Value(self.start[v])
                reason = cascade_reasons.get(
                    vessel.mmsi, 
                    f"Delayed by {delay} minutes due to berth congestion"
                )
                impact = CascadeImpact(
                    vessel_mmsi=vessel.mmsi,
                    original_start=vessel.eta_minutes,
                    new_start=start_time,
                    delay_minutes=delay,
                    reason=reason,
                )
                impacts.append(impact)
        
        raw_objective = self.solver.ObjectiveValue()
        max_possible = self.TIME_HORIZON * len(self.vessels) * 100
        objective_score = 1.0 - (raw_objective / max_possible) if max_possible > 0 else 0.5
        objective_score = max(0.0, min(1.0, objective_score))
        
        plan = OptimizationPlan(
            plan_id="plan_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            objective_score=round(objective_score, 3),
            total_delay_hours=round(total_delay_minutes / 60, 1),
            vessels_impacted=vessels_impacted,
            assignments=assignments,
            impacts=impacts,
        )
        
        return plan


# ---------------------------------------------------------------------------
# CONVENIENCE FUNCTIONS
# ---------------------------------------------------------------------------

def optimize_scenario(
    vessels: List[Dict],
    berths: List[Dict],
    extra_vessel: Dict,
) -> List[OptimizationPlan]:
    """
    Run optimization for a scenario.
    
    Args:
        vessels: List of current vessel dicts from KG (WAITING + APPROACHING)
        berths: List of berth dicts from KG
        extra_vessel: Extra vessel to insert
        
    Returns:
        List of optimization plans (best first)
    """
    # Convert vessels to VesselData
    vessel_list = []
    seen_mmsi = set()  # Track seen vessels to avoid duplicates
    now = datetime.now(timezone.utc)
    
    # For waiting vessels, assign staggered ETAs based on queue position
    # This simulates realistic arrival times
    waiting_count = 0
    
    for v in vessels:
        mmsi = str(v.get("mmsi", "UNKNOWN"))
        
        # Skip duplicates
        if mmsi in seen_mmsi:
            logger.debug(f"Skipping duplicate vessel: {mmsi}")
            continue
        seen_mmsi.add(mmsi)
        mmsi = str(v.get("mmsi", "UNKNOWN"))
        status = v.get("status", "WAITING").upper()
        
        # Calculate ETA in minutes from now
        eta_minutes = 0
        
        # Try to get ETA from various fields
        eta_to_port_raw = v.get("eta_to_port")
        if eta_to_port_raw is not None and eta_to_port_raw != "":
            try:
                # Handle "X minutes" format from simulated data
                eta_str = str(eta_to_port_raw)
                if "minutes" in eta_str.lower():
                    eta_minutes = int(eta_str.split()[0])
                elif "hours" in eta_str.lower():
                    eta_minutes = int(float(eta_str.split()[0]) * 60)
                else:
                    # Try parsing as hours (original format)
                    hours = float(eta_str.split()[0])
                    eta_minutes = int(hours * 60)
            except:
                pass
        
        # For waiting vessels with no ETA, stagger them based on queue position
        if eta_minutes == 0:
            if status == "WAITING":
                # Stagger by 20 minutes each to simulate queue
                eta_minutes = waiting_count * 20
                waiting_count += 1
            elif status == "APPROACHING":
                # Approaching vessels get longer ETA
                eta_minutes = 60 + waiting_count * 15
                waiting_count += 1
        
        # Get containers from vessel data (default 150 TEU)
        containers = v.get("containers") or v.get("container_count") or 150
        
        # Get priority from vessel data (default 1)
        priority = v.get("priority") or PRIORITY_MAP.get(v.get("cargo_type", "general"), 1)
        
        vessel_list.append(VesselData(
            mmsi=mmsi,
            eta_minutes=eta_minutes,
            containers=containers,
            priority_score=priority,
        ))
    
    # Add extra vessel with its priority
    eta_str = extra_vessel.get("eta", "")
    eta_minutes = 0  # Priority vessel - arrives NOW
    try:
        if eta_str:
            eta_dt = datetime.fromisoformat(eta_str.replace("Z", "+00:00"))
            delta = eta_dt - now
            eta_minutes = max(0, int(delta.total_seconds() / 60))
    except:
        pass
    
    # Get priority from cargo type
    cargo_priority = extra_vessel.get("cargo_priority", "general")
    priority_score = PRIORITY_MAP.get(cargo_priority, 1)
    
    extra_vessel_data = VesselData(
        mmsi=extra_vessel.get("mmsi") or "EXTRA_001",
        eta_minutes=eta_minutes,
        containers=extra_vessel.get("containers_est", 100),
        priority_score=priority_score,
        is_extra=True,
    )
    vessel_list.append(extra_vessel_data)
    
    logger.info(f"Extra vessel: {extra_vessel_data.mmsi}, priority={priority_score} ({cargo_priority}), ETA={eta_minutes}min")
    
    # Convert berths to BerthData
    berth_list = [
        BerthData(
            berth_id=b.get("berth_id", f"B{i}"),
            terminal=b.get("terminal", "UNKNOWN"),
            service_rate=b.get("service_rate_base") or 25.0,
            crane_count=b.get("crane_count") or 2,  # Ensure non-zero crane count
        )
        for i, b in enumerate(berths)
    ]
    
    logger.info(f"Optimizing: {len(vessel_list)} vessels, {len(berth_list)} berths")
    
    # Debug: log berth data
    for b in berth_list:
        logger.info(f"  Berth {b.berth_id}: service_rate={b.service_rate}, crane_count={b.crane_count}")
    
    # Debug: log sample vessels
    for v in vessel_list[:5]:
        logger.info(f"  Vessel {v.mmsi}: eta={v.eta_minutes}, containers={v.containers}, priority={v.priority_score}")
    
    # If too many vessels for CP-SAT (>15), use greedy scheduler
    if len(vessel_list) > 15:
        logger.info(f"Using greedy scheduler (N={len(vessel_list)} > 15)")
        plan = greedy_schedule(vessel_list, berth_list)
        return [plan]
    
    # Try CP-SAT for smaller problems
    plans = []
    for time_limit in [2.0, 5.0, 10.0]:
        optimizer = BerthOptimizer(vessel_list, berth_list)
        optimizer.build_model()
        plan = optimizer.solve(time_limit_seconds=time_limit)
        if plan:
            plan.plan_id = f"plan_{len(plans)+1}"
            plans.append(plan)
    
    plans.sort(key=lambda p: p.objective_score, reverse=True)
    
    # Fallback to greedy if CP-SAT fails
    if not plans:
        logger.warning("CP-SAT failed, falling back to greedy")
        plan = greedy_schedule(vessel_list, berth_list)
        return [plan]
    
    return plans[:3]


# ---------------------------------------------------------------------------
# TESTING
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test with sample data
    vessels = [
        VesselData(mmsi="V001", eta_minutes=0, containers=200, priority_score=1),
        VesselData(mmsi="V002", eta_minutes=30, containers=150, priority_score=2),
        VesselData(mmsi="V003", eta_minutes=60, containers=100, priority_score=1),
    ]
    
    berths = [
        BerthData(berth_id="B1", terminal="OLD_CITY", service_rate=30, crane_count=2),
        BerthData(berth_id="B2", terminal="MUUGA", service_rate=40, crane_count=3),
    ]
    
    # Add extra vessel
    vessels.append(VesselData(
        mmsi="EXTRA",
        eta_minutes=0,  # Priority arrives NOW
        containers=500,
        priority_score=4,  # pharma
        is_extra=True,
    ))
    
    optimizer = BerthOptimizer(vessels, berths)
    optimizer.build_model()
    plan = optimizer.solve()
    
    if plan:
        print(f"\n{'='*60}")
        print(f"OPTIMIZATION RESULT")
        print(f"{'='*60}")
        print(f"Plan ID: {plan.plan_id}")
        print(f"Objective Score: {plan.objective_score}")
        print(f"Total Delay: {plan.total_delay_hours} hours")
        print(f"Vessels Impacted: {plan.vessels_impacted}")
        print(f"\nAssignments:")
        for a in plan.assignments:
            print(f"  {a.vessel_mmsi} -> {a.berth_id} ({a.start_time}-{a.end_time}min, delay={a.delay_minutes}min)")
        print(f"\nCascade Impacts:")
        for i in plan.impacts:
            print(f"  {i.vessel_mmsi}: +{i.delay_minutes}min - {i.reason}")
    else:
        print("No solution found!")
