"""Seeded scenario generator for SIMULATED demo data.

Pure Python plus NumPy. No Django imports. Output is SIMULATED and must be
labeled as such wherever it is shown (AGENTS.md hard rule 3).

Days are numbered 1 to 21 (no day 0). All trend sizes and blackout windows
below are PLACEHOLDERS for demo storytelling, not clinical values.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SCENARIOS: tuple[str, ...] = ("calm_week", "drift_day6", "fever_blackout", "isolation_mood")

# Placeholder scenario magnitudes.
DRIFT_START_DAY = 6          # resting_hr and sleep drift start here
RESTING_HR_PER_DAY = 1.5     # bpm added per day after DRIFT_START_DAY
SLEEP_PER_DAY = -0.25        # hours added per day after DRIFT_START_DAY
FEVER_DAYS = (9, 10)         # temperature spike days
FEVER_TEMP_C = 38.3          # placeholder fever value, not a clinical threshold
FEVER_BLACKOUT_DAYS = (8, 9, 10, 11)
MOOD_START_DAY = 7           # isolation_mood decline starts here
MOOD_PER_DAY = -0.15         # points per day after MOOD_START_DAY
EXERCISE_START_DAY = 7       # exercise decline starts here
EXERCISE_PER_DAY = -3.0      # minutes per day after EXERCISE_START_DAY


def load_indicators() -> list[dict]:
    """Load indicator definitions from data/indicators.json."""
    with (DATA_DIR / "indicators.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def _offset(scenario: str, key: str, day: int) -> float:
    """Return the trend offset added to an indicator's normal centre on a day."""
    if scenario == "drift_day6":
        if key == "resting_hr" and day >= DRIFT_START_DAY:
            return RESTING_HR_PER_DAY * (day - DRIFT_START_DAY + 1)
        if key == "sleep_hours" and day >= DRIFT_START_DAY:
            return SLEEP_PER_DAY * (day - DRIFT_START_DAY + 1)
    if scenario == "isolation_mood":
        if key == "mood" and day >= MOOD_START_DAY:
            return MOOD_PER_DAY * (day - MOOD_START_DAY + 1)
        if key == "exercise_min" and day >= EXERCISE_START_DAY:
            return EXERCISE_PER_DAY * (day - EXERCISE_START_DAY + 1)
    return 0.0


def _centre(scenario: str, indicator: dict, day: int) -> float:
    """Return the mean for one indicator on one day, before noise."""
    if scenario == "fever_blackout" and indicator["key"] == "temperature" and day in FEVER_DAYS:
        return FEVER_TEMP_C
    return float(indicator["normal_center"]) + _offset(scenario, indicator["key"], day)


def _in_blackout(scenario: str, day: int) -> bool:
    """Return True when the day falls inside the scenario's blackout window."""
    return scenario == "fever_blackout" and day in FEVER_BLACKOUT_DAYS


def generate(scenario: str, days: int = 21, seed: int = 42) -> list[dict]:
    """Generate seeded demo readings for one scenario.

    Returns one dict per (day, indicator), ordered by day then by the order
    in data/indicators.json. Each dict has keys: day, indicator_key, value,
    in_blackout. Days run from 1 to ``days``. Values are clamped to each
    indicator's min_valid and max_valid.

    Raises ValueError for an unknown scenario or days < 1.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario!r}. Choose from: {', '.join(SCENARIOS)}")
    if days < 1:
        raise ValueError("days must be at least 1")

    indicators = load_indicators()
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for day in range(1, days + 1):
        blackout = _in_blackout(scenario, day)
        for indicator in indicators:
            mean = _centre(scenario, indicator, day)
            noise = rng.normal(0.0, float(indicator["normal_wobble"]))
            value = float(np.clip(mean + noise, indicator["min_valid"], indicator["max_valid"]))
            rows.append(
                {
                    "day": day,
                    "indicator_key": indicator["key"],
                    "value": round(value, 2),
                    "in_blackout": blackout,
                }
            )
    return rows
