"""Tests for the seed_demo management command."""
import re
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError

from core.models import CheckIn, CrewMember, Reading

pytestmark = pytest.mark.django_db

DEMO_NAME = "Demo crew (SIMULATED)"


def _run(scenario, reset=False):
    out = StringIO()
    call_command("seed_demo", scenario=scenario, reset=reset, stdout=out)
    return out.getvalue()


def test_seed_creates_21_days_of_six_indicators():
    _run("drift_day6", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    readings = Reading.objects.filter(crew_member=crew)
    assert readings.count() == 21 * 6
    assert readings.values("recorded_at").distinct().count() == 21
    assert all(r.is_simulated for r in readings)
    assert CheckIn.objects.filter(crew_member=crew).count() == 21


def test_reset_does_not_duplicate_rows():
    _run("calm_week", reset=True)
    _run("calm_week", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    assert Reading.objects.filter(crew_member=crew).count() == 126
    assert CheckIn.objects.filter(crew_member=crew).count() == 21


def test_first_run_without_reset_works():
    _run("calm_week")
    crew = CrewMember.objects.get(name=DEMO_NAME)
    assert Reading.objects.filter(crew_member=crew).count() == 126


def test_rerun_without_reset_is_refused_when_data_exists():
    _run("calm_week", reset=True)
    with pytest.raises(CommandError, match="--reset"):
        _run("drift_day6")
    crew = CrewMember.objects.get(name=DEMO_NAME)
    assert Reading.objects.filter(crew_member=crew).count() == 126


def test_reset_replaces_previous_scenario_without_mixing():
    _run("fever_blackout", reset=True)
    _run("calm_week", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    assert Reading.objects.filter(crew_member=crew).count() == 126
    assert not Reading.objects.filter(crew_member=crew, in_blackout=True).exists()
    assert not CheckIn.objects.filter(crew_member=crew, in_blackout=True).exists()


def test_reading_unique_per_indicator_per_day():
    crew = CrewMember.objects.create(name="Unique test")
    Reading.objects.create(
        crew_member=crew, indicator_key="mood", value=3.0,
        recorded_at="2026-01-01", environment="station",
    )
    with pytest.raises(IntegrityError):
        Reading.objects.create(
            crew_member=crew, indicator_key="mood", value=4.0,
            recorded_at="2026-01-01", environment="station",
        )


def test_checkin_unique_per_crew_member_per_day():
    crew = CrewMember.objects.create(name="Unique checkin test")
    CheckIn.objects.create(crew_member=crew, date="2026-01-01", environment="station")
    with pytest.raises(IntegrityError):
        CheckIn.objects.create(crew_member=crew, date="2026-01-01", environment="rover")


def test_reset_only_touches_demo_crew_member():
    other = CrewMember.objects.create(name="Real crew member")
    Reading.objects.create(
        crew_member=other,
        indicator_key="mood",
        value=4.0,
        recorded_at="2026-01-01",
        environment="station",
    )
    _run("fever_blackout", reset=True)
    _run("fever_blackout", reset=True)
    assert Reading.objects.filter(crew_member=other).count() == 1


def test_output_summarises_21_days_and_marks_simulated():
    output = _run("drift_day6", reset=True)
    assert "SIMULATED" in output
    day_rows = [line for line in output.splitlines() if re.match(r"^\s*\d+\s", line)]
    assert len(day_rows) == 21


def test_blackout_days_are_stored_with_flag():
    _run("fever_blackout", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    flagged = set(
        Reading.objects.filter(crew_member=crew, in_blackout=True)
        .values_list("recorded_at", flat=True)
    )
    assert len(flagged) == 4


def test_unknown_scenario_is_rejected():
    with pytest.raises(CommandError):
        _run("no_such_scenario")
