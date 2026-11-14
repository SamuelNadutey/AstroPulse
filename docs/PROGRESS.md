# AstroPulse progress

Decision support, not a diagnosis. Read AGENTS.md before doing anything.

## Stage checklist

Source: "AstroPulse: OpenCode Build Plan" (docs/AstroPulse OpenCode Build Plan.pdf).

- [x] Stage 0: Project setup and AGENTS.md
- [x] Stage 1: Data layer, indicator config and the simulator
- [x] Stage 2: The status engine (baseline and severity)
- [x] Stage 3: Check-in flow and environment profiles
- [x] Stage 4: The body map and status dashboard
- [x] Stage 5: Trend charts
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
- Stage 4 complete (body map and status dashboard, built with the optional
  `?date=` demo review agreed at plan time):
  - `core/templates/core/_bodymap.html`: inline SVG front-view body map.
    Five focusable region groups (head, chest, lungs, torso, legs) with
    `role="button"`, `tabindex="0"`, an aria-label carrying region name +
    severity word + color name, and `hx-get` into `#region-panel` with
    `hx-trigger="click, keyup[key==='Enter']"` for keyboard users (bundled
    HTMX trigger syntax only). Each region shows a severity icon + text
    label next to it; shape colors come from the sev-* CSS variables.
  - Color-blind-safe (Okabe-Ito derived) placeholder palette as CSS
    variables (fill + darker text tone per severity) in `app.css`, plus a
    legend with icon + word + color name for all five severities.
  - `core/services.py`: `run_status_for` entries now carry `body_region`;
    new `REGION_LABELS`, `worst_severity()` (severity rank from the
    engine's public constants) and `region_statuses(entries)` which groups
    by region with the WORST severity winning for shared regions (head =
    sleep_hours + mood).
  - `/region/<name>/` (`region_detail`): HTMX partial showing each of the
    region's indicators — value today, severity icon + text + color,
    reasons — plus a per-indicator "View trend" link. Unknown regions 404.
  - `/trend/<indicator_key>/`: tiny placeholder page ("Trend charts arrive
    in the next build stage") so the trend links are not dead (Stage 5).
  - `/status/` is now the dashboard: overall banner ("All indicators
    normal" or worst severity with icon + word), CSS-grid layout with body
    map + detail panel (collapses to one column under 48rem), the Stage 3
    per-indicator list kept as a no-JS fallback, per-row SIMULATED badges.
  - `?date=YYYY-MM-DD` on `/status/` and `/region/<name>/` reviews a past
    day (invalid/future dates fall back to today). Added so the seeded
    drift_day6 demo can be walked day by day.
  - `tests/test_bodymap.py`: 9 tests — region mapping matches the spec,
    worst-severity aggregation, focusable regions with aria-labels, the
    no-color-only rule (icon + text for every severity), region endpoint
    indicator selection, 404s, the drift_day6 escalation story and date
    fallback. Full suite: 70 tests passing.

## Acceptance check

- `seed_demo --scenario drift_day6`, verified live:
  - Day 21 (default): head region red (sleep 3.59 h, "Below the critical
    limit of 4"), chest green (resting_hr 82.93 bpm; the adaptive baseline
    absorbed the drift), others green.
  - Day 14 (`/status/?date=<today-7>`): chest AND head orange
    ("Resting heart rate is 3.49 spreads above your usual range"), so the
    escalation is demonstrable mid-scenario via the date parameter.
  - Day 6: chest red (the drift spike).
  - Region panels show reasons and per-indicator trend links; SIMULATED
    badges appear on the banner and simulated rows.
  - Severity is still not monotonically rising over time (Stage 2 known
    issue); the Stage 7 CUSUM remains the planned fix for slow drift.

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
- The dashboard supports an optional `?date=YYYY-MM-DD` (default today,
  future dates clamped) so the seeded demo scenarios can be reviewed day
  by day; real use stays on today's date.
- The trend link on region panels points at a minimal `/trend/<key>/`
  placeholder until Stage 5 delivers the charts.
- Body-map region-to-indicator mapping is derived from
  `data/indicators.json` (`body_region`), not hardcoded; `REGION_LABELS`
  provides the five display names.
- Region colors use an Okabe-Ito derived placeholder palette (CSS
  variables); severity is always icon + text + color.
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
- The body map is stylised placeholder art (simple circles/rects); a
  designer-quality silhouette is a demo-preparation polish item.
- SVG focus outlines vary by browser; `:focus` outline is styled but
  keyboard behaviour should be re-verified in the Stage 10 accessibility
  audit.
- Stage 4 UI fixes committed after review (commit `41b66ee`):
  Django template comments `{# #}` no longer leak into rendered HTML;
  mood shows "4.34 / 5" (scale separate from value); region labels are
  14px for legibility; SIMULATED badge moved to sit beside each
  indicator name.
- Stage 5 complete (trend charts with bundled Plotly):
  - `core/charts.py`: `build_trend_figure(indicator, readings, baseline,
    limits_entry)` returns a JSON-serialisable Plotly figure dict. Shows
    readings as a line-with-markers trace, a personal-baseline band
    (median +/- 2 spreads, spread computed from engine `build_baseline`
    median/MAD and `engine.scoring._MAD_SCALE`), horizontal dotted lines
    for sourced limits (yellow/orange/red), and a placeholder "Forecast
    (Stage 7)" trace. `trend_summary()` renders a plain-text summary for
    accessibility. All numbers are placeholders, not clinical values.
  - `core/views.py`: `trend()` renders `/trend/<indicator_key>/` with the
    figure embedded via `json_script`; `trend_chart()` is an HTMX partial
    (`/trend/<indicator_key>/chart/`) swapped into `#trend-container` by
    the chart selector. No external data is fetched.
  - `core/urls.py`: added `/trend/<indicator_key>/chart/` endpoint.
  - `core/templates/core/trend.html`: chart page loads Plotly from
    `core/static/vendor/plotly-basic.min.js` only, calls `Plotly.newPlot`
    with `displaylogo: false`, has an indicator `<select>` HTMX chart
    selector, and a data-table fallback inside `<details>`.
  - `core/templates/core/_trend_chart.html`: partial with `json_script`,
    `#trend-plot`, text summary, and data table.
  - `core/static/core/app.css`: trend selector, plot sizing, summary and
    data-table styles.
  - `tests/test_charts.py`: 9 tests — readings trace present, baseline
    band uses engine median/MAD, limit lines render, page loads with
    bundled Plotly only (no external URLs), HTMX partial works, summary
    text, 404 for unknown indicators, and drift_day6 resting HR drift is
    visible.
  - Full suite: 79 tests passing.

## Acceptance check

- `seed_demo --scenario drift_day6`, then `/trend/resting_hr/` (verified
  against a live dev server): the chart shows resting heart rate rising
  from 64.66 to 82.93 bpm over the 14-day window against a baseline band
  of median 74.7 +/- ~8.5 spreads, so the drift away from the baseline
  is obvious. The plain-text summary reads "Resting heart rate rose from
  64.66 to 82.93 bpm. Your baseline median is 74.7 bpm." No external URLs
  appear in the HTML.

## Needs a source

- Replace placeholder limits with sourced values (resolved in Stage 6).
  `data/limits.json` thresholds, valid ranges and MAD floors are placeholders.
  `data/sources.json` holds `verified: false` stubs titled
  "PLACEHOLDER: replace with a real cited source"; no real citation, URL or
  publisher is invented. Limit reasons currently say "(see source)" and must be
  wired to real source ids once cited values exist.

## Next

1. Stage 6 (build plan): replace placeholder limits with sourced values.
2. Stage 7: drift detection and forecasting (CUSUM + forecast band on the
   trend charts).
3. Polish: friendlier engine reason wording and per-indicator units in reasons.
