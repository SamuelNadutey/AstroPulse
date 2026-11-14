"""Tests for the forecast (engine/forecast.py)."""
import numpy as np
import pytest

from engine.forecast import MAX_HORIZON, MIN_HORIZON, forecast


def test_perfect_line_forecast_is_close_to_the_line_with_narrow_band():
    history = [2.0 * x + 1.0 for x in range(10)]
    result = forecast(history, horizon=5, window=10)
    assert result is not None
    for step, value in zip(result.days, result.values):
        expected = 2.0 * (9 + step) + 1.0
        assert value == pytest.approx(expected, abs=1e-6)
    widths = [u - l for u, l in zip(result.upper, result.lower)]
    assert max(widths) < 1e-6


def test_noisy_history_gives_wider_band_than_clean_history():
    rng = np.random.default_rng(7)
    clean = [60.0 + 0.5 * x for x in range(10)]
    noisy = [v + rng.normal(0.0, 2.0) for v in clean]
    clean_fc = forecast(clean, horizon=5)
    noisy_fc = forecast(noisy, horizon=5)
    clean_width = clean_fc.upper[0] - clean_fc.lower[0]
    noisy_width = noisy_fc.upper[0] - noisy_fc.lower[0]
    assert noisy_width > clean_width
    assert noisy_width > 1.0


def test_band_widens_with_horizon():
    rng = np.random.default_rng(3)
    history = [60.0 + 0.3 * x + rng.normal(0.0, 1.5) for x in range(12)]
    result = forecast(history, horizon=MAX_HORIZON, window=10)
    widths = [u - l for u, l in zip(result.upper, result.lower)]
    assert all(later > earlier for earlier, later in zip(widths, widths[1:]))


def test_fewer_than_five_points_returns_none():
    assert forecast([1.0, 2.0, 3.0, 4.0]) is None
    assert forecast([]) is None


def test_five_points_is_enough():
    assert forecast([1.0, 2.0, 3.0, 4.0, 5.0]) is not None


def test_non_finite_points_are_skipped_before_counting():
    history = [1.0, float("nan"), 2.0, None, 3.0, 4.0, 5.0]
    result = forecast(history)
    assert result is not None


def test_horizon_outside_three_to_seven_is_rejected():
    history = [float(x) for x in range(10)]
    with pytest.raises(ValueError):
        forecast(history, horizon=MIN_HORIZON - 1)
    with pytest.raises(ValueError):
        forecast(history, horizon=MAX_HORIZON + 1)


def test_projection_length_matches_horizon():
    history = [float(x) for x in range(10)]
    for horizon in range(MIN_HORIZON, MAX_HORIZON + 1):
        result = forecast(history, horizon=horizon)
        assert len(result.days) == horizon
        assert result.days[0] == 1
