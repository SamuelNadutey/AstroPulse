"""Tests for the seeded scenario simulator (pure Python, no Django)."""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from simulator import generator
from simulator.generator import SCENARIOS, generate, load_indicators

INDICATORS = {ind["key"]: ind for ind in load_indicators()}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _series(rows, key):
    days = [r["day"] for r in rows if r["indicator_key"] == key]
    values = [r["value"] for r in rows if r["indicator_key"] == key]
    return np.array(days, dtype=float), np.array(values, dtype=float)


def test_all_four_scenarios_exist():
    assert set(SCENARIOS) == {"calm_week", "drift_day6", "fever_blackout", "isolation_mood"}
    for name in SCENARIOS:
        assert generate(name)


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        generate("not_a_scenario")


def test_same_seed_gives_identical_output():
    for name in SCENARIOS:
        assert generate(name, seed=42) == generate(name, seed=42)


def test_different_seed_gives_different_output():
    for name in SCENARIOS:
        assert generate(name, seed=1) != generate(name, seed=2)


def test_days_run_1_to_21_for_six_indicators():
    rows = generate("calm_week")
    assert len(rows) == 21 * 6
    assert sorted({r["day"] for r in rows}) == list(range(1, 22))
    assert {r["indicator_key"] for r in rows} == set(INDICATORS)


def test_calm_week_has_no_trend():
    rows = generate("calm_week")
    for key, ind in INDICATORS.items():
        days, values = _series(rows, key)
        slope = np.polyfit(days, values, 1)[0]
        assert abs(slope) < 0.2 * ind["normal_wobble"], f"{key} slope {slope:.3f} too large"


def test_drift_day6_resting_hr_mean_rises_after_day_6():
    rows = generate("drift_day6")
    _, values = _series(rows, "resting_hr")
    days, _ = _series(rows, "resting_hr")
    before = values[days <= 5].mean()
    after = values[days >= 7].mean()
    assert after > before + 5


def test_drift_day6_sleep_falls_after_day_6():
    rows = generate("drift_day6")
    days, values = _series(rows, "sleep_hours")
    assert values[days >= 7].mean() < values[days <= 5].mean() - 0.5


def test_fever_blackout_flags_blackout_days():
    rows = generate("fever_blackout")
    for row in rows:
        expected = row["day"] in (8, 9, 10, 11)
        assert row["in_blackout"] is expected, row
    days, temps = _series(rows, "temperature")
    assert all(temps[np.isin(days, [9, 10])] >= 38.0)
    assert all(temps[~np.isin(days, [9, 10])] < 38.0)


def test_non_blackout_scenarios_never_flag_blackout():
    for name in ("calm_week", "drift_day6", "isolation_mood"):
        assert not any(r["in_blackout"] for r in generate(name))


def test_isolation_mood_and_exercise_decline_from_day_7():
    rows = generate("isolation_mood")
    days, mood = _series(rows, "mood")
    assert mood[days >= 8].mean() < mood[days <= 6].mean() - 0.5
    days, exercise = _series(rows, "exercise_min")
    assert exercise[days >= 8].mean() < exercise[days <= 6].mean() - 10


def test_every_value_is_within_valid_range():
    for name in SCENARIOS:
        for row in generate(name):
            ind = INDICATORS[row["indicator_key"]]
            assert ind["min_valid"] <= row["value"] <= ind["max_valid"], row


def test_clamping_holds_for_extreme_drift():
    rows = generate("drift_day6", days=60)
    for row in rows:
        ind = INDICATORS[row["indicator_key"]]
        assert ind["min_valid"] <= row["value"] <= ind["max_valid"]
    sleep_floor = [
        r for r in rows
        if r["indicator_key"] == "sleep_hours" and r["value"] == INDICATORS["sleep_hours"]["min_valid"]
    ]
    assert sleep_floor, "sleep_hours never reached min_valid, so clamping was not exercised"


def test_simulator_source_does_not_import_django():
    source = Path(generator.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+django\b", source, re.MULTILINE)


def test_indicator_file_has_required_fields():
    required = {
        "key", "label", "unit", "bad_direction", "body_region", "input_type",
        "min_valid", "max_valid", "mad_floor", "normal_center", "normal_wobble",
    }
    data = json.loads((DATA_DIR / "indicators.json").read_text(encoding="utf-8"))
    assert len(data) == 6
    for entry in data:
        assert required <= entry.keys(), entry["key"]
        assert entry["min_valid"] < entry["max_valid"]
