"""Static sanity checks for the bundled stylesheet.

Regression test for the Stage 10 audit finding: ``app.css`` referenced
``var(--sev-green)`` etc., but the palette only defines
``--sev-green-fill`` / ``--sev-green-text``, so the severity color bar on
guidance and relay cards never rendered.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_CSS = BASE_DIR / "core" / "static" / "core" / "app.css"


def test_every_css_variable_reference_is_defined():
    css = APP_CSS.read_text(encoding="utf-8")
    defined = set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", css))
    referenced = set(re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", css))
    missing = referenced - defined
    assert not missing, (
        "Undefined CSS custom properties referenced: " + ", ".join(sorted(missing))
    )


def test_severity_color_bars_use_palette_variables():
    css = APP_CSS.read_text(encoding="utf-8")
    for severity in ("gray", "green", "yellow", "orange", "red"):
        card_block = re.search(
            rf"\.guidance-card\.sev-{severity}\s*\{{([^}}]*)\}}", css
        )
        assert card_block is not None, f"missing .guidance-card.sev-{severity} rule"
        assert f"var(--sev-{severity}-fill)" in card_block.group(1)
