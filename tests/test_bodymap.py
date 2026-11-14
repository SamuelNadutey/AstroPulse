"""Tests for the Stage 4 body map and status dashboard."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from core.models import CrewMember, Reading
from core.services import (
    REGION_LABELS,
    load_indicators,
    region_statuses,
    run_status_for,
    worst_severity,
)

pytestmark = pytest.mark.django_db

DEMO_NAME = "Demo crew (SIMULATED)"
ENTER_TRIGGER = 'hx-trigger="click, keyup[key===\'Enter\']"'


# --- data mapping -------------------------------------------------------

def test_indicator_region_mapping_matches_spec():
    expected = {
        "resting_hr": "chest",
        "sleep_hours": "head",
        "temperature": "torso",
        "mood": "head",
        "exercise_min": "legs",
        "spo2": "lungs",
    }
    for config in load_indicators():
        assert config["body_region"] == expected[config["key"]]
    assert set(REGION_LABELS) == set(expected.values())
    # Every region the map renders has at least one indicator.
    grouped = {c["body_region"] for c in load_indicators()}
    assert grouped == set(REGION_LABELS)


def test_worst_severity_wins_for_shared_regions():
    def entry(region, severity):
        return {
            "body_region": region,
            "result": SimpleNamespace(severity=severity),
        }

    entries = [entry("head", "green"), entry("head", "orange")]
    regions = region_statuses(entries)
    head = next(r for r in regions if r["name"] == "head")
    assert head["severity"] == "orange"

    # All green -> green; all gray -> gray; empty region -> gray.
    assert worst_severity(["gray", "red", "yellow"]) == "red"
    assert worst_severity([]) is None


# --- body map rendering --------------------------------------------------

def test_all_regions_render_focusable_with_aria_labels():
    call_command("seed_demo", scenario="drift_day6", reset=True)
    client = Client()
    response = client.get("/status/")
    assert response.status_code == 200
    content = response.content.decode()
    assert content.count('role="button"') >= 5
    assert content.count('tabindex="0"') >= 5
    assert content.count(ENTER_TRIGGER) >= 5
    for name in REGION_LABELS:
        assert f'id="bm-{name}"' in content
        assert f"aria-label=\"{REGION_LABELS[name]} — " in content
    # Severity word appears next to each region (icon + text + color).
    for word in ("Normal", "Watch", "Concern", "Contact ground", "Not enough data"):
        assert word in content


def test_every_severity_renders_icon_and_text_not_color_only():
    crew = CrewMember.objects.create(name="Map severity crew")
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

    history("resting_hr", 60.0)   # z = 6.0 -> red (chest)
    today_reading("resting_hr", 72.0)
    history("sleep_hours", 7.5)   # z = 2.0 -> yellow (head)
    today_reading("sleep_hours", 6.5)
    history("temperature", 36.8)  # green (torso)
    today_reading("temperature", 36.8)
    history("mood", 4.0)          # z = 3.0 -> orange (head shares)
    today_reading("mood", 2.5)
    history("exercise_min", 45.0)  # no reading today -> gray (legs)
    history("spo2", 97.5)
    today_reading("spo2", 98.0)   # green (lungs)

    client = Client()
    response = client.get("/status/")
    content = response.content.decode()
    # Legend carries every severity as icon + word + color name.
    for word in ("Not enough data", "Normal", "Watch", "Concern", "Contact ground"):
        assert word in content
    # Each region renders an inline SVG icon (5 regions + legend + banner).
    assert content.count("<svg") >= 11
    # Shared head region shows the WORST severity: mood orange beats sleep yellow.
    assert 'aria-label="Head — Concern (orange)"' in content
    assert 'aria-label="Chest — Contact ground (red)"' in content
    assert 'aria-label="Legs — Not enough data (gray)"' in content


# --- region detail endpoint ----------------------------------------------

def test_region_endpoint_returns_right_indicators():
    call_command("seed_demo", scenario="drift_day6", reset=True)
    client = Client()
    head = client.get("/region/head/")
    assert head.status_code == 200
    head_content = head.content.decode()
    assert "Sleep" in head_content
    assert "Mood and stress" in head_content
    assert "Blood oxygen" not in head_content
    assert "Resting heart rate" not in head_content
    assert "View trend" in head_content

    chest = client.get("/region/chest/")
    assert chest.status_code == 200
    assert "Resting heart rate" in chest.content.decode()
    assert "Sleep" not in chest.content.decode()


def test_unknown_region_is_404():
    client = Client()
    assert client.get("/region/nose/").status_code == 404


def test_unknown_trend_indicator_is_404():
    client = Client()
    assert client.get("/trend/nope/").status_code == 404
    assert client.get("/trend/resting_hr/").status_code == 200


# --- acceptance: drift_day6 escalation ------------------------------------

def test_drift_day6_chest_and_head_escalate_with_reasons():
    call_command("seed_demo", scenario="drift_day6", reset=True)
    crew = CrewMember.objects.get(name=DEMO_NAME)
    client = Client()
    today = timezone.localdate()

    # Day 14 (today - 7): both drifted indicators are elevated against the
    # then-baseline; clicking the regions shows the engine's reasons.
    day14 = (today - timedelta(days=7)).isoformat()
    page = client.get(f"/status/?date={day14}")
    content = page.content.decode()
    assert 'aria-label="Chest — Concern (orange)"' in content
    assert 'aria-label="Head — Concern (orange)"' in content
    chest = client.get(f"/region/chest/?date={day14}")
    chest_content = chest.content.decode()
    assert "Concern (orange)" in chest_content
    assert "spreads above your usual range" in chest_content

    # Day 21 (default view): the adaptive baseline absorbed the heart-rate
    # drift, but sleep has fallen below its critical limit -> head is red.
    page = client.get("/status/")
    assert 'aria-label="Head — Contact ground (red)"' in page.content.decode()
    head = client.get("/region/head/")
    head_content = head.content.decode()
    assert "Contact ground (red)" in head_content
    assert "Below the critical limit of 4" in head_content


def test_invalid_and_future_dates_fall_back_to_today():
    call_command("seed_demo", scenario="drift_day6", reset=True)
    client = Client()
    today = timezone.localdate()
    for bad in ("garbage", "2099-01-01"):
        response = client.get(f"/status/?date={bad}")
        assert response.status_code == 200
        assert today.isoformat() in response.content.decode()
