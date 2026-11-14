"""Sourced guidance selection.

All guidance rules and citations live in ``data/guidance.json`` and
``data/sources.json``. Templates must display citations as plain text only
(title, publisher, year, URL); the URL is never a clickable link or loaded
resource (AGENTS.md hard rule 1 and 4).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from engine.status import (
    SEVERITY_GRAY,
    SEVERITY_GREEN,
    SEVERITY_ORANGE,
    SEVERITY_RED,
    SEVERITY_YELLOW,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Drift guidance has not been signed off by the safety owner
# (docs/GUIDANCE_REVIEW.md). While False, a yellow drift flag shows the normal
# yellow rule. Set to True only after sign-off.
DRIFT_GUIDANCE_APPROVED = False


@dataclass(frozen=True)
class GuidanceResult:
    """A guidance rule with its sources resolved from ``data/sources.json``."""

    id: str
    indicator_key: str
    trigger: dict
    headline: str
    likely_contributors: list[str]
    suggested_actions: list[dict]
    remeasure_after: str
    contact_ground_text: str
    source_ids: list[str]
    sources: list[dict]


@lru_cache(maxsize=1)
def load_sources() -> dict[str, dict]:
    """Return a mapping of source id -> source dict."""
    path = DATA_DIR / "sources.json"
    with path.open("r", encoding="utf-8") as f:
        entries = json.load(f)
    return {entry["id"]: entry for entry in entries}


@lru_cache(maxsize=1)
def load_guidance() -> list[dict]:
    """Return the list of guidance rules from ``data/guidance.json``."""
    path = DATA_DIR / "guidance.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _display_citation(source: dict) -> str:
    """Plain-text citation used by templates."""
    year = source.get("year")
    year_text = str(year) if year is not None else "n.d."
    return f"{source['title']}, {source['publisher']}, {year_text}"


def _indicator_key(status_result) -> str | None:
    """Extract an indicator key from a status result or mock object."""
    if hasattr(status_result, "indicator") and status_result.indicator is not None:
        return getattr(status_result.indicator, "key", None)
    return getattr(status_result, "indicator_key", None)


def _resolve_sources(source_ids: list[str]) -> list[dict]:
    """Return source dicts for ``source_ids``, with a display citation added."""
    all_sources = load_sources()
    resolved = []
    for sid in source_ids:
        if sid == "TODO":
            continue
        source = all_sources.get(sid)
        if source is None:
            continue
        display = source.copy()
        display["display_citation"] = _display_citation(source)
        resolved.append(display)
    return resolved


def _sourced_actions(actions: list[dict]) -> list[dict]:
    """Keep only actions with at least one source id that resolves.

    Actions still marked TODO (or citing unknown ids) are never shown to users
    (AGENTS.md hard rule 4).
    """
    known = load_sources()
    return [
        action
        for action in actions
        if any(sid != "TODO" and sid in known for sid in action.get("source_ids", []))
    ]


def _to_result(rule: dict) -> GuidanceResult:
    """Build a :class:`GuidanceResult` from a rule dict."""
    return GuidanceResult(
        id=rule["id"],
        indicator_key=rule["indicator_key"],
        trigger=rule["trigger"],
        headline=rule["headline"],
        likely_contributors=rule.get("likely_contributors", []),
        suggested_actions=_sourced_actions(rule.get("suggested_actions", [])),
        remeasure_after=rule.get("remeasure_after", ""),
        contact_ground_text=rule.get("contact_ground_text", ""),
        source_ids=rule.get("source_ids", []),
        sources=_resolve_sources(rule.get("source_ids", [])),
    )


def select_guidance(status_result) -> GuidanceResult | None:
    """Pick the right guidance rule for an engine StatusResult.

    ``status_result`` must expose ``severity`` and either an ``indicator``
    attribute with a ``key`` or a plain ``indicator_key`` attribute. Drift
    is read with ``getattr(status_result, 'drift', False)`` so it works
    before Stage 7 adds that field.

    Returns ``None`` for gray/green. For yellow, returns the drift rule when
    drift is flagged, otherwise the yellow rule. For orange/red, returns the
    matching severity rule even when drift is true.
    """
    severity = getattr(status_result, "severity", None)
    if severity in (SEVERITY_GRAY, SEVERITY_GREEN, None):
        return None

    indicator_key = _indicator_key(status_result)
    if not indicator_key:
        raise ValueError("status_result has no indicator key")

    rules = load_guidance()
    is_drift = bool(getattr(status_result, "drift", False)) and DRIFT_GUIDANCE_APPROVED

    if severity == SEVERITY_YELLOW and is_drift:
        for rule in rules:
            if (
                rule.get("indicator_key") == indicator_key
                and rule.get("trigger", {}).get("drift") is True
            ):
                return _to_result(rule)

    for rule in rules:
        if (
            rule.get("indicator_key") == indicator_key
            and rule.get("trigger", {}).get("severity") == severity
        ):
            return _to_result(rule)

    return None
