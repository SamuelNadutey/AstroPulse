"""HTMX and Plotly are bundled locally, not loaded from the internet.

Checks:
- the vendor files exist under core/static/vendor/ and are non-trivial,
- every template reference to them uses a ``{% static 'vendor/...' %}``
  tag (never a raw path, never a CDN URL),
- app.css references no external @import or url() resources,
- base.html (loaded on every page) includes the bundled HTMX file.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = BASE_DIR / "core" / "templates"
STATIC = BASE_DIR / "core" / "static"

HTMX = STATIC / "vendor" / "htmx.min.js"
PLOTLY = STATIC / "vendor" / "plotly-basic.min.js"

TEMPLATE_RE = re.compile(r"(htmx\.min\.js|plotly-basic\.min\.js)")


def test_vendor_files_exist_and_are_non_trivial():
    for path, name in ((HTMX, "htmx.min.js"), (PLOTLY, "plotly-basic.min.js")):
        assert path.is_file(), f"missing bundled vendor file: {name}"
        assert path.stat().st_size > 10_000, f"{name} looks truncated"


def test_templates_reference_vendor_files_via_static_tag():
    offenders = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if TEMPLATE_RE.search(line):
                if "{% static 'vendor/" not in line:
                    offenders.append(
                        f"{path.relative_to(BASE_DIR).as_posix()}:{line_number}: {line.strip()}"
                    )
    assert not offenders, (
        "vendor files must be referenced via {% static 'vendor/...' %}:\n"
        + "\n".join(offenders)
    )


def test_no_template_loads_vendor_files_from_the_internet():
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        assert "unpkg.com" not in text
        assert "cdn." not in text
        assert "jsdelivr" not in text


def test_app_css_has_no_external_imports_or_urls():
    css = (STATIC / "core" / "app.css").read_text(encoding="utf-8")
    assert "@import" not in css
    for match in re.finditer(r"url\([^)]*\)", css):
        target = match.group(0)
        assert "http" not in target and "//" not in target


def test_base_template_loads_bundled_htmx():
    base = (TEMPLATES / "core" / "base.html").read_text(encoding="utf-8")
    assert "{% static 'vendor/htmx.min.js' %}" in base


def test_trend_template_loads_bundled_plotly():
    trend = (TEMPLATES / "core" / "trend.html").read_text(encoding="utf-8")
    assert "{% static 'vendor/plotly-basic.min.js' %}" in trend
