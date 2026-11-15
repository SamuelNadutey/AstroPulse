# AstroPulse

AstroPulse is an offline mission-health dashboard prototype. It supports local check-ins, trends, a 3D interactive body map, and locally queued relay items. It is decision support, not a diagnosis.

## Start a demo

On Windows, from the project folder run:

```powershell
.\run-demo.ps1
```

The first run creates a local Python environment, installs the requirements, migrates the SQLite database, and loads a 21-day `drift_day6` sample if demo data is not already present. Then open <http://127.0.0.1:8000/>. Later runs keep the existing demo database. Stop the server with Ctrl+C.

To load a different sample scenario and replace the existing demo rows, run:

```powershell
.\run-demo.ps1 -Scenario calm_week -ResetDemo
```

Available scenarios are `calm_week`, `drift_day6`, `fever_blackout`, and `isolation_mood`. `-ResetDemo` replaces only the SIMULATED demo crew's readings and check-ins.

Every generated sample reading is marked **SIMULATED**. The SQLite database is local and is not committed to the repository. For an empty database without demo readings, the dashboard shows gray **Not enough data** states until a check-in is recorded.
