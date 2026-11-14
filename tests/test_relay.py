"""Tests for blackout mode and the exportable relay summary."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from core.models import AppState, CheckIn, CrewMember, Reading, RelayItem
from core.services import current_blackout, set_blackout


@pytest.mark.django_db
def test_blackout_banner_hidden_by_default(client):
    response = client.get(reverse("core:home"))
    content = response.content.decode()
    assert "OFFLINE: no contact with ground" not in content
    assert "Toggle blackout mode" in content


@pytest.mark.django_db
def test_blackout_banner_shown_when_blackout_on(client):
    set_blackout(True)
    response = client.get(reverse("core:home"))
    content = response.content.decode()
    assert "OFFLINE: no contact with ground" in content


@pytest.mark.django_db
def test_blackout_toggle_persists(client):
    url = reverse("core:blackout_toggle")
    client.post(url, {"blackout": "on"})
    assert current_blackout() is True
    client.post(url, {})
    assert current_blackout() is False


@pytest.mark.django_db
def test_checkin_form_defaults_to_current_blackout(client):
    set_blackout(True)
    response = client.get(reverse("core:checkin"))
    content = response.content.decode()
    assert 'id="id_blackout"' in content
    # The checkbox should be checked when blackout is on.
    assert 'name="blackout"' in content


@pytest.mark.django_db
def test_relay_page_exists_and_shows_empty_state(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    CheckIn.objects.create(crew_member=crew, date=timezone.localdate(), environment="station")
    response = client.get(reverse("core:relay"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Relay summary" in content
    assert "No open relay items" in content


@pytest.mark.django_db
def test_relay_item_created_for_orange_during_blackout(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    # Build a flat history and a value that yields an orange z-score.
    # resting_hr mad_floor=3.0; history median 60, value 69 -> z=(69-60)/3=3 -> orange.
    for i in range(5, 0, -1):
        Reading.objects.create(
            crew_member=crew,
            indicator_key="resting_hr",
            value=60.0,
            recorded_at=today - timedelta(days=i),
            environment="station",
        )
    Reading.objects.create(
        crew_member=crew,
        indicator_key="resting_hr",
        value=69.0,
        recorded_at=today,
        environment="station",
    )
    CheckIn.objects.create(crew_member=crew, date=today, environment="station", in_blackout=True)

    set_blackout(True)
    client.get(reverse("core:status"))

    item = RelayItem.objects.filter(crew_member=crew, indicator_key="resting_hr").first()
    assert item is not None
    assert item.severity == "orange"
    assert item.contact_ground_open is True
    assert item.resolved is False


@pytest.mark.django_db
def test_no_duplicate_open_relay_items(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    for i in range(5, 0, -1):
        Reading.objects.create(
            crew_member=crew,
            indicator_key="resting_hr",
            value=60.0,
            recorded_at=today - timedelta(days=i),
            environment="station",
        )
    Reading.objects.create(
        crew_member=crew,
        indicator_key="resting_hr",
        value=69.0,
        recorded_at=today,
        environment="station",
    )
    CheckIn.objects.create(crew_member=crew, date=today, environment="station", in_blackout=True)

    set_blackout(True)
    client.get(reverse("core:status"))
    client.get(reverse("core:status"))

    assert RelayItem.objects.filter(crew_member=crew, indicator_key="resting_hr", resolved=False).count() == 1


@pytest.mark.django_db
def test_relay_resolve_marks_item_resolved_with_note(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    item = RelayItem.objects.create(
        crew_member=crew,
        for_date=today,
        indicator_key="resting_hr",
        severity="orange",
        headline="Elevated heart rate",
    )
    response = client.post(
        reverse("core:relay_resolve", kwargs={"item_id": item.pk}),
        {"note": "Rested and rechecked"},
    )
    assert response.status_code == 302
    item.refresh_from_db()
    assert item.resolved is True
    assert item.resolved_note == "Rested and rechecked"


@pytest.mark.django_db
def test_relay_export_contains_flagged_item_and_safety_line(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    RelayItem.objects.create(
        crew_member=crew,
        for_date=today,
        indicator_key="temperature",
        severity="red",
        headline="High temperature",
        reason="Above the critical limit of 38",
        action_taken="Cooled and rechecked",
        contact_ground_open=True,
    )
    Reading.objects.create(
        crew_member=crew,
        indicator_key="temperature",
        value=38.5,
        recorded_at=today,
        environment="station",
        is_simulated=True,
    )
    # Keep blackout off so the manually created item is not overwritten by a
    # fresh status evaluation.
    CheckIn.objects.create(crew_member=crew, date=today, environment="station", in_blackout=False)

    response = client.get(reverse("core:relay_export"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    content = response.content.decode()
    assert "temperature" in content
    assert "(severity red)" in content
    assert "Action taken: Cooled and rechecked" in content
    assert "Open contact-ground items:" in content
    assert "Decision support, not a diagnosis. Simulated demonstration data." in content


@pytest.mark.django_db
def test_nothing_exported_until_requested(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    RelayItem.objects.create(
        crew_member=crew,
        for_date=today,
        indicator_key="temperature",
        severity="red",
        headline="High temperature",
    )
    # No export request means no text file response.
    response = client.get(reverse("core:relay"))
    assert response.status_code == 200
    assert response["Content-Type"] != "text/plain"


@pytest.mark.django_db
def test_fever_blackout_creates_temperature_relay_item(client):
    call_command("seed_demo", scenario="fever_blackout", reset=True)
    crew = CrewMember.objects.get(name="Demo crew (SIMULATED)")
    today = timezone.localdate()
    # The scenario spans 21 days; today is day 21. Fever days are 9 and 10.
    fever_date = today - timedelta(days=21 - 10)

    set_blackout(True)
    client.get(reverse("core:status") + f"?date={fever_date.isoformat()}")

    item = RelayItem.objects.filter(
        crew_member=crew, indicator_key="temperature", for_date=fever_date
    ).first()
    assert item is not None
    assert item.severity in ("orange", "red")
    assert item.contact_ground_open is True


@pytest.mark.django_db
def test_relay_export_filename_includes_date(client):
    response = client.get(reverse("core:relay_export"))
    assert response.status_code == 200
    today = timezone.localdate().isoformat()
    assert f'relay_summary_{today}.txt' in response["Content-Disposition"]


@pytest.mark.django_db
def test_relay_export_includes_logged_action(client):
    crew, _ = CrewMember.objects.get_or_create(name="Test crew")
    today = timezone.localdate()
    RelayItem.objects.create(
        crew_member=crew,
        for_date=today,
        indicator_key="resting_hr",
        severity="orange",
        headline="Elevated heart rate",
        action_taken="Rested and rechecked",
    )
    CheckIn.objects.create(crew_member=crew, date=today, environment="station", in_blackout=False)
    response = client.get(reverse("core:relay_export"))
    content = response.content.decode()
    assert "Action taken: Rested and rechecked" in content
