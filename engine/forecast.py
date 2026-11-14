"""Short-range linear forecast with an uncertainty band.

Pure Python with NumPy only; no Django imports. The band is a ROUGH indication
of spread, not a statistical guarantee: it is one residual standard deviation
scaled by the usual prediction-interval leverage term, which widens as the
projection moves away from the fitted data. Window and horizon limits are
PLACEHOLDERS, not clinical values (AGENTS.md hard rule 6).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Placeholder: most recent points used for the linear fit.
DEFAULT_WINDOW = 10
# Placeholder: projected days ahead (3 to 7 are allowed).
DEFAULT_HORIZON = 5
MIN_POINTS = 5
MIN_HORIZON = 3
MAX_HORIZON = 7


@dataclass(frozen=True)
class Forecast:
    """Projected values for the next ``days`` days with a rough band.

    Attributes:
        days: Days ahead, 1-based (``1`` is the day after the last reading).
        values: Projected values.
        lower: Lower band edge per day.
        upper: Upper band edge per day.
    """

    days: tuple[int, ...]
    values: tuple[float, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]


def _recent_finite(values, window: int) -> list[float]:
    try:
        selected = list(values)[-window:]
    except TypeError:
        return []
    cleaned = []
    for raw in selected:
        try:
            number = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            cleaned.append(number)
    return cleaned


def forecast(
    history_values,
    horizon: int = DEFAULT_HORIZON,
    window: int = DEFAULT_WINDOW,
) -> Forecast | None:
    """Fit a line to the last ``window`` readings and project ``horizon`` days.

    The band is one residual standard deviation times
    ``sqrt(1 + 1/n + (x - x_mean)^2 / Sxx)``, so it is narrow near the data and
    wider further out. This is a rough indication, not a statistical guarantee.

    Args:
        history_values: Readings, oldest to newest, one per day.
        horizon: Days to project, 3 to 7.
        window: Most recent points used for the fit.

    Returns:
        A :class:`Forecast`, or ``None`` when fewer than 5 finite points remain.

    Raises:
        ValueError: If ``horizon`` is outside 3 to 7.
    """
    if not MIN_HORIZON <= horizon <= MAX_HORIZON:
        raise ValueError(f"horizon must be between {MIN_HORIZON} and {MAX_HORIZON}")
    ys = np.asarray(_recent_finite(history_values, window), dtype=float)
    n = int(ys.size)
    if n < MIN_POINTS:
        return None

    xs = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    residuals = ys - (slope * xs + intercept)
    residual_sd = math.sqrt(float(np.sum(residuals**2)) / (n - 2))

    x_mean = float(xs.mean())
    sxx = float(np.sum((xs - x_mean) ** 2))
    days, values, lower, upper = [], [], [], []
    for step in range(1, horizon + 1):
        x_future = (n - 1) + step
        projected = slope * x_future + intercept
        leverage = 1.0 + 1.0 / n + (x_future - x_mean) ** 2 / sxx
        half_width = residual_sd * math.sqrt(leverage)
        days.append(step)
        values.append(float(projected))
        lower.append(float(projected - half_width))
        upper.append(float(projected + half_width))
    return Forecast(tuple(days), tuple(values), tuple(lower), tuple(upper))
