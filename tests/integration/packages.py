#!/usr/bin/env python3
"""Downloads the Checkmk packages the integration tests install.

    python3 tests/integration/packages.py 2.4 2.5           # prints the path of each
    python3 tests/integration/packages.py --check 2.4 2.5   # every maintained one tested?

Takes the newest patch release of each version from Checkmk's list of stable
releases, which also gives each package's SHA-256, in the free edition (Raw up
to 2.4, Community from 2.5) for Debian 12, the base of the test image. A
package is kept in the cache directory (BI_PIE_CACHE, default
~/.cache/bi-pie) and checked again before every use, so a download that broke
off is fetched again instead of installed.

BI_PIE_PACKAGE_2_4 and BI_PIE_PACKAGE_2_5 name a package file to use instead,
e.g. an older patch release.
"""

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

RELEASES = "https://download.checkmk.com/stable_downloads.json"
DOWNLOADS = "https://download.checkmk.com/checkmk"
# The free edition's key in the list, whatever the package is called.
EDITION = "community"
DISTRIBUTION = "bookworm"
CACHE = Path(os.environ.get("BI_PIE_CACHE", Path.home() / ".cache" / "bi-pie"))


@dataclass(frozen=True)
class Package:
    version: str  # the patch release, e.g. 2.5.0p20
    path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _releases() -> dict[str, dict]:
    response = requests.get(RELEASES, timeout=60)
    response.raise_for_status()
    return response.json()["checkmk"]


def _download(url: str, target: Path, sha256: str) -> None:
    partial = target.with_name(target.name + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with partial.open("wb") as file:
            for block in response.iter_content(1 << 20):
                file.write(block)
    if (actual := _sha256(partial)) != sha256:
        partial.unlink()
        raise ValueError(f"{url}: SHA-256 {actual}, the list of releases says {sha256}")
    partial.rename(target)


def package(version: str, releases: dict[str, dict] | None = None) -> Package:
    """The package of the newest patch release of ``version`` (``2.4``), downloaded."""
    own = os.environ.get(f"BI_PIE_PACKAGE_{version.replace('.', '_')}")
    if own:
        path = Path(own).resolve()
        # check-mk-raw-2.4.0p41_0.bookworm_amd64.deb -> 2.4.0p41
        return Package(path.name.split("-")[-1].split("_")[0], path)

    release = (releases or _releases())[f"{version}.0"]
    name, sha256 = release["editions"][EDITION][DISTRIBUTION]
    target = CACHE / name
    if target.exists() and _sha256(target) == sha256:
        return Package(release["version"], target)
    CACHE.mkdir(parents=True, exist_ok=True)
    _download(f"{DOWNLOADS}/{release['version']}/{name}", target, sha256)
    return Package(release["version"], target)


def packages(versions: list[str]) -> list[Package]:
    releases = None if all(os.environ.get(f"BI_PIE_PACKAGE_{v.replace('.', '_')}") for v in versions) else _releases()
    return [package(version, releases) for version in versions]


def _number(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def check(tested: list[str]) -> list[str]:
    """What keeps the package from covering every version Checkmk maintains: a
    current ("stable") version that is not tested, or one outside the manifest's
    version.min_required and version.usable_until."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import build  # pylint: disable=import-outside-toplevel

    lowest, beyond = build.MANIFEST["version.min_required"], build.MANIFEST["version.usable_until"]
    problems = []
    for key, release in sorted(_releases().items(), key=lambda item: _number(item[0])):
        if release.get("class") != "stable":
            continue
        version = key.removesuffix(".0")
        if version not in tested:
            problems.append(f"Checkmk {release['version']} is maintained, but not tested")
        if not _number(str(lowest)) <= _number(key) < _number(str(beyond)):
            problems.append(f"Checkmk {key} is maintained, but outside the manifest's {lowest} to {beyond}")
    return problems


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        # The versions CI tests (its matrix) against those Checkmk maintains.
        found = check(sys.argv[2:])
        print("\n".join(found) or "Every version Checkmk maintains is tested: " + ", ".join(sys.argv[2:]))
        sys.exit(1 if found else 0)
    for found in packages(sys.argv[1:] or ["2.4", "2.5"]):
        print(found.path)
