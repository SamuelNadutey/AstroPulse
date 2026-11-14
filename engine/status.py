"""Personal-baseline status evaluation.

Pure Python with NumPy only; no Django imports. Every threshold, boundary and
floor in this module is a placeholder, not a clinical value (AGENTS.md hard
rule 6).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite, isinf, isnan

from engine.baseline import DEFAULT_WINDOW, Baseline, build_baseline
from engine.limits import check_limits
from engine.scoring import signed_bad_z

# Severity levels, least to most severe. The engine only produces the textual
# level; the UI must render icon + text + color (AGENTS.md hard rule 5).
SEVERITY_GRAY = "gray"
SEVERITY_GREEN = "green"
SEVERITY_YELLOW = "yellow"
SEVERITY_ORANGE = "orange"
SEVERITY_RED = "red"

_SEVERITY_ORDER = (
    SEVERITY_GRAY,
    SEVERITY_GREEN,
    SEVERITY_YELLOW,
    SEVERITY_ORANGE,
    SEVERITY_RED,
)

# Placeholder z-score boundaries for personal severity (not clinical values).
_Z_YELLOW = 1.5
_Z_ORANGE = 2.5
_Z_RED = 3.5

_LIMIT_LABEL = {
    SEVERITY_YELLOW: "cautionary",
    SEVERITY_ORANGE: "warning",
    SEVERITY_RED: "critical",
}


@dataclass(frozen=True)
class Indicator:
    """Metadata for a single indicator (all numeric fields are placeholders).

    Attributes:
        key: Stable identifier (e.g. ``"resting_hr"``).
        name: Human-readable name used in reason strings.
        bad_direction: ``"high"`` (high values are bad) or ``"low"``.
        mad_floor: Placeholder floor on the scaled MAD, in indicator units.
        min_valid: Placeholder lower bound; readings below are ignored.
        max_valid: Placeholder upper bound; readings above are ignored.
    """

    key: str
    name: str
    bad_direction: str
    mad_floor: float
    min_valid: float
    max_valid: float


@dataclass(frozen=True)
class StatusResult:
    """Result of evaluating a new reading against a personal baseline.

    Attributes:
        severity: Final severity, the worse of ``personal_severity`` and
            ``limit_severity`` (``gray`` when neither applies).
        personal_severity: Severity from the robust z-score, or ``None`` when
            there is not enough history.
        limit_severity: Severity from absolute limits, or ``None``.
        z: The unfavorable robust z-score, or ``None`` when not enough history.
        baseline: The :class:`~engine.baseline.Baseline` used (its
            ``enough_data`` flag says whether a personal severity is valid).
        reasons: Plain-English explanation strings.
    """

    severity: str
    personal_severity: str | None
    limit_severity: str | None
    z: float | None
    baseline: Baseline
    reasons: list[str] = field(default_factory=list)


def _rank(severity: str | None) -> int:
    return _SEVERITY_ORDER.index(severity) if severity in _SEVERITY_ORDER else -1


def _worse(a: str | None, b: str | None) -> str | None:
    """Return the more severe of two severities (``None`` counts as least)."""
    return a if _rank(a) >= _rank(b) else b


def _personal_severity(z: float) -> str:
    """Map a non-negative z to a severity (thresholds are placeholders)."""
    if z < _Z_YELLOW:
        return SEVERITY_GREEN
    if z < _Z_ORANGE:
        return SEVERITY_YELLOW
    if z < _Z_RED:
        return SEVERITY_ORANGE
    return SEVERITY_RED


def _format_z(z: float) -> str:
    """Format a z-score without rounding across a placeholder boundary.

    One decimal is the usual text, but ``2.46`` must not display as ``2.5``
    while the severity is still the band below that boundary.
    """
    text = f"{z:.1f}"
    rounded = float(text)
    for boundary in (_Z_YELLOW, _Z_ORANGE, _Z_RED):
        if z < boundary <= rounded or rounded < boundary <= z:
            return f"{z:.2f}"
    return text


def _to_valid(value, indicator: Indicator) -> float | None:
    """Return ``value`` as a float if valid, else ``None``.

    A value is valid when it is a finite number within the indicator's
    placeholder ``min_valid``/``max_valid`` range.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(v):
        return None
    if v < indicator.min_valid or v > indicator.max_valid:
        return None
    return v


def _limit_reason(indicator_key: str, severity: str, limits: Mapping) -> str:
    """Build a plain-English reason for a breached absolute limit."""
    entry = limits.get(indicator_key) if isinstance(limits, Mapping) else None
    direction = entry.get("direction") if isinstance(entry, Mapping) else "high"
    threshold = entry.get(severity) if isinstance(entry, Mapping) else None
    relation = "Above" if direction == "high" else "Below"
    label = _LIMIT_LABEL.get(severity, "limit")
    return f"{relation} the {label} limit of {threshold} (see source)."


def evaluate(
    indicator: Indicator,
    history_values,
    new_value,
    limits: Mapping,
) -> StatusResult:
    """Evaluate ``new_value`` for ``indicator`` against personal + absolute limits.

    Only the most recent placeholder window of readings is used. Invalid
    historical readings (``None``, ``NaN``, non-numeric, or outside
    ``min_valid``/``max_valid``) inside that window are ignored and noted.
    ``None``, a bare number, or a string/bytes history is not a sequence of
    readings and does not crash. An invalid new reading is ignored and yields
    a ``gray`` result. With enough history the personal severity is derived
    from the unfavorable robust z-score; the absolute limit severity is always
    checked independently. The final severity is the worse of the two
    (``gray`` when neither applies).

    Args:
        indicator: :class:`Indicator` metadata for the reading.
        history_values: Iterable of prior readings, oldest to newest.
        new_value: The reading to evaluate.
        limits: Mapping of indicator key to limit definitions (see
            :func:`engine.limits.check_limits`).

    Returns:
        A :class:`StatusResult`.
    """
    reasons: list[str] = []
    ignored_history = 0
    clean_history: list[float] = []

    if history_values is None:
        history_values = ()
    elif isinstance(history_values, (str, bytes, bytearray)):
        reasons.append("Ignored history (not a sequence of readings).")
        history_values = ()
    try:
        # Placeholder window: invalid entries still occupy a slot, matching
        # build_baseline. Older readings outside the window are not used.
        recent = list(history_values)[-DEFAULT_WINDOW:]
    except TypeError:
        reasons.append("Ignored history (not a sequence of readings).")
        recent = []

    for raw in recent:
        v = _to_valid(raw, indicator)
        if v is None:
            ignored_history += 1
        else:
            clean_history.append(v)

    if ignored_history:
        reasons.append(
            f"Ignored {ignored_history} historical reading(s) (missing, "
            f"non-numeric, or outside {indicator.min_valid} to {indicator.max_valid})."
        )

    baseline = build_baseline(clean_history)

    value = _to_valid(new_value, indicator)
    if value is None:
        reasons.append(
            f"Ignored the new reading {new_value!r} (missing, non-numeric, or "
            f"outside {indicator.min_valid} to {indicator.max_valid})."
        )
        return StatusResult(
            severity=SEVERITY_GRAY,
            personal_severity=None,
            limit_severity=None,
            z=None,
            baseline=baseline,
            reasons=reasons,
        )

    z: float | None = None
    personal_severity: str | None = None
    if baseline.enough_data:
        z = signed_bad_z(value, baseline, indicator.bad_direction, indicator.mad_floor)
        if isnan(z):
            reasons.append(
                f"{indicator.name} could not be compared with your usual range."
            )
            z = None
        elif isinf(z):
            # Overflowed deviation is worse than every placeholder boundary.
            personal_severity = SEVERITY_RED
            reasons.append(f"{indicator.name} is far outside your usual range.")
        else:
            personal_severity = _personal_severity(z)
            if z >= _Z_YELLOW:
                relation = "above" if indicator.bad_direction == "high" else "below"
                reasons.append(
                    f"{indicator.name} is {_format_z(z)} spreads {relation} your usual range."
                )
    elif baseline.n >= 5:
        reasons.append(
            f"{indicator.name} history could not be summarized (readings are too extreme)."
        )
    else:
        reasons.append(
            "Not enough history yet for your personal baseline (need 5 readings)."
        )

    limit_severity = check_limits(indicator.key, value, limits)
    if limit_severity is not None:
        reasons.append(_limit_reason(indicator.key, limit_severity, limits))

    severity = _worse(personal_severity, limit_severity) or SEVERITY_GRAY
    return StatusResult(
        severity=severity,
        personal_severity=personal_severity,
        limit_severity=limit_severity,
        z=z,
        baseline=baseline,
        reasons=reasons,
    )
