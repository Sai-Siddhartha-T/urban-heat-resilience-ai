## 2026-11-09T13:53:44Z
You are AGENT 2: Demographic Data and Vulnerability Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_demographics_m2\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Your exclusive write ownership:
- `backend/app/services/demographics.py` (create)
- `backend/app/services/risk.py` (enhance demographic integration)
- `backend/tests/test_demographics.py` (create)

Tasks:
1. Ingest and structure real demographic and population information:
   - WorldPop catalog/raster integration (country, year, resolution).
   - GHSL (GHS-POP) population and settlement density raster discovery.
   - Census of India demographic indicators where geographically available (e.g. ward-level population, age structure, elderly share).
2. Retrieve/aggregate population count, population density, and age distribution (specifically vulnerable elderly share age >= 65).
3. Implement spatial joining of demographic data to geographical analysis zones (handling multi-resolution alignment and grid reprojection without inventing values).
4. Handle missing demographic information transparently without inventing false values; maintain explicit `missing_indicators` list.
5. Enhance the heat-risk framework:
   Heat Risk = Hazard × Exposure × Vulnerability
   (IPCC AR5/AR6 multiplicative model: $100 \times \text{Hazard}^{w_H} \times \text{Exposure}^{w_E} \times \text{Vulnerability}^{w_V}$)
   Ensure configurable parametric weights ($w_H, w_E, w_V \in [0.1, 3.0]$) and clear component normalization.
   Do not assume population density alone represents vulnerability; elderly share and socioeconomic proxies are essential.
6. Clearly distinguish observed demographic data from synthetic/proxy baseline in metadata.
7. Write unit and integration tests in `backend/tests/test_demographics.py` and run `pytest`. Ensure 0 regressions across the entire suite.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_demographics_m2\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method with exact test execution results.
When done, message the orchestrator.
