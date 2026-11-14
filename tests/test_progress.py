"""Tests for action logging and the progress view."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from core.models import ActionLog, CheckIn, CrewMember, RelayItem
from core.services import log_action, progress_for


@pytest.mark.django_db
def test_log_action_creates_action_log(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    response = client.post(
        reverse("core:log_action"),
        {
            "date": today.isoformat(),
            "indicator_key": "resting_hr",
            "action_id": "rest-quietly",
            "action_text": "Recheck after quiet rest",
        },
    )
    assert response.status_code == 302
    assert ActionLog.objects.filter(
        crew_member=crew,
        date=today,
        indicator_key="resting_hr",
        action_id="rest-quietly",
    ).exists()


@pytest.mark.django_db
def test_log_action_updates_relay_item_action_taken(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    item = RelayItem.objects.create(
        crew_member=crew,
        for_date=today,
        indicator_key="resting_hr",
        severity="orange",
        headline="Elevated heart rate",
        resolved=False,
    )
    client.post(
        reverse("core:log_action"),
        {
            "date": today.isoformat(),
            "indicator_key": "resting_hr",
            "action_id": "rest-quietly",
            "action_text": "Recheck after quiet rest",
        },
    )
    item.refresh_from_db()
    assert item.action_taken == "Recheck after quiet rest"


@pytest.mark.django_db
def test_log_action_is_idempotent(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    for _ in range(3):
        client.post(
            reverse("core:log_action"),
            {
                "date": today.isoformat(),
                "indicator_key": "resting_hr",
                "action_id": "rest-quietly",
                "action_text": "Recheck after quiet rest",
            },
        )
    assert ActionLog.objects.filter(
        crew_member=crew, date=today, indicator_key="resting_hr"
    ).count() == 1


@pytest.mark.django_db
def test_progress_page_renders(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    CheckIn.objects.create(crew_member=crew, date=timezone.localdate(), environment="station")
    response = client.get(reverse("core:progress"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Progress" in content
    assert "Your score rewards completing check-ins, never health outcomes." in content


@pytest.mark.django_db
def test_progress_shows_streak_and_weekly_counts(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    for i in range(5, -1, -1):
        CheckIn.objects.create(
            crew_member=crew, date=today - timedelta(days=i), environment="station"
        )
    log_action(crew, today, "resting_hr", "rest-quietly", "Rested")
    response = client.get(reverse("core:progress"))
    content = response.content.decode()
    assert "6 / 7" in content
    assert "6</p>" in content or "6 day" in content  # current streak


@pytest.mark.django_db
def test_streak_resets_after_missed_day():
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    CheckIn.objects.create(crew_member=crew, date=today - timedelta(days=3), environment="station")
    CheckIn.objects.create(crew_member=crew, date=today - timedelta(days=2), environment="station")
    CheckIn.objects.create(crew_member=crew, date=today, environment="station")
    data = progress_for(crew, today)
    assert data["current_streak"] == 1


@pytest.mark.django_db
def test_score_ignores_severities_calm_vs_drift():
    call_command("seed_demo", scenario="calm_week", reset=True)
    crew = CrewMember.objects.get(name="Demo crew (SIMULATED)")
    today = timezone.localdate()
    calm = progress_for(crew, today)

    call_command("seed_demo", scenario="drift_day6", reset=True)
    crew = CrewMember.objects.get(name="Demo crew (SIMULATED)")
    drift = progress_for(crew, today)

    assert calm["weekly_score"] == drift["weekly_score"]
    assert calm["weekly_checkins"] == drift["weekly_checkins"]


@pytest.mark.django_db
def test_missed_today_shows_pick_up_message(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    CheckIn.objects.create(
        crew_member=crew, date=timezone.localdate() - timedelta(days=1), environment="station"
    )
    response = client.get(reverse("core:progress"))
    content = response.content.decode()
    assert "Pick up where you left off" in content


@pytest.mark.django_db
def test_no_shaming_for_missed_day(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    response = client.get(reverse("core:progress"))
    content = response.content.decode()
    assert "Pick up where you left off" in content
    assert "failed" not in content.lower()
    assert "streak lost" not in content.lower()


@pytest.mark.django_db
def test_progress_has_no_health_based_badges(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    CheckIn.objects.create(crew_member=crew, date=timezone.localdate(), environment="station")
    response = client.get(reverse("core:progress"))
    content = response.content.decode()
    # Score description must come from check-ins/actions, not health outcomes.
    assert "from 1 check-in and 0 actions" in content
    assert "Your score rewards completing check-ins, never health outcomes." in content
    # No severity classes or outcome language in the progress section.
    assert "sev-" not in content
    assert "Contact ground" not in content
