"""Tests for the Stage 3 check-in flow, environment profiles and status page."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from core.forms import CheckInForm
from core.models import CheckIn, CrewMember, Reading
from core.services import load_environments, run_status_for

pytestmark = pytest.mark.django_db

LOCAL_CREW_NAME = "You (local)"
DEMO_NAME = "Demo crew (SIMULATED)"

VALID_DATA = {
    "environment": "station",
    "resting_hr": "62",
    "sleep_hours": "7.5",
    "temperature": "36.8",
    "mood": "4",
    "exercise_min": "45",
    "spo2": "98",
    "blackout": "on",
    "note": "test note",
}


# --- environments.json -------------------------------------------------

def test_environments_json_has_four_complete_environments():
    envs = load_environments()
    assert {e["key"] for e in envs} == {"station", "transit", "rover", "surface_base"}
    for entry in envs:
        assert entry["label"]
        assert entry["comms_delay_text"]
        assert entry["extra_prompts"]
        # Equipment lists may only reference measurable device indicators.
        assert set(entry["available_equipment"]) <= {"resting_hr", "temperature", "spo2"}
    # Environments must be distinguishable: prompts and comms text differ.
    assert len({e["comms_delay_text"] for e in envs}) == len(envs)
    assert len({tuple(e["extra_prompts"]) for e in envs}) == len(envs)


def test_rover_has_no_spo2_equipment():
    rover = next(e for e in load_environments() if e["key"] == "rover")
    assert "spo2" not in rover["available_equipment"]


# --- form --------------------------------------------------------------

def test_form_rejects_out_of_range_values():
    form = CheckInForm(environment="station", data={**VALID_DATA, "resting_hr": "500"})
    assert not form.is_valid()
    assert "resting_hr" in form.errors
    assert "between 30 and 200 bpm" in form.errors["resting_hr"][0]

    form = CheckInForm(environment="station", data={**VALID_DATA, "sleep_hours": "20"})
    assert not form.is_valid()
    assert "between 0 and 14 hours" in form.errors["sleep_hours"][0]


def test_form_rejects_bad_mood_and_garbage():
    form = CheckInForm(environment="station", data={**VALID_DATA, "mood": "9"})
    assert not form.is_valid()
    assert "from 1 to 5" in form.errors["mood"][0]

    form = CheckInForm(environment="station", data={**VALID_DATA, "exercise_min": "abc"})
    assert not form.is_valid()
    assert "number" in form.errors["exercise_min"][0]


def test_rover_form_skips_spo2_but_station_has_it():
    assert "spo2" not in CheckInForm(environment="rover").fields
    assert "spo2" in CheckInForm(environment="station").fields
    # Self-report indicators are always asked, on every environment.
    for key in ("sleep_hours", "mood", "exercise_min"):
        assert key in CheckInForm(environment="rover").fields


def test_unknown_environment_falls_back_to_station():
    form = CheckInForm(environment="moon_base")
    assert form.environment_config["key"] == "station"


def test_invalid_post_links_errors_with_aria_describedby():
    client = Client()
    response = client.post("/checkin/", {**VALID_DATA, "resting_hr": "500"})
    assert response.status_code == 200
    content = response.content.decode()
    assert 'aria-describedby="id_resting_hr_error"' in content
    assert 'id="id_resting_hr_error"' in content


# --- check-in POST ------------------------------------------------------

def test_post_creates_readings_and_checkin_then_redirects():
    client = Client()
    response = client.post("/checkin/", VALID_DATA)
    assert response.status_code == 302
    assert response.url == "/status/"

    crew = CrewMember.objects.get(name=LOCAL_CREW_NAME)
    today = timezone.localdate()
    assert Reading.objects.filter(crew_member=crew, recorded_at=today).count() == 6
    reading = Reading.objects.get(crew_member=crew, indicator_key="resting_hr")
    assert reading.value == 62.0
    assert reading.environment == "station"
    assert reading.in_blackout is True
    assert reading.is_simulated is False
    checkin = CheckIn.objects.get(crew_member=crew, date=today)
    assert checkin.in_blackout is True
    assert checkin.note == "test note"


def test_recheckin_same_day_replaces_readings_without_error():
    client = Client()
    assert client.post("/checkin/", VALID_DATA).status_code == 302
    assert client.post("/checkin/", {**VALID_DATA, "resting_hr": "64"}).status_code == 302

    crew = CrewMember.objects.get(name=LOCAL_CREW_NAME)
    today = timezone.localdate()
    assert Reading.objects.filter(crew_member=crew, recorded_at=today).count() == 6
    reading = Reading.objects.get(crew_member=crew, indicator_key="resting_hr")
    assert reading.value == 64.0
    assert CheckIn.objects.filter(crew_member=crew, date=today).count() == 1


def test_invalid_post_saves_nothing():
    client = Client()
    client.post("/checkin/", {**VALID_DATA, "temperature": "45"})
    assert Reading.objects.count() == 0
    assert CheckIn.objects.count() == 0


def test_environment_switcher_partial_swaps_fields():
    client = Client()
    station = client.get("/checkin/fields/", {"environment": "station"})
    rover = client.get("/checkin/fields/", {"environment": "rover"})
    assert station.status_code == 200 and rover.status_code == 200
    station_content = station.content.decode()
    rover_content = rover.content.decode()
    assert 'id="checkin-fields"' in station_content
    assert "Blood oxygen" in station_content
    assert "Blood oxygen" not in rover_content
    # The extra prompts differ between environments.
    station_env = next(e for e in load_environments() if e["key"] == "station")
    rover_env = next(e for e in load_environments() if e["key"] == "rover")
    assert station_env["extra_prompts"][0] in station_content
    assert rover_env["extra_prompts"][0] in rover_content
    assert rover_env["extra_prompts"][0] not in station_content


# --- status page and service -------------------------------------------

def test_run_status_for_without_readings_is_gray_everywhere():
    crew = CrewMember.objects.create(name="Empty crew")
    entries = run_status_for(crew, timezone.localdate())
    assert len(entries) == 6
    assert all(entry["result"].severity == "gray" for entry in entries)
    assert all(entry["value"] is None for entry in entries)


def test_status_page_shows_every_severity_as_icon_text_color():
    crew = CrewMember.objects.create(name="Severity crew")
    today = timezone.localdate()

    def history(key, value, days=5):
        for offset in range(1, days + 1):
            Reading.objects.create(
                crew_member=crew,
                indicator_key=key,
                value=value,
                recorded_at=today - timedelta(days=offset),
                environment="station",
            )

    def today_reading(key, value):
        Reading.objects.create(
            crew_member=crew,
            indicator_key=key,
            value=value,
            recorded_at=today,
            environment="station",
        )

    # Flat placeholder histories so the MAD floor drives the z-score
    # (scaled-MAD denominator equals the indicator's mad_floor).
    history("resting_hr", 60.0)              # z = (72-60)/2.0 = 6.0 -> red
    today_reading("resting_hr", 72.0)
    history("sleep_hours", 7.5)              # z = (7.5-6.5)/0.5 = 2.0 -> yellow
    today_reading("sleep_hours", 6.5)
    history("temperature", 36.8)             # z 0 -> green
    today_reading("temperature", 36.8)
    history("mood", 4.0)                     # z = (4-2.5)/0.5 = 3.0 -> orange
    today_reading("mood", 2.5)
    history("exercise_min", 45.0)            # no reading today -> gray
    history("spo2", 97.5)
    today_reading("spo2", 98.0)              # green

    client = Client()
    response = client.get("/status/")
    assert response.status_code == 200
    content = response.content.decode()
    for word in ("Not enough data", "Normal", "Watch", "Concern", "Contact ground"):
        assert word in content
    for severity in ("gray", "green", "yellow", "orange", "red"):
        assert f"sev-{severity}" in content
    # Icon + text + color: every row carries an inline SVG icon.
    assert content.count("<svg") >= 5
    # Placeholder disclaimer shown.
    assert "placeholders, not clinical values" in content


def test_simulated_badge_appears_for_seeded_data():
    call_command("seed_demo", scenario="drift_day6", reset=True)
    client = Client()
    response = client.get("/status/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "SIMULATED" in content
    assert DEMO_NAME in content


def test_drift_day6_flags_elevated_resting_hr_but_calm_week_does_not():
    # Day 14 of the 21-day demo (7 days before today, day 21): drift_day6
    # has drifted well above baseline there, while calm_week stays near its
    # center. Day 6 is avoided because with only 5 history points the MAD
    # floor can flag even calm wobble (placeholder thresholds).
    call_command("seed_demo", scenario="drift_day6", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    day14 = timezone.localdate() - timedelta(days=7)
    hr = next(
        e for e in run_status_for(crew, day14) if e["key"] == "resting_hr"
    )
    assert hr["result"].severity == "orange"

    call_command("seed_demo", scenario="calm_week", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    calm = next(
        e for e in run_status_for(crew, day14) if e["key"] == "resting_hr"
    )
    assert calm["result"].severity in ("gray", "green")
