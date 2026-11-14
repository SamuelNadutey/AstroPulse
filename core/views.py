"""Views for AstroPulse.

Server-rendered templates plus one HTMX partial for the check-in form
environment switcher. Every page inherits the footer:
'Decision support, not a diagnosis.'

No engine math lives here: status results come from core.services
(run_status_for), which calls the pure engine.
"""
from django.http import Http404
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.forms import CheckInForm
from core.models import CheckIn, CrewMember, Reading
from core.services import (
    REGION_LABELS,
    SEVERITY_GREEN,
    SEVERITY_GRAY,
    SEVERITY_ORANGE,
    SEVERITY_RED,
    SEVERITY_YELLOW,
    load_indicators,
    region_statuses,
    run_status_for,
    worst_severity,
)

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


def _clean_date(raw):
    """Parse a ?date= query parameter for the dashboard.

    Invalid or future dates fall back to today: the dashboard describes the
    present, and past dates exist so a seeded demo scenario can be reviewed
    day by day.
    """
    today = timezone.localdate()
    parsed = parse_date(raw) if raw else None
    if parsed is None or parsed > today:
        return today
    return parsed


def _overall(entries):
    """Overall banner info: the worst severity across all indicators."""
    if not entries:
        return {
            "severity": SEVERITY_GRAY,
            **SEVERITY_DISPLAY[SEVERITY_GRAY],
            "is_simulated": False,
        }
    severity = worst_severity([e["result"].severity for e in entries])
    word = (
        "All indicators normal"
        if severity == SEVERITY_GREEN
        else SEVERITY_DISPLAY[severity]["word"]
    )
    return {
        "severity": severity,
        "word": word,
        "shape": SEVERITY_DISPLAY[severity]["shape"],
        "is_simulated": any(e["is_simulated"] for e in entries),
    }


def _legend():
    """Legend items in severity order (icon + word + color, never color alone)."""
    return [
        {"severity": severity, **SEVERITY_DISPLAY[severity]}
        for severity in (
            SEVERITY_GRAY,
            SEVERITY_GREEN,
            SEVERITY_YELLOW,
            SEVERITY_ORANGE,
            SEVERITY_RED,
        )
    ]


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
    """Status dashboard: body map + region detail panel + overall banner.

    ?date=YYYY-MM-DD reviews a past day (placeholder demo support, e.g. the
    seeded drift_day6 scenario); invalid or future dates fall back to today.
    """
    crew = _current_crew()
    date = _clean_date(request.GET.get("date"))
    context = {
        "entries": [],
        "regions": [],
        "legend": _legend(),
        "overall": _overall([]),
        "crew": crew,
        "date": date,
    }
    if crew is not None:
        entries = run_status_for(crew, date)
        for entry in entries:
            entry["display"] = SEVERITY_DISPLAY[entry["result"].severity]
        context["entries"] = entries
        context["regions"] = region_statuses(entries)
        for region in context["regions"]:
            region["display"] = SEVERITY_DISPLAY[region["severity"]]
        context["overall"] = _overall(entries)
    return render(request, "core/status.html", context)


def region_detail(request, region: str):
    """HTMX partial: detail panel for one body region.

    Shows today's (or the selected ?date=) value, severity icon + text +
    color and reasons for each indicator mapped to the region, plus a
    "View trend" link per indicator (trend charts arrive in Stage 5).
    """
    if region not in REGION_LABELS:
        raise Http404(f"Unknown body region: {region}")
    crew = _current_crew()
    date = _clean_date(request.GET.get("date"))
    region_info = {
        "name": region,
        "label": REGION_LABELS[region],
        "severity": SEVERITY_GRAY,
        "entries": [],
        "is_simulated": False,
    }
    if crew is not None:
        entries = run_status_for(crew, date)
        regions = region_statuses(entries)
        region_info = next(r for r in regions if r["name"] == region)
        region_info["label"] = REGION_LABELS[region]
        for entry in region_info["entries"]:
            entry["display"] = SEVERITY_DISPLAY[entry["result"].severity]
        region_info["is_simulated"] = any(
            e["is_simulated"] for e in region_info["entries"]
        )
    region_info["display"] = SEVERITY_DISPLAY[region_info["severity"]]
    return render(
        request,
        "core/_region_detail.html",
        {"region": region_info, "date": date},
    )


def trend(request, indicator_key: str):
    """Placeholder page for one indicator's trend (charts arrive in Stage 5)."""
    config = next(
        (c for c in load_indicators() if c["key"] == indicator_key), None
    )
    if config is None:
        raise Http404(f"Unknown indicator: {indicator_key}")
    return render(request, "core/trend.html", {"indicator": config})
