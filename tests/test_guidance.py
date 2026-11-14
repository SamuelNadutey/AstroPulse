"""Tests for the sourced-guidance system and its validation (Stage 6)."""
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.guidance import GuidanceResult, load_guidance, load_sources, select_guidance
from core.validation import (
    GuidanceValidationError,
    collect_errors,
    list_needs_source,
    validate_guidance_data,
)
from engine.status import (
    SEVERITY_GRAY,
    SEVERITY_GREEN,
    SEVERITY_ORANGE,
    SEVERITY_RED,
    SEVERITY_YELLOW,
)


# Helpers ------------------------------------------------------------------


def _make_rule(**overrides):
    """Return a minimal valid guidance rule; override fields as needed."""
    return {
        "id": "test.indicator.yellow",
        "indicator_key": "resting_hr",
        "trigger": {"severity": "yellow"},
        "headline": "Test headline",
        "likely_contributors": ["A", "B"],
        "suggested_actions": [
            {"id": "act-1", "text": "Do something.", "source_ids": ["src_arzeno_cv"]}
        ],
        "remeasure_after": "2 hours",
        "contact_ground_text": "Contact ground if it persists.",
        "source_ids": ["src_arzeno_cv"],
        **overrides,
    }


def _make_sources():
    return [
        {
            "id": "src_arzeno_cv",
            "title": "Arzeno cardiovascular",
            "publisher": "NASA",
            "year": None,
            "url": "https://example.com/arzeno",
            "supports": "x",
            "verified": False,
            "verify_note": "n",
        }
    ]


def _make_status(indicator_key, severity, drift=False):
    return SimpleNamespace(
        indicator_key=indicator_key,
        severity=severity,
        drift=drift,
    )


# Real-data validation ------------------------------------------------------


def test_real_data_has_no_structural_errors_except_todo():
    errors = collect_errors()
    non_todo = [e for e in errors if "uses TODO source" not in e]
    assert non_todo == []


@pytest.mark.xfail(strict=False, reason="Needs real sources, resolved before the Stage 10 audit")
def test_no_todo_sources():
    errors = collect_errors()
    todo_errors = [e for e in errors if "uses TODO source" in e]
    assert todo_errors == []


# Synthetic validation errors ----------------------------------------------


def test_missing_rule_source_ids():
    errors = collect_errors(
        guidance=[_make_rule(source_ids=[], id="rule.missing")],
        sources=_make_sources(),
    )
    assert "RULE rule.missing: no source_ids" in errors


def test_missing_action_source_ids():
    rule = _make_rule(
        id="rule.act.missing",
        suggested_actions=[{"id": "act-1", "text": "x"}],
    )
    errors = collect_errors(guidance=[rule], sources=_make_sources())
    assert "RULE rule.act.missing ACTION act-1: no source_ids" in errors


def test_unknown_rule_source_id():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.unknown", source_ids=["src_nope"])],
        sources=_make_sources(),
    )
    assert "RULE rule.unknown: unknown source id 'src_nope'" in errors


def test_unknown_action_source_id():
    rule = _make_rule(
        id="rule.act.unknown",
        suggested_actions=[
            {"id": "act-1", "text": "x", "source_ids": ["src_nope"]}
        ],
    )
    errors = collect_errors(guidance=[rule], sources=_make_sources())
    assert "RULE rule.act.unknown ACTION act-1: unknown source id 'src_nope'" in errors


def test_todo_rule_source():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.todo", source_ids=["TODO"])],
        sources=_make_sources(),
    )
    assert "RULE rule.todo: uses TODO source" in errors


def test_todo_action_source():
    rule = _make_rule(
        id="rule.act.todo",
        suggested_actions=[{"id": "act-1", "text": "x", "source_ids": ["TODO"]}],
    )
    errors = collect_errors(guidance=[rule], sources=_make_sources())
    assert "RULE rule.act.todo ACTION act-1: uses TODO source" in errors


def test_missing_contact_ground_text():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.contact", contact_ground_text="")],
        sources=_make_sources(),
    )
    assert "RULE rule.contact: missing contact_ground_text" in errors


def test_duplicate_rule_id():
    rule = _make_rule(id="rule.dup")
    errors = collect_errors(guidance=[rule, rule], sources=_make_sources())
    assert "RULE rule.dup: duplicate id" in errors


def test_unknown_indicator_key():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.ind", indicator_key="not_real")],
        sources=_make_sources(),
    )
    assert "RULE rule.ind: unknown indicator_key 'not_real'" in errors


def test_invalid_trigger():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.trig", trigger={"severity": "blue"})],
        sources=_make_sources(),
    )
    assert "RULE rule.trig: invalid trigger" in errors


def test_missing_headline():
    errors = collect_errors(
        guidance=[_make_rule(id="rule.head", headline="")],
        sources=_make_sources(),
    )
    assert "RULE rule.head: missing headline" in errors


def test_validate_guidance_data_raises():
    with pytest.raises(GuidanceValidationError) as exc:
        validate_guidance_data(
            guidance=[_make_rule(id="bad", source_ids=[])],
            sources=_make_sources(),
        )
    assert "RULE bad: no source_ids" in str(exc.value)


def test_strict_mode_reports_unverified_source():
    sources = [
        {
            "id": "src_unverified",
            "title": "x",
            "publisher": "y",
            "year": None,
            "url": "https://example.com",
            "supports": "z",
            "verified": False,
            "verify_note": "n",
        }
    ]
    errors = collect_errors(
        guidance=[_make_rule(id="rule.ok", source_ids=["src_unverified"])],
        sources=sources,
        strict=True,
    )
    assert "SOURCE src_unverified: not verified" in errors


# Rule coverage ------------------------------------------------------------


def test_all_indicators_have_four_rules():
    rules = load_guidance()
    assert len(rules) == 24
    indicators = {r["indicator_key"] for r in rules}
    assert indicators == {
        "resting_hr",
        "sleep_hours",
        "temperature",
        "mood",
        "exercise_min",
        "spo2",
    }
    for key in indicators:
        severities = {
            r["trigger"].get("severity")
            for r in rules
            if r["indicator_key"] == key and "severity" in r["trigger"]
        }
        assert severities == {"yellow", "orange", "red"}
        drift = [r for r in rules if r["indicator_key"] == key and r["trigger"].get("drift")]
        assert len(drift) == 1


# select_guidance ----------------------------------------------------------


def test_select_guidance_returns_none_for_green_and_gray():
    assert select_guidance(_make_status("resting_hr", SEVERITY_GREEN)) is None
    assert select_guidance(_make_status("resting_hr", SEVERITY_GRAY)) is None


@pytest.mark.parametrize("severity", [SEVERITY_YELLOW, SEVERITY_ORANGE, SEVERITY_RED])
def test_select_guidance_returns_rule_for_each_severity(severity):
    for key in ["resting_hr", "sleep_hours", "temperature", "mood", "exercise_min", "spo2"]:
        result = select_guidance(_make_status(key, severity))
        assert isinstance(result, GuidanceResult)
        assert result.indicator_key == key
        assert result.trigger.get("severity") == severity


def test_select_guidance_yellow_with_drift_returns_drift_rule():
    result = select_guidance(_make_status("resting_hr", SEVERITY_YELLOW, drift=True))
    assert result.id == "resting_hr.drift"


def test_select_guidance_yellow_without_drift_returns_yellow_rule():
    result = select_guidance(_make_status("resting_hr", SEVERITY_YELLOW, drift=False))
    assert result.id == "resting_hr.yellow"


@pytest.mark.parametrize("severity", [SEVERITY_ORANGE, SEVERITY_RED])
def test_select_guidance_drift_at_orange_red_returns_severity_rule(severity):
    result = select_guidance(_make_status("resting_hr", severity, drift=True))
    assert result.trigger.get("severity") == severity


# Sources and citations ----------------------------------------------------


def test_selected_guidance_has_resolved_sources():
    result = select_guidance(_make_status("resting_hr", SEVERITY_ORANGE))
    assert result.sources
    for src in result.sources:
        assert src.get("title")
        assert src.get("publisher")
        assert src.get("url")
        assert "display_citation" in src


ALLOWED_SOURCES = {
    "resting_hr": {"src_arzeno_cv", "src_otsuka_hrv"},
    "sleep_hours": {"src_nasa_sleep_evidence", "src_nasa_sleep_prd", "src_hera_2020"},
    "temperature": {"src_stahn_temp_2017"},
    "mood": {"src_nasa_behav_evidence", "src_nasa_behav_evidence_update", "src_nasa_behav_risk_page", "src_hera_2020"},
    "exercise_min": {"src_nasa_exercise_iws", "src_roberts_2025", "src_loerch_exercise"},
    "spo2": {"src_statpearls_pulseox"},
}
STD_SOURCE = "src_nasa_std_3001_v1"


def test_rule_sources_are_within_allowed_list():
    rules = load_guidance()
    for rule in rules:
        key = rule["indicator_key"]
        allowed = ALLOWED_SOURCES[key]
        for sid in rule["source_ids"]:
            is_red = rule["trigger"].get("severity") == "red"
            if is_red:
                assert sid in allowed or sid == STD_SOURCE, f"{rule['id']} uses {sid}"
            else:
                assert sid in allowed, f"{rule['id']} uses {sid}"


def test_red_contact_ground_text_differs_from_orange():
    rules = load_guidance()
    by_indicator = {}
    for r in rules:
        by_indicator.setdefault(r["indicator_key"], {})[
            r["trigger"].get("severity")
        ] = r
    for key, mapping in by_indicator.items():
        orange = mapping.get("orange")
        red = mapping.get("red")
        assert orange and red, key
        assert red["contact_ground_text"] != orange["contact_ground_text"]
        red_text = red["contact_ground_text"].lower()
        assert "now" in red_text or "as soon as" in red_text


# Content quality ----------------------------------------------------------


def test_no_digits_in_non_spo2_text_fields():
    rules = load_guidance()
    for rule in rules:
        if rule["indicator_key"] == "spo2":
            continue
        text_parts = [
            rule["headline"],
            rule["contact_ground_text"],
            *rule.get("likely_contributors", []),
        ]
        for action in rule.get("suggested_actions", []):
            text_parts.append(action.get("text", ""))
        for part in text_parts:
            assert not any(ch.isdigit() for ch in part), (
                f"{rule['id']} contains a digit: {part!r}"
            )


BANNED_PHRASES = ["you have", "you are suffering", "diagnosis of", "you are sick"]


def test_no_diagnosis_phrases_in_guidance():
    rules = load_guidance()
    for rule in rules:
        parts = [
            rule["headline"].lower(),
            rule["contact_ground_text"].lower(),
            *(c.lower() for c in rule.get("likely_contributors", [])),
        ]
        for action in rule.get("suggested_actions", []):
            parts.append(action.get("text", "").lower())
        combined = " ".join(parts)
        for phrase in BANNED_PHRASES:
            assert phrase not in combined, f"{rule['id']} contains '{phrase}'"


# Management command -------------------------------------------------------


def test_check_guidance_command_prints_ok(capsys):
    call_command("check_guidance")
    captured = capsys.readouterr()
    assert "OK" in captured.out
    assert "rules/actions still need a source" in captured.out
    assert "sources are not yet verified" in captured.out


def test_check_guidance_command_strict_fails():
    with pytest.raises(CommandError):
        call_command("check_guidance", "--strict")


def test_list_needs_source_matches_todo_errors():
    errors = collect_errors()
    todo_count = len([e for e in errors if "uses TODO source" in e])
    needs = list_needs_source()
    assert len(needs) == todo_count
    assert all("ACTION" in item or item.startswith("RULE ") for item in needs)
