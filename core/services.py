"""Data-loading layer between the Django app and the pure engine.

Loads JSON config (indicators, limits, environments, sources) and turns
stored Readings into engine inputs. Views call run_status_for() and never
do engine math themselves. Every threshold and equipment list here is a
PLACEHOLDER, not a clinical or operational value (AGENTS.md hard rule 6).
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from engine.baseline import build_baseline
from engine.status import Indicator, StatusResult, SEVERITY_GRAY, evaluate

from core.models import Reading

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Placeholder personal-baseline window in days; the engine itself also caps
# the history at 14 entries (engine.baseline.DEFAULT_WINDOW).
BASELINE_DAYS = 14


def _load_json(name: str):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def load_indicators() -> list[dict]:
    return _load_json("indicators.json")


def load_limits() -> dict:
    return _load_json("limits.json")


def load_environments() -> list[dict]:
    return _load_json("environments.json")


def load_sources() -> list[dict]:
    return _load_json("sources.json")


def get_environment(key: str | None) -> dict:
    """Return the environment entry for ``key``.

    Unknown or missing keys fall back to the first entry (station) so a bad
    query parameter can never crash the form.
    """
    environments = load_environments()
    for entry in environments:
        if entry["key"] == key:
            return entry
    return environments[0]


def _engine_indicator(config: dict) -> Indicator:
    """Map an indicators.json entry to the engine's Indicator dataclass.

    indicators.json uses ``label``; the engine expects ``name``.
    """
    return Indicator(
        key=config["key"],
        name=config.get("label", config["key"]),
        bad_direction=config["bad_direction"],
        mad_floor=config["mad_floor"],
        min_valid=config["min_valid"],
        max_valid=config["max_valid"],
    )


def run_status_for(crew_member, date) -> list[dict]:
    """Evaluate every indicator for ``crew_member`` on ``date``.

    Loads the personal-baseline window of history (the placeholder last 14
    days, one value per day, oldest to newest) plus the reading for ``date``
    itself, then calls engine.status.evaluate. Returns a list of entries in
    indicators.json order:

        {"key", "label", "unit", "value", "result", "is_simulated"}

    ``value`` is None and the result is gray with "No reading recorded
    today." when there is no reading for ``date``.
    """
    limits = load_limits()
    window_start = date - timedelta(days=BASELINE_DAYS)
    entries: list[dict] = []
    for config in load_indicators():
        key = config["key"]
        history = list(
            Reading.objects.filter(
                crew_member=crew_member,
                indicator_key=key,
                recorded_at__gte=window_start,
                recorded_at__lt=date,
            )
            .order_by("recorded_at")
            .values_list("value", flat=True)
        )
        today = Reading.objects.filter(
            crew_member=crew_member,
            indicator_key=key,
            recorded_at=date,
        ).first()
        if today is None:
            result = StatusResult(
                severity=SEVERITY_GRAY,
                personal_severity=None,
                limit_severity=None,
                z=None,
                baseline=build_baseline(history),
                reasons=["No reading recorded today."],
            )
            value = None
        else:
            value = today.value
            result = evaluate(_engine_indicator(config), history, value, limits)
        entries.append(
            {
                "key": key,
                "label": config["label"],
                "unit": config["unit"],
                "value": value,
                "result": result,
                "is_simulated": bool(today is not None and today.is_simulated),
            }
        )
    return entries
