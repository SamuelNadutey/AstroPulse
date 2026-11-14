"""Tests for Stage 5 trend charts (bundled Plotly, no network access)."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from core.charts import build_trend_figure, trend_summary
from core.services import indicator_trend
from engine.baseline import build_baseline
from engine.scoring import _MAD_SCALE

pytestmark = pytest.mark.django_db

DEMO_NAME = "Demo crew (SIMULATED)"


def _seed_drift_day6():
    call_command("seed_demo", scenario="drift_day6", reset=True)


def _drift_day6_hr(today=None):
    _seed_drift_day6()
    from core.models import CrewMember

    crew = CrewMember.objects.get(name=DEMO_NAME)
    today = today or timezone.localdate()
    data = indicator_trend(crew, "resting_hr", today)
    return crew, today, data


# --- build_trend_figure ---------------------------------------------------

def test_build_trend_figure_has_readings_trace():
    _, today, data = _drift_day6_hr()
    figure = build_trend_figure(
        data["indicator"], data["readings"], data["baseline"], data["limits_entry"]
    )
    readings_traces = [t for t in figure["data"] if t.get("mode") == "lines+markers"]
    assert len(readings_traces) == 1
    assert readings_traces[0]["name"] == "Resting heart rate"
    assert len(readings_traces[0]["x"]) == len(data["readings"])
    assert len(readings_traces[0]["y"]) == len(data["readings"])


def test_build_trend_figure_baseline_band_uses_engine_median_and_mad():
    _, today, data = _drift_day6_hr()
    baseline = data["baseline"]
    assert baseline.enough_data is True
    spread = max(data["indicator"]["mad_floor"], _MAD_SCALE * baseline.mad)
    expected_upper = baseline.median + 2.0 * spread
    expected_lower = baseline.median - 2.0 * spread

    figure = build_trend_figure(
        data["indicator"], data["readings"], baseline, data["limits_entry"]
    )
    upper = [t for t in figure["data"] if t.get("fill") == "tonexty"][0]
    lower = [
        t
        for t in figure["data"]
        if t.get("fill") is None
        and t.get("line", {}).get("width") == 0
        and t.get("showlegend") is False
    ][0]
    assert all(v == expected_upper for v in upper["y"])
    assert all(v == expected_lower for v in lower["y"])


def test_build_trend_figure_has_limit_lines():
    _, today, data = _drift_day6_hr()
    figure = build_trend_figure(
        data["indicator"],
        data["readings"],
        baseline=None,
        limits_entry=data["limits_entry"],
    )
    shapes = figure["layout"].get("shapes", [])
    assert len(shapes) == 3  # yellow, orange, red dotted lines
    assert all(s["type"] == "line" and s["line"]["dash"] == "dot" for s in shapes)
    annotations = figure["layout"].get("annotations", [])
    assert len(annotations) == 3


# --- views ----------------------------------------------------------------

def test_trend_page_loads_with_bundled_plotly_only():
    _seed_drift_day6()
    client = Client()
    response = client.get("/trend/resting_hr/")
    assert response.status_code == 200
    content = response.content.decode()
    # Bundled Plotly from vendor, no CDN / external URL.
    assert "vendor/plotly-basic.min.js" in content
    assert 'src="http' not in content
    assert 'src="https' not in content
    # Figure embedded via json_script for client-side Plotly.newPlot.
    assert "trend-figure-data" in content
    assert "trend-plot" in content
    assert "Resting heart rate trend" in content
    assert "placeholders, not clinical values" in content


def test_trend_chart_partial_for_htmx():
    _seed_drift_day6()
    client = Client()
    response = client.get("/trend/resting_hr/chart/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    content = response.content.decode()
    assert "trend-plot" in content
    assert "trend-figure-data" in content
    assert "Show data table" in content


def test_trend_chart_partial_has_summary_and_table():
    _seed_drift_day6()
    client = Client()
    response = client.get("/trend/resting_hr/chart/", HTTP_HX_REQUEST="true")
    content = response.content.decode()
    assert "Last 14 days" in content
    assert "rose" in content or "fell" in content or "stayed flat" in content
    assert "<table" in content
    assert "<th>Date</th>" in content


def test_unknown_trend_indicator_is_404():
    client = Client()
    assert client.get("/trend/nope/").status_code == 404


# --- acceptance: drift_day6 resting HR drift is obvious ------------------

def test_drift_day6_resting_hr_trend_shows_clear_drift():
    _seed_drift_day6()
    client = Client()
    response = client.get("/trend/resting_hr/")
    assert response.status_code == 200
    content = response.content.decode()
    # The summary describes the rise (drift) in plain text.
    assert "Last 14 days: Resting heart rate rose" in content
    # The figure carries the readings and the baseline band.
    assert "trend-figure-data" in content
    assert "trend-plot" in content


def test_trend_summary_uses_baseline_median():
    _, today, data = _drift_day6_hr()
    summary = trend_summary(data["indicator"], data["readings"], data["baseline"])
    assert "baseline median is" in summary
    assert f"{data['baseline'].median:.1f}" in summary
