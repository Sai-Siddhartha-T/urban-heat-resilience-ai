# Combinatorial Optimization for Urban Heat Interventions

This document describes the backend optimization engine powering the Heatwise multi-zone intervention planner.

## 1. Overview

The optimization service formulates and solves discrete, multi-zone intervention allocation problems using **Google OR-Tools CP-SAT** (Constraint Programming - Satisfiability).

The primary goal is to determine the most effective distribution of cooling interventions (urban trees, native vegetation, pocket parks, cool roofs, reflective pavements, green corridors, rooftop gardens, and water features) across priority urban zones, subject to **real physical, environmental, land-availability, and water-availability constraints**.

### Complete Removal of Financial Budget Constraints
In real-world municipal planning, urban heat mitigation is primarily bounded by physical spatial limits (available ground, roof, and road areas), ecological constraints (vegetation limits), and municipal resource capacity (daily irrigation water availability). Indicative CapEx/OpEx metrics are indicative benchmarks rather than hard physical boundary limits.

Consequently:
- Financial budget constraints are **completely removed from the OR-Tools CP-SAT model**. The solver optimizes strictly against physical surface capacities, land availability, roof exclusivity, vegetation ceilings, and municipal water limits.
- On the API contract (`/api/optimization/run`), optimization requests operate purely on physical parameters (`city`, `zone_ids`, `water_limit`, `max_vegetation_pct`, `land_limit_pct`, `min_cooling`). Arbitrary financial constraints are excluded from the mathematical solver.
- Post-hoc indicative financial metrics (`total_cost`, and `estimated_cost` per zone) are calculated and returned transparently for reporting, cost estimation, and municipal planning review without restricting physical cooling allocations.

---

## 2. Architecture & Modules

- **`backend/app/services/optimization.py`**:
  Core CP-SAT mathematical optimization model, constraint formulation, solver invocation, automatic half-water alternative scenario generation, and diagnostic infeasibility analysis.
- **`backend/app/services/planning.py`**:
  Intervention catalog, hypothetical cooling/water coefficients, single-zone physical capacity simulation (`simulate`), convenience conversions (`apply_convenience`), and PEP 562 backwards-compatible re-export of `optimize`.
- **`backend/app/routes/optimization.py`**:
  FastAPI route handlers:
  - `POST /api/optimization/run` – Solves the multi-zone allocation problem and automatically computes a 50% water sensitivity alternative.
  - `GET /api/optimization/results` – Retrieves historical optimization records for a city.
- **`backend/app/schemas.py`**:
  Pydantic models `OptimizationRequest` and `OptimizationResponse` defining the API contracts.

---

## 3. Mathematical Formulation

### 3.1 Decision Variables
For each selected zone $z \in Z$ and intervention type $k \in K$:
$$x_{z,k} \in \{0, 1, 2, \dots, \lfloor \text{cap}_{z, s(k)} / 5 \rfloor\}$$
Each integer increment represents a **5 percentage point** coverage of the zone's total area.

### 3.2 Constraints

1. **Surface Capacity Limits (Physical)**:
   Interventions on the same surface cannot exceed available surface area:
   $$\sum_{k \in K_{\text{ground}}} 5 \cdot x_{z,k} \le \text{cap}_{z, \text{ground}}$$
   $$\sum_{k \in K_{\text{roof}}} 5 \cdot x_{z,k} \le \text{roof\_pct}_z$$
   $$\sum_{k \in K_{\text{road}}} 5 \cdot x_{z,k} \le \text{road\_pct}_z$$

2. **Land-Availability Scaling & Protected Zones (Physical / Land)**:
   Ground capacity is modulated by planner-specified land utilization percentage:
   $$\text{cap}_{z, \text{ground}} = \begin{cases} 0 & \text{if zone } z \text{ is protected} \\ \text{available\_land\_pct}_z \times \frac{\text{land\_limit\_pct}}{100} & \text{otherwise} \end{cases}$$

3. **Roof Mutual Exclusivity (Physical)**:
   Cool roofs and rooftop gardens cannot co-exist in the same zone:
   $$b_z \in \{0, 1\}$$
   $$x_{z, \text{cool\_roofs}} = 0 \quad \text{if } b_z = 1$$
   $$x_{z, \text{roof\_gardens}} = 0 \quad \text{if } b_z = 0$$

4. **Maximum Added Vegetation Limit (Environmental)**:
   Total added vegetative coverage in any zone cannot exceed the ecological ceiling:
   $$\sum_{k \in K_{\text{vegetation}}} 5 \cdot x_{z,k} \le \text{max\_vegetation\_pct}$$

5. **Target Mean Cooling Constraint (Environmental)**:
   Total cooling across all zones must satisfy the minimum required mean surface cooling:
   $$\text{cooling}_z = \min\left(3.0, \sum_{k \in K} 5 \cdot x_{z,k} \times \frac{\text{rate}_k}{10}\right)$$
   $$\sum_{z \in Z} \text{cooling}_z \ge \lceil \text{min\_cooling} \times 1000 \times |Z| \rceil / 1000$$

6. **Daily Water Availability (Resource)**:
   Total irrigation demand across all zones cannot exceed available municipal water supply:
   $$\sum_{z \in Z} \sum_{k \in K} 5 \cdot x_{z,k} \times \text{water\_rate}_k \times \text{area\_km2}_z \le \text{water\_limit}$$

### 3.3 Objective Function
Maximize equity-weighted population-, vulnerability-, and heat-risk reduction:
$$\max \sum_{z \in Z} \text{cooling}_z \times \text{priority}_z$$
where:
$$\text{priority}_z = \max\left(1, \text{round}\left(\text{pop}_z \times (0.2 + \text{elderly\_share}_z) \times \max(0.2, \text{SUHII}_z)\right)\right)$$

---

## 4. Infeasibility Handling & Clear Warnings

When the CP-SAT solver determines that no feasible solution exists (`status == INFEASIBLE`), the system performs automated constraint diagnosis via `diagnose_infeasibility()` and returns clear, actionable warnings in `violations`:

1. **Physical Capacity Limitation**:
   Identifies when `min_cooling` exceeds the theoretical upper bound achievable across the zones given land, roof, and road area limits.
2. **Water Availability Limitation**:
   Identifies when water is negative, zero, or severely constrained, preventing vegetative interventions from reaching the cooling target.
3. **Vegetation / Land Availability Limitation**:
   Identifies when `max_vegetation_pct=0` or `land_limit_pct=0` prevents the necessary interventions.
4. **Actionable Recommendations**:
   Recommends lowering `min_cooling`, increasing `water_limit`, or relaxing land/vegetation parameters.

Example infeasible response:
```json
{
  "status": "INFEASIBLE",
  "feasible": false,
  "selections": [],
  "violations": [
    "Requested minimum mean cooling is incompatible with land, roof, road, protection, vegetation, or water constraints.",
    "Physical capacity limitation: The requested minimum cooling of 3.80°C exceeds the theoretical maximum achievable (0.85°C) given available ground (100% limit), roof, and road surface capacities across the 5 selected zone(s).",
    "Recommendation: Lower the minimum cooling target (min_cooling), increase available water (water_limit), or relax land/vegetation constraints to achieve feasibility."
  ],
  "water_used": 0.0,
  "total_water_used": 0.0,
  "water_available": 1000.0,
  "total_cost": 0.0,
  "mean_cooling": 0.0,
  "population_in_selected_zones": 0,
  "alternative": null
}
```

---

## 5. API Contract (`/api/optimization/run`)

### Request
```json
{
  "city": "Ahmedabad",
  "zone_ids": ["zone-1", "zone-2"],
  "water_limit": 1000,
  "max_vegetation_pct": 40,
  "land_limit_pct": 100,
  "min_cooling": 0.3
}
```
*Note: Optimization operates strictly on physical surface capacities, land limits, and water resources. Financial budget fields have been removed.*

### Response
```json
{
  "status": "OPTIMAL",
  "feasible": true,
  "selections": [
    {
      "zone_id": "zone-1",
      "zone_name": "East District",
      "coverage": {
        "trees": 15.0,
        "cool_roofs": 20.0
      },
      "feasible": true,
      "violations": [],
      "before_suhii": 3.8,
      "after_suhii": 3.125,
      "estimated_cooling": 0.675,
      "sensitivity_range": [0.405, 0.945],
      "water_m3_day": 120.0,
      "estimated_cost": 82500.0,
      "area_coverage": {
        "ground": 15.0,
        "roof": 20.0,
        "road": 0.0
      },
      "population": 28400,
      "risk_score": 32.5
    }
  ],
  "violations": [],
  "water_used": 340.5,
  "total_water_used": 340.5,
  "water_available": 1000.0,
  "total_cost": 450000.0,
  "mean_cooling": 0.42,
  "population_in_selected_zones": 58200,
  "alternative": {
    "label": "Half-water alternative",
    "feasible": true,
    "water_used": 165.2,
    "mean_cooling": 0.28
  }
}
```

---

## 6. Verification & Tests

Unit tests covering feasible and infeasible scenarios are located in:
`backend/tests/test_optimization.py`

Run tests with:
```powershell
pytest backend/tests/test_optimization.py -v
```
