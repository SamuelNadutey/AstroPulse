# AstroPulse progress

Decision support, not a diagnosis. Read AGENTS.md before doing anything.

## Stage checklist

Source: "AstroPulse: OpenCode Build Plan" (docs/AstroPulse OpenCode Build Plan.pdf).

- [x] Stage 0: Project setup and AGENTS.md
- [x] Stage 1: Data layer, indicator config and the simulator
- [x] Stage 2: The status engine (baseline and severity)
- [x] Stage 3: Check-in flow and environment profiles
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
- Stage 3 complete (check-in flow and environment profiles, connects the form
  to the Stage 2 engine):
  - `data/environments.json`: station, transit, rover, surface_base, each with
    `label`, `comms_delay_text`, `available_equipment` (device indicator keys;
    the rover has no SpO2 clip, so spo2 is skipped there) and `extra_prompts`.
    All prompt/comms copy is placeholder demo text.
  - `core/forms.py`: `CheckInForm` built from indicators.json plus the selected
    environment. Device indicators appear only when the environment lists the
    equipment; self-report indicators are always asked. Friendly validation
    messages against min_valid/max_valid (placeholder ranges), mood as a 1-5
    select, blackout checkbox ("Blackout: no contact with ground") and a note
    field. `link_errors_to_aria()` points invalid fields at their error block
    via aria-describedby.
  - `core/services.py`: JSON loaders + `run_status_for(crew_member, date)`
    loads the 14-day history per indicator, maps label -> name and calls
    `engine.status.evaluate`. No engine math in views.
  - `core/views.py` / `core/urls.py`: `/checkin/` (GET form, POST saves
    Readings + CheckIn then redirects to `/status/`), `/checkin/fields/`
    (HTMX partial that swaps only `#checkin-fields` when the environment
    select changes, `hx-get`), `/status/` placeholder page.
  - `/status/` lists every indicator with inline SVG icon + severity word +
    color (circle/triangle/diamond/octagon), reasons, a per-row SIMULATED
    badge for simulated readings, and a "placeholders, not clinical values"
    note. HTMX is loaded from `core/static/vendor/` only.
  - `tests/test_checkin.py`: 15 tests covering environments.json completeness,
    form validation, rover vs station fields, aria error linking, POST
    creating readings/checkin, same-day re-check-in, the partial swap, every
    severity (gray/green/yellow/orange/red) as icon+text+color on the page,
    the SIMULATED badge and drift_day6 vs calm_week severity.
- Full suite: 61 tests passing (`pytest` in a project venv).

## Acceptance check

- `seed_demo --scenario drift_day6`, then `/status/` (verified against a live
  dev server): the day-21 view shows resting_hr green at 82.93 bpm (the
  adaptive 14-day baseline has absorbed the drift), Sleep red at 3.59 hours
  (below the red limit), other indicators green, per-row SIMULATED badges.
  Severity is therefore not monotonically rising over the demo; the drift
  story is carried by the limit breach and the elevated absolute value (the
  Stage 7 CUSUM is the planned mechanism for slow drift).

## Decisions

- Scenario days are numbered 1 to 21 (no day 0).
- `seed_demo --reset` clears only the demo crew member's data. Without it,
  `seed_demo` stops if demo data already exists.
- Command tests live in their own file, `tests/test_seed_demo.py`.
- Demo readings use environment `station`. The four environment keys are
  hardcoded as choices in `core/models.py`; labels/equipment come from
  `data/environments.json` (filled in Stage 3).
- The check-in form asks self-report indicators on every environment and only
  shows device indicators the environment's `available_equipment` supports
  (e.g. no spo2 on the rover).
- A same-day re-check-in replaces that day's readings and updates the CheckIn
  instead of erroring on the unique constraint.
- Real check-ins are stored under a single local crew member, "You (local)",
  until the dashboard/auth stage introduces profiles. `/status/` shows the
  crew member with the most recent CheckIn (fallback: first crew member).
- Engine treats only the most recent window of readings; a bare string/bytes or
  non-sequence history is rejected (not iterated) and a zero/non-finite MAD floor
  must not divide by zero or report a fake green.
- The robust-z denominator is the scaled MAD (1.4826 * MAD) with mad_floor as a
  floor on the scaled value; flat placeholder histories therefore divide by
  mad_floor itself.

## In progress

- None.

## Known issues

- `CheckIn` has no `is_simulated` field (the spec does not list one). Demo
  check-ins are marked only by their note, "SIMULATED demo check-in". The
  `/status/` SIMULATED badge is driven by the day's Reading.is_simulated.
- `Reading.indicator_key` is not validated at the model level; the check-in
  form only submits keys from indicators.json (validation stays form-side).
- `guidance.json` is still an empty placeholder; `environments.json` is now
  filled but all of its prompt/comms copy is placeholder demo text.
- All thresholds, ranges, MAD floors and scenario magnitudes are placeholders,
  not clinical values (see docs/INDICATORS.md and "Needs a source").
- The personal-baseline engine has no dates. Duplicate calendar days are not
  collapsed; callers must pass one value per day. Dated pairs and date strings
  are rejected as non-numeric, not parsed. `run_status_for` filters by date and
  passes one value per day, oldest to newest.
- `drift_day6` (resting_hr, seed 42): personal-baseline severity spikes at day 6
  then fluctuates and adapts (baseline median rises), so it is not monotonically
  rising over time; absolute drift vs. adaptive baseline needs care in UI/reasoning.
  The Stage 7 CUSUM is the planned mechanism for slow drift.
- `mood` renders as a 1-5 select; garbage input surfaces Django's default
  "Select a valid choice" text alongside the friendly invalid message.
- Severity reason wording from the engine ("is 6.0 spreads above your usual
  range") is functional but stiff; rewording is a later polish task.

## Needs a source

- Replace placeholder limits with sourced values (resolved in Stage 6).
  `data/limits.json` thresholds, valid ranges and MAD floors are placeholders.
  `data/sources.json` holds `verified: false` stubs titled
  "PLACEHOLDER: replace with a real cited source"; no real citation, URL or
  publisher is invented. Limit reasons currently say "(see source)" and must be
  wired to real source ids once cited values exist.

## Next

1. Stage 4 (build plan): the body map and status dashboard.
2. Stage 6: replace placeholder limits with sourced values (see above).
3. Polish: friendlier engine reason wording and per-indicator units in reasons.
