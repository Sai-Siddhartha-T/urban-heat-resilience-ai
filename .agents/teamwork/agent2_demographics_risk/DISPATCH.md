## 2026-11-10T12:29:21Z
You are specialized AGENT 2: Demographic Data and Vulnerability Engineer working on Milestone M2 (Heat Risk Framework & Demographics Overhaul) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent2_demographics_risk
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_3\handoff.md` first.
Your exclusive file ownership:
- `backend/app/services/demographics.py`
- `backend/app/services/risk.py`
- `backend/tests/test_demographics.py`
- `backend/tests/test_risk.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R6):
1. Multi-Factor Hazard Decomposition (`backend/app/services/risk.py`):
   - Expand `calculate_hazard(properties)`: Transparently decompose hazard into a composite index combining:
     - Surface heat / SUHII (relative to rural reference)
     - Ambient air temperature (from Open-Meteo or climatological peak)
     - Heatwave duration (consecutive days above local heat threshold)
     Normalize transparently with clear weightings and physical units.
2. Multi-Factor Exposure Decomposition (`risk.py`):
   - Expand `calculate_exposure(properties)`: Combine:
     - Population density (people/km²)
     - Residential building density / built-up density (from GHSL or building footprint %)
     - Sensitive land-use indicators (proximity to schools, hospitals, informal settlements)
3. Vulnerability Integrity (CRITICAL):
   - DO NOT substitute population density for vulnerability.
   - Maintain vulnerability as an index composed of:
     - Age sensitivity: Elderly share (>65) and child share (<5)
     - Socioeconomic deprivation: Poverty rate, informal housing %, outdoor worker share
     - Adaptive capacity / cooling deficit: Lack of tree canopy, lack of indoor cooling/AC
4. Demographics Service Real Data Integration (`backend/app/services/demographics.py`):
   - Replace queries to US Census (`api.census.gov`) with authentic municipal ward demographic profiles for Indian target cities (Ahmedabad AMC 48 wards benchmark, Delhi, Hyderabad).
   - Implement raster sampling support for WorldPop (population density) and GHSL (built-up surface fraction).
5. Verification:
   - Run `pytest backend/tests/test_demographics.py backend/tests/test_risk.py`. Ensure all tests pass.
   - Document all changes and test outputs in `handoff.md`.

Write your report to `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent2_demographics_risk\handoff.md` and send a message when complete.


## 2026-11-10T12:51:04Z
**Context**: Milestone M2 (Demographics, Vulnerability & Transparent Heat Risk)
**Content**: Status query: Checking in on progress for `backend/app/services/risk.py` (multi-factor hazard and exposure) and `backend/app/services/demographics.py` (Indian municipal ward data).
**Action**: Please report your current status, recent updates, or deliver your handoff report if complete.
