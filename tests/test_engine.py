"""Tests for the personal-baseline status engine (pure Python, NumPy only)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import warnings

from engine.baseline import DEFAULT_WINDOW, build_baseline
from engine.limits import check_limits
from engine.scoring import signed_bad_z
from engine.status import (
    SEVERITY_GRAY,
    SEVERITY_GREEN,
    SEVERITY_YELLOW,
    SEVERITY_ORANGE,
    SEVERITY_RED,
    Indicator,
    evaluate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_json(rel_path: str):
    with open(REPO_ROOT / rel_path, encoding="utf-8") as fh:
        return json.load(fh)


def resting_hr_indicator(**overrides) -> Indicator:
    defaults = dict(
        key="resting_hr",
        name="Resting heart rate",
        bad_direction="high",
        mad_floor=3.0,
        min_valid=30,
        max_valid=220,
    )
    defaults.update(overrides)
    return Indicator(**defaults)


def limits(entry):
    return {"resting_hr": entry}


# --- baseline / personal severity ---


def test_gray_when_fewer_than_5_points():
    ind = resting_hr_indicator()
    result = evaluate(ind, [60, 61, 59, 62], 63, {})
    assert result.severity == SEVERITY_GRAY
    assert result.personal_severity is None
    assert result.z is None
    assert result.baseline.enough_data is False
    assert result.baseline.n == 4
    assert any("need 5 readings" in r for r in result.reasons)


def test_mad_floor_on_flat_history():
    baseline = build_baseline([60, 60, 60, 60, 60])
    assert baseline.enough_data is True
    assert baseline.median == 60
    assert baseline.mad == 0
    # Flat history -> MAD 0 -> the floor is the only denominator.
    z = signed_bad_z(62, baseline, "high", mad_floor=2.0)
    assert math.isclose(z, 1.0, rel_tol=1e-9)


def test_one_outlier_barely_moves_the_median():
    baseline = build_baseline([60, 60, 60, 60, 60, 200])
    assert baseline.median == 60


def test_good_direction_never_raises_severity():
    ind = resting_hr_indicator()
    # History around 60; a lower heart rate is the favorable direction.
    result = evaluate(ind, [60, 61, 59, 60, 62], 50, {})
    assert result.z == 0.0
    assert result.personal_severity == SEVERITY_GREEN
    assert result.severity == SEVERITY_GREEN


def test_boundary_values():
    ind = resting_hr_indicator(mad_floor=1.0, min_valid=-100.0, max_valid=100.0)
    history = [0.0, 0.0, 0.0, 0.0, 0.0]
    cases = [
        (1.5, SEVERITY_YELLOW),
        (2.5, SEVERITY_ORANGE),
        (3.5, SEVERITY_RED),
    ]
    for value, expected in cases:
        result = evaluate(ind, history, value, {})
        assert result.personal_severity == expected, (value, result.personal_severity)
        assert result.severity == expected, (value, result.severity)


def test_worse_of_two_logic():
    ind = resting_hr_indicator(mad_floor=1.0)
    history = [60.0, 60.0, 60.0, 60.0, 60.0]
    lims = limits({"yellow": 60.5, "orange": 70.0, "red": 90.0, "direction": "high"})

    # Personal green (z = 1.0) but limit yellow -> final yellow.
    r1 = evaluate(ind, history, 61.0, lims)
    assert r1.personal_severity == SEVERITY_GREEN
    assert r1.limit_severity == SEVERITY_YELLOW
    assert r1.severity == SEVERITY_YELLOW

    # Personal orange (z = 3.0) beats limit yellow -> final orange.
    r2 = evaluate(ind, history, 63.0, lims)
    assert r2.personal_severity == SEVERITY_ORANGE
    assert r2.limit_severity == SEVERITY_YELLOW
    assert r2.severity == SEVERITY_ORANGE


def test_nan_handling():
    ind = resting_hr_indicator()
    # NaN and None in history are ignored; still enough valid data.
    result = evaluate(ind, [60, float("nan"), 61, None, 59, 60, 62], 63, {})
    assert result.baseline.enough_data is True
    assert result.severity == SEVERITY_GREEN
    assert any("Ignored" in r for r in result.reasons)

    # A NaN new reading is ignored and yields gray.
    result = evaluate(ind, [60, 61, 59, 60, 62], float("nan"), {})
    assert result.severity == SEVERITY_GRAY
    assert any("Ignored the new reading" in r for r in result.reasons)


def test_not_enough_data_with_limit_reports_both_reasons():
    ind = resting_hr_indicator()
    lims = limits({"yellow": 100.0, "orange": 120.0, "red": 140.0, "direction": "high"})
    # Only 3 readings (insufficient history) but the value breaches orange.
    result = evaluate(ind, [60, 61, 59], 130, lims)
    assert result.personal_severity is None
    assert result.limit_severity == SEVERITY_ORANGE
    assert result.severity == SEVERITY_ORANGE  # limit still applies
    assert any("Not enough history" in r for r in result.reasons)
    assert any("warning limit" in r for r in result.reasons)


def test_calm_week_no_false_alarm():
    ind = resting_hr_indicator()
    calm_week = [60, 61, 59, 60, 62, 58, 60]
    data_limits = load_json("data/limits.json")
    for day in range(len(calm_week)):
        history = calm_week[:day]
        result = evaluate(ind, history, calm_week[day], data_limits)
        assert result.severity not in (SEVERITY_ORANGE, SEVERITY_RED), (
            day,
            result.severity,
            result.reasons,
        )


# --- absolute limits ---


def test_check_limits_returns_severity_or_none():
    lims = limits({"yellow": 100.0, "orange": 120.0, "red": 140.0, "direction": "high"})
    assert check_limits("resting_hr", 99, lims) is None
    assert check_limits("resting_hr", 100, lims) == SEVERITY_YELLOW
    assert check_limits("resting_hr", 121, lims) == SEVERITY_ORANGE
    assert check_limits("resting_hr", 140, lims) == SEVERITY_RED
    assert check_limits("unknown", 200, lims) is None
    assert check_limits("resting_hr", float("nan"), lims) is None

    low_lims = limits({"yellow": 95.0, "orange": 90.0, "red": 85.0, "direction": "low"})
    assert check_limits("resting_hr", 96, low_lims) is None
    assert check_limits("resting_hr", 95, low_lims) == SEVERITY_YELLOW
    assert check_limits("resting_hr", 85, low_lims) == SEVERITY_RED


# --- data file integrity ---


def test_limits_json_structure_and_indicator_keys():
    data_limits = load_json("data/limits.json")
    indicators = load_json("data/indicators.json")
    indicator_keys = {item["key"] for item in indicators}
    assert len(indicator_keys) == 6
    assert set(data_limits.keys()) == indicator_keys

    for key, entry in data_limits.items():
        assert key in indicator_keys, key
        for field in ("yellow", "orange", "red", "direction", "placeholder"):
            assert field in entry, (key, field)
        assert entry["placeholder"] is True
        assert entry["direction"] in ("high", "low")


# --- adversarial ---


def test_adversarial_empty_history():
    """Missing history must not crash, and must not invent a personal score."""
    ind = resting_hr_indicator()
    for history in ([], (), None):
        result = evaluate(ind, history, 60, {})
        assert result.severity == SEVERITY_GRAY
        assert result.baseline.n == 0
        assert result.baseline.enough_data is False
        assert result.z is None
        assert result.personal_severity is None
        assert any("need 5 readings" in r for r in result.reasons)
        assert not any("spreads" in r for r in result.reasons)

    # A bare number is not a history. Must not crash or be read as readings.
    result = evaluate(ind, 60, 61, {})
    assert result.severity == SEVERITY_GRAY
    assert result.z is None
    assert any("not a sequence" in r for r in result.reasons)

    # Empty history still reports an absolute limit breach.
    lims = limits({"yellow": 100.0, "orange": 120.0, "red": 140.0, "direction": "high"})
    result = evaluate(ind, [], 150, lims)
    assert result.severity == SEVERITY_RED
    assert any("need 5 readings" in r for r in result.reasons)
    assert any("critical limit" in r for r in result.reasons)


def test_adversarial_constant_history():
    """A flat history must not divide by zero or raise a false alarm."""
    ind = resting_hr_indicator()
    history = [60.0] * 20
    same = evaluate(ind, history, 60.0, {})
    assert same.severity == SEVERITY_GREEN
    assert same.z == 0.0
    assert same.baseline.mad == 0.0
    assert same.baseline.n == DEFAULT_WINDOW
    assert not any("spreads" in r for r in same.reasons)

    # 1 bpm is inside the placeholder floor, so it stays green.
    step = evaluate(ind, history, 61.0, {})
    assert step.severity == SEVERITY_GREEN
    assert step.z < 1.5
    assert not any("spreads" in r for r in step.reasons)

    # A real step on a flat history is scored against the floor, one decimal,
    # and must not round up into the next placeholder boundary.
    jumped = evaluate(ind, history, 65.0, {})
    assert jumped.personal_severity == SEVERITY_YELLOW
    assert any("1.7 spreads" in r for r in jumped.reasons)

    near_boundary = resting_hr_indicator(mad_floor=1.0, min_valid=-100.0, max_valid=100.0)
    almost = evaluate(near_boundary, [0.0] * 5, 2.46, {})
    assert almost.personal_severity == SEVERITY_YELLOW
    assert any("2.46" in r for r in almost.reasons)
    assert not any("2.5 spreads" in r for r in almost.reasons)

    # A zero floor on a flat history used to raise ZeroDivisionError.
    flat = resting_hr_indicator(mad_floor=0.0)
    equal = evaluate(flat, [60.0] * 14, 60.0, {})
    assert equal.severity == SEVERITY_GREEN
    assert equal.z == 0.0
    shifted = evaluate(flat, [60.0] * 14, 70.0, {})
    assert shifted.severity != SEVERITY_GREEN
    assert shifted.z != 0.0
    assert not any("0.0 spreads" in r or "0 spreads" in r for r in shifted.reasons)


def test_adversarial_huge_outliers():
    """Huge finite values must not overflow the baseline or hide a real shift."""
    ind = resting_hr_indicator()
    # One in-range outlier barely moves the median.
    mixed = evaluate(ind, [60, 61, 59, 60, 62, 220, 60, 61], 60, {})
    assert 59 <= mixed.baseline.median <= 62
    assert mixed.severity == SEVERITY_GREEN

    # Invalid outliers fill the recent window, so older calm readings must
    # not be pulled back in and scored as a personal baseline.
    buried = evaluate(ind, [60, 61, 59, 60, 62] + [1e16] * DEFAULT_WINDOW, 60, {})
    assert buried.baseline.enough_data is False
    assert buried.baseline.n == 0
    assert buried.severity == SEVERITY_GRAY
    assert any("Ignored" in r for r in buried.reasons)
    assert not any("spreads" in r for r in buried.reasons)

    wide_high = resting_hr_indicator(min_valid=-1e308, max_valid=1e308, mad_floor=1.0)
    wide_low = resting_hr_indicator(
        key="spo2",
        name="Oxygen saturation",
        bad_direction="low",
        mad_floor=1.0,
        min_valid=-1e308,
        max_valid=1e308,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        even_huge = build_baseline([1e308] * 14)
        even_negative = build_baseline([-1e308] * 14)
        drop = evaluate(wide_low, [1e308] * 14, 0.0, {})
        surge = evaluate(wide_high, [-1e308] * 14, 1e308, {})

    assert even_huge.enough_data is True
    assert even_huge.median == 1e308
    assert even_huge.mad == 0.0
    assert math.isfinite(even_huge.median)
    assert even_negative.median == -1e308
    assert math.isfinite(even_negative.median)

    # A much lower value is unfavorable for a low-is-bad indicator. Overflow
    # used to report z=0 and green.
    assert drop.severity == SEVERITY_RED
    assert drop.baseline.median == 1e308
    assert any("below" in r for r in drop.reasons)
    assert not any("inf" in r.lower() for r in drop.reasons)

    # Opposite-sign extremes must still alarm, not collapse to a fake green.
    assert surge.severity == SEVERITY_RED
    assert surge.baseline.median == -1e308
    assert any("above" in r or "far outside" in r for r in surge.reasons)


def test_adversarial_negative_values():
    """Negatives outside range are ignored; valid negatives keep direction."""
    ind = resting_hr_indicator()
    result = evaluate(ind, [60, -1, 61, -50, 59, 60, 62], -5, {})
    assert result.severity == SEVERITY_GRAY
    assert result.z is None
    assert result.personal_severity is None
    assert result.limit_severity is None
    assert result.baseline.n == 5
    assert result.baseline.median == 60
    assert any("Ignored the new reading" in r and "-5" in r for r in result.reasons)
    assert any("Ignored 2 historical" in r for r in result.reasons)
    assert not any("spreads" in r or "limit" in r for r in result.reasons)

    # A negative must not be scored against an absolute low limit either.
    spo2 = resting_hr_indicator(
        key="spo2",
        name="Oxygen saturation",
        bad_direction="low",
        mad_floor=1.0,
        min_valid=50,
        max_valid=100,
    )
    rejected = evaluate(spo2, [98, 97, 99, 98, 97], -1, load_json("data/limits.json"))
    assert rejected.severity == SEVERITY_GRAY
    assert rejected.limit_severity is None
    assert not any("limit" in r for r in rejected.reasons)

    signed = resting_hr_indicator(
        name="X", mad_floor=1.0, min_valid=-100.0, max_valid=100.0
    )
    history = [-5, -5, -4, -6, -5]
    favorable = evaluate(signed, history, -20, {})
    assert favorable.severity == SEVERITY_GREEN
    assert favorable.z == 0.0
    unfavorable = evaluate(signed, history, -2, {})
    assert unfavorable.z == 3.0
    assert unfavorable.personal_severity == SEVERITY_ORANGE
    assert any("above" in r for r in unfavorable.reasons)

    low = resting_hr_indicator(
        name="X",
        bad_direction="low",
        mad_floor=1.0,
        min_valid=-100.0,
        max_valid=100.0,
    )
    worse = evaluate(low, history, -20, {})
    assert worse.severity == SEVERITY_RED
    assert worse.z == 15.0
    assert any("below" in r for r in worse.reasons)


def test_adversarial_duplicate_dates():
    """Repeated values must not crash; dates must not be parsed as readings."""
    ind = resting_hr_indicator()
    # Seven days logged twice: duplicates stay in the window and stay flat.
    duplicated = evaluate(ind, [60.0, 60.0] * 7, 60.0, {})
    assert duplicated.severity == SEVERITY_GREEN
    assert duplicated.z == 0.0
    assert duplicated.baseline.n == 14
    assert duplicated.baseline.mad == 0.0

    # A repeated high value must not make a lower new reading look worse.
    repeated_high = evaluate(ind, [200.0] * 14, 60.0, {})
    assert repeated_high.severity == SEVERITY_GREEN
    assert repeated_high.z == 0.0

    # Dated pairs are not numbers. Ignoring them must not invent a baseline.
    dated = [("2026-01-01", 60.0), ("2026-01-01", 75.0)] * 3
    paired = evaluate(ind, dated, 60.0, {})
    assert paired.severity == SEVERITY_GRAY
    assert paired.z is None
    assert paired.baseline.n == 0
    assert any("Ignored" in r for r in paired.reasons)
    assert not any("spreads" in r for r in paired.reasons)

    # A date string must not be split into digit readings (wrong severity).
    mood = resting_hr_indicator(
        key="mood",
        name="Mood",
        bad_direction="low",
        mad_floor=1.0,
        min_valid=1,
        max_valid=10,
    )
    as_text = evaluate(mood, "2026-01-01", 5, {})
    assert as_text.baseline.n == 0
    assert as_text.severity == SEVERITY_GRAY
    assert as_text.z is None
    assert any("not a sequence" in r for r in as_text.reasons)

    # A list of date strings used to raise ValueError inside the baseline.
    baseline = build_baseline(["2026-01-01"] * 6)
    assert baseline.n == 0
    assert baseline.enough_data is False


def test_sources_json_are_unverified_citation_stubs():
    sources = load_json("data/sources.json")
    assert len(sources) == 14
    for entry in sources:
        assert entry["verified"] is False
        assert entry["id"].startswith("src_")
        assert entry["title"]
        assert entry["title"] != "PLACEHOLDER: replace with a real cited source"
        assert entry["publisher"]
        assert entry["url"]
        assert entry["supports"]
        assert "verify_note" in entry
