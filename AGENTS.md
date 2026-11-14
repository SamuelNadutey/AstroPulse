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
(paste section 4 of the build plan here: indicators table, severity levels, 
engine rules, scenarios, environments)
## Commands
run: python manage.py runserver
test: pytest
seed: python manage.py seed_demo --scenario <name>