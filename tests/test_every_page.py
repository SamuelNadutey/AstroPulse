"""Every page in the project renders with seeded demo data.

For each scenario in ``simulator.generator.SCENARIOS``, assert that every
main URL returns 200, renders the footer line 'Decision support, not a
diagnosis.', and labels the demo data SIMULATED.

``/relay/export/`` is a plain-text download rather than an HTML page, so it
is asserted separately (200, text/plain, correct filename, no footer).
``/checkin/fields/`` and ``/region/<name>/`` are HTMX partials and are
asserted for 200 (plus the SIMULATED badge for regions).
``/relay/<id>/resolve/`` is POST-only and intentionally not requested here.
"""
import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from simulator.generator import SCENARIOS
from core.models import CrewMember, RelayItem

FOOTER_TEXT = b"Decision support, not a diagnosis."
SIMULATED = b"SIMULATED"

# Region detail is an HTMX partial (no base template, so no footer); it is
# asserted for 200 and the SIMULATED badge instead. Seeded data is simulated,
# so the badge must appear.
FULL_PAGES = (
    ["", "checkin/", "status/", "progress/", "relay/"]
    + [f"trend/{key}/" for key in (
        "resting_hr", "sleep_hours", "temperature", "mood", "exercise_min", "spo2"
    )]
)

# HTMX partials render into a panel rather than the base template.
# The field-swap partial is asserted for 200 only; region partials include
# per-indicator SIMULATED badges, so those are asserted too.
FIELD_PARTIALS = ["checkin/fields/"]
REGION_PARTIALS = [
    f"region/{region}/" for region in ("head", "chest", "lungs", "torso", "legs")
]


@pytest.mark.django_db
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("url", FULL_PAGES)
def test_every_page_returns_200_with_footer_and_simulated_badge(client, scenario, url):
    call_command("seed_demo", scenario=scenario, reset=True)
    response = client.get(f"/{url}")
    assert response.status_code == 200, f"{url} -> {response.status_code}"
    assert FOOTER_TEXT in response.content, f"footer missing on {url}"
    assert SIMULATED in response.content, f"SIMULATED badge missing on {url}"


@pytest.mark.django_db
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("url", FIELD_PARTIALS)
def test_htmx_field_partial_returns_200(client, scenario, url):
    call_command("seed_demo", scenario=scenario, reset=True)
    response = client.get(f"/{url}")
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("url", REGION_PARTIALS)
def test_region_partials_return_200_and_simulated_badge(client, scenario, url):
    call_command("seed_demo", scenario=scenario, reset=True)
    response = client.get(f"/{url}")
    assert response.status_code == 200
    assert SIMULATED in response.content, f"SIMULATED badge missing on {url}"


@pytest.mark.django_db
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_relay_export_is_a_plain_text_download(client, scenario):
    call_command("seed_demo", scenario=scenario, reset=True)
    today = timezone.localdate().isoformat()
    # Seed one relay item so the download has content to export.
    crew = CrewMember.objects.get(name="Demo crew (SIMULATED)")
    RelayItem.objects.get_or_create(
        crew_member=crew,
        for_date=timezone.localdate(),
        indicator_key="resting_hr",
        defaults={"severity": "orange", "headline": "Demo export item"},
    )
    response = client.get(reverse("core:relay_export"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert f'relay_summary_{today}.txt' in response["Content-Disposition"]
    # The export is not an HTML page: it carries the plain-text safety line.
    assert b"Decision support, not a diagnosis." in response.content
