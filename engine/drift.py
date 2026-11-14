"""Slow-drift detection: one-sided CUSUM on robust z-scores.

Pure Python with NumPy only; no Django imports. A single noisy reading adds
little to the CUSUM, while a run of moderately unfavorable readings adds up
and crosses the alarm threshold.

PLACEHOLDERS (AGENTS.md hard rule 6): ``DEFAULT_K``, ``DEFAULT_H``, ``Z_CAP``
and ``REFERENCE_POINTS`` were tuned on synthetic data so calm-week noise does
not raise drift across 20 seeds. They are not clinical values. ``DEFAULT_K``
and ``DEFAULT_H`` deliberately trade detection latency for a low false-alarm
rate: a gradual drift is flagged roughly a week after it starts rather than
within a day or two.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from engine.baseline import Baseline, build_baseline
from engine.scoring import robust_z

# Placeholder: allowance per reading, in robust-z units. Deviations smaller
# than k spreads add nothing to the sum. Tuned so calm-week noise across 20
# seeds never raises drift, while still flagging a gradual drift a day or two
# before a single reading turns extreme (see the drift_day6 acceptance test).
DEFAULT_K = 1.0
# Placeholder: alarm threshold on the CUSUM sum, in robust-z units.
DEFAULT_H = 7.0
# Placeholder: caps one reading's contribution so a single outlier cannot
# raise drift on its own (3.5 matches the personal red boundary).
Z_CAP = 3.5
# Placeholder: earliest valid readings used as the pre-drift reference.
REFERENCE_POINTS = 5


@dataclass(frozen=True)
class DriftResult:
    """Outcome of a drift check.

    Attributes:
        drifting: ``True`` when the CUSUM is above ``h`` at the latest reading.
        days_in_drift: Consecutive readings since the CUSUM last sat at zero
            (0 when it is at zero now).
        started_on_index: Index (within the checked series) where that run
            began, or ``None``.
        reason: Plain-English reason when drifting, else ``None``.
    """

    drifting: bool
    days_in_drift: int
    started_on_index: int | None
    reason: str | None


def _no_drift() -> DriftResult:
    return DriftResult(False, 0, None, None)


def _signed_bad_z(value: float, baseline: Baseline, bad_direction: str, mad_floor: float):
    """Unclamped robust z, positive when the deviation is unfavorable."""
    z = robust_z(value, baseline, mad_floor)
    if not math.isfinite(z):
        return None
    return z if bad_direction == "high" else -z


def detect_drift(
    history_values,
    baseline: Baseline,
    bad_direction: str,
    mad_floor: float,
    k: float = DEFAULT_K,
    h: float = DEFAULT_H,
) -> DriftResult:
    """Run a one-sided CUSUM over readings scored against a reference baseline.

    ``history_values`` should be the readings AFTER the reference period, oldest
    to newest. Each reading's unfavorable z is capped at ``Z_CAP`` and the sum
    ``S = max(0, S + z - k)`` is updated. Drift means ``S > h`` at the latest
    reading.

    Args:
        history_values: Numeric readings, oldest to newest.
        baseline: Reference :class:`~engine.baseline.Baseline` (pre-drift).
        bad_direction: ``"high"`` or ``"low"``.
        mad_floor: Placeholder floor on the scaled MAD.
        k: Placeholder per-reading allowance (robust-z units).
        h: Placeholder alarm threshold (robust-z units).

    Raises:
        ValueError: If ``bad_direction`` is not ``"high"`` or ``"low"``.
    """
    if bad_direction not in ("high", "low"):
        raise ValueError(f"bad_direction must be 'high' or 'low', got {bad_direction!r}")
    if not baseline.enough_data:
        return _no_drift()

    cusum = 0.0
    start = None
    count = 0
    for index, raw in enumerate(history_values):
        count = index + 1
        z = _signed_bad_z(float(raw), baseline, bad_direction, mad_floor)
        if z is None:
            continue
        cusum = max(0.0, cusum + min(z, Z_CAP) - k)
        if cusum == 0.0:
            start = None
        elif start is None:
            start = index

    if cusum <= 0.0 or start is None:
        return _no_drift()
    days = count - start
    drifting = cusum > h
    reason = None
    if drifting:
        direction = "above" if bad_direction == "high" else "below"
        reason = f"{days} days {direction} your usual range."
    return DriftResult(drifting, days, start, reason)


def detect_series_drift(
    series,
    bad_direction: str,
    mad_floor: float,
    reference_points: int = REFERENCE_POINTS,
    k: float = DEFAULT_K,
    h: float = DEFAULT_H,
) -> DriftResult:
    """Split a series into a reference period and a test period, then detect.

    The first ``reference_points`` finite values form the reference baseline;
    the rest are scored by :func:`detect_drift`. Non-finite entries are skipped.
    """
    values = []
    for raw in series:
        try:
            number = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            values.append(number)
    if len(values) <= reference_points:
        return _no_drift()
    reference = values[:reference_points]
    baseline = build_baseline(
        reference, window=reference_points, min_points=reference_points
    )
    return detect_drift(
        values[reference_points:], baseline, bad_direction, mad_floor, k=k, h=h
    )
