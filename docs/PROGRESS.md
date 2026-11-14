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
- [x] Stage 6: Sources and cited guidance
- [x] Stage 7: Drift detection and forecasting
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
    issue); the Stage 7 CUSUM is the fix for slow drift (see the Stage 7
    acceptance note above).

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
- All thresholds, ranges, MAD floors and scenario magnitudes are placeholders,
  not clinical values (see docs/INDICATORS.md and "Needs a source").
- The personal-baseline engine has no dates. Duplicate calendar days are not
  collapsed; callers must pass one value per day. Dated pairs and date strings
  are rejected as non-numeric, not parsed. `run_status_for` filters by date and
  passes one value per day, oldest to newest.
- `drift_day6` (resting_hr, seed 42): personal-baseline severity spikes at day 6
  then fluctuates and adapts (baseline median rises), so it is not monotonically
  rising over time. The Stage 7 drift CUSUM now keeps the indicator yellow even
  when the adaptive baseline reads green, but the overall trend is still not
  monotonic by design.
- Drift tuning tradeoff: `DEFAULT_K=1.0` and `DEFAULT_H=7.0` were tuned so
  `calm_week` never drifts across the required 20 seeds, which gives roughly a
  week of latency on the gradual drift (resting_hr flags day 13, sleep day 12).
  Beyond 20 seeds, `exercise_min` (the noisiest indicator, wobble 8 on a centre
  of 45) is the main source of occasional false drift; tightening k/h further
  would break the "yellow before extreme" story, so this is a deliberate,
  documented tradeoff (yellow is a low-risk "watch" prompt).
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
- Stage 6 complete (sourced guidance and citation validation):
  - `data/sources.json`: 14 provided sources, all with `verified: false`
    and a `verify_note`. Optional `doi` and `alt_url` preserved. Years
    are `null` where noted; the UI displays those as "n.d.".
  - `data/guidance.json`: 24 rules (yellow/orange/red/drift for each of
    the six indicators). Every rule cites only sources from the allowed
    per-indicator table; `src_nasa_std_3001_v1` is used only on red
    rules as a secondary source. Actions use `TODO` source ids when no
    provided source clearly covers the action.
  - `core/guidance.py`: cached loaders, `GuidanceResult`, and
    `select_guidance(status_result)` that returns the drift rule for
    yellow+drift, the severity rule for orange/red, and `None` for
    green/gray. Resolved sources include `display_citation` and `url`
    (plain text only, never a link or loaded resource).
  - `core/validation.py`: `collect_errors()`, `list_needs_source()`,
    `validate_guidance_data()`, and `GuidanceValidationError`. Checks
    missing/unknown/TODO source ids for rules and actions, missing
    `contact_ground_text`, duplicate ids, unknown indicator keys,
    invalid triggers, and missing headlines. `strict=True` reports
    unverified sources.
  - `core/management/commands/check_guidance.py`:
    `python manage.py check_guidance [--strict]`. Prints `OK` and the
    TODO list in normal mode; fails in strict mode until all sources are
    verified.
  - `tests/test_guidance.py`: 32 tests including synthetic validation
    errors, rule coverage, `select_guidance` behavior, resolved sources,
    allowed-source compliance, red/orange contact wording, digit checks
    (allowed only in spo2), banned diagnosis phrases, and the management
    command. `test_no_todo_sources` is marked `xfail` until real action
    sources are found.
  - `tests/test_engine.py`: updated the outdated sources placeholder
    test to match the new real sources file.
  - Full suite: 110 passed, 1 xfailed.
- Guidance card UI (follows Stage 6 sourced guidance):
  - `core/templates/core/_guidance_card.html`: reusable card with sections
    in order — Status and reason, Likely contributors, What you can do,
    Measure again in, When to contact ground, Sources. Citations render as
    plain text only; URLs are never clickable links or loaded resources.
  - Card included per indicator in the region detail panel
    (`core/templates/core/_region_detail.html`) and under each trend chart
    (`core/templates/core/_trend_chart.html`).
  - `core/views.py`: `_status_entry_for()` and `_guidance_for()` helpers
    feed the card. Green shows a short reassuring card with no contact-ground
    alarm; gray shows "Not enough data yet" plus the fix-it prompt.
  - `core/static/core/app.css`: guidance-card styles, severity-colored left
    border, distinct contact-ground block, accessible section headings.
  - `tests/test_guidance_card.py`: 10 tests covering all six sections at
    orange, contact-ground prominence at red, gray message, green
    reassurance, plain-text sources, and accessible headings.
  - Full suite: 120 passed, 1 xfailed.
- Stage 7 complete (drift detection and forecasting, pure Python + NumPy):
  - `engine/drift.py`: `detect_drift(history_values, baseline, bad_direction,
    k=1.0, h=7.0)` runs a one-sided CUSUM on the signed robust z-scores of
    readings after a reference period. A per-reading cap (Z_CAP=3.5) stops a
    single outlier from tripping drift. `detect_series_drift` splits a series
    into a 5-point reference and a test period. Returns a `DriftResult` with
    `drifting`, `days_in_drift`, `started_on_index` and a plain-English reason
    such as "5 days above your usual range.".
  - `engine/forecast.py`: `forecast(history_values, horizon=5, window=10)`
    fits a line with `numpy.polyfit` on the last window points and projects
    3 to 7 days with a band from the residual standard deviation widened by
    the prediction-interval leverage term. Returns `None` below 5 points. The
    docstring states the band is a rough indication, not a guarantee.
  - `engine/status.py`: `StatusResult` gains a `drift` flag; `evaluate` takes
    an optional `long_history` and runs the CUSUM. A drift flag raises the
    final severity to at least yellow but never red, and appends a reason.
  - `core/services.py`: `run_status_for` loads a 28-day `DRIFT_LOOKBACK_DAYS`
    history for drift; personal severity still uses the 14-day window.
  - `core/charts.py`: the "Forecast (Stage 7)" placeholder is replaced by a
    dashed projected line and a shaded band labeled "Forecast (uncertain)".
  - `core/guidance.py`: drift guidance stays gated behind
    `DRIFT_GUIDANCE_APPROVED = False` until the safety owner signs off; a
    yellow drift flag currently shows the normal yellow rule.
  - `data/indicators.json`: corrected two placeholder MAD floors so z-scores
    are honest — `resting_hr` 2.0 -> 3.0 and `exercise_min` 5.0 -> 8.0 (both
    had been below the simulator's `normal_wobble`, inflating z and causing
    false drift).
  - `tests/test_drift.py` (13) and `tests/test_forecast.py` (8): single
    outlier never drifts, sustained shift drifts with direction-aware reason,
    drift_day6 flags resting_hr and sleep_hours within a week, calm_week never
    drifts across 20 seeds, forecast accuracy and band-width behaviour,
    fewer-than-5 points returns None, horizon bounds.
  - `tests/test_bodymap.py`: added the acceptance test that day 21 chest is
    yellow from drift (the adaptive baseline would otherwise show green).
  - Full suite: 148 passed, 1 xfailed.

## Acceptance check

- `seed_demo --scenario drift_day6`, then `/trend/resting_hr/` (verified
  against a live dev server): the chart shows resting heart rate rising
  from 64.66 to 82.93 bpm over the 14-day window against a baseline band
  of median 74.7 +/- ~8.5 spreads, so the drift away from the baseline
  is obvious. The plain-text summary reads "Resting heart rate rose from
  64.66 to 82.93 bpm. Your baseline median is 74.7 bpm." No external URLs
  appear in the HTML.
- Stage 7 acceptance (`seed_demo --scenario drift_day6`): the drift CUSUM
  flags resting_hr on day 13 and sleep_hours on day 12, so the dashboard
  shows yellow while the individual readings are still moderate, before they
  turn orange/red at day 14. By day 21 the adaptive baseline has absorbed the
  heart-rate rise (personal severity green), but drift keeps chest yellow —
  the story the detector exists to tell. `calm_week` never drifts across 20
  seeds and all six indicators.

## Needs a source

- Placeholder limits in `data/limits.json` are still unsourced except where
  noted. Thresholds, valid ranges and MAD floors remain placeholders, not
  clinical values.
- The following suggested actions currently use `TODO` source ids because no
  provided source clearly covers the action. They must be resolved before the
  Stage 10 audit:
  - RULE resting_hr.yellow ACTION rest-quietly
  - RULE resting_hr.yellow ACTION note-stimulants
  - RULE resting_hr.orange ACTION rest-rehydrate
  - RULE resting_hr.orange ACTION recheck-calm
  - RULE resting_hr.red ACTION stop-activity
  - RULE resting_hr.red ACTION check-sensor
  - RULE resting_hr.drift ACTION recovery-time
  - RULE resting_hr.drift ACTION review-load
  - RULE sleep_hours.yellow ACTION wind-down
  - RULE sleep_hours.yellow ACTION dark-quiet
  - RULE sleep_hours.orange ACTION adjust-light
  - RULE sleep_hours.orange ACTION protect-sleep
  - RULE sleep_hours.red ACTION seek-support
  - RULE sleep_hours.red ACTION minimize-stimuli
  - RULE sleep_hours.drift ACTION review-sleep-schedule
  - RULE sleep_hours.drift ACTION track-triggers
  - RULE temperature.yellow ACTION rest-cool
  - RULE temperature.yellow ACTION recheck-cooled
  - RULE temperature.orange ACTION cooler-area
  - RULE temperature.orange ACTION recheck-same-sensor
  - RULE temperature.red ACTION stop-exertion
  - RULE temperature.red ACTION verify-sensor
  - RULE temperature.drift ACTION check-sensor-env
  - RULE temperature.drift ACTION consistent-recheck
  - RULE mood.yellow ACTION short-break
  - RULE mood.yellow ACTION note-stressors
  - RULE mood.orange ACTION scheduled-countermeasure
  - RULE mood.orange ACTION reach-crewmate
  - RULE mood.red ACTION ask-support
  - RULE mood.red ACTION pause-demands
  - RULE mood.drift ACTION social-activity
  - RULE mood.drift ACTION review-workload-sleep
  - RULE exercise_min.yellow ACTION short-movement
  - RULE exercise_min.yellow ACTION check-equipment
  - RULE exercise_min.orange ACTION prioritize-exercise
  - RULE exercise_min.orange ACTION discuss-alternatives
  - RULE exercise_min.red ACTION revise-plan
  - RULE exercise_min.red ACTION assess-barriers
  - RULE exercise_min.drift ACTION crew-session
  - RULE exercise_min.drift ACTION review-barriers
  - RULE spo2.yellow ACTION check-placement
  - RULE spo2.yellow ACTION rest-recheck
  - RULE spo2.orange ACTION different-sensor
  - RULE spo2.orange ACTION breathe-slowly
  - RULE spo2.red ACTION alert-ground
  - RULE spo2.red ACTION recheck-sensor
  - RULE spo2.drift ACTION sensor-recheck
  - RULE spo2.drift ACTION track-readings

## Safety review (guidance wording)

- `docs/GUIDANCE_REVIEW.md` records a per-rule review of `data/guidance.json`
  (diagnosis-like wording, unsafe advice, unsupported claims, contact-ground
  gaps), plus an independent second review by an AI reviewer agent.
- Main open findings: all 48 actions are `TODO`-sourced; red rules lack
  on-board emergency direction; mood.red has no crisis pathway; several
  contributors name conditions; some sources are weak for their claims.
- Changes made after review (see GUIDANCE_REVIEW.md "Changes made after
  review"): unsourced actions hidden from the card; condition labels replaced
  with observable wording (test-enforced); spo2 urgency and wording aligned;
  `127.0.0.1` allowed in settings.
- Still blocked: red-rule emergency direction, mood.red crisis pathway,
  sourcing the 48 actions, verifying the 14 sources, and the safety owner's
  sign-off (**pending**).
- Guidance wording must not be treated as approved until sign-off.
- Test count: 124 passed, 1 xfailed.

## Needs human verification

All `data/sources.json` entries have `verified: false`. Verify each source
and flip `verified` to `true` by hand after checking the page:

- `src_nasa_sleep_evidence`: NTRS ID 20150016964. Year not shown in the search result; check the page.
- `src_nasa_sleep_prd`: NTRS ID 20160003864. Year not shown; check the page.
- `src_hera_2020`: Front. Physiol. 11:394. The author list in the search result was garbled (appears to be Nasrini et al.); check authors.
- `src_nasa_behav_evidence`: NTRS ID 20160004365. Year not shown; check the page.
- `src_nasa_behav_evidence_update`: Year 2025 inferred from file name and NTRS ID; verify.
- `src_nasa_behav_risk_page`: Page showed 'Last Updated Sep 17, 2025'. Confirm exact page title.
- `src_nasa_exercise_iws`: NTRS ID 20230013277. 2023 is the NTRS 'date acquired'; confirm title, authors and year.
- `src_roberts_2025`: Journal name inferred from the DOI prefix; verify. First author appears to be Roberts.
- `src_loerch_exercise`: Author appears to be L. H. Loerch. Journal name and year not confirmed; URL built from the DOI.
- `src_arzeno_cv`: Arzeno et al., NTRS ID 20100036638. Year not shown; check.
- `src_otsuka_hrv`: Otsuka et al., Heliyon Dec 2016. Weak support for resting heart rate; flag for human review.
- `src_stahn_temp_2017`: Stahn et al., Sci Rep 7:16180.
- `src_statpearls_pulseox`: This URL is a StatPearls mirror. Replace with the canonical NCBI Bookshelf URL; authors and year not shown.
- `src_nasa_std_3001_v1`: Revision C date taken from the document history (Sept 15, 2023); verify.

## Next

1. Safety owner review of data/guidance.json: see docs/GUIDANCE_REVIEW.md
   (pending sign-off; findings by rule id). Includes the drift-guidance gate
   (`DRIFT_GUIDANCE_APPROVED`) which must be flipped after sign-off.
2. Polish: friendlier engine reason wording and per-indicator units in reasons.
3. Stage 8: Blackout mode and the relay summary.
