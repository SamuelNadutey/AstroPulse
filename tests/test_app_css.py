"""Static sanity checks for the bundled stylesheets.

Regression test for the Stage 10 audit finding: ``app.css`` referenced
``var(--sev-green)`` etc., but the palette only defines
``--sev-green-fill`` / ``--sev-green-text``, so the severity color bar on
guidance and relay cards never rendered.

Since the UI port (Phase 1) splits tokens and shell styles into
``theme.css``, the undefined-variable check spans both stylesheets.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_CSS = BASE_DIR / "core" / "static" / "core" / "app.css"
THEME_CSS = BASE_DIR / "core" / "static" / "core" / "theme.css"


def _combined_stylesheets() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (APP_CSS, THEME_CSS)
        if path.exists()
    )


def test_every_css_variable_reference_is_defined():
    css = _combined_stylesheets()
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
