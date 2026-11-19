"""Checks on the package sources and the built MKP; no Checkmk site needed."""

import ast
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402


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
    assert (ROOT / "src/web/htdocs/bi_charts/index.html").is_file()


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
    with tarfile.open(build.build()) as mkp:
        manifest = ast.literal_eval(mkp.extractfile("info").read().decode())
        with tarfile.open(fileobj=io.BytesIO(mkp.extractfile(f"{part}.tar").read())) as inner:
            assert inner.getnames() == expected
    assert manifest["files"][part] == expected


def test_mkp_manifests_agree() -> None:
    with tarfile.open(build.build()) as mkp:
        assert mkp.getnames() == ["info", "info.json", "web.tar", "gui.tar"]
        python_manifest = ast.literal_eval(mkp.extractfile("info").read().decode())
        json_manifest = json.loads(mkp.extractfile("info.json").read())
    assert python_manifest == json_manifest
    assert python_manifest["version.min_required"] == "2.4.0"


def test_build_is_reproducible() -> None:
    assert build.build().read_bytes() == build.build().read_bytes()


def test_mkp_ships_the_chart_library_with_its_licenses() -> None:
    with tarfile.open(build.build()) as mkp:
        with tarfile.open(fileobj=io.BytesIO(mkp.extractfile("web.tar").read())) as web:
            library = web.extractfile("htdocs/bi_charts/echarts.min.js").read()
            notice = web.extractfile("htdocs/bi_charts/NOTICE-echarts.txt").read()
    assert library == (ROOT / "node_modules/echarts/dist/echarts.min.js").read_bytes()
    assert b"Apache ECharts" in notice
    # The page loads the copy beside it, nothing from elsewhere.
    page = (ROOT / "src/web/htdocs/bi_charts/index.html").read_text()
    assert '<script src="echarts.min.js"></script>' in page
    assert "https://" not in page.split("<script>")[0].split("<style>")[0]
