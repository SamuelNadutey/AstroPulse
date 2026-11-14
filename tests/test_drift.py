"""Tests for the slow-drift CUSUM (engine/drift.py).

Pure-Python integration tests use the seeded simulator to confirm the drift
detector flags a slow shift on drift_day6 while staying quiet on calm_week.
"""
import pytest

from engine.baseline import build_baseline
from engine.drift import detect_drift, detect_series_drift
from simulator.generator import generate, load_indicators

REFERENCE = [62.0, 62.5, 61.5, 62.0, 62.2]

INDICATORS = {ind["key"]: ind for ind in load_indicators()}


def _series(rows, key, upto):
    return [r["value"] for r in rows if r["indicator_key"] == key and r["day"] <= upto]


def _drift_day(key, rows, k=None, h=None):
    ind = INDICATORS[key]
    kwargs = {} if k is None else {"k": k}
    if h is not None:
        kwargs["h"] = h
    return next(
        (
            d
            for d in range(6, 22)
            if detect_series_drift(
                _series(rows, key, d), ind["bad_direction"], ind["mad_floor"], **kwargs
            ).drifting
        ),
        None,
    )


def test_flat_series_does_not_drift():
    result = detect_series_drift(REFERENCE + [62.1] * 12, "high", 2.0)
    assert result.drifting is False
    assert result.reason is None


def test_single_outlier_does_not_trigger_drift():
    series = REFERENCE + [62.0] * 4 + [100.0] + [62.0] * 4
    result = detect_series_drift(series, "high", 2.0)
    assert result.drifting is False


def test_single_outlier_at_the_latest_reading_does_not_trigger_drift():
    series = REFERENCE + [62.0] * 8 + [100.0]
    result = detect_series_drift(series, "high", 2.0)
    assert result.drifting is False


def test_sustained_high_shift_triggers_drift_with_reason():
    series = REFERENCE + [70.0] * 10
    result = detect_series_drift(series, "high", 2.0)
    assert result.drifting is True
    assert result.days_in_drift >= 2
    assert result.started_on_index is not None
    assert result.reason.endswith("days above your usual range.")


def test_sustained_low_shift_is_reported_as_below_for_low_bad_direction():
    reference = [7.5, 7.4, 7.6, 7.5, 7.5]
    series = reference + [5.0] * 10
    result = detect_series_drift(series, "low", 0.5)
    assert result.drifting is True
    assert result.reason.endswith("days below your usual range.")


def test_rise_is_ignored_when_bad_direction_is_low():
    series = REFERENCE + [75.0] * 12
    result = detect_series_drift(series, "low", 2.0)
    assert result.drifting is False


def test_started_on_index_points_at_the_first_shifted_reading():
    series = REFERENCE + [62.0] * 3 + [70.0] * 10
    result = detect_series_drift(series, "high", 2.0)
    assert result.drifting is True
    assert result.started_on_index >= 3


def test_not_enough_reference_points_means_no_drift():
    result = detect_series_drift([62.0, 70.0, 70.0], "high", 2.0)
    assert result.drifting is False


def test_non_finite_readings_are_skipped():
    series = REFERENCE + [float("nan"), 62.0, None, 62.1]
    result = detect_series_drift(series, "high", 2.0)
    assert result.drifting is False


def test_invalid_bad_direction_raises():
    baseline = build_baseline(REFERENCE)
    with pytest.raises(ValueError):
        detect_drift([62.0], baseline, "sideways", 2.0)


def test_insufficient_baseline_never_drifts():
    baseline = build_baseline([62.0, 62.0])
    result = detect_drift([90.0] * 20, baseline, "high", 2.0)
    assert result.drifting is False


# --- seeded integration: drift_day6 and calm_week -------------------------


def test_drift_day6_resting_hr_and_sleep_drift_within_a_week():
    rows = generate("drift_day6")
    resting_day = _drift_day("resting_hr", rows)
    sleep_day = _drift_day("sleep_hours", rows)
    assert resting_day is not None
    assert sleep_day is not None
    # Drift starts day 6; a robust detector needs roughly a week of data.
    assert resting_day <= 14
    assert sleep_day <= 13


def test_drift_day6_flags_before_the_first_extreme_reading_returns():
    # The day-6 reading is a one-off spike (personal orange), then readings
    # moderate. Drift should flag during that moderate stretch, well before
    # the later orange/red readings at day 14+.
    rows = generate("drift_day6")
    resting_day = _drift_day("resting_hr", rows)
    assert resting_day is not None
    assert resting_day < 14


def test_calm_week_never_drifts_across_all_indicators_and_20_seeds():
    for seed in range(20):
        rows = generate("calm_week", seed=seed)
        for key, ind in INDICATORS.items():
            for day in range(6, 22):
                result = detect_series_drift(
                    _series(rows, key, day),
                    ind["bad_direction"],
                    ind["mad_floor"],
                )
                assert result.drifting is False, (
                    f"false drift: seed={seed} key={key} day={day}"
                )
