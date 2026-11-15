"""Views for AstroPulse.

Server-rendered templates plus one HTMX partial for the check-in form
environment switcher. Every page inherits the footer:
'Decision support, not a diagnosis.'

No engine math lives here: status results come from core.services
(run_status_for), which calls the pure engine.
"""
from datetime import timedelta
from types import SimpleNamespace

from django.http import Http404, HttpResponse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.forms import CheckInForm
from core.models import ActionLog, CheckIn, CrewMember, Reading, RelayItem
from core.charts import build_trend_figure, trend_summary
from core.guidance import select_guidance
from core.services import (
    REGION_LABELS,
    SEVERITY_GREEN,
    SEVERITY_GRAY,
    SEVERITY_ORANGE,
    SEVERITY_RED,
    SEVERITY_YELLOW,
    blackout_active_for,
    current_blackout,
    get_environment,
    indicator_trend,
    load_indicators,
    log_action,
    progress_for,
    region_statuses,
    run_status_for,
    set_blackout,
    worst_severity,
    BASELINE_DAYS,
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


def _status_entry_for(crew_member, indicator_key, date):
    """Return the status entry for one indicator on a given date, or None."""
    for entry in run_status_for(crew_member, date):
        if entry["key"] == indicator_key:
            return entry
    return None


def _guidance_for(status_result, indicator_key):
    """Wrap a status result so select_guidance can pick a rule by indicator key."""
    if status_result is None:
        return None
    wrapper = SimpleNamespace(
        severity=status_result.severity,
        indicator_key=indicator_key,
        drift=False,
    )
    return select_guidance(wrapper)


def home(request):
    """Serve the Today dashboard at the root entry point."""
    return status(request)


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
        form = CheckInForm(
            environment=request.GET.get("environment", "station"),
            initial={"blackout": current_blackout()},
        )
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
        "last_checkin": None,
        "environment": None,
        "hero_reason": "Complete a check-in to establish your personal baseline.",
        "body_region_data": [],
        "empty_indicators": [
            {"label": item["label"], "unit": item["unit"]}
            for item in load_indicators()
        ],
    }
    if crew is not None:
        context["last_checkin"] = CheckIn.objects.filter(
            crew_member=crew
        ).order_by("-date").first()
        selected_checkin = CheckIn.objects.filter(
            crew_member=crew, date=date
        ).first() or context["last_checkin"]
        if selected_checkin:
            context["environment"] = get_environment(selected_checkin.environment)
        entries = run_status_for(crew, date)
        for entry in entries:
            entry["display"] = SEVERITY_DISPLAY[entry["result"].severity]
        context["entries"] = entries
        context["regions"] = region_statuses(entries)
        for region in context["regions"]:
            region["display"] = SEVERITY_DISPLAY[region["severity"]]
        context["body_region_data"] = [
            {
                "name": region["name"],
                "label": region["label"],
                "severity": region["severity"],
                "word": region["display"]["word"],
            }
            for region in context["regions"]
        ]
        context["overall"] = _overall(entries)
        flagged = [
            reason
            for entry in entries
            if entry["result"].severity in (SEVERITY_YELLOW, SEVERITY_ORANGE, SEVERITY_RED)
            for reason in entry["result"].reasons
        ]
        if flagged:
            context["hero_reason"] = flagged[0]
        elif entries and context["overall"]["severity"] == SEVERITY_GREEN:
            context["hero_reason"] = "Current readings are within the available personal reference and placeholder limit checks."
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
            entry["guidance"] = _guidance_for(entry["result"], entry["key"])
        region_info["is_simulated"] = any(
            e["is_simulated"] for e in region_info["entries"]
        )
    region_info["display"] = SEVERITY_DISPLAY[region_info["severity"]]
    context = {"region": region_info, "date": date}
    template = (
        "core/_region_detail.html"
        if request.headers.get("HX-Request")
        else "core/region.html"
    )
    return render(request, template, context)


def trend(request, indicator_key: str):
    """Trend page for one indicator: bundled Plotly chart + selector.

    The figure is built by core.charts (engine baseline + limits only) and
    embedded through json_script; Plotly.newPlot runs client-side against
    the locally bundled Plotly script. No external data is fetched.
    """
    config = next(
        (c for c in load_indicators() if c["key"] == indicator_key), None
    )
    if config is None:
        raise Http404(f"Unknown indicator: {indicator_key}")
    crew = _current_crew()
    date = _clean_date(request.GET.get("date"))
    context = {
        "indicator": config,
        "date": date,
        "indicators": load_indicators(),
        "figure": None,
        "summary": None,
    }
    if crew is not None:
        data = indicator_trend(crew, indicator_key, date)
        if data is not None:
            figure = build_trend_figure(
                data["indicator"],
                data["readings"],
                data["baseline"],
                data["limits_entry"],
            )
            context["figure"] = figure
            context["summary"] = trend_summary(
                data["indicator"], data["readings"], data["baseline"]
            )
            context["readings"] = data["readings"]
            context["is_simulated"] = any(
                bool(getattr(r, "is_simulated", False))
                for r in Reading.objects.filter(
                    crew_member=crew, indicator_key=indicator_key,
                    recorded_at__gte=date - timedelta(days=BASELINE_DAYS),
                    recorded_at__lte=date,
                )
            )
        entry = _status_entry_for(crew, indicator_key, date)
        if entry is not None:
            context["status_result"] = entry["result"]
            context["status_display"] = SEVERITY_DISPLAY[entry["result"].severity]
            context["guidance"] = _guidance_for(entry["result"], indicator_key)
        else:
            context["status_result"] = SimpleNamespace(
                severity=SEVERITY_GRAY,
                reasons=["Not enough data yet for this indicator."],
            )
            context["status_display"] = SEVERITY_DISPLAY[SEVERITY_GRAY]
            context["guidance"] = None
    if request.headers.get("HX-Request"):
        return render(request, "core/_trend_chart.html", context)
    return render(request, "core/trend.html", context)


def trend_chart(request, indicator_key: str):
    """HTMX partial: trend chart container for one indicator.

    Swapped into #trend-container by the chart selector on /trend/<key>/.
    """
    return trend(request, indicator_key)


def blackout_toggle(request):
    """Toggle the global blackout state from the header switch.

    Accepts POST (and GET for simplicity in tests). Redirects back to the
    referring page, or home if no referrer is provided.
    """
    if request.method == "POST":
        set_blackout(request.POST.get("blackout") == "on")
    else:
        set_blackout(request.GET.get("blackout") == "on")
    return redirect(request.META.get("HTTP_REFERER") or "core:home")


def _relay_context(crew_member, date):
    """Build the context shared by /relay/ and the export view."""
    week_start = date - timedelta(days=6)
    open_items = RelayItem.objects.filter(
        crew_member=crew_member, resolved=False
    ).order_by("-for_date", "indicator_key")
    recent_items = RelayItem.objects.filter(
        crew_member=crew_member,
        for_date__gte=week_start,
        for_date__lte=date,
        severity__in=(SEVERITY_ORANGE, SEVERITY_RED),
    ).order_by("-for_date", "indicator_key")
    contact_open = RelayItem.objects.filter(
        crew_member=crew_member, contact_ground_open=True, resolved=False
    ).order_by("-for_date", "indicator_key")
    any_simulated = Reading.objects.filter(
        crew_member=crew_member,
        recorded_at__gte=week_start,
        recorded_at__lte=date,
        is_simulated=True,
    ).exists()
    return {
        "crew": crew_member,
        "date": date,
        "open_items": open_items,
        "recent_items": recent_items,
        "contact_open": contact_open,
        "any_simulated": any_simulated,
    }


def relay(request):
    """Relay summary page: open items, recent flags, unresolved contact-ground."""
    crew = _current_crew()
    if crew is None:
        return render(request, "core/relay.html", {"crew": None})
    date = _clean_date(request.GET.get("date"))
    # Ensure relay items are current for the requested date if blackout is on.
    if blackout_active_for(crew, date):
        run_status_for(crew, date)
    context = _relay_context(crew, date)
    return render(request, "core/relay.html", context)


def relay_resolve(request, item_id: int):
    """Mark a relay item resolved with an optional note (HTMX-aware)."""
    item = get_object_or_404(RelayItem, pk=item_id)
    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        item.resolved = True
        item.resolved_at = timezone.now()
        item.resolved_note = note
        item.save(update_fields=["resolved", "resolved_at", "resolved_note", "updated_at"])
    if request.headers.get("HX-Request"):
        return render(request, "core/_relay_item.html", {"item": item})
    return redirect("core:relay")


def _format_relay_summary(context) -> str:
    """Render the relay summary as plain text for radio read-back."""
    lines: list[str] = []
    crew = context.get("crew")
    if crew is None:
        return "No crew member selected.\n"

    date = context["date"]
    week_start = date - timedelta(days=6)
    lines.append(f"AstroPulse relay summary")
    lines.append(f"Crew: {crew.name}")
    lines.append(f"Date range: {week_start.isoformat()} to {date.isoformat()}")

    # Environment for the requested date; fall back to the most recent check-in.
    from core.models import CheckIn

    checkin = CheckIn.objects.filter(crew_member=crew, date=date).first()
    if checkin is None:
        checkin = CheckIn.objects.filter(crew_member=crew).order_by("-date").first()
    env = checkin.environment if checkin else "unknown"
    lines.append(f"Environment: {env}")
    lines.append("")

    open_items = list(context["open_items"])
    recent_items = list(context["recent_items"])
    contact_open = list(context["contact_open"])

    if recent_items:
        lines.append("Flagged indicators (last 7 days):")
        for item in recent_items:
            display = SEVERITY_DISPLAY.get(item.severity, {"word": item.severity})
            lines.append(f"- {item.indicator_key}: {display['word']} (severity {item.severity})")
            if item.headline:
                lines.append(f"  {item.headline}")
            if item.reason:
                lines.append(f"  Reason: {item.reason}")
            if item.action_taken:
                lines.append(f"  Action taken: {item.action_taken}")
        lines.append("")
    else:
        lines.append("No flagged indicators in the last 7 days.")
        lines.append("")

    if contact_open:
        lines.append("Open contact-ground items:")
        for item in contact_open:
            lines.append(f"- {item.indicator_key} on {item.for_date.isoformat()}: {item.headline}")
        lines.append("")

    if open_items:
        lines.append(f"Total open relay items: {len(open_items)}")
        for item in open_items:
            lines.append(f"- {item.indicator_key} {item.for_date.isoformat()}: {item.headline}")
        lines.append("")

    if context.get("any_simulated"):
        lines.append("Decision support, not a diagnosis. Simulated demonstration data.")
    else:
        lines.append("Decision support, not a diagnosis.")
    lines.append("")
    lines.append("Data stays on this device. Export generated only on request.")
    return "\n".join(lines)


def relay_export(request):
    """Download the relay summary as a plain-text file."""
    crew = _current_crew()
    if crew is None:
        text = "No crew member selected.\n"
    else:
        date = _clean_date(request.GET.get("date"))
        if blackout_active_for(crew, date):
            run_status_for(crew, date)
        context = _relay_context(crew, date)
        text = _format_relay_summary(context)

    filename = f"relay_summary_{timezone.localdate().isoformat()}.txt"
    response = HttpResponse(text, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def log_action_view(request):
    """Log a suggested action as completed (HTMX-aware).

    Expects POST params: date, indicator_key, action_id, action_text.
    Returns a small partial with the action marked done.
    """
    if request.method != "POST":
        raise Http404("Action logging requires POST.")

    crew = _current_crew()
    if crew is None:
        raise Http404("No crew member selected.")

    raw_date = request.POST.get("date")
    date = parse_date(raw_date) if raw_date else None
    if date is None:
        date = timezone.localdate()

    indicator_key = request.POST.get("indicator_key", "").strip()
    action_id = request.POST.get("action_id", "").strip()
    action_text = request.POST.get("action_text", "").strip()
    if not indicator_key or not action_id:
        raise Http404("indicator_key and action_id are required.")

    log_action(crew, date, indicator_key, action_id, action_text)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "core/_action_done.html",
            {
                "indicator_key": indicator_key,
                "action_id": action_id,
                "action_text": action_text,
            },
        )
    return redirect(request.META.get("HTTP_REFERER") or "core:status")


def progress(request):
    """Progress view: streaks, weekly check-ins, and a completion-based score."""
    crew = _current_crew()
    if crew is None:
        return render(request, "core/progress.html", {"crew": None})
    date = _clean_date(request.GET.get("date"))
    context = {"crew": crew, "date": date}
    context.update(progress_for(crew, date))
    return render(request, "core/progress.html", context)
