#!/usr/bin/env python3
"""Build the bi_charts MKP from the files under src/.

    build-mkp             # writes dist/bi_charts-<version>.mkp
    build-mkp --version   # prints the version (pyproject.toml's)

``build-mkp`` is this module's entry point once the project is installed
(``pip install -e .``); ``python3 scripts/build_mkp.py`` does the same without.

An MKP is a gzipped tar holding the manifest twice (``info`` as a Python
literal, ``info.json`` for external tools) and one uncompressed tar per package
part. Each part tar holds paths relative to that part's directory in the site,
which Checkmk resolves itself, so the same archive installs on 2.4 and 2.5 even
though the directories differ between the two.

The page is built first (scripts/build_page.mjs, Node.js and ``npm ci``): its
modules under src/page/ bundled with ECharts into one file under build/.

Building here instead of with ``mkp package`` needs no Checkmk site and gives a
byte-identical archive for identical sources.
"""

import argparse
import gzip
import io
import json
import pprint
import subprocess
import tarfile
import tomllib
from pathlib import Path

# The checkout: an editable install (pip install -e .) runs this file where it lies.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

NAME = "bi_charts"
# The project's version, which the release bot writes (pyproject.toml, tool.commitizen).
VERSION: str = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]

# Part name -> files, relative to the part's directory in the site:
#   web  ~/local/share/check_mk/web
#   gui  ~/local/lib/check_mk/gui/plugins (2.4), ~/local/lib/python3/cmk/gui/plugins (2.5)
FILES: dict[str, list[str]] = {
    "web": [
        "htdocs/bi_charts/index.html",
        "htdocs/bi_charts/LICENSE-echarts.txt",
        "htdocs/bi_charts/NOTICE-echarts.txt",
        "htdocs/bi_charts/LICENSE-zrender.txt",
    ],
    "gui": ["dashboard/bi_charts"],
}

# The files from elsewhere than src/: the built page (build_page), and the licenses
# of the chart library it bundles (Apache-2.0; zrender, which it bundles, BSD), in
# the version package-lock.json pins: `npm ci` puts it into node_modules.
PAGE = ROOT / "build/bi_charts/index.html"
MODULES = ROOT / "node_modules"
OTHER_SOURCES: dict[str, Path] = {
    "web/htdocs/bi_charts/index.html": PAGE,
    "web/htdocs/bi_charts/LICENSE-echarts.txt": MODULES / "echarts/LICENSE",
    "web/htdocs/bi_charts/NOTICE-echarts.txt": MODULES / "echarts/NOTICE",
    "web/htdocs/bi_charts/LICENSE-zrender.txt": MODULES / "zrender/LICENSE",
}

MANIFEST: dict[str, object] = {
    "title": "BI charts",
    "name": NAME,
    "description": (
        "Dashboard element with charts of BI aggregations: their states as a "
        "pie, the BI trees as rings, a treemap or a tree, and the states per "
        "group as donuts or bars, with a list of the aggregations that are not "
        "OK.\n\n"
        "Ships a static page that reads the BI aggregation states from the REST "
        "API with the viewer's session, and a dashboard that embeds it. Embed "
        "the page in your own dashboards with the custom URL element (2.4) or "
        "the Embed URL widget (2.5) and the URL local/bi_charts/index.html. "
        "Draws with Apache ECharts (Apache-2.0), which the package includes."
    ),
    "version": VERSION,
    "version.packaged": "2.4.0",
    "version.min_required": "2.4.0",
    # The packaged dashboard format and the local htdocs path are internals that
    # were only checked against the 2.4 and 2.5 sources.
    "version.usable_until": "2.6.0",
    "author": "Dawid Ciepiela",
    "download_url": "https://git.ciepiela.org/dawid/checkmk-bi-charts",
    "files": FILES,
}


def _add(tar: tarfile.TarFile, name: str, content: bytes) -> None:
    # Fixed metadata keeps the archive reproducible.
    info = tarfile.TarInfo(name)
    info.size = len(content)
    info.mode = 0o644
    info.mtime = 0
    tar.addfile(info, io.BytesIO(content))


def _source(name: str) -> Path:
    if name not in OTHER_SOURCES:
        return SRC / name
    if not OTHER_SOURCES[name].is_file():
        raise SystemExit(f"{OTHER_SOURCES[name]} is missing: run `npm ci` first")
    return OTHER_SOURCES[name]


def build_page() -> Path:
    """Build the page from src/page/ into build/ (scripts/build_page.mjs); its path."""
    if not (MODULES / "esbuild").is_dir():
        raise SystemExit("esbuild is missing: run `npm ci` first")
    subprocess.run(["node", str(ROOT / "scripts/build_page.mjs")], check=True, stdout=subprocess.DEVNULL)
    return PAGE


def _part_tar(part: str, files: list[str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name in files:
            _add(tar, name, _source(f"{part}/{name}").read_bytes())
    return buffer.getvalue()


def build() -> Path:
    build_page()
    target = ROOT / "dist" / f"{NAME}-{VERSION}.mkp"
    target.parent.mkdir(exist_ok=True)
    # mtime=0 in the gzip header, again for reproducibility.
    with (
        gzip.GzipFile(target, "wb", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as mkp,
    ):
        _add(mkp, "info", (pprint.pformat(MANIFEST) + "\n").encode())
        _add(mkp, "info.json", json.dumps(MANIFEST).encode())
        for part, files in FILES.items():
            _add(mkp, f"{part}.tar", _part_tar(part, files))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the bi_charts MKP into dist/.")
    parser.add_argument("--version", action="store_true", help="print the version and build nothing")
    if parser.parse_args().version:
        print(VERSION)
    else:
        print(build())


if __name__ == "__main__":
    main()
