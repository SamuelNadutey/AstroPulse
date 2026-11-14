"""Vendored Three.js and the optional 3D body view.

Three.js is copied from the prototype's local package into
``core/static/vendor/three/`` and loaded through a page-scoped import map.
Nothing is fetched from the network, and the 2D SVG body map stays the
default and the fallback.
"""
import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent.parent
VENDOR = BASE_DIR / "core" / "static" / "vendor" / "three"
GLB = BASE_DIR / "core" / "static" / "core" / "models" / "astropulse_body.glb"
SCRIPT = BASE_DIR / "core" / "static" / "core" / "js" / "body3d.js"

VENDOR_FILES = (
    ("build/three.module.js", 500_000),
    ("build/three.core.js", 1_000_000),
    ("examples/jsm/loaders/GLTFLoader.js", 50_000),
    ("examples/jsm/controls/OrbitControls.js", 20_000),
    ("examples/jsm/utils/BufferGeometryUtils.js", 20_000),
    ("examples/jsm/utils/SkeletonUtils.js", 5_000),
)


def test_vendor_files_are_present_and_non_trivial():
    for relative, minimum in VENDOR_FILES:
        path = VENDOR / relative
        assert path.is_file(), f"missing vendored file: {relative}"
        assert path.stat().st_size >= minimum, f"{relative} looks truncated"


def test_vendor_license_is_kept():
    assert (VENDOR / "LICENSE").is_file()


def test_local_assets_are_found_by_staticfiles():
    assert GLB.is_file()
    assert GLB.stat().st_size > 100_000
    assert finders.find("core/models/astropulse_body.glb")
    assert finders.find("vendor/three/build/three.module.js")
    assert finders.find("vendor/three/build/three.core.js")
    assert finders.find("vendor/three/examples/jsm/loaders/GLTFLoader.js")


def test_body3d_script_has_no_network_calls():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "http://" not in text
    assert "https://" not in text
    assert "fetch(" not in text
    assert "//" not in text


def test_body3d_script_disables_itself_when_webgl_or_model_fails():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "3D view unavailable. Accessible body map shown." in text
    assert "3D model could not be loaded" in text
    assert "renderer.dispose()" in text
    assert "cancelAnimationFrame" in text
    assert "observer.disconnect()" in text


@pytest.mark.django_db
def test_svg_body_map_is_the_default_view(client):
    call_command("seed_demo", scenario="calm_week", reset=True)
    content = client.get("/status/").content.decode()
    root = re.search(r"<svg id=\"bodymap\"[^>]*>", content)
    assert root is not None
    assert "hidden" not in root.group(0)


@pytest.mark.django_db
def test_import_map_has_no_external_targets(client):
    call_command("seed_demo", scenario="calm_week", reset=True)
    content = client.get("/status/").content.decode()
    import_map = re.search(
        r'<script type="importmap">(.*?)</script>', content, re.S
    )
    assert import_map is not None
    body = import_map.group(1)
    assert "three.module.js" in body
    assert "http" not in body
    assert "//" not in body
