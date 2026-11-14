"""Trend chart figures built with the bundled Plotly.

Pure functions: take indicator config, readings, a personal baseline and
optional limits, and return a Plotly figure dict that is JSON-serialisable.
No Django imports, no network access, no re-implemented engine math -- the
baseline median/MAD come from engine.baseline and the spread scale factor
comes from engine.scoring. Every number is a placeholder, not a clinical
value (AGENTS.md hard rule 6).
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from engine.baseline import Baseline
from engine.scoring import _MAD_SCALE

# Number of recent days shown on a trend chart (placeholder).
TREND_DAYS = 14
# Band half-width in robust spreads around the baseline median (placeholder).
BAND_SPREADS = 2.0

# Limit line colours (Okabe-Ito derived, placeholder only).
_LIMIT_COLOUR = {
    "red": "#d55e00",
    "orange": "#e69f00",
    "yellow": "#b88600",
}


def _clean(value):
    """Coerce a value to a JSON-serialisable Python native.

    NumPy scalars become Python int/float; dates become ISO strings;
    non-finite floats become ``None`` so Plotly never receives ``NaN``.
    """
    import numpy as np

    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and not isfinite(value):
        return None
    return value


def trend_summary(indicator, readings, baseline):
    """Plain-English summary of the trend for the aria/text fallback."""
    label = indicator.get("label", indicator["key"])
    unit = indicator.get("unit", "")
    if not readings:
        return f"No readings for {label} in the last {TREND_DAYS} days."
    first_val = readings[0][1]
    last_val = readings[-1][1]
    direction = "rose" if last_val > first_val else ("fell" if last_val < first_val else "stayed flat")
    parts = [f"Last {TREND_DAYS} days: {label} {direction} from {first_val} to {last_val} {unit}."]
    if baseline is not None and baseline.enough_data and baseline.median is not None:
        parts.append(f" Your baseline median is {baseline.median:.1f} {unit}.")
    return " ".join(parts)


def build_trend_figure(indicator, readings, baseline, limits_entry=None):
    """Build a Plotly trend figure as a JSON-serialisable dict.

    Args:
        indicator: dict with key, label, unit, bad_direction, mad_floor, ...
        readings: list of ``(date, value)`` oldest to newest for the window.
        baseline: :class:`~engine.baseline.Baseline` for the indicator.
        limits_entry: dict or None from ``data/limits.json``.

    Returns:
        A Plotly figure dict (``data`` + ``layout``) safe for
        ``json_script``.
    """
    label = indicator.get("label", indicator["key"])
    unit = indicator.get("unit", "")
    mad_floor = indicator.get("mad_floor", 0.0)

    dates = [_clean(d) for d, _ in readings]
    values = [_clean(v) for _, v in readings]

    traces = []

    # Readings trace: line with markers.
    traces.append(
        {
            "x": dates,
            "y": values,
            "mode": "lines+markers",
            "name": label,
            "line": {"width": 2},
            "marker": {"size": 6},
        }
    )

    # Personal baseline band: median +/- BAND_SPREADS * spread.
    spread = None
    median = None
    if (
        baseline is not None
        and baseline.enough_data
        and baseline.mad is not None
        and baseline.median is not None
    ):
        spread = max(mad_floor, _MAD_SCALE * baseline.mad)
        median = baseline.median
        upper = [median + BAND_SPREADS * spread] * len(dates)
        lower = [median - BAND_SPREADS * spread] * len(dates)
        # Lower bound first (no fill), then upper bound fills between them.
        traces.append(
            {
                "x": dates,
                "y": lower,
                "mode": "lines",
                "line": {"width": 0},
                "showlegend": False,
                "hoverinfo": "skip",
            }
        )
        traces.append(
            {
                "x": dates,
                "y": upper,
                "mode": "lines",
                "line": {"width": 0},
                "fill": "tonexty",
                "fillcolor": "rgba(128, 128, 128, 0.15)",
                "name": f"Typical range (x{BAND_SPREADS} spreads)",
                "showlegend": True,
            }
        )

    # Forecast placeholder reserved for Stage 7.
    tail_dates = dates[-2:] if len(dates) >= 2 else dates
    tail_values = values[-2:] if len(values) >= 2 else values
    traces.append(
        {
            "x": tail_dates,
            "y": tail_values,
            "mode": "lines",
            "line": {"dash": "dot"},
            "name": "Forecast (Stage 7)",
            "visible": "legendonly",
        }
    )

    layout = {
        "title": {"text": f"{label} trend", "x": 0.5},
        "xaxis": {"title": "Date", "type": "category"},
        "yaxis": {"title": unit},
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.2},
        "margin": {"l": 60, "r": 20, "t": 60, "b": 80},
    }

    # Horizontal dotted limit lines (only when a sourced limit exists).
    shapes = []
    annotations = []
    if isinstance(limits_entry, dict):
        for sev, thr_key in (("red", "red"), ("orange", "orange"), ("yellow", "yellow")):
            threshold = limits_entry.get(thr_key)
            if not isinstance(threshold, (int, float)):
                continue
            shapes.append(
                {
                    "type": "line",
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "y0": threshold,
                    "y1": threshold,
                    "line": {"dash": "dot", "width": 1, "color": _LIMIT_COLOUR[sev]},
                }
            )
            annotations.append(
                {
                    "x": 1,
                    "xref": "paper",
                    "xanchor": "right",
                    "y": threshold,
                    "yref": "y",
                    "text": f"{sev} limit ({threshold})",
                    "showarrow": False,
                    "font": {"size": 10, "color": _LIMIT_COLOUR[sev]},
                    "bgcolor": "rgba(255, 255, 255, 0.7)",
                }
            )
    if shapes:
        layout["shapes"] = shapes
    if annotations:
        layout.setdefault("annotations", []).extend(annotations)

    return {"data": traces, "layout": layout}
