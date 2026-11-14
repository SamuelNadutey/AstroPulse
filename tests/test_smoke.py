"""Smoke tests for the AstroPulse skeleton."""
import pytest
from django.urls import reverse

FOOTER_TEXT = b"Decision support, not a diagnosis."


@pytest.mark.django_db
def test_home_returns_200(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_home_shows_the_dashboard(client):
    # / is the dashboard entry point (same view as /status/).
    response = client.get(reverse("core:home"))
    assert b"Dashboard" in response.content
    assert b"No data yet" in response.content


@pytest.mark.django_db
def test_footer_text_present(client):
    response = client.get(reverse("core:home"))
    assert FOOTER_TEXT in response.content
