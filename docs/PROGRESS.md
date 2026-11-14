# AstroPulse progress

Decision support, not a diagnosis. Read AGENTS.md before doing anything.

## Stage checklist

Source: "AstroPulse: OpenCode Build Plan" (docs/AstroPulse OpenCode Build Plan.pdf).

- [x] Stage 0: Project setup and AGENTS.md
- [x] Stage 1: Data layer, indicator config and the simulator
- [x] Stage 2: The status engine (baseline and severity)
- [ ] Stage 3: Check-in flow and environment profiles
- [ ] Stage 4: The body map and status dashboard
- [ ] Stage 5: Trend charts
- [ ] Stage 6: Sources and cited guidance
- [ ] Stage 7: Drift detection and forecasting
- [ ] Stage 8: Blackout mode and the relay summary
- [ ] Stage 9: Actions and the progress view
- [ ] Stage 10: Hardening, accessibility and the offline audit
- [ ] Stage 11: Stretch, on-device language model rewording
- [ ] Stage 12: Demo preparation

## Done

- Stage 0 complete (commit `0f69ff8`, message "stage-0"):
  - `requirements.txt`, `config/`, `core/` skeleton, base template with footer,
    `core/static/core/app.css`, `core/static/vendor/` (HTMX and Plotly basic),
    `engine/` and `simulator/` placeholders, empty `data/` JSON files, smoke test,
    `.gitignore`.
- Stage 1 complete (commit `c696b19`, message "stage-1"):
  - `data/indicators.json`: six indicators from the build plan (resting_hr,
    sleep_hours, temperature, mood, exercise_min, spo2). All numbers are placeholders.
  - `docs/INDICATORS.md`: documents the schema and the placeholder status.
  - `core/models.py`: `CrewMember`, `Reading` (unique on crew member, indicator
    and date), `CheckIn`. Migrations `0001_initial` and `0002_checkin_unique_per_day`.
  - `simulator/generator.py`: `generate(scenario, days=21, seed=42)` for
    calm_week, drift_day6, fever_blackout, isolation_mood. Days are 1 to 21.
    Uses `numpy.random.default_rng(seed)`. Values are clamped to valid ranges.
  - `core/management/commands/seed_demo.py`: `seed_demo --scenario <name> [--reset]`.
    Creates or reuses "Demo crew (SIMULATED)". `--reset` clears only that crew
    member's data. Prints a 21-day table.
  - `tests/test_simulator.py` and `tests/test_seed_demo.py`.
- Stage 2 (personal-baseline status engine, pure Python + NumPy, no Django imports):
  - `engine/baseline.py`: `build_baseline(values, window=14, min_points=5)` and
    `Baseline(median, mad, n, enough_data)`.
  - `engine/scoring.py`: `robust_z` and `signed_bad_z` (1.4826 * MAD with a floor;
    unfavorable deviation only, never negative).
  - `engine/limits.py`: `check_limits(indicator_key, value, limits)` returns a
    severity or None; takes an already-parsed mapping (file loading outside engine).
  - `engine/status.py`: `evaluate(indicator, history_values, new_value, limits)`
    returns `StatusResult` with final severity = worse of personal and limit.
  - `tests/test_engine.py`: baseline/severity behaviors, limits, data-file checks,
    calm_week no-false-alarm, and adversarial cases.
  - Placeholder limit data: `data/limits.json` entries marked `"placeholder": true`;
    `data/sources.json` has matching `verified: false` stubs.

## Decisions

- Scenario days are numbered 1 to 21 (no day 0).
- `seed_demo --reset` clears only the demo crew member's data. Without it,
  `seed_demo` stops if demo data already exists.
- Command tests live in their own file, `tests/test_seed_demo.py`.
- Demo readings use environment `station`. The four environment keys are
  hardcoded as choices in `core/models.py` until `data/environments.json` is
  filled in Stage 3.
- Engine treats only the most recent window of readings; a bare string/bytes or
  non-sequence history is rejected (not iterated) and a zero/non-finite MAD floor
  must not divide by zero or report a fake green.

## In progress

- None. Local WIP (engine + fixes) is being reconciled onto stage-1.

## Known issues

- `CheckIn` has no `is_simulated` field (the spec does not list one). Demo
  check-ins are marked only by their note, "SIMULATED demo check-in".
- `Reading.indicator_key` is not validated against `indicators.json` (Stage 3).
- `environments.json` and `guidance.json` are still empty placeholders.
- All thresholds, ranges, MAD floors and scenario magnitudes are placeholders,
  not clinical values (see docs/INDICATORS.md and "Needs a source").
- The personal-baseline engine has no dates. Duplicate calendar days are not
  collapsed; callers must pass one value per day. Dated pairs and date strings
  are rejected as non-numeric, not parsed.
- `drift_day6` (resting_hr, seed 42): personal-baseline severity spikes at day 6
  then fluctuates and adapts (baseline median rises), so it is not monotonically
  rising over time; absolute drift vs. adaptive baseline needs care in UI/reasoning.

## Needs a source

- Replace placeholder limits with sourced values (resolved in Stage 6).
  `data/limits.json` thresholds, valid ranges and MAD floors are placeholders.
  `data/sources.json` holds `verified: false` stubs titled
  "PLACEHOLDER: replace with a real cited source"; no real citation, URL or
  publisher is invented. Limit reasons currently say "(see source)" and must be
  wired to real source ids once cited values exist.

## Next

1. Run `pytest` with project dependencies installed and fix any integration issues
   from reconciling engine/data with stage-1.
2. Stage 3 (build plan): check-in flow and environment profiles.
3. Stage 6: replace placeholder limits with sourced values (see above).
