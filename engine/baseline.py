"""Personal-baseline computation (median / MAD).

Pure Python with NumPy only; no Django imports. Every threshold in this
module is a placeholder, not a clinical value (AGENTS.md hard rule 6).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Placeholder: how many recent readings form the personal window.
DEFAULT_WINDOW = 14
# Placeholder: minimum valid readings before a personal baseline is used.
DEFAULT_MIN_POINTS = 5


@dataclass(frozen=True)
class Baseline:
    """Summary of an indicator's recent personal baseline.

    Attributes:
        median: Median of the most recent valid readings.
        mad: Median absolute deviation of those readings.
        n: Number of valid readings actually used.
        enough_data: ``True`` when ``n >= min_points``.
    """

    median: float
    mad: float
    n: int
    enough_data: bool


def _as_finite(values, window: int) -> np.ndarray:
    """Return finite floats from the most recent ``window`` entries.

    ``None``, non-numeric values, ``NaN`` and infinities are skipped. A
    string or bytes object is not a sequence of readings (a date string
    must not be split into digit readings). ``window <= 0`` yields nothing;
    ``list(...)[-0:]`` would otherwise return the whole sequence.
    """
    if values is None or isinstance(values, (str, bytes, bytearray)):
        return np.asarray([], dtype=float)
    if window <= 0:
        return np.asarray([], dtype=float)
    try:
        selected = list(values)[-window:]
    except TypeError:
        return np.asarray([], dtype=float)
    cleaned: list[float] = []
    for item in selected:
        try:
            number = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            cleaned.append(number)
    return np.asarray(cleaned, dtype=float)


def _median(arr: np.ndarray) -> float:
    """Median that stays finite for huge finite inputs.

    Even-count medians average the two central values. NumPy's ``(a + b) / 2``
    overflows to infinity near the float range; ``a/2 + b/2`` is the same
    median and stays finite. This is numerical stability, not a threshold.
    """
    ordered = np.sort(arr)
    mid = int(ordered.size) // 2
    if ordered.size % 2 == 1:
        return float(ordered[mid])
    return float(ordered[mid - 1]) / 2.0 + float(ordered[mid]) / 2.0


def build_baseline(
    values,
    window: int = DEFAULT_WINDOW,
    min_points: int = DEFAULT_MIN_POINTS,
) -> Baseline:
    """Build a baseline from the most recent ``window`` values.

    Only the most recent ``window`` entries are considered; ``None``,
    non-numeric, ``NaN`` and infinite entries are ignored. If fewer than
    ``min_points`` valid readings remain, or the median cannot be represented
    as a finite number, ``enough_data`` is ``False`` and ``median``/``mad``
    are ``NaN``.

    Args:
        values: Iterable of numeric readings (may contain ``None``/``NaN``).
        window: Number of most-recent readings to use. Placeholder (default 14).
        min_points: Minimum valid readings required. Placeholder (default 5).

    Returns:
        A :class:`Baseline`.
    """
    arr = _as_finite(values, window)
    n = int(arr.size)
    if n < min_points or n == 0:
        return Baseline(
            median=float("nan"),
            mad=float("nan"),
            n=n,
            enough_data=False,
        )
    median = _median(arr)
    mad = _median(np.abs(arr - median))
    if not math.isfinite(median) or not math.isfinite(mad):
        return Baseline(
            median=float("nan"),
            mad=float("nan"),
            n=n,
            enough_data=False,
        )
    return Baseline(median=median, mad=mad, n=n, enough_data=True)
