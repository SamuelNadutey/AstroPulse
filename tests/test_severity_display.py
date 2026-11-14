"""Every severity renders as icon + text label + color class.

Renders the guidance card (the component used everywhere a severity is
shown) for each severity and asserts all three channels are present:

- icon: an inline <svg> marker,
- text: the severity word from the shared SEVERITY_DISPLAY mapping,
- color class: the ``sev-<severity>`` class on the card article.
"""
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

SEVERITY_WORDS = {
    "gray": "Not enough data",
    "green": "Normal",
    "yellow": "Watch",
    "orange": "Concern",
    "red": "Contact ground",
}

SEVERITY_SHAPES = {
    "gray": "circle-empty",
    "green": "circle",
    "yellow": "triangle",
    "orange": "diamond",
    "red": "octagon",
}


@pytest.mark.parametrize("severity", list(SEVERITY_WORDS))
def test_guidance_card_shows_icon_text_and_color_class(severity):
    result = SimpleNamespace(
        severity=severity,
        reasons=["A placeholder reason."],
        drift=False,
    )
    display = {
        "shape": SEVERITY_SHAPES[severity],
        "word": SEVERITY_WORDS[severity],
    }
    html = render_to_string(
        "core/_guidance_card.html",
        {
            "result": result,
            "display": display,
            "guidance": None,
            "indicator_key": "resting_hr",
            "date": None,
        },
    )
    # Icon: an inline SVG severity marker.
    assert "<svg" in html, f"{severity}: no icon rendered"
    # Text label: the severity word.
    assert SEVERITY_WORDS[severity] in html, f"{severity}: no text label"
    # Color class: sev-<severity> on the card.
    assert f"sev-{severity}" in html, f"{severity}: no color class"


@pytest.mark.parametrize("severity,shape", list(SEVERITY_SHAPES.items()))
def test_severity_icon_partial_renders_svg(severity, shape):
    html = render_to_string(
        "core/_severity_icon.html", {"shape": shape}
    )
    assert "<svg" in html
