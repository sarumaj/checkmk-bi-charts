"""The package across the update from Checkmk 2.4 to 2.5.

    pytest tests/integration/test_update.py

Installs the package on a 2.4 site, then updates the site to 2.5 with
``omd update``, as an administrator would.
"""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

import build
import checkmk_site
from checkmk_site import AGGREGATION, SITE, STATE_ENDPOINT, Site


pytestmark = pytest.mark.skipif(
    not {"2.4", "2.5"} <= set(checkmk_site.VERSIONS), reason="needs Checkmk 2.4 and 2.5 (BI_PIE_VERSIONS)"
)


@pytest.fixture(scope="module")
def updated_site() -> Iterator[Site]:
    site = checkmk_site.start("2.4")
    try:
        checkmk_site.install_package(site)
        checkmk_site.prepare_monitoring(site)
        checkmk_site.update(site, "2.5")
        yield site
    finally:
        site.stop()


def test_site_runs_the_new_version(updated_site: Site) -> None:
    result = updated_site.run("omd version")
    assert result.rc == 0, result.stderr
    assert " 2.5.0" in result.stdout, result.stdout


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"/omd/sites/{SITE}/local/share/check_mk/web/htdocs/bi_pie/index.html", id="page"),
        pytest.param(f"/omd/sites/{SITE}/local/lib/python3/cmk/gui/plugins/dashboard/bi_pie", id="dashboard"),
    ],
)
def test_update_keeps_the_files(updated_site: Site, path: str) -> None:
    assert updated_site.host.file(path).is_file


def test_update_keeps_the_package_enabled(updated_site: Site) -> None:
    result = updated_site.run("mkp list")
    assert result.rc == 0, result.stderr
    assert any(
        build.NAME in line and build.VERSION in line and "Enabled" in line for line in result.stdout.splitlines()
    ), result.stdout


def test_update_keeps_the_dashboard(updated_site: Site) -> None:
    response = updated_site.gui().get(
        updated_site.url + "api/unstable/objects/dashboard_relative_grid/bi_pie",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200, response.text[:500]
    assert "local/bi_pie/index.html" in response.text


def test_page_still_draws_after_the_update(page: Page, updated_site: Site) -> None:
    gui = updated_site.gui()
    # The monitoring core needs a moment after the update before BI has data.
    assert gui.get(updated_site.url + STATE_ENDPOINT).status_code == 200
    page.context.add_cookies(
        [{"name": cookie.name, "value": cookie.value, "url": updated_site.url} for cookie in gui.cookies]
    )
    page.goto(updated_site.url + "local/bi_pie/index.html?view=tree&refresh=3")
    expect(page.locator(f'path.seg[aria-label^="{AGGREGATION}:"]')).to_have_count(1, timeout=120_000)
    expect(page.locator("#msg.err")).to_have_count(0)
