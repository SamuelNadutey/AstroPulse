# AstroPulse progress

Decision support, not a diagnosis. Read AGENTS.md before doing anything.

## Stage checklist

Note: the stage checklist is summarized from the build plan referenced in
AGENTS.md (section 4/domain spec). AGENTS.md in this repo does not yet
contain the explicit stage list; update this section when it does.

- [x] **Stage 0 — Project skeleton**: Django `config` project + `core` app,
      SQLite, `ALLOWED_HOSTS=localhost`, base template with header/status
      banner/footer, home page, smoke tests, data JSON placeholders.
- [ ] Stage 1 — Data model, indicator catalog and environments.
- [ ] Stage 2 — Check-in flow (server-rendered, HTMX later).
- [ ] Stage 3 — Engine rules and severity levels.
- [ ] Stage 4 — Simulator scenarios (seeded demo data).
- [ ] Stage 5 — Dashboard with Plotly charts (bundled).
- [ ] Stage 6 — Inline SVG body map.
- [ ] Stage 7 — Guidance rules with verified source references.
- [ ] Stage 8 — Hardening, full test pass and docs.

## Done

- Stage 0 complete:
  - `requirements.txt`: Django>=5.0, numpy, pytest, pytest-django.
  - `config/`: settings (SQLite, DEBUG on, localhost only), urls, wsgi/asgi.
  - `core/`: app with home view at `/`, `core/static/core/app.css`
    (system font stack, no external assets), `base.html` with header,
    offline/SIMULATED status banner slot, content block and exact footer.
  - `engine/`, `simulator/`: empty packages, NumPy-only docstrings.
  - `data/`: empty valid JSON placeholders (indicators, limits, sources,
    guidance, environments).
  - `pytest.ini` + `tests/test_smoke.py` (200, running message, footer).
  - `.gitignore` for Python, Django and SQLite.

## In progress

- None.

## Known issues

- AGENTS.md still lacks the pasted domain spec (section 4); stage list
  above is provisional.
- No JavaScript yet (deliberate): HTMX/Plotly not bundled.
- Data JSON files are intentionally empty; no clinical values exist yet.

## Next

1. Paste the domain spec into AGENTS.md and reconcile the stage list.
2. Stage 1: define models, indicators and environments.
