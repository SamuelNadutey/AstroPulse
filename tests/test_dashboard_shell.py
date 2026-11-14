"""Phase 1 UI shell tests: theme.css, nav, footer, badge and body map.

The UI port is Django-native (no React, no Tailwind, no build step). These
tests pin the parts that must stay true: the permanent footer, the SIMULATED
badge, a keyboard-accessible SVG body map as the default view, and an opt-in
3D view that loads only local vendored files.
"""
import re
from pathlib import Path

import pytest
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent.parent
THEME_CSS = BASE_DIR / "core" / "static" / "core" / "theme.css"
APP_CSS = BASE_DIR / "core" / "static" / "core" / "app.css"
BASE_TEMPLATE = BASE_DIR / "core" / "templates" / "core" / "base.html"

FOOTER_TEXT = "Decision support, not a diagnosis."

pytestmark = pytest.mark.django_db


def _seed():
    call_command("seed_demo", scenario="calm_week", reset=True)


def test_theme_css_is_offline_only():
    css = THEME_CSS.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert "@import" not in code
    assert "url(" not in code
    assert "http://" not in css
    assert "https://" not in css
    assert "//" not in css


def test_base_shell_renders_on_every_page(client):
    _seed()
    urls = (
        "/",
        "/status/",
        "/checkin/",
        "/relay/",
        "/progress/",
        "/trend/resting_hr/",
    )
    for url in urls:
        content = client.get(url).content.decode()
        assert FOOTER_TEXT in content, f"footer missing on {url}"
        assert "SIMULATED" in content, f"SIMULATED badge missing on {url}"
        assert 'class="skip-link"' in content, f"skip link missing on {url}"
        assert "core/theme.css" in content, f"theme.css missing on {url}"
        assert 'aria-label="Main navigation"' in content
        assert 'id="main-content"' in content


def test_nav_contains_the_five_sections(client):
    _seed()
    content = client.get("/status/").content.decode()
    for name in ("Dashboard", "Check-in", "Trends", "Relay", "Progress"):
        assert f">{name}</a>" in content, f"nav link missing: {name}"


def test_nav_marks_the_current_page(client):
    _seed()
    dashboard = client.get("/status/").content.decode()
    assert re.search(r'href="/"[^>]*aria-current="page"', dashboard)
    trends = client.get("/trend/resting_hr/").content.decode()
    assert re.search(
        r'href="/trend/resting_hr/"[^>]*aria-current="page"', trends
    )


def test_dashboard_is_the_entry_point(client):
    _seed()
    for url in ("/", "/status/"):
        content = client.get(url).content.decode()
        assert "Dashboard" in content
        assert "Body map" in content
        assert 'id="bodymap"' in content


def test_body_map_is_an_svg_with_focusable_regions(client):
    _seed()
    content = client.get("/status/").content.decode()
    root = re.search(r"<svg id=\"bodymap\"[^>]*>", content)
    assert root is not None, "body map SVG root is missing"
    map_block = re.search(r"<svg id=\"bodymap\".*</svg>", content, re.S)
    assert map_block is not None, "body map SVG is not closed"
    for region in ("head", "chest", "lungs", "torso", "legs"):
        assert f'id="bm-{region}"' in map_block.group(0)
    assert content.count('role="button"') >= 5
    assert content.count('tabindex="0"') >= 5


def test_three_d_view_is_opt_in_and_local(client):
    _seed()
    content = client.get("/status/").content.decode()
    assert 'id="view-toggle-3d"' in content
    assert 'aria-pressed="false"' in content
    assert "type=\"importmap\"" in content
    assert "/static/vendor/three/build/three.module.js" in content
    assert "/static/vendor/three/examples/jsm/" in content
    assert "http://" not in content
    assert "https://" not in content
    # The 3D container starts hidden; the SVG map is the default view.
    assert re.search(r'id="body3d".*?hidden', content, re.S)
    assert "core/models/astropulse_body.glb" in content


def test_only_the_dashboard_loads_the_3d_view(client):
    _seed()
    content = client.get("/progress/").content.decode()
    assert "vendor/three" not in content
    assert "astropulse_body.glb" not in content


def test_every_page_has_exactly_one_h1(client):
    _seed()
    urls = (
        "/",
        "/status/",
        "/checkin/",
        "/trend/resting_hr/",
        "/relay/",
        "/progress/",
    )
    for url in urls:
        content = client.get(url).content.decode()
        assert content.count("<h1") == 1, f"expected one h1 on {url}"


def test_stylesheets_load_in_the_documented_order():
    # theme.css is the later stylesheet so it can restyle shared components.
    html = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert html.index("core/app.css") < html.index("core/theme.css")


def test_single_main_landmark_with_a_working_skip_link(client):
    _seed()
    content = client.get("/").content.decode()
    assert content.count("<main") == 1
    assert 'id="main-content"' in content
    assert 'href="#main-content"' in content
    assert "<h1" in content


def test_body_map_keeps_a_visible_focus_indicator():
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (APP_CSS, THEME_CSS)
    )
    assert ".bm-region:focus" in combined
    assert not re.search(
        r"\.bm-region[^{]*\{[^}]*outline\s*:\s*none", combined
    ), "the body map must keep a visible keyboard focus indicator"


def test_severity_palette_has_a_single_source():
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (APP_CSS, THEME_CSS)
    )
    for severity in ("gray", "green", "yellow", "orange", "red"):
        for suffix in ("fill", "text"):
            name = f"--sev-{severity}-{suffix}:"
            assert combined.count(name) == 1, f"{name} defined more than once"
