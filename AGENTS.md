# AstroPulse: agent instructions
AstroPulse is an offline health self-assessment tool for astronauts. It is 
decision support, never diagnosis. Read docs/PROGRESS.md before doing 
anything.
## Stack
Python 3.11+, Django 5, SQLite, server-rendered templates, HTMX (bundled), 
Plotly (bundled), inline SVG body map. engine/ and simulator/ are pure Python 
(NumPy only, no Django imports).
## Hard rules
1. Nothing may load from the internet. No CDN links, no web fonts, no 
external URLs in templates or static files.
2. Footer on every page: 'Decision support, not a diagnosis.'
3. Demo data is labeled SIMULATED wherever shown.
4. Every guidance rule and action prompt must reference at least one id in 
data/sources.json. Never invent sources, URLs or clinical limits. If a source 
is missing, add an entry with verified:false and flag it in docs/PROGRESS.md.
5. Severity is always shown as icon + text + color, never color alone.
6. Thresholds are placeholders, not clinical values. Say so in code comments.
7. Scoring and streaks reward completing check-ins, never health outcomes.
8. Keep diffs small. Only touch files named in the task. Do not refactor 
unrelated code.
9. Every feature ships with tests. Run `pytest` before declaring done.
10. At the end of each task, update docs/PROGRESS.md (done, in progress, 
known issues, next).
## Domain spec
Source: section 4 of "AstroPulse: OpenCode Build Plan".

Indicators (six):

| key | label | unit | bad direction | body region | input type |
|---|---|---|---|---|---|
| resting_hr | Resting heart rate | bpm | high | chest | device |
| sleep_hours | Sleep | hours | low | head | self-report |
| temperature | Body temperature | °C | high | torso | device |
| mood | Mood and stress | 1 to 5 | low | head | self-report |
| exercise_min | Exercise | minutes | low | legs | self-report |
| spo2 | Blood oxygen | % | low | lungs | device |

Severity levels: gray (not enough data), green (normal), yellow (watch),
orange (concern), red (contact ground). Always display icon plus text plus color.

Engine rules (placeholders to tune, not clinical values):
- Baseline window: the last 14 days of readings. Minimum 5 readings, otherwise
  gray with "Not enough data yet".
- Score: z = (x - median) / (1.4826 * MAD), with a minimum MAD floor per
  indicator. Only the bad direction counts.
- Personal severity: z below 1.5 green, below 2.5 yellow, below 3.5 orange,
  otherwise red.
- Limit severity: compared with sourced limits stored in data/limits.json.
- Final severity is the worse of the two, always with a written reason such as
  "5 days above your usual range".
- Drift: a one-sided CUSUM on the robust z-scores flags slow shifts that single
  readings miss.
- Forecast: linear fit on the last 7 to 14 days, projected 3 to 7 days with an
  uncertainty band from residual spread.

Scenarios (seeded, repeatable): calm_week, drift_day6 (resting HR up, sleep
down from day 6), fever_blackout (temperature spike during a blackout),
isolation_mood (mood and exercise decline).

Environments: station, transit, rover, surface_base. Each changes which prompts
appear, which equipment is assumed, and the communication delay shown.

Safety rules (tested automatically):
1. Footer on every page: "Decision support, not a diagnosis."
2. All demo data is labeled SIMULATED.
3. Every guidance rule and action prompt links to at least one source in
   data/sources.json.
4. No external URL in any template or static file (the page may display a
   citation URL as text, but never load from it).
5. HTMX and Plotly are bundled in core/static/vendor/.
6. Progress and scoring reward completing check-ins, never health outcomes.
7. Data stays on the device. Export happens only on request.
## Commands
run: python manage.py runserver
test: pytest
seed: python manage.py seed_demo --scenario <name>