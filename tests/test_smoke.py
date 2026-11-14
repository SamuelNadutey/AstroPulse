"""Smoke tests for the AstroPulse skeleton."""
from django.urls import reverse

FOOTER_TEXT = b"Decision support, not a diagnosis."


def test_home_returns_200(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200


def test_home_shows_running_message(client):
    response = client.get(reverse("core:home"))
    assert b"AstroPulse is running" in response.content


def test_footer_text_present(client):
    response = client.get(reverse("core:home"))
    assert FOOTER_TEXT in response.content
