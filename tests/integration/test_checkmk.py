"""The package on real Checkmk 2.4 and 2.5 sites, started in Docker.

    pytest tests/integration/test_checkmk.py

Needs Docker, pytest-testinfra, requests, pytest-playwright and a browser. The
first run downloads Checkmk's packages (about 600 MB) and builds the image from
them (several minutes); each site then takes a minute or two.
"""

import json
from collections.abc import Iterator
from typing import Any

import pytest
import requests
from playwright.sync_api import Page, expect

import build_mkp
import checkmk_site
from checkmk_site import AGGREGATION, MONITORED_HOST, SITE, STATE_ENDPOINT, Site


@pytest.fixture(scope="module", params=checkmk_site.VERSIONS)
def site(request: pytest.FixtureRequest) -> Iterator[Site]:
    site = checkmk_site.start(request.param)
    try:
        checkmk_site.install_package(site)
        checkmk_site.prepare_monitoring(site)
        yield site
    finally:
        site.stop()


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"/omd/sites/{SITE}/local/share/check_mk/web/htdocs/bi_charts/index.html", id="page"),
        pytest.param(f"/omd/sites/{SITE}/local/lib/python3/cmk/gui/plugins/dashboard/bi_charts", id="dashboard"),
    ],
)
def test_package_installs_its_files(site: Site, path: str) -> None:
    installed = site.host.file(path)
    assert installed.is_file
    assert installed.user == SITE
    # The site's Apache and GUI run as the site user. mkp writes with the site's umask
    # (0077 in its .profile), so the file is the user's alone: 0600.
    assert installed.mode & 0o400
    assert not installed.mode & 0o022


def test_package_is_enabled(site: Site) -> None:
    result = site.run("mkp list")
    assert result.rc == 0, result.stderr
    assert any(
        build_mkp.NAME in line and build_mkp.VERSION in line and "Enabled" in line for line in result.stdout.splitlines()
    ), result.stdout


def test_page_is_served(site: Site) -> None:
    gui = site.gui()
    response = gui.get(site.url + "local/bi_charts/index.html")
    assert response.status_code == 200
    assert "<title>BI aggregation states</title>" in response.text
    # The chart library beside it, as JavaScript.
    response = gui.get(site.url + "local/bi_charts/echarts.min.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["Content-Type"]


def test_state_endpoint_accepts_the_session_cookie(site: Site) -> None:
    response = site.gui().get(site.url + STATE_ENDPOINT, params={"filter_names": [AGGREGATION]})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert list(answer["aggregations"]) == [AGGREGATION]
    # The fields the page reads.
    aggregation = answer["aggregations"][AGGREGATION]
    assert isinstance(aggregation["state"], int)
    assert isinstance(aggregation["acknowledged"], bool)
    assert isinstance(aggregation["in_downtime"], bool)
    assert isinstance(answer["missing_sites"], list)
    assert isinstance(answer["missing_aggr"], list)


def test_state_endpoint_rejects_anonymous_requests(site: Site) -> None:
    response = requests.get(site.url + STATE_ENDPOINT, headers={"Accept": "application/json"})
    assert response.status_code == 401


def test_tree_endpoint_returns_the_full_tree(site: Site) -> None:
    response = site.gui().get(
        site.url + "ajax_fetch_aggregation_data.py", params={"aggregations": json.dumps([AGGREGATION])}
    )
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["result_code"] == 0, answer
    # The fields the page reads, on the root rule and down to a host or service.
    root = answer["result"]["node_config"]["hierarchy"]
    assert root["name"] == AGGREGATION
    assert set(root["rule_id"]) >= {"pack", "rule"}
    assert isinstance(root["type_specific"]["core"]["state"], int)
    assert "acknowledged" in root["type_specific"]["core"]
    assert "in_downtime" in root["type_specific"]["core"]
    leaf = root
    while leaf["children"]:
        leaf = leaf["children"][0]
    assert leaf is not root
    assert "rule_id" not in leaf
    assert leaf["type_specific"]["core"]["hostname"] == MONITORED_HOST
    assert isinstance(leaf["type_specific"]["core"]["state"], int)


def test_list_link_opens_the_aggregation(site: Site) -> None:
    response = site.gui().get(site.url + "view.py", params={"view_name": "aggr_single", "aggr_name": AGGREGATION})
    assert response.status_code == 200
    assert AGGREGATION in response.text


def test_packaged_dashboard_embeds_the_page(site: Site) -> None:
    gui = site.gui()
    if site.version == "2.4":
        # 2.4 renders the widget's iframe into the dashboard page.
        response = gui.get(site.url + "dashboard.py", params={"name": "bi_charts"})
    else:
        # 2.5 builds the dashboard in the browser from this endpoint.
        response = gui.get(
            site.url + "api/unstable/objects/dashboard_relative_grid/bi_charts", headers={"Accept": "application/json"}
        )
    assert response.status_code == 200, response.text[:500]
    assert "local/bi_charts/index.html" in response.text


def _log_in(page: Page, site: Site) -> None:
    """Give the browser the session of a logged-in user."""
    page.context.add_cookies(
        [{"name": cookie.name, "value": cookie.value, "url": site.url} for cookie in site.gui().cookies]
    )


def _items(page: Page, kind: str) -> list[dict[str, Any]]:
    """The chart's items of one kind (the page's hook), once there are any."""
    page.wait_for_function(
        "(kind) => window.biCharts && biCharts.items().some((i) => i.kind === kind)", arg=kind, timeout=60_000
    )
    return [i for i in page.evaluate("biCharts.items()") if i["kind"] == kind]


def test_page_draws_the_pie_in_a_browser(page: Page, site: Site) -> None:
    _log_in(page, site)
    page.goto(site.url + "local/bi_charts/index.html")
    expect(page.locator("#msg.err")).to_have_count(0)
    expect(page.locator("#total")).to_have_text("1")
    assert len(_items(page, "state")) == 1


@pytest.mark.parametrize("view", ["rings", "treemap", "tree", "sankey"])
def test_page_draws_the_trees_in_a_browser(page: Page, site: Site, view: str) -> None:
    _log_in(page, site)
    page.goto(site.url + f"local/bi_charts/index.html?view={view}&depth=5")
    expect(page.locator("#msg.err")).to_have_count(0)
    assert [i["path"] for i in _items(page, "aggregation")] == [AGGREGATION]
    # At least one rule below the aggregation, and the host's services below; the sankey
    # ends in the hosts, its services summed into them.
    assert _items(page, "rule")
    leaves = _items(page, "host" if view == "sankey" else "service")
    assert any(MONITORED_HOST in i["path"] for i in leaves)
    # Hovering the aggregation tells its rule.
    item = _items(page, "aggregation")[0]
    page.evaluate(
        "([s, d]) => biCharts.chart.dispatchAction({ type: 'showTip', seriesIndex: s, dataIndex: d })",
        [item["seriesIndex"], item["dataIndex"]],
    )
    expect(page.locator(".tip")).to_contain_text("Rule default / host")


def test_page_draws_the_groups_in_a_browser(page: Page, site: Site) -> None:
    _log_in(page, site)
    # Per BI pack, the default: the site's one aggregation is of the pack "default".
    page.goto(site.url + "local/bi_charts/index.html?view=groups")
    expect(page.locator("#msg.err")).to_have_count(0)
    assert [i["path"].split(" › ")[0] for i in _items(page, "group-state")] == ["default"]


def test_page_draws_the_tiles_in_a_browser(page: Page, site: Site) -> None:
    _log_in(page, site)
    page.goto(site.url + "local/bi_charts/index.html?view=tiles")
    expect(page.locator("#msg.err")).to_have_count(0)
    assert [i["path"] for i in _items(page, "aggregation")] == [AGGREGATION]


def test_page_draws_the_impact_in_a_browser(page: Page, site: Site) -> None:
    _log_in(page, site)
    page.goto(site.url + "local/bi_charts/index.html?view=impact")
    expect(page.locator("#msg.err")).to_have_count(0)
    # The host's services that are not OK (its agent does not answer), each in the
    # one aggregation; or none, if every one of them is OK by now.
    page.wait_for_function(
        "() => window.biCharts && (biCharts.items().length > 0 ||"
        " document.getElementById('chart').textContent.includes('All hosts and services are OK'))",
        timeout=60_000,
    )
    for item in page.evaluate("biCharts.items()"):
        assert item["kind"] == "impact"
        assert item["path"].startswith(MONITORED_HOST)


def test_dashboard_shows_the_widget_in_a_browser(page: Page, site: Site) -> None:
    _log_in(page, site)
    page.goto(site.url + "dashboard.py?name=bi_charts")
    widget = page.frame_locator('iframe[src*="local/bi_charts/index.html"]')
    expect(widget.locator("#total")).to_have_text("1")
    expect(widget.locator("#msg.err")).to_have_count(0)
