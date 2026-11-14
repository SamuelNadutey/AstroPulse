"""Validation for guidance rules and citations.

Enforces the project rule: no guidance without a source. Every rule and every
suggested action must reference an id in ``data/sources.json``. TODO placeholders
are allowed during development but are flagged so they can be listed in
``docs/PROGRESS.md``.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.services import load_indicators

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class GuidanceValidationError(Exception):
    """Raised when guidance data fails validation."""

    pass


def _load_json(filename: str):
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_sources() -> list[dict]:
    """Load ``data/sources.json`` as a list."""
    return _load_json("sources.json")


def load_guidance() -> list[dict]:
    """Load ``data/guidance.json`` as a list."""
    return _load_json("guidance.json")


def _valid_trigger(trigger) -> bool:
    if not isinstance(trigger, dict):
        return False
    if trigger.get("drift") is True:
        return True
    severity = trigger.get("severity")
    return severity in {"yellow", "orange", "red"}


def collect_errors(
    guidance: list[dict] | None = None,
    sources: list[dict] | None = None,
    indicators: list[dict] | None = None,
    *,
    strict: bool = False,
) -> list[str]:
    """Return every validation problem, one string per line.

    With ``strict=True``, also report sources that are not yet verified.
    """
    if guidance is None:
        guidance = load_guidance()
    if sources is None:
        sources = load_sources()
    if indicators is None:
        indicators = load_indicators()

    source_ids = {s["id"] for s in sources}
    indicator_keys = {i["key"] for i in indicators}

    errors: list[str] = []
    seen_ids: set[str] = set()

    for rule in guidance:
        rid = rule.get("id")
        if rid in seen_ids:
            errors.append(f"RULE {rid}: duplicate id")
        seen_ids.add(rid)

        if not rule.get("headline"):
            errors.append(f"RULE {rid}: missing headline")

        indicator_key = rule.get("indicator_key")
        if indicator_key not in indicator_keys:
            errors.append(f"RULE {rid}: unknown indicator_key '{indicator_key}'")

        if not _valid_trigger(rule.get("trigger")):
            errors.append(f"RULE {rid}: invalid trigger")

        rule_sources = rule.get("source_ids")
        if not rule_sources:
            errors.append(f"RULE {rid}: no source_ids")
        else:
            if "TODO" in rule_sources:
                errors.append(f"RULE {rid}: uses TODO source")
            for sid in rule_sources:
                if sid != "TODO" and sid not in source_ids:
                    errors.append(f"RULE {rid}: unknown source id '{sid}'")

        if not rule.get("contact_ground_text"):
            errors.append(f"RULE {rid}: missing contact_ground_text")

        for action in rule.get("suggested_actions", []):
            aid = action.get("id")
            action_sources = action.get("source_ids")
            if not action_sources:
                errors.append(f"RULE {rid} ACTION {aid}: no source_ids")
            else:
                if "TODO" in action_sources:
                    errors.append(f"RULE {rid} ACTION {aid}: uses TODO source")
                for sid in action_sources:
                    if sid != "TODO" and sid not in source_ids:
                        errors.append(
                            f"RULE {rid} ACTION {aid}: unknown source id '{sid}'"
                        )

    if strict:
        for src in sources:
            if not src.get("verified"):
                errors.append(f"SOURCE {src['id']}: not verified")

    return errors


def list_needs_source(guidance: list[dict] | None = None) -> list[str]:
    """Return a human-readable list of rules/actions that use the TODO source."""
    if guidance is None:
        guidance = load_guidance()

    needs: list[str] = []
    for rule in guidance:
        rid = rule.get("id")
        if "TODO" in rule.get("source_ids", []):
            needs.append(f"RULE {rid}")
        for action in rule.get("suggested_actions", []):
            if "TODO" in action.get("source_ids", []):
                needs.append(f"RULE {rid} ACTION {action.get('id')}")
    return needs


def validate_guidance_data(
    guidance: list[dict] | None = None,
    sources: list[dict] | None = None,
    indicators: list[dict] | None = None,
    *,
    strict: bool = False,
) -> None:
    """Raise :class:`GuidanceValidationError` if there are any problems."""
    errors = collect_errors(guidance, sources, indicators, strict=strict)
    if errors:
        raise GuidanceValidationError("\n".join(errors))
