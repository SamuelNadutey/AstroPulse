"""Safety test: no external URLs in templates or static files.

Scans every file in ``core/templates`` and ``core/static`` for ``http://``,
``https://`` and protocol-relative ``//`` references, wherever they appear
(``src``, ``href``, ``action``, ``url(...)``, ``@import``, ``fetch(...)`` or
anywhere else).

Two exemptions, both deliberate:

1. ``core/static/vendor/`` (the bundled HTMX and Plotly artifacts) is exempt
   from the literal-URL check. These are third-party minified files; their
   URLs occur only inside namespace/DTD identifier strings such as
   ``http://www.w3.org/2000/svg`` and inside internal JS code (for example
   ``location.href``). They are never fetched at runtime and cannot be edited
   without invalidating the vendored artifact, so we do not rewrite them.
   Templates must reference the vendor files via ``{% static 'vendor/...' %}``;
   that is enforced by tests/test_vendor_bundled.py.

2. ``_guidance_card.html`` (the citation partial) may display a source URL as
   plain text. A URL on a citation-partial line is allowed only if the line
   contains no attribute or loader usage (``src=``, ``href=``, ``action=``,
   ``url(``, ``@import``, ``fetch(``). All other files and all other lines
   must be completely free of external URLs.

The failure message lists every offending file and line number.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCAN_ROOTS = [BASE_DIR / "core" / "templates", BASE_DIR / "core" / "static"]

VENDOR_DIR = BASE_DIR / "core" / "static" / "vendor"
CITATION_PARTIAL = "_guidance_card.html"

URL_RE = re.compile(r"https?://", re.IGNORECASE)
PROTOCOL_RELATIVE_RE = re.compile(r"(?<!:)//[A-Za-z0-9][^\s\"'<>)*]*")
LOADER_RE = re.compile(
    r"\b(src\s*=|href\s*=|action\s*=|url\s*\(|@import|fetch\s*\()",
    re.IGNORECASE,
)


def _iter_scanned_files():
    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if VENDOR_DIR in path.parents:
                continue
            yield path


def _violations_for(path: Path) -> list[str]:
    rel = path.relative_to(BASE_DIR).as_posix()
    is_citation_partial = path.name == CITATION_PARTIAL
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary files in static/ cannot be scanned for external URLs.
        return []
    violations = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        matches = list(URL_RE.finditer(line)) + list(
            PROTOCOL_RELATIVE_RE.finditer(line)
        )
        if not matches:
            continue
        if is_citation_partial and not LOADER_RE.search(line):
            # Plain displayed citation text (e.g. {{ source.url }}); never a
            # fetched resource. Allowed only in the citation partial.
            continue
        for match in matches:
            violations.append(
                f"{rel}:{line_number}: external URL reference "
                f"{match.group(0)!r} in: {line.strip()}"
            )
    return violations


def test_no_external_urls_in_templates_or_static_files():
    violations = []
    for path in _iter_scanned_files():
        violations.extend(_violations_for(path))
    assert not violations, (
        "External URLs found (must not be loaded or referenced):\n"
        + "\n".join(violations)
    )
