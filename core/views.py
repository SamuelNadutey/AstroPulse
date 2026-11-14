"""Views for AstroPulse.

Server-rendered templates plus one HTMX partial for the check-in form
environment switcher. Every page inherits the footer:
'Decision support, not a diagnosis.'

No engine math lives here: status results come from core.services
(run_status_for), which calls the pure engine.
"""
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import CheckInForm
from core.models import CheckIn, CrewMember, Reading
from core.services import run_status_for

# Single local crew member for real (non-simulated) check-ins until the
# dashboard/auth stage introduces profiles. Demo seeding creates its own
# "Demo crew (SIMULATED)" member.
LOCAL_CREW_NAME = "You (local)"

# Severity display: icon shape + plain word + color class. Severity is always
# shown as icon + text + color, never color alone (AGENTS.md hard rule 5).
# These words are placeholder UI copy, not clinical instructions.
SEVERITY_DISPLAY = {
    "gray": {"shape": "circle-empty", "word": "Not enough data"},
    "green": {"shape": "circle", "word": "Normal"},
    "yellow": {"shape": "triangle", "word": "Watch"},
    "orange": {"shape": "diamond", "word": "Concern"},
    "red": {"shape": "octagon", "word": "Contact ground"},
}


def _current_crew():
    """The crew member shown on /status/: the latest check-in wins.

    Falls back to the first crew member (so seeded demo data shows even
    before a real check-in exists), then to None.
    """
    latest = (
        CheckIn.objects.select_related("crew_member")
        .order_by("-date", "-pk")
        .first()
    )
    return latest.crew_member if latest else CrewMember.objects.first()


def home(request):
    """Home page placeholder: confirms the Django project is running."""
    return render(request, "core/home.html")


def checkin(request):
    """Daily check-in: GET shows the form, POST saves readings + check-in.

    A re-check-in for the same day replaces that day's readings (Reading is
    unique per crew member, indicator and date) and updates the CheckIn.
    """
    today = timezone.localdate()
    if request.method == "POST":
        form = CheckInForm(
            environment=request.POST.get("environment") or "station",
            data=request.POST,
        )
        if form.is_valid():
            crew, _ = CrewMember.objects.get_or_create(name=LOCAL_CREW_NAME)
            environment = form.cleaned_data["environment"]
            blackout = form.cleaned_data["blackout"]
            with transaction.atomic():
                Reading.objects.filter(crew_member=crew, recorded_at=today).delete()
                for key, value in form.indicator_values():
                    Reading.objects.create(
                        crew_member=crew,
                        indicator_key=key,
                        value=value,
                        recorded_at=today,
                        environment=environment,
                        in_blackout=blackout,
                    )
                CheckIn.objects.update_or_create(
                    crew_member=crew,
                    date=today,
                    defaults={
                        "environment": environment,
                        "in_blackout": blackout,
                        "note": form.cleaned_data["note"],
                    },
                )
            return redirect("core:status")
        form.link_errors_to_aria()
    else:
        form = CheckInForm(environment=request.GET.get("environment", "station"))
    return render(request, "core/checkin.html", {"form": form})


def checkin_fields(request):
    """HTMX partial: re-render the form fields for the chosen environment."""
    form = CheckInForm(environment=request.GET.get("environment", "station"))
    return render(request, "core/_form_fields.html", {"form": form})


def status(request):
    """Status placeholder page: severity icon + text + color per indicator."""
    crew = _current_crew()
    context = {"entries": [], "crew": crew}
    if crew is not None:
        entries = run_status_for(crew, timezone.localdate())
        for entry in entries:
            entry["display"] = SEVERITY_DISPLAY[entry["result"].severity]
        context["entries"] = entries
    return render(request, "core/status.html", context)
