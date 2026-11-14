"""Robust z-scoring against a personal baseline.

Pure Python with NumPy only; no Django imports. The MAD scale factor and the
``mad_floor`` are placeholders, not clinical values (AGENTS.md hard rule 6).
"""
from __future__ import annotations

import math

from engine.baseline import Baseline

# Placeholder: converts MAD to a robust estimate of the standard deviation
# for normally distributed data. Not a clinical value.
_MAD_SCALE = 1.4826


def robust_z(value: float, baseline: Baseline, mad_floor: float) -> float:
    """Return the signed robust z-score of ``value`` relative to ``baseline``.

    The spread is ``max(mad_floor, 1.4826 * baseline.mad)`` so a perfectly
    flat history still yields a finite denominator when ``mad_floor`` is
    positive. A non-positive or non-finite spread does not divide by zero:
    an unchanged value returns ``0.0`` and any other value returns ``NaN``.

    Args:
        value: The reading to score.
        baseline: A :class:`~engine.baseline.Baseline`.
        mad_floor: Placeholder floor on the scaled MAD, in the indicator's
            units. Must be positive to score a real deviation.

    Returns:
        ``(value - baseline.median) / spread``, or ``0.0`` / ``NaN`` when
        the spread is not a positive finite number.
    """
    scaled = _MAD_SCALE * baseline.mad
    if math.isfinite(mad_floor) and math.isfinite(scaled):
        spread = max(mad_floor, scaled)
    else:
        spread = float("nan")
    # A flat history with a missing floor must not raise ZeroDivisionError,
    # and a non-finite spread must not be reported as a confident z of 0.
    if not math.isfinite(spread) or spread <= 0:
        if (
            math.isfinite(value)
            and math.isfinite(baseline.median)
            and value == baseline.median
        ):
            return 0.0
        return float("nan")
    return (value - baseline.median) / spread


def signed_bad_z(
    value: float,
    baseline: Baseline,
    bad_direction: str,
    mad_floor: float,
) -> float:
    """Return only the unfavorable deviation from baseline (never negative).

    For ``bad_direction="high"`` the unfavorable deviation is ``value - median``;
    for ``bad_direction="low"`` it is ``median - value``. A deviation in the
    favorable direction is clamped to zero.

    Args:
        value: The reading to score.
        baseline: A :class:`~engine.baseline.Baseline`.
        bad_direction: ``"high"`` (high values are bad) or ``"low"``.
        mad_floor: Placeholder floor on the scaled MAD.

    Returns:
        A non-negative robust z-score measuring only the unfavorable deviation.

    Raises:
        ValueError: If ``bad_direction`` is not ``"high"`` or ``"low"``.
    """
    if bad_direction not in ("high", "low"):
        raise ValueError(
            f"bad_direction must be 'high' or 'low', got {bad_direction!r}"
        )
    z = robust_z(value, baseline, mad_floor)
    # max(0, nan) is 0, which would hide a failed score as "on baseline".
    if not math.isfinite(z):
        return z
    if bad_direction == "high":
        return max(0.0, z)
    return max(0.0, -z)
