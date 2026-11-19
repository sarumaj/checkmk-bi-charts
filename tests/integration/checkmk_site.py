"""Starts Checkmk sites in Docker and prepares them for the integration tests.

The sites run in an image built here from Checkmk's own packages
(packages.py: the newest patch release of 2.4 and of 2.5, checked against the
SHA-256 Checkmk publishes) on Debian 12. Both versions are installed in the
image, so a site created with 2.4 can be updated to 2.5 in its container with
``omd update``, as on a server. The image is built once per pair of packages
and kept; a new patch release builds a new one.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import requests
import testinfra
from testinfra.backend.base import CommandResult
from testinfra.host import Host

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
import packages  # noqa: E402

SITE = "cmk"
USER = "cmkadmin"
PASSWORD = "bi-pie-integration"
MONITORED_HOST = "bipie-test"
# The default BI pack's rule "host" titles its aggregations like this.
AGGREGATION = f"Host {MONITORED_HOST}"
VERSIONS = ["2.4", "2.5"]
# The site's own Apache listens here, inside the container.
PORT = 5000
DOCKERFILE = Path(__file__).parent / "image" / "Dockerfile"

STATE_ENDPOINT = "api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke"


@dataclass
class Site:
    version: str
    container: str
    url: str  # base URL of the GUI, ends with /<site>/check_mk/
    host: Host  # the container, as root

    def run(self, command: str) -> CommandResult:
        """Run a command as the site user, with the site's environment."""
        return self.host.run("su - %s -c %s", SITE, command)

    def api(self) -> requests.Session:
        """Session that authenticates every request with the admin's credentials."""
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {USER} {PASSWORD}", "Accept": "application/json"})
        return session

    def gui(self) -> requests.Session:
        """Session that is logged in through the login form and holds only the cookie."""
        session = requests.Session()
        response = session.post(
            self.url + "login.py",
            data={"_username": USER, "_password": PASSWORD, "_login": "1", "_origtarget": "index.py"},
        )
        assert response.status_code == 200, response.text[:500]
        assert session.cookies, "the login set no session cookie"
        return session

    def stop(self) -> None:
        """Remove the container with the site."""
        _docker("rm", "--force", self.container)


def _docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"docker {args[0]} failed:\n{result.stdout[-3000:]}{result.stderr[-3000:]}")
    return result.stdout.strip()


@cache
def _packages() -> dict[str, packages.Package]:
    return dict(zip(VERSIONS, packages.packages(VERSIONS), strict=True))


@cache
def image() -> str:
    """The image with both versions installed, built unless it exists."""
    found = list(_packages().values())
    digest = hashlib.sha256(" ".join(p.path.name for p in found).encode() + DOCKERFILE.read_bytes()).hexdigest()
    tag = f"bi-pie-checkmk:{digest[:12]}"
    if _docker("images", "--quiet", tag):
        return tag
    # The build context holds the packages and nothing else, as hard links where
    # they can be made: the packages are large.
    context = packages.CACHE / f"context-{digest[:12]}"
    shutil.rmtree(context, ignore_errors=True)
    context.mkdir(parents=True)
    try:
        for package in found:
            try:
                os.link(package.path, context / package.path.name)
            except OSError:
                shutil.copy(package.path, context / package.path.name)
        _docker("build", "--quiet", "--tag", tag, "--file", str(DOCKERFILE), str(context))
    finally:
        shutil.rmtree(context, ignore_errors=True)
    return tag


def _version_directory(host: Host, version: str) -> str:
    """The version's directory in /omd/versions, e.g. 2.5.0p20.community."""
    release = _packages()[version].version
    for name in host.check_output("ls /omd/versions").split():
        if name.startswith(release + "."):
            return name
    raise LookupError(f"Checkmk {release} is not installed in the image")


def _wait(site: Site, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(site.url + "login.py", timeout=5).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(3)
    raise TimeoutError(f"Checkmk {site.version} did not answer within {timeout:.0f} s")


def _start_site(site: Site) -> None:
    result = site.host.run("omd start %s", SITE)
    assert result.rc == 0, f"omd start: {result.stdout}{result.stderr}"
    _wait(site, 300)


def start(version: str) -> Site:
    """Start a container, create a site of ``version`` (2.4 or 2.5) in it and wait
    until the GUI answers."""
    # --init: omd stop leaves zombies that only an init reaps, and omd update refuses
    # a site whose processes it still sees.
    container = _docker(
        "run", "--detach", "--init",
        "--publish", f"127.0.0.1::{PORT}",
        image(), "sleep", "infinity",
    )  # fmt: skip
    # "docker port" prints "127.0.0.1:<port>".
    address = _docker("port", container, f"{PORT}/tcp").splitlines()[0]
    host = testinfra.get_host(f"docker://{container}")
    site = Site(version, container, f"http://{address}/{SITE}/check_mk/", host)
    try:
        # No tmpfs, which a container may not mount. The site's own Apache serves the
        # GUI on PORT; the system Apache the packages install stays off.
        for command in (
            f"omd -V {_version_directory(host, version)} create --no-tmpfs --admin-password {PASSWORD} {SITE}",
            f"omd config {SITE} set APACHE_TCP_ADDR 0.0.0.0",
            f"omd config {SITE} set APACHE_TCP_PORT {PORT}",
        ):
            result = host.run(command)
            assert result.rc == 0, f"{command}: {result.stdout}{result.stderr}"
        _start_site(site)
    except BaseException:
        site.stop()
        raise
    return site


def update(site: Site, version: str) -> None:
    """Update the site to ``version`` with omd update, as an administrator would."""
    result = site.host.run("omd stop %s", SITE)
    assert result.rc == 0, f"omd stop: {result.stdout}{result.stderr}"
    command = f"omd -f -V {_version_directory(site.host, version)} update --conflict=install {SITE}"
    result = site.host.run(command)
    assert result.rc == 0, f"{command}: {result.stdout[-3000:]}{result.stderr[-3000:]}"
    site.version = version
    _start_site(site)


def install_package(site: Site) -> None:
    mkp = build.build()
    _docker("cp", str(mkp), f"{site.container}:/tmp/{mkp.name}")
    site.host.run_test("chmod 644 /tmp/%s", mkp.name)
    for command in (f"mkp add /tmp/{mkp.name}", f"mkp enable {build.NAME} {build.VERSION}"):
        result = site.run(command)
        assert result.rc == 0, f"{command}: {result.stdout}{result.stderr}"


def prepare_monitoring(site: Site) -> None:
    """Create one host and enable the default BI aggregation, which covers every host."""
    api = site.api()
    response = api.post(
        site.url + "api/1.0/domain-types/host_config/collections/all",
        json={"host_name": MONITORED_HOST, "folder": "/", "attributes": {"ipaddress": "127.0.0.1"}},
    )
    assert response.status_code == 200, response.text

    # A fresh site ships this aggregation disabled. Sending back what the server
    # returned keeps the body valid on every version.
    aggregation_url = site.url + "api/1.0/objects/bi_aggregation/default_aggregation"
    response = api.get(aggregation_url)
    assert response.status_code == 200, response.text
    aggregation = response.json()
    aggregation["computation_options"]["disabled"] = False
    response = api.put(aggregation_url, json=aggregation)
    assert response.status_code == 200, response.text

    # Bring the new host into the monitoring core.
    result = site.run("cmk -R")
    assert result.rc == 0, result.stdout + result.stderr

    # The aggregation appears once the core knows the host and BI has compiled.
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        response = api.get(site.url + STATE_ENDPOINT)
        if response.status_code == 200 and AGGREGATION in response.json()["aggregations"]:
            return
        time.sleep(3)
    raise TimeoutError(f"Aggregation {AGGREGATION!r} did not appear: {response.status_code} {response.text[:500]}")
