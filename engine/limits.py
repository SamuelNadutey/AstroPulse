"""Absolute indicator limits (placeholders only).

Pure Python with NumPy only; no Django imports. ``check_limits`` takes an
already-parsed limits mapping; loading ``data/limits.json`` happens outside
the engine. Every threshold here is a placeholder, not a clinical value
(AGENTS.md hard rule 6).
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite, isnan


def check_limits(indicator_key: str, value, limits: Mapping) -> str | None:
    """Return the worst severity breached by ``value`` for ``indicator_key``.

    ``limits`` uses the structure
    ``{key: {"yellow": float, "orange": float, "red": float, "direction": "high"|"low"}}``.
    All thresholds are placeholders.

    Args:
        indicator_key: The indicator key (e.g. ``"resting_hr"``).
        value: The reading to check.
        limits: Mapping of indicator key to limit definitions.

    Returns:
        ``"red"``, ``"orange"`` or ``"yellow"`` for the most severe breached
        threshold, or ``None`` when the value is within all limits, no limit
        is defined for ``indicator_key``, or ``value`` is missing/non-finite.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(v):
        return None

    if not isinstance(limits, Mapping):
        return None
    entry = limits.get(indicator_key)
    if not isinstance(entry, Mapping):
        return None

    direction = entry.get("direction")
    if direction not in ("high", "low"):
        return None

    # Thresholds are placeholders, not clinical values (AGENTS.md hard rule 6).
    # "high": larger values are worse, so yellow < orange < red.
    # "low": smaller values are worse, so yellow > orange > red.
    for severity, threshold in (
        ("red", entry.get("red")),
        ("orange", entry.get("orange")),
        ("yellow", entry.get("yellow")),
    ):
        if not isinstance(threshold, (int, float)) or isnan(threshold):
            continue
        if direction == "high" and v >= threshold:
            return severity
        if direction == "low" and v <= threshold:
            return severity
    return None
