# Dispatch: Milestone 2 Iteration 2 AI Guardrail Specialist (explorer_m2_iter2_1)

## Context
Working Directory: d:\Urban-Heat-Resilience-AI
State Directory: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1
Original Request Path: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Gate Status Document: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Challenger M2-2 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\handoff.md
Challenger M2-1 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md

## Objective
Investigate and design the exact drop-in remediation for the AI numeric guardrail pipeline in `backend/app/services/ai.py`:
1. **Fix Catastrophic Regex Backtracking on Metric Units**:
   - `NUMERIC_MEASUREMENT_PATTERN` currently causes `\d+` to backtrack on letters like `"m"` in `"10m"` and `"30m"`, splitting `"10m"` into `"1"` and `"0m"`, which triggers false-positive `ValueError` when `1` is not in facts.
   - Design regex pattern that prevents backtracking into digit sequences (e.g. using non-digit word boundaries or atomic grouping/possessive quantifiers simulation), and recognize metric units (`m`, `km`, `cm`, `mm`, `ha`) in the unit pattern, and/or whitelist spatial resolution expressions (`10m`, `30m`, `60m`, `100m`, `250m`) in `ENTITY_WHITELIST`.
2. **Support Scientific Notation**:
   - Allow scientific notation `(?:[eE][-+]?\d+)` in the value group so numbers like `1.85e-3` are parsed as single floating-point numbers.
3. **Eliminate Fact Zero-Rounding Leakage**:
   - `extract_numbers_from_facts()` currently rounds fractional values $< 0.5$ to `0` via `int(round(val))`. Combined with absolute tolerance `abs(raw_val - fn) < 0.15`, any hallucinated number in `(-0.15, 0.15)` matches `0`.
   - Update fact extraction so fractional values $< 1.0$ (when nonzero) are not rounded to `0`, or require `fn != 0` for absolute tolerance.

## Deliverable
Write your complete architectural and code remediation blueprint to `handoff.md` in your state folder with complete drop-in code for `backend/app/services/ai.py`. Remember: Explorer recommends fix strategy and provides exact code blueprints, but does NOT modify the source files directly.


## 2026-11-09T08:20:31Z
You are the AI Guardrail Regex & Measurement Specialist for Milestone 2 Iteration 2 of the Urban Heat Resilience & Mitigation Platform.

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md

Your workspace: d:\Urban-Heat-Resilience-AI
Your dedicated state folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1
Read your full dispatch instructions at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\DISPATCH.md
Read the Gate Status at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Read Challenger M2-2's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\handoff.md
Read Challenger M2-1's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md

Investigate `backend/app/services/ai.py` and provide an exact, drop-in remediation blueprint for:
1. Catastrophic regex backtracking on metric units (`10m`, `30m` backtracking `\d+` to `1` and `3`):
   - Redesign `NUMERIC_MEASUREMENT_PATTERN` so digits cannot backtrack into sub-sequences when letters follow.
   - Include standalone metric units (`m`, `km`, `cm`, `mm`, `ha`) in the unit pattern, or whitelist spatial resolution patterns (`10m`, `30m`, `60m`, etc.) in `ENTITY_WHITELIST`.
2. Scientific notation support:
   - Allow exponential scientific notation `(?:[eE][-+]?\d+)` in the value group.
3. Fact zero-rounding leakage:
   - In `extract_numbers_from_facts()`, do not round fractional numbers `< 1.0` (when nonzero) to `0`, preventing fabricated values in `(-0.15, 0.15)` from matching `0`.

Verify your design against `backend/tests/test_challenger_m2.py` and provide the full drop-in replacement code for `backend/app/services/ai.py` in `handoff.md`.
Send a message back to the orchestrator upon completion. Remember: Explorers investigate and recommend blueprints, but do NOT modify source code files.


## 2026-11-09T08:34:17Z
**Context**: Milestone 2 Iteration 2 AI Guardrail Regex Investigation
**Content**: Status inquiry regarding your regex and fact rounding remediation blueprint. Explorer 3 has delivered its blueprint.
**Action**: Please report current status and ETA, or complete your handoff.md report.
