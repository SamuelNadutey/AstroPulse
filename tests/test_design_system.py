"""Contracts for the Figma-derived Django design system."""
import re
from pathlib import Path

import pytest
from django.template.loader import render_to_string

from core.charts import CHART_PALETTE

BASE_DIR = Path(__file__).resolve().parent.parent
APP_CSS = BASE_DIR / "core" / "static" / "core" / "app.css"
BASE_TEMPLATE = BASE_DIR / "core" / "templates" / "core" / "base.html"

SEVERITY_WORDS = {
    "gray": "Not enough data",
    "green": "Normal",
    "yellow": "Watch",
    "orange": "Concern",
    "red": "Contact ground",
}
PALETTE_TOKENS = {
    "text": "--ink",
    "muted": "--muted",
    "line": "--line",
    "paper": "--surface-raised",
    "reading": "--brand-deep",
    "brand": "--brand",
    "band": "--brand-band",
    "insufficient": "--status-insufficient",
    "normal": "--status-normal",
    "watch": "--status-watch",
    "concern": "--status-concern",
    "contact": "--status-contact",
}


def _tokens(css):
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css))


def test_footer_has_exact_text_and_at_least_14px_style():
    css = APP_CSS.read_text(encoding="utf-8")
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    tokens = _tokens(css)
    assert "Decision support, not a diagnosis." in template
    assert re.search(r"\.site-footer\s*\{[^}]*font-size:\s*var\(--text-14\)", css)
    assert tokens["--text-14"].strip() == "14px"


def test_no_app_css_font_size_is_below_12px():
    css = APP_CSS.read_text(encoding="utf-8")
    tokens = _tokens(css)
    for value in re.findall(r"font-size\s*:\s*([^;}]+)", css):
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)px\s*", value)
        if match:
            assert float(match.group(1)) >= 12, f"font size below 12px: {value}"
        elif value.strip().startswith("var(--text-"):
            token = value.strip()[4:-1]
            assert float(tokens[token].replace("px", "")) >= 12, token


@pytest.mark.parametrize("severity,word", SEVERITY_WORDS.items())
def test_shared_status_glyph_has_icon_word_and_severity_class(severity, word):
    html = render_to_string("core/_status_glyph.html", {"severity": severity})
    assert "<svg" in html
    assert word in html
    assert f"sev-{severity}" in html
    if severity == "red":
        assert ">!</text>" in html


def test_app_css_has_no_import_or_url_function():
    css = APP_CSS.read_text(encoding="utf-8")
    assert "@import" not in css.lower()
    assert "url(" not in css.lower()


@pytest.mark.django_db
def test_base_has_skip_link_and_active_navigation_marker(client):
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert 'class="skip-link" href="#main"' in template
    response = client.get("/status/")
    content = response.content.decode()
    assert re.search(r'<a href="/status/" aria-current="page">', content)
    assert 'aria-expanded="false" aria-controls="primary-navigation"' in template


def test_chart_palette_matches_app_css_tokens():
    tokens = _tokens(APP_CSS.read_text(encoding="utf-8"))
    for chart_name, css_token in PALETTE_TOKENS.items():
        assert CHART_PALETTE[chart_name] == tokens[css_token].strip()
