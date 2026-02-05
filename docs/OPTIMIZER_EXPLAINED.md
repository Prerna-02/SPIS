# Berth Optimizer: Greedy vs CP-SAT & Extra Vessel

## Short answers

- **What does "greedy" mean here?**  
  **Greedy** = a fast fallback scheduler that assigns each vessel to the **first berth that becomes free**, in order of priority then ETA. It doesn’t search for a globally best schedule. The Neo4j graph shows nodes like `greedy_...` when a run used this greedy scheduler (e.g. when there are too many vessels for CP-SAT or CP-SAT fails).

- **Where is the extra vessel added?**  
  The **extra vessel** is the one you add in the UI (ETA, containers, cargo priority). The optimizer inserts it into the queue with existing vessels and assigns it to a berth. In the **Berth Timeline** it appears as **EXTRA-_001** (or similar). In your screenshot it is in the **MUUGA_B2** row, between other vessels (e.g. between VESSEL-7995 and VESSEL-9131). So: **extra vessel = added in the scenario; its place in the schedule = the berth and slot the optimizer chose (e.g. MUUGA_B2).**

- **Why CP-SAT?**  
  **CP-SAT** (Constraint Programming – Satisfiability) is used to find a **good or optimal** berth assignment that minimizes total delay and respects constraints (one berth per vessel, no overlapping use, crane capacity, priorities). We use it when the problem is small enough (≤15 vessels); for larger instances we fall back to the **greedy** scheduler so we always get a feasible schedule quickly.

---

## Detailed explanation

### 1. What “greedy” means here

In this project there are two ways we assign vessels to berths:

| Method   | When it’s used | What it does |
|----------|-----------------|--------------|
| **CP-SAT** | Default when there are **≤ 15 vessels** | Builds a constraint model and searches for a best (or very good) schedule. |
| **Greedy** | When there are **> 15 vessels** or when **CP-SAT fails** (no solution in time) | Sorts vessels by **priority (highest first)** then **ETA**, then assigns each vessel to the berth that becomes **available soonest**. No global search. |

So **“greedy”** here means:

- We make **local** decisions: for each vessel we only look at “which berth is free earliest?” and put the vessel there.
- We do **not** re-optimize the whole schedule (e.g. we don’t try moving earlier vessels to reduce total delay).
- It’s **fast** and always gives a feasible schedule, but the solution can be **worse** than what CP-SAT would find for the same input.

In the **Neo4j graph** you see nodes labeled things like **greedy_20250104_123456** when that **plan** was produced by the greedy scheduler. The graph still shows **HAS_ASSIGNMENT** and **CAUSES_IMPACT** for that plan: which vessel got which berth and what delay impacts that caused. So “greedy” in the graph = “this solution came from the greedy algorithm,” not a different kind of object.

---

### 2. Where the extra vessel is added

- **In the problem:** You define an **extra vessel** in the optimization UI (ETA, estimated containers, cargo priority). The backend adds this vessel to the current port state and runs the optimizer (CP-SAT or greedy).
- **In the solution:** The optimizer assigns **every** vessel (including the extra one) to a berth and a time slot. So the “extra vessel” is **one of the vessels in the plan**; it’s just the one that was **added by you** for this scenario.
- **In the UI:**  
  - In the **Berth Timeline**, the extra vessel appears with a name like **EXTRA-_001** (from `EXTRA-` + last part of its MMSI/id).  
  - In your screenshot it appears on the **MUUGA_B2** berth row, between two other vessels (e.g. VESSEL-7995 and VESSEL-9131), and is shown as **delayed** (yellow) like many others. So **the extra vessel has been added into the schedule at MUUGA_B2** in that run.

So: **“Where is the extra vessel added?”** → It’s **added to the scenario** in the UI; **where it appears** is the **berth and position** the optimizer chose—in your image, that’s **MUUGA_B2**.

---

### 3. Why we use CP-SAT (detailed)

**CP-SAT** (Google OR-Tools) is a constraint programming / SAT-based solver. We use it because:

1. **Constraints**  
   Berth assignment has many rules: each vessel gets exactly one berth, no two vessels use the same berth at the same time, crane capacity limits, service time depends on berth and vessel, etc. CP-SAT is built to model and satisfy such constraints.

2. **Objective**  
   We want to **minimize** a weighted combination of total delay, congestion, cost, and priority penalties (see TRD v2). CP-SAT can optimize this over the set of feasible schedules instead of just finding any feasible one.

3. **Quality vs speed**  
   For small N (e.g. ≤15 vessels), CP-SAT can find a **good or optimal** schedule in a few seconds. For larger N, the same model can become too slow or fail to find a solution in time, so we **fall back to greedy** to guarantee a quick feasible schedule.

4. **In code**  
   - **CP-SAT** is used in `services/kg/optimizer.py` (e.g. `BerthOptimizer` with `cp_model`).  
   - **Greedy** is implemented in `greedy_schedule()` in the same file and is used when `len(vessel_list) > 15` or when CP-SAT returns no solution.

So in short: **we use CP-SAT to get a high-quality, constraint-respecting schedule when the problem is small enough; we use greedy when we need a fast, safe fallback.**

---

## Summary table

| Topic | Short answer |
|-------|--------------|
| **Greedy** | Fast fallback: assign each vessel to the earliest-available berth by priority then ETA. Used when N>15 or CP-SAT fails. “greedy_…” in Neo4j = plan from this scheduler. |
| **Extra vessel** | The vessel you add in the scenario. It’s scheduled like any other; in the Berth Timeline it appears as EXTRA-_001 (or similar). In your screenshot it’s on **MUUGA_B2**. |
| **Why CP-SAT** | To optimize berth assignment (minimize delay, respect constraints). Used for N≤15; greedy used otherwise so we always get a feasible schedule. |
