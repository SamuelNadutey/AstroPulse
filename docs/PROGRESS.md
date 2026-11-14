# AstroPulse progress

Decision support, not a diagnosis. Read AGENTS.md before doing anything.

## Stage checklist

Source: "AstroPulse: OpenCode Build Plan" (docs/AstroPulse OpenCode Build Plan.pdf).

- [x] Stage 0: Project setup and AGENTS.md
- [ ] Stage 1: Data layer, indicator config and the simulator (built, review pending, not tagged)
- [ ] Stage 2: The status engine (baseline and severity)
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
- Stage 1 built (not yet reviewed or tagged):
  - `data/indicators.json`: six indicators from the build plan (resting_hr,
    sleep_hours, temperature, mood, exercise_min, spo2). All numbers are placeholders.
  - `docs/INDICATORS.md`: documents the schema and the placeholder status.
  - `core/models.py`: `CrewMember`, `Reading` (unique on crew member, indicator
    and date), `CheckIn`. Migration `core/migrations/0001_initial.py`.
  - `simulator/generator.py`: `generate(scenario, days=21, seed=42)` for
    calm_week, drift_day6, fever_blackout, isolation_mood. Days are 1 to 21.
    Uses `numpy.random.default_rng(seed)`. Values are clamped to valid ranges.
  - `core/management/commands/seed_demo.py`: `seed_demo --scenario <name> [--reset]`.
    Creates or reuses "Demo crew (SIMULATED)". `--reset` clears only that crew
    member's data. Prints a 21-day table.
  - `tests/test_simulator.py` (15 tests) and `tests/test_seed_demo.py` (11 tests).
  - AGENTS.md: section 4 of the build plan pasted into the Domain spec.
  - Migration `core/migrations/0002_checkin_unique_per_day.py`: one check-in per
    crew member per day.
- Stage 1 review fixes (review findings 1, 2, 3, 4 and 6):
  - `seed_demo` refuses to run without `--reset` when the demo crew exists,
    so scenarios cannot silently mix. `--reset` replaces the demo data.
  - Clamping test now asserts that a bound is actually reached.
  - Tests added for the unique constraints on `Reading` and `CheckIn`.
  - Progress counts corrected.
- Second review fixes:
  - `seed_demo` docstring updated to describe the `--reset` requirement.
  - Guard simplified to check for the demo crew member's existence.
- `pytest`: 29 passed.
- Acceptance: `seed_demo --scenario drift_day6 --reset` prints 21 days for six indicators.

## Decisions

- Scenario days are numbered 1 to 21 (no day 0).
- `seed_demo --reset` clears only the demo crew member's data. Without it,
  `seed_demo` stops if demo data already exists.
- Command tests live in their own file, `tests/test_seed_demo.py`.
- Demo readings use environment `station`. The four environment keys are
  hardcoded as choices in `core/models.py` until `data/environments.json` is
  filled in Stage 3.

## In progress

- Stage 1 is ready for final review. Tag `stage-1` after one more pass with
  an independent model (per build plan review rule).

## Known issues

- No `stage-0` git tag exists yet. The commit is there, but `git tag` is empty.
- The vendored Plotly file is `core/static/vendor/plotly-basic.min.js`. The
  build plan names `plotly.min.js` (Stage 0 Step C and Stage 5). Decide
  whether to keep the basic bundle or replace it.
- `CheckIn` has no `is_simulated` field (the spec does not list one). Demo
  check-ins are marked only by their note, "SIMULATED demo check-in". Consider
  adding the field at review.
- Review items deferred: `Reading.indicator_key` is not validated against
  `indicators.json` (Stage 3); CrewMember name is not unique; the demo dates
  depend on today's date; `.gitattributes` for line endings; negative
  `normal_wobble` is not rejected.
- `environments.json`, `limits.json`, `sources.json` and `guidance.json` are
  still empty placeholders. They are filled in Stages 3 and 6.
- All thresholds and scenario magnitudes are placeholders (see docs/INDICATORS.md).

## Next

1. Run the Stage 1 review prompt, fix findings, and tag `stage-1`.
2. Stage 2: the status engine (plan first, with the Stage 2 prompt).
