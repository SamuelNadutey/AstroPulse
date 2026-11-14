"""Tests for the guidance card UI on the region panel and trend page."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from core.models import CrewMember, Reading

pytestmark = pytest.mark.django_db

DEMO_NAME = "Demo crew (SIMULATED)"


def _client():
    return Client()


def _today():
    return timezone.localdate()


class TestGuidanceCardRegionPanel:
    def test_region_detail_orange_shows_all_six_sections(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day14 = _today() - timedelta(days=7)
        client = _client()
        response = client.get(f"/region/chest/?date={day14.isoformat()}")
        assert response.status_code == 200
        content = response.content.decode()
        assert "guidance-card" in content
        assert "gc-status" in content
        assert "gc-contributors" in content
        assert "gc-actions" in content
        assert "gc-remeasure" in content
        assert "gc-contact" in content
        assert "gc-sources" in content
        assert "<ol>" in content
        assert "display_citation" not in content  # rendered as plain text

    def test_region_detail_red_shows_contact_ground_block(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day21 = _today()
        client = _client()
        response = client.get(f"/region/head/?date={day21.isoformat()}")
        assert response.status_code == 200
        content = response.content.decode()
        assert "gc-contact" in content
        assert "When to contact ground" in content
        assert "Contact ground now" in content or "as soon as" in content

    def test_region_detail_gray_shows_not_enough_data(self):
        crew = CrewMember.objects.create(name="Gray test crew")
        today = _today()
        # Only one reading: not enough for a personal baseline.
        Reading.objects.create(
            crew_member=crew,
            indicator_key="resting_hr",
            value=70.0,
            recorded_at=today,
            environment="station",
        )
        client = _client()
        response = client.get("/region/chest/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "guidance-card" in content
        assert "Not enough data yet" in content
        assert "Add at least five readings" in content

    def test_region_detail_green_shows_reassuring_card(self):
        call_command("seed_demo", scenario="calm_week", reset=True)
        client = _client()
        response = client.get("/region/chest/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "guidance-card" in content
        assert "This indicator looks normal" in content
        assert "When to contact ground" not in content

    def test_region_detail_card_lists_at_least_one_source_when_guided(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day14 = _today() - timedelta(days=7)
        client = _client()
        response = client.get(f"/region/chest/?date={day14.isoformat()}")
        content = response.content.decode()
        assert "gc-sources" in content
        # Each guided card should contain a source citation and a plain-text URL.
        assert "source-citation" in content
        assert "source-url" in content


class TestGuidanceCardTrendPage:
    def test_trend_page_orange_shows_all_sections(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day14 = _today() - timedelta(days=7)
        client = _client()
        response = client.get(f"/trend/resting_hr/?date={day14.isoformat()}")
        assert response.status_code == 200
        content = response.content.decode()
        assert "guidance-card" in content
        assert "gc-status" in content
        assert "gc-contributors" in content
        assert "gc-actions" in content
        assert "gc-remeasure" in content
        assert "gc-contact" in content
        assert "gc-sources" in content

    def test_trend_page_red_shows_contact_ground(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day21 = _today()
        client = _client()
        response = client.get(f"/trend/sleep_hours/?date={day21.isoformat()}")
        assert response.status_code == 200
        content = response.content.decode()
        assert "gc-contact" in content
        assert "When to contact ground" in content

    def test_trend_page_gray_shows_not_enough_data(self):
        crew = CrewMember.objects.create(name="Gray trend crew")
        today = _today()
        Reading.objects.create(
            crew_member=crew,
            indicator_key="resting_hr",
            value=70.0,
            recorded_at=today,
            environment="station",
        )
        client = _client()
        response = client.get("/trend/resting_hr/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Not enough data yet" in content
        assert "Add at least five readings" in content

    def test_trend_page_sources_are_plain_text_not_links(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day14 = _today() - timedelta(days=7)
        client = _client()
        response = client.get(f"/trend/resting_hr/?date={day14.isoformat()}")
        content = response.content.decode()
        assert "gc-sources" in content
        # URLs must be displayed as text, never as href attributes.
        assert 'href="http' not in content
        assert 'href="https' not in content


class TestGuidanceCardAccessibility:
    def test_guidance_card_has_accessible_headings(self):
        call_command("seed_demo", scenario="drift_day6", reset=True)
        day14 = _today() - timedelta(days=7)
        client = _client()
        response = client.get(f"/trend/resting_hr/?date={day14.isoformat()}")
        content = response.content.decode()
        assert "Status and reason" in content
        assert "Likely contributors" in content
        assert "What you can do" in content
        assert "Measure again in" in content
        assert "When to contact ground" in content
        assert "Sources" in content
        assert "<h4" in content  # headings are h4 elements
