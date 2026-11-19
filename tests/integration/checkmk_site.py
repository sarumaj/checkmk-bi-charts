"""Starts Checkmk in Docker and prepares it for the integration tests.

Uses the official images, whose entrypoint creates the site on first start and
runs ``omd update`` when a volume written by an older version is mounted.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
import testinfra
from testinfra.backend.base import CommandResult
from testinfra.host import Host

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

SITE = "cmk"  # the images' default site ID
USER = "cmkadmin"
PASSWORD = "bi-pie-integration"
MONITORED_HOST = "bipie-test"
# The default BI pack's rule "host" titles its aggregations like this.
AGGREGATION = f"Host {MONITORED_HOST}"

# The Raw edition was renamed to Community with 2.5, and the image with it.
IMAGES = {
    "2.4": os.environ.get("BI_PIE_IMAGE_2_4", "checkmk/check-mk-raw:2.4.0-latest"),
    "2.5": os.environ.get("BI_PIE_IMAGE_2_5", "checkmk/check-mk-community:2.5.0-latest"),
}

STATE_ENDPOINT = "api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke"


@dataclass
class Site:
    version: str
    container: str
    url: str  # base URL of the GUI, ends with /<site>/check_mk/
    host: Host

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
        """Stop the site cleanly and remove the container; a mounted volume stays."""
        _docker("stop", "--time", "180", self.container)
        _docker("rm", "--force", self.container)


def _docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout.strip()


def start(version: str, volume: str | None = None) -> Site:
    """Start a container and wait until the GUI answers."""
    mount = ["--volume", f"{volume}:/omd/sites"] if volume else []
    container = _docker(
        "run", "--detach",
        "--publish", "127.0.0.1::5000",
        "--tmpfs", f"/opt/omd/sites/{SITE}/tmp:uid=1000,gid=1000",
        "--env", f"CMK_PASSWORD={PASSWORD}",
        *mount,
        IMAGES[version],
    )  # fmt: skip
    # "docker port" prints "127.0.0.1:<port>".
    address = _docker("port", container, "5000/tcp").splitlines()[0]
    site = Site(version, container, f"http://{address}/{SITE}/check_mk/", testinfra.get_host(f"docker://{container}"))

    # Creating a site takes about a minute, updating one several.
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        try:
            if requests.get(site.url + "login.py", timeout=5).status_code == 200:
                return site
        except requests.ConnectionError:
            pass
        time.sleep(3)
    logs = _docker("logs", "--tail", "60", container)
    _docker("rm", "--force", container)
    raise TimeoutError(f"Checkmk {version} did not come up:\n{logs}")


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
