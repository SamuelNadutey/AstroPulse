"""The real guidance data satisfies the sourcing rules.

Runs the project guidance validation against the real ``data/guidance.json``
and ``data/sources.json``. Two known, documented states make this different
from a naive ``errors == []`` assertion:

- 48 actions are intentionally TODO-sourced and hidden from the UI until the
  safety owner finds real sources (see docs/PROGRESS.md, "Needs a source").
  Those are tolerated; everything else must be clean.
- All sources are ``verified: false`` until a human checks each page
  (see docs/PROGRESS.md, "Needs human verification"). Strict mode exists to
  report that; it is expected to stay red until sign-off.
"""
from core.guidance import load_sources, select_guidance
from core.validation import collect_errors, list_needs_source, load_guidance, load_sources as load_source_list


def test_real_guidance_has_no_structural_errors():
    errors = collect_errors()
    remaining = [e for e in errors if "uses TODO source" not in e]
    assert remaining == [], (
        "Guidance data has structural problems:\n" + "\n".join(remaining)
    )


def test_every_rule_has_contact_ground_text_and_a_resolvable_source():
    source_ids = {entry["id"] for entry in load_source_list()}
    for rule in load_guidance():
        assert rule.get("contact_ground_text"), (
            f"RULE {rule.get('id')}: missing contact_ground_text"
        )
        rule_sources = [sid for sid in rule.get("source_ids", []) if sid != "TODO"]
        assert rule_sources, f"RULE {rule.get('id')}: no resolvable source id"
        for sid in rule_sources:
            assert sid in source_ids, f"RULE {rule.get('id')}: unknown source id {sid}"


def test_todo_actions_are_listed_for_progress_md():
    # The TODO list is documented in docs/PROGRESS.md ("Needs a source").
    needs = list_needs_source()
    assert needs, "expected the documented TODO-sourced actions to be listed"


def test_unsourced_actions_are_never_shown_in_guidance():
    # AGENTS.md hard rule 4: actions whose sources are TODO are hidden from
    # users. Every selected guidance rule must expose only actions with at
    # least one resolvable source.
    known = load_sources()
    for rule in load_guidance():
        trigger = rule.get("trigger", {})
        severity = trigger.get("severity") or (
            "yellow" if trigger.get("drift") else None
        )
        if severity not in ("yellow", "orange", "red"):
            continue
        result = select_guidance(
            type(
                "Result",
                (),
                {
                    "severity": severity,
                    "indicator_key": rule["indicator_key"],
                    "drift": bool(trigger.get("drift")),
                },
            )()
        )
        if result is None:
            continue
        for action in result.suggested_actions:
            assert any(
                sid != "TODO" and sid in known
                for sid in action.get("source_ids", [])
            ), f"action {action.get('id')} shown with no resolvable source"


def test_strict_mode_reports_unverified_sources():
    strict_errors = collect_errors(strict=True)
    assert any("not verified" in e for e in strict_errors), (
        "strict mode should report the pending human verification of sources"
    )
