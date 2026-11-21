"""Checks on the package sources and the built MKP; no Checkmk site needed."""

import ast
import io
import json
import re
import tarfile
from pathlib import Path

import pytest

import build_mkp

ROOT = Path(__file__).parent.parent.parent


@pytest.mark.parametrize(
    "key, expected",
    [
        pytest.param("name", "bi_charts", id="name matches the file key"),
        pytest.param("packaged", True, id="marked as packaged"),
        pytest.param("public", True, id="visible to other users"),
    ],
)
def test_dashboard_definition(key: str, expected: object) -> None:
    dashboards = ast.literal_eval((ROOT / "src/gui/dashboard/bi_charts").read_text())
    assert dashboards["bi_charts"][key] == expected


def test_dashboard_embeds_the_page_site_relative() -> None:
    dashboards = ast.literal_eval((ROOT / "src/gui/dashboard/bi_charts").read_text())
    dashlets = dashboards["bi_charts"]["dashlets"]
    # A site-relative URL keeps the package independent of the site name.
    assert [(d["type"], d["url"]) for d in dashlets] == [("url", "local/bi_charts/index.html")]
    assert (ROOT / "src/page/index.html").is_file()


@pytest.mark.parametrize(
    "part, expected",
    [
        pytest.param(
            "web",
            [
                "htdocs/bi_charts/index.html",
                "htdocs/bi_charts/echarts.min.js",
                "htdocs/bi_charts/LICENSE-echarts.txt",
                "htdocs/bi_charts/NOTICE-echarts.txt",
                "htdocs/bi_charts/LICENSE-zrender.txt",
            ],
            id="web part",
        ),
        pytest.param("gui", ["dashboard/bi_charts"], id="gui part"),
    ],
)
def test_mkp_parts_hold_the_manifest_files(part: str, expected: list[str]) -> None:
    with tarfile.open(build_mkp.build()) as mkp:
        manifest = ast.literal_eval(mkp.extractfile("info").read().decode())
        with tarfile.open(fileobj=io.BytesIO(mkp.extractfile(f"{part}.tar").read())) as inner:
            assert inner.getnames() == expected
    assert manifest["files"][part] == expected


def test_mkp_manifests_agree() -> None:
    with tarfile.open(build_mkp.build()) as mkp:
        assert mkp.getnames() == ["info", "info.json", "web.tar", "gui.tar"]
        python_manifest = ast.literal_eval(mkp.extractfile("info").read().decode())
        json_manifest = json.loads(mkp.extractfile("info.json").read())
    assert python_manifest == json_manifest
    assert python_manifest["version.min_required"] == "2.4.0"


def test_build_is_reproducible() -> None:
    assert build_mkp.build().read_bytes() == build_mkp.build().read_bytes()


def test_mkp_ships_the_built_page_with_the_licenses_of_its_library() -> None:
    with tarfile.open(build_mkp.build()) as mkp:
        with tarfile.open(fileobj=io.BytesIO(mkp.extractfile("web.tar").read())) as web:
            page = web.extractfile("htdocs/bi_charts/index.html").read().decode()
            library = web.extractfile("htdocs/bi_charts/echarts.min.js").read()
            notice = web.extractfile("htdocs/bi_charts/NOTICE-echarts.txt").read()
    assert page == build_mkp.PAGE.read_text()
    assert b"Apache ECharts" in notice
    # ECharts as its release has it, byte for byte, for a reviewer to compare.
    assert library == (build_mkp.MODULES / "echarts/dist/echarts.min.js").read_bytes()
    version = json.loads((build_mkp.MODULES / "echarts/package.json").read_text())["version"]
    # The stylesheet and the page's script inline (the build markers replaced); the one
    # file loaded is the library beside it, with its version against a cached older one.
    assert "<!-- build:" not in page
    assert page.count("<script>") == 1 and page.count("<style>") == 1
    assert re.findall(r"<script[^>]*\ssrc=\"([^\"]*)\"|<link\b", page) == [f"echarts.min.js?v={version}"]


def test_the_pages_script_is_its_own_code_not_minified() -> None:
    """Checkmk's reviewers read the package: the page's script is the modules of
    src/page/ as written, without ECharts in it."""
    build_mkp.build_page()
    script = build_mkp.PAGE.read_text().split("<script>\n", 1)[1].split("</script>", 1)[0]
    assert "// src/page/chart.js" in script and "node_modules" not in script
    assert "function initChart() {" in script
    assert max(len(line) for line in script.splitlines()) < 600
