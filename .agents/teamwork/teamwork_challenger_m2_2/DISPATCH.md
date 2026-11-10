# Dispatch: Milestone 2 ML Spatial & AI Guardrail Challenger (challenger_m2_2)

## Context
Working Directory: d:\Urban-Heat-Resilience-AI
State Directory: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2
Original Request Path: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project Scope Document: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Worker Handoff Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m2_2\handoff.md
Test Ready Document: d:\Urban-Heat-Resilience-AI\TEST_READY.md

## Objective
Empirically stress-test spatial clustering, model validation, and AI numeric guardrails:
1. Spatial clustering stress-testing:
   - Probe `assign_spatial_partitions()` in `backend/app/services/ml.py` with unusual and pathological GeoJSON configurations:
     - 3-zone small city (below 5-zone threshold).
     - 5-zone minimal city.
     - 8-zone, 12-zone, 25-zone, 50-zone configurations.
     - Perfectly collinear zones (all along the exact same latitude or longitude line).
     - Concentric ring zones or zero-area geometries.
   - Verify that spatial cross-validation does not crash, does not produce empty training sets, and yields valid partition assignments.
2. AI numeric guardrail adversarial stress-testing:
   - Probe the regex validation pipeline in `backend/app/services/ai.py` with adversarial text inputs:
     - Text containing valid domain numbers (`"Sentinel-2 captured 10m resolution imagery with Landsat-8 in 2024"`).
     - Sneaky numbers embedded in words or hex codes (`"model_v2_run3"`, `"0x1A4F"`).
     - Extreme scientific notation (`"1.45e-3"`).
     - Hallucinated temperatures (`"The temperature dropped by 45.2°C"` vs real baseline delta).
     - Verify that true facts pass and fabricated statistics are caught.
3. Run tests and document all empirical test results.

## Completion Criteria
Write your empirical findings report to `handoff.md` in your state folder with clear sections:
- Empirical Testing Methodology
- Spatial Partitioning Stress Scenarios & Results
- AI Guardrail Regex Adversarial Results
- Final Verdict: **APPROVE** or **REQUEST_CHANGES**


## 2026-11-09T08:00:37Z
You are the ML Spatial & AI Guardrail Challenger for Milestone 2 of the Urban Heat Resilience & Mitigation Platform.

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md

Your workspace: d:\Urban-Heat-Resilience-AI
Your dedicated state folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2
Read your full dispatch instructions at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\DISPATCH.md
Read the Project Scope Document at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read Worker M2's handoff report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m2_2\handoff.md

Empirically stress-test spatial clustering and AI numeric guardrails:
1. Spatial clustering stress testing:
   - Probe `assign_spatial_partitions()` in `backend/app/services/ml.py` with unusual and pathological GeoJSON configurations:
     - 3-zone, 5-zone, 8-zone, 12-zone, 50-zone configurations.
     - Collinear zones (same latitude/longitude), concentric ring zones, or zero-area geometries.
   - Verify that spatial cross-validation does not crash and produces valid partition assignments.
2. AI numeric guardrail adversarial stress testing:
   - Probe regex validation in `backend/app/services/ai.py` with adversarial text inputs:
     - Valid domain entity numbers (Sentinel-2, Landsat-8, PM2.5, years, bullet points).
     - Sneaky numbers embedded in words, hex codes, scientific notation.
     - Fabricated statistics vs true baseline tolerance.
3. Execute empirical tests and document results.

Document your empirical findings in `handoff.md` in your state folder with an explicit verdict: APPROVE or REQUEST_CHANGES.
Send a message back to the orchestrator upon completion.
