#!/usr/bin/env python3
"""Build the bi_charts MKP from the files under src/.

    ./build.py            # writes dist/bi_charts-<version>.mkp

An MKP is a gzipped tar holding the manifest twice (``info`` as a Python
literal, ``info.json`` for external tools) and one uncompressed tar per package
part. Each part tar holds paths relative to that part's directory in the site,
which Checkmk resolves itself, so the same archive installs on 2.4 and 2.5 even
though the directories differ between the two.

Building here instead of with ``mkp package`` needs no Checkmk site and gives a
byte-identical archive for identical sources.
"""

import gzip
import io
import json
import pprint
import tarfile
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

NAME = "bi_charts"
VERSION = "0.4.0"

# Part name -> files, relative to the part's directory in the site:
#   web  ~/local/share/check_mk/web
#   gui  ~/local/lib/check_mk/gui/plugins (2.4), ~/local/lib/python3/cmk/gui/plugins (2.5)
FILES: dict[str, list[str]] = {
    "web": ["htdocs/bi_charts/index.html"],
    "gui": ["dashboard/bi_charts"],
}

MANIFEST: dict[str, object] = {
    "title": "BI aggregation state pie",
    "name": NAME,
    "description": (
        "Dashboard element that shows the state distribution of BI aggregations "
        "as a pie chart, with a list of the aggregations that are not OK. An "
        "optional layered view adds one ring per level of the BI tree.\n\n"
        "Ships a static page that reads the BI aggregation states from the REST "
        "API with the viewer's session, and a dashboard that embeds it. Embed "
        "the page in your own dashboards with the custom URL element and the "
        "URL local/bi_charts/index.html."
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


def _part_tar(part: str, files: list[str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name in files:
            _add(tar, name, (SRC / part / name).read_bytes())
    return buffer.getvalue()


def build() -> Path:
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


if __name__ == "__main__":
    print(build())
