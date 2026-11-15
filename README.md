# AstroPulse

AstroPulse is an offline, local-first mission-health dashboard prototype for astronaut self-assessment. It brings check-ins, personal trends, a 3D interactive body map, blackout handling, and a local relay queue into one Django web app.

> **Decision support, not a diagnosis.** AstroPulse is a research and demonstration prototype, not a medical device. Limits, normal ranges, and simulator values are placeholders, not clinical values. Source verification and safety review are still in progress; see [docs/PROGRESS.md](docs/PROGRESS.md) and [docs/GUIDANCE_REVIEW.md](docs/GUIDANCE_REVIEW.md).

## Quick start: Windows demo

Clone the repository, open PowerShell in the `AstroPulse` folder, and run:

```powershell
.\run-demo.ps1
```

The launcher creates a local `.venv` if needed, installs Python dependencies when they are missing, applies database migrations, seeds the default `drift_day6` scenario if demo data is absent, and starts Django. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Stop the server with **Ctrl+C**.

The demo contains 21 days of generated data for six indicators. All demo records are labeled **SIMULATED**. The launcher preserves an existing demo database. To replace its demo readings with another scenario:

```powershell
.\run-demo.ps1 -Scenario calm_week -ResetDemo
```

Available scenarios:

| Scenario | What it demonstrates |
| --- | --- |
| `calm_week` | Steady simulated readings |
| `drift_day6` | Gradual resting heart rate and sleep changes |
| `fever_blackout` | A temperature spike during a communication blackout |
| `isolation_mood` | Changes in mood and exercise |

If the launcher reports that port 8000 is already in use, stop the other AstroPulse server with **Ctrl+C** before starting this one. You can choose another port with `-Address 127.0.0.1:8001`.

## Manual setup

Use this path on macOS/Linux, or when you want to run Django commands yourself.

### Requirements

- Python 3.11 or later
- pip
- A browser with JavaScript and WebGL for the 3D map (the interactive SVG map remains available without WebGL)

### Install and start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --scenario drift_day6
python manage.py runserver
```

On Windows, create the environment with `py -3 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`. If PowerShell blocks activation, use the `run-demo.ps1` launcher or invoke `.venv\Scripts\python.exe` directly.

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Django's development server is intended for local use only.

### Change or reload the demo data

The seed command requires a scenario name:

```bash
python manage.py seed_demo --scenario fever_blackout --reset
```

`--reset` replaces only the `Demo crew (SIMULATED)` member's readings and check-ins. Without it, the command stops if demo data already exists. Refresh the page after seeding. If you start the app without seed data, the Today page shows gray **Not enough data** states; complete a check-in to begin recording local readings.

## Using the app

- **Today** (`/` or `/status/`): overall status, current readings, mission context, and the interactive 3D body map. Drag to orbit, scroll or pinch to zoom, select a marker or region button for details, and use **Reset view** to restore the camera. If WebGL or the model is unavailable, the interactive SVG map is used.
- **Check-in** (`/checkin/`): record a local daily check-in. The fields adjust to the selected environment.
- **Trends** (`/trend/<indicator>/`): inspect history, baseline, drift, and forecast for an indicator. Forecasts are uncertain projections.
- **Relay** (`/relay/`): review and resolve items queued during a blackout, or explicitly export a local summary.
- **Progress** (`/progress/`): review check-in completion history. Progress rewards participation, not health outcomes.
- **Communication blackout**: toggle blackout mode from the sidebar. Flagged items are queued locally; the app does not transmit them.

The six configured indicators are resting heart rate, sleep, body temperature, mood and stress, exercise, and blood oxygen. Indicator definitions and environment profiles are in `data/`.

## How the project is organized

```text
config/                     Django settings and URL configuration
core/                       Web app: models, forms, views, services, templates, static files
  management/commands/      seed_demo and check_guidance commands
  migrations/               SQLite schema migrations
  static/core/               Local CSS, JavaScript, and body model
  static/vendor/             Bundled HTMX, Plotly, and 3D dependencies
  templates/core/            Server-rendered Django pages and partials
data/                       Indicator, environment, limit, guidance, and source JSON
docs/                       Build plan, progress notes, indicator catalog, review notes
engine/                     Pure-Python scoring, status, drift, and forecast logic
simulator/                  Deterministic synthetic scenario generator
tests/                      Django and engine regression tests
ui-reference/               Reference-only Figma implementation and design audit
```

The runtime is Django templates with local JavaScript enhancements. The React files in `ui-reference/` are design references; the app serves the Django implementation. The 3D model and vendor libraries are stored in the repository. Templates and static assets do not depend on a CDN or web fonts.

## Data and privacy

- SQLite is stored as `db.sqlite3` in the project folder. It is intentionally excluded from Git, so cloning the repository does **not** copy anyone's local readings or database.
- Demo data is generated on the local machine by `seed_demo` and is explicitly marked **SIMULATED**.
- Check-ins and readings remain local. Relay export only happens when a user requests it.
- The UI's offline/local status describes this prototype's local storage and lack of automatic transmission; it is not a claim that a device has no network connection.

## Development commands

Run these from the project root with the virtual environment active:

```bash
python manage.py runserver                 # local development server
python manage.py migrate                   # apply schema migrations
python manage.py seed_demo --scenario calm_week
python manage.py seed_demo --scenario drift_day6 --reset
python manage.py check                     # Django configuration check
python manage.py check_guidance            # validate guidance/source references
pytest                                      # test suite
```

`check_guidance` warns about sources awaiting verification. `--strict` also treats unverified sources as errors; some source and safety reviews remain open.

## Scoring and safety constraints

The engine uses a personal history window and robust statistics, with severity based on the worse of personal-pattern and absolute-limit checks. It also includes gradual-drift detection and short-range forecasting. The minimum history, score boundaries, limit values, simulator centers, and forecast intervals are implementation placeholders. They must not be interpreted as medical thresholds or used for operational decisions.

Important project rules are recorded in [AGENTS.md](AGENTS.md): show severity with icon, text, and color; label every demo value as simulated; cite guidance from `data/sources.json`; keep data local; and do not reward health outcomes. Read [docs/PROGRESS.md](docs/PROGRESS.md) for completed work, known limitations, and outstanding reviews.

The checked-in Django settings use `DEBUG=True`, a development-only secret, and localhost hosts. Do not expose the development server to a network or treat this configuration as production-ready.
