"""Browser tests of the page against the stub in checkmk_stub.py.

Needs pytest-playwright and a browser (``playwright install chromium``, or
``pytest --browser-channel chrome`` to use an installed Chrome), and the chart
library in node_modules (``npm ci``).

ECharts draws shapes that say nothing about what they stand for, so the tests
read the chart through the page's hook ``biCharts.items()``: every item's path,
state, kind and color, and where ECharts keeps it, which also lets a test show
an item's tooltip as hovering would.
"""

import re
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, expect

from checkmk_stub import Stub

# 6 aggregations, each with 2 host rules of 2 services.
RULES = 6 + 12
SERVICES = 24


def items(page: Page, count: int | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    """The chart's items (of one kind), once the chart shows at least ``count`` of them."""
    if count:
        page.wait_for_function(
            "([count, kind]) => window.biCharts &&"
            " biCharts.items().filter((i) => !kind || i.kind === kind).length >= count",
            arg=[count, kind],
        )
    found = page.evaluate("biCharts.items()")
    return [item for item in found if not kind or item["kind"] == kind]


def click(page: Page, path: str) -> None:
    """Click an item with the mouse, in the middle of where ECharts drew it."""
    item = next(item for item in items(page) if item["path"] == path)
    x, y = page.evaluate(
        """([s, d]) => {
            const layout = biCharts.chart.getModel().getSeriesByIndex(s).getData().getItemLayout(d);
            const box = document.getElementById("chart").getBoundingClientRect();
            // Bars have a rectangle; the tiles their middle as the value.
            const [x, y] = layout && layout.width !== undefined
                ? [layout.x + layout.width / 2, layout.y + layout.height / 2]
                : biCharts.chart.getOption().series[s].data[d].value;
            return [box.left + x, box.top + y];
        }""",
        [item["seriesIndex"], item["dataIndex"]],
    )
    page.mouse.click(x, y)


def show_tip(page: Page, path: str) -> None:
    """Show an item's tooltip, as hovering it does."""
    item = next(item for item in items(page) if item["path"] == path)
    page.evaluate(
        "([s, d]) => biCharts.chart.dispatchAction({ type: 'showTip', seriesIndex: s, dataIndex: d })",
        [item["seriesIndex"], item["dataIndex"]],
    )


# --- the pie, the legend and the list ----------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("", ["OK 3 50 %", "WARN 1 17 %", "CRIT 1 17 %", "UNKNOWN 1 17 %"], id="all aggregations"),
        pytest.param("?group=web", ["OK 2 67 %", "WARN 0 0 %", "CRIT 1 33 %"], id="one group"),
        pytest.param("?name=Shop&name=ERP", ["OK 1 50 %", "WARN 0 0 %", "CRIT 0 0 %", "UNKNOWN 1 50 %"], id="two names"),
    ],
)
def test_legend_counts_and_shares(page: Page, stub: Stub, query: str, expected: list[str]) -> None:
    page.goto(stub.page + query)
    expect(page.locator("#legend tbody tr")).to_have_text(expected, use_inner_text=True)


def test_pie_has_one_slice_per_state_present(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    expect(page.locator("#total")).to_have_text("6")
    slices = items(page, 4)
    assert [(s["path"], s["kind"]) for s in slices] == [
        ("OK", "state"), ("WARN", "state"), ("CRIT", "state"), ("UNKNOWN", "state")
    ]


def test_ok_is_paler_than_the_problems(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    colors = {s["path"]: s["color"] for s in items(page, 4)}
    # 55 % opacity: 0x8c.
    assert colors["OK"] == "#13d3898c"
    assert colors["CRIT"] == "#ff3232"


def test_muted_0_draws_ok_in_full_color(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?muted=0")
    assert {s["path"]: s["color"] for s in items(page, 4)}["OK"] == "#13d389"


def test_colors_replace_the_state_colors(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?colors=crit:00ff00,ok:0000ff&muted=0")
    colors = {s["path"]: s["color"] for s in items(page, 4)}
    assert (colors["CRIT"], colors["OK"]) == ("#00ff00", "#0000ff")
    expect(page.locator("#legend tbody tr", has_text="CRIT").locator("i")).to_have_css(
        "background-color", "rgb(0, 255, 0)"
    )


def test_list_holds_the_problems_worst_first(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    expect(page.locator("#list li")).to_have_text(
        ["CRIT Payment ack", "UNKNOWN ERP", "WARN Storage downtime"], use_inner_text=True
    )
    expect(page.locator("#list a").first).to_have_attribute(
        "href", stub.base + "view.py?view_name=aggr_single&aggr_name=Payment"
    )


def test_click_on_legend_row_narrows_the_list(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    page.locator("#legend tbody tr", has_text="OK").click()
    expect(page.locator("#list li")).to_have_text(["OK Mail", "OK Shop", "OK Wiki"], use_inner_text=True)


def test_legend_bars_show_the_shares(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    expect(page.locator("#legend .fill")).to_have_count(4)
    widths = page.locator("#legend .fill").evaluate_all("(fills) => fills.map((f) => parseFloat(f.style.width))")
    assert widths == [50, 16.7, 16.7, 16.7]


def test_hover_on_slice_lists_its_aggregations(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    items(page, 4)
    show_tip(page, "WARN")
    expect(page.locator(".tip")).to_contain_text("WARN: 1 of 6 aggregations (16.7 %)")
    expect(page.locator(".tip")).to_contain_text("Storage in downtime")


def test_hover_on_legend_row_fades_other_states(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=rings&depth=2")
    items(page, RULES)
    page.locator("#legend tbody tr", has_text="CRIT").hover()
    page.wait_for_function("biCharts.items().some((i) => i.faded)")
    full = [i["path"] for i in items(page) if not i["faded"]]
    # Payment, its failing host rule and that host's failing service.
    assert full == ["Payment", "Payment › Payment-1", "Payment › Payment-1 › Payment-1 CPU"], full
    # Off the row again: everything in full color.
    page.mouse.move(1, 1)
    page.wait_for_function("!biCharts.items().some((i) => i.faded)")


# --- the views of the trees ----------------------------------------------------------


@pytest.mark.parametrize(
    "depth, rules",
    [
        pytest.param(1, 6, id="aggregations only"),
        pytest.param(2, RULES, id="plus host rules"),
        pytest.param(5, RULES, id="deeper than the rules"),
    ],
)
def test_rings_draw_one_ring_per_rule_level(page: Page, stub: Stub, depth: int, rules: int) -> None:
    page.goto(f"{stub.page}?view=rings&depth={depth}")
    items(page, SERVICES, "service")
    found = items(page)
    assert len([i for i in found if i["kind"] in ("aggregation", "rule")]) == rules
    # Every service is a pill in the outer band, however few rings are drawn.
    assert len([i for i in found if i["kind"] == "service"]) == SERVICES


def test_rings_legend_counts_hosts_and_services(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=rings")
    # 24 services in total; each non-OK aggregation has exactly one bad service.
    expect(page.locator("#legend tbody tr")).to_have_text(
        ["OK 3 50 % 21", "WARN 1 17 % 1", "CRIT 1 17 % 1", "UNKNOWN 1 17 % 1"], use_inner_text=True
    )


def test_wide_ring_segments_carry_their_name_along_the_ring(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=rings&depth=2&animation=0&name=Payment")
    items(page, 4, "service")
    # One aggregation: its ring is whole, its two host rules half a ring each, wide
    # enough to bend their names along them.
    expect(page.locator("#arcs textPath")).to_have_text(["Payment", "Payment-1", "Payment-2"])
    # Six aggregations: a sixth of the ring each, narrow, so along the radius.
    page.goto(stub.page + "?view=rings&depth=2&animation=0")
    items(page, SERVICES, "service")
    expect(page.locator("#chart text", has_text="ERP").first).to_be_attached()


@pytest.mark.parametrize("view", ["pie", "rings"])
def test_bent_names_read_from_left_to_right(page: Page, stub: Stub, view: str) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(f"{stub.page}?view={view}&animation=0&name=Payment&name=ERP&name=Shop")
    expect(page.locator("#arcs textPath").first).to_be_attached()
    # Each arc's end lies right of its start (or level with it, at the sides), so that no
    # name stands on its head.
    ends = page.locator("#arcs path").evaluate_all(
        "(arcs) => arcs.map((a) => [a.getPointAtLength(0).x, a.getPointAtLength(a.getTotalLength()).x])"
    )
    assert ends and all(end >= start - 1 for start, end in ends), ends


def test_pie_slices_carry_their_state_and_count(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?animation=0")
    expect(page.locator("#arcs textPath", has_text="OK 3")).to_have_count(1)


def test_labels_0_draws_no_names(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=rings&labels=0&animation=0")
    items(page, SERVICES, "service")
    expect(page.locator("#chart text")).to_have_count(0)
    expect(page.locator("#arcs text")).to_have_count(0)


@pytest.mark.parametrize(
    "path, expected",
    [
        pytest.param(
            "Payment",
            ["Payment", "CRIT, acknowledged", "Rule default / application", "4 hosts and services below: 3 OK, 1 CRIT"],
            id="aggregation",
        ),
        pytest.param(
            "Payment › Payment-1",
            ["Payment", "Payment-1", "CRIT", "Rule default / host", "2 hosts and services below: 1 OK, 1 CRIT"],
            id="rule",
        ),
        pytest.param(
            "Payment › Payment-1 › Payment-1 CPU",
            ["Payment › Payment-1", "Payment-1 CPU", "CRIT", "Service on host Payment-1"],
            id="service",
        ),
    ],
)
@pytest.mark.parametrize("view", ["rings", "treemap", "tree"])
def test_hover_on_a_node_shows_its_details(page: Page, stub: Stub, view: str, path: str, expected: list[str]) -> None:
    page.goto(f"{stub.page}?view={view}")
    items(page, SERVICES, "service")
    show_tip(page, path)
    for line in expected:
        expect(page.locator(".tip")).to_contain_text(line)


@pytest.mark.parametrize("view", ["treemap", "tree"])
def test_treemap_and_tree_hold_every_node(page: Page, stub: Stub, view: str) -> None:
    page.goto(f"{stub.page}?view={view}")
    items(page, SERVICES, "service")
    found = items(page)
    kinds = [i["kind"] for i in found]
    assert (kinds.count("aggregation"), kinds.count("rule"), kinds.count("service")) == (6, 12, SERVICES)


@pytest.mark.parametrize("view", ["rings", "treemap", "tree", "impact"])
def test_views_of_the_trees_refuse_more_aggregations_than_max(page: Page, stub: Stub, view: str) -> None:
    page.goto(f"{stub.page}?view={view}&max=5")
    expect(page.locator("#msg")).to_contain_text(f"The {view} view is limited to 5 aggregations, 6 matched")
    assert len(items(page, 4, "state")) == 4
    assert stub.tree_requests == 0


def test_failed_tree_request_is_reported(page: Page, stub: Stub) -> None:
    stub.tree_result_code = 1
    page.goto(stub.page + "?view=rings")
    expect(page.locator("#msg.err")).to_have_text("Loading the aggregation trees failed: tree unavailable")
    assert items(page) == []


# --- the views of the groups ---------------------------------------------------------


def test_groups_draw_a_donut_per_group(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=groups&group=web&group=infra")
    found = items(page, 5, "group-state")
    assert sorted(i["path"] for i in found) == [
        "infra › OK", "infra › UNKNOWN", "infra › WARN", "web › CRIT", "web › OK"
    ]
    titles = page.evaluate("biCharts.chart.getOption().title.map((t) => [t.subtext, t.text])")
    # web: Shop and Wiki OK, Payment CRIT; infra: Mail OK, Storage WARN, ERP UNKNOWN.
    assert titles == [["web", "67 %"], ["infra", "33 %"]]


def test_groups_by_pack_without_group_parameters(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=groups")
    found = items(page, 4, "group-state")
    # The stub's trees are all of the BI pack "default".
    assert sorted(i["path"] for i in found) == ["default › CRIT", "default › OK", "default › UNKNOWN", "default › WARN"]


def test_bars_stack_the_states_per_group(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=bars&group=web&group=infra")
    items(page, 5, "group-state")
    option = page.evaluate(
        "(() => { const o = biCharts.chart.getOption();"
        " return { groups: o.yAxis[0].data, series: o.series.map((s) => [s.name, s.data.map((d) => d.value)]) }; })()"
    )
    assert option["groups"] == ["web", "infra"]
    assert option["series"] == [["OK", [2, 1]], ["WARN", [0, 1]], ["CRIT", [1, 0]], ["UNKNOWN", [0, 1]]]


def test_hover_on_a_group_shows_its_states(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=bars&group=web&group=infra")
    items(page, 5, "group-state")
    show_tip(page, "infra › WARN")
    expect(page.locator(".tip")).to_contain_text("infra")
    expect(page.locator(".tip")).to_contain_text("3 aggregations: 1 OK, 1 WARN, 1 UNKNOWN")


# --- tiles and impact -----------------------------------------------------------------


def test_tiles_hold_every_aggregation_worst_first(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles")
    found = items(page, 6, "aggregation")
    assert [(i["path"], i["state"]) for i in found] == [
        ("Payment", 2), ("ERP", 3), ("Storage", 1), ("Mail", 0), ("Shop", 0), ("Wiki", 0)
    ]
    expect(page.locator("#chart text").first).to_have_text("Payment")
    # The states alone: no tree is loaded.
    assert stub.tree_requests == 0


def test_tiles_name_acknowledgement_and_downtime(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles")
    items(page, 6, "aggregation")
    # A line per <text> or <tspan>, as the SVG renderer writes them.
    lines = page.locator("#chart text, #chart tspan").evaluate_all(
        "(nodes) => nodes.filter((n) => !n.querySelector('tspan')).map((n) => n.textContent)"
    )
    assert "ack" in lines and "downtime" in lines


def test_hover_and_click_on_a_tile(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles")
    items(page, 6, "aggregation")
    show_tip(page, "Payment")
    expect(page.locator(".tip")).to_contain_text("CRIT, acknowledged")
    click(page, "Storage")
    expect(page.locator("#detail")).to_have_text("Storage: WARN downtime", use_inner_text=True)


def test_tiles_labels_0_draws_no_names(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles&labels=0")
    items(page, 6, "aggregation")
    expect(page.locator("#chart text")).to_have_count(0)


SHARED = {"Shop": [("san-1", "Latency", 1)], "Payment": [("san-1", "Latency", 1)], "Storage": [("san-1", "Latency", 1)]}


def impact(page: Page) -> dict[str, Any]:
    """The rows of the view impact and, per state, the aggregations of each row."""
    return page.evaluate(
        "(() => { const o = biCharts.chart.getOption();"
        " return { rows: o.yAxis[0].data, series: o.series.map((s) => [s.name, s.data.map((d) => d.value)]) }; })()"
    )


def test_impact_ranks_what_drags_most_aggregations_down(page: Page, stub: Stub) -> None:
    stub.extra_leaves = SHARED
    page.goto(stub.page + "?view=impact")
    items(page, 4, "impact")
    shown = impact(page)
    # san-1 is in three aggregations, two of them not OK; then each aggregation's own
    # service, CRIT before UNKNOWN before WARN.
    assert shown["rows"] == ["san-1 › Latency", "Payment-1 › CPU", "ERP-1 › CPU", "Storage-1 › CPU"]
    assert shown["series"] == [
        ["OK", [1, 0, 0, 0]], ["WARN", [1, 0, 0, 1]], ["CRIT", [1, 1, 0, 0]], ["UNKNOWN", [0, 0, 1, 0]]
    ]


def test_impact_top_limits_the_rows(page: Page, stub: Stub) -> None:
    stub.extra_leaves = SHARED
    page.goto(stub.page + "?view=impact&top=2")
    items(page, 2, "impact")
    assert impact(page)["rows"] == ["san-1 › Latency", "Payment-1 › CPU"]


def test_hover_and_click_on_an_impact_bar(page: Page, stub: Stub) -> None:
    stub.extra_leaves = SHARED
    page.goto(stub.page + "?view=impact")
    items(page, 4, "impact")
    show_tip(page, "san-1 › Latency › WARN")
    for line in ["san-1 › Latency", "WARN", "In 3 aggregations: 1 OK, 1 WARN, 1 CRIT", "Payment", "Shop"]:
        expect(page.locator(".tip")).to_contain_text(line)
    # A click narrows the list to the aggregations of that state the host or service is in.
    click(page, "san-1 › Latency › OK")
    expect(page.locator("#list li")).to_have_text(["OK Shop"], use_inner_text=True)


def test_impact_when_everything_is_ok(page: Page, stub: Stub) -> None:
    stub.aggregations = {"Shop": (0, False, False, "web")}
    page.goto(stub.page + "?view=impact")
    expect(page.locator("#chart")).to_contain_text("All hosts and services are OK")


# --- the views of the trees: crowding, order, problems only, flows ----------------------

# 300 more OK services below the aggregation Shop: more than the rings' band has room for.
CROWD = {"Shop": [(f"web-{i}", "CPU", 0) for i in range(300)]}


def test_rings_draw_neighbours_of_one_state_as_one_pill_when_crowded(page: Page, stub: Stub) -> None:
    stub.extra_leaves = CROWD
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=rings&animation=0")
    found = items(page, 1, "leaves")
    paths = [i["path"] for i in found]
    assert "Shop › 300 hosts and services" in paths
    # Payment-2's two services are OK alike; Payment-1's are not, so they stay apart.
    assert "Payment › Payment-2 › 2 hosts and services" in paths
    assert {"Payment › Payment-1 › Payment-1 CPU", "Payment › Payment-1 › Payment-1 Memory"} <= {
        i["path"] for i in items(page, kind="service")
    }
    show_tip(page, "Shop › 300 hosts and services")
    for line in ["OK", "web-0 › CPU", "and 292 more"]:
        expect(page.locator(".tip")).to_contain_text(line)


def test_rings_draw_a_pill_per_host_or_service_when_there_is_room(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=rings&animation=0")
    items(page, SERVICES, "service")
    assert items(page, kind="leaves") == []


def test_treemap_draws_the_worst_first_in_opaque_colors(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=treemap")
    items(page, SERVICES, "service")
    data = page.evaluate("biCharts.chart.getOption().series[0].data.map((d) => [d.name, d.itemStyle.color])")
    assert [name for name, _ in data] == ["Payment", "ERP", "Storage", "Mail", "Shop", "Wiki"]
    # Drawn over its parent, a pale OK would add up to a brighter one.
    assert all(len(color) == 7 for _, color in data), data


def test_tree_nodes_are_filled_with_their_state(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tree")
    items(page, SERVICES, "service")
    assert page.evaluate("biCharts.chart.getOption().series[0].symbol") == "circle"


@pytest.mark.parametrize("view", ["rings", "treemap", "tree", "sankey"])
def test_problems_1_draws_only_the_paths_to_problems(page: Page, stub: Stub, view: str) -> None:
    page.goto(f"{stub.page}?view={view}&problems=1&depth=5")
    found = items(page, 3, "aggregation")
    assert sorted(i["path"] for i in found) == ["ERP", "Payment", "Storage"]
    expect(page.locator("#msg")).to_have_text("Problems only: 3 aggregations OK throughout left out.")
    # Of each, its host with the problem; the other host is OK throughout.
    leaves = [i["path"] for i in items(page) if i["kind"] in ("service", "host")]
    assert not any("-2" in path for path in leaves), leaves
    # The tooltip still tells what is below in all.
    show_tip(page, "Payment")
    expect(page.locator(".tip")).to_contain_text("4 hosts and services below: 3 OK, 1 CRIT")


def test_problems_1_when_everything_is_ok(page: Page, stub: Stub) -> None:
    stub.aggregations = {"Shop": (0, False, False, "web")}
    page.goto(stub.page + "?view=rings&problems=1")
    expect(page.locator("#chart")).to_contain_text("All hosts and services are OK")


def test_sankey_joins_what_aggregations_share(page: Page, stub: Stub) -> None:
    stub.extra_leaves = SHARED
    page.goto(stub.page + "?view=sankey")
    found = items(page, 6, "aggregation")
    kinds = [i["kind"] for i in items(page)]
    # 6 aggregations, their 12 host rules, the 12 hosts below those and san-1 once.
    assert (kinds.count("aggregation"), kinds.count("rule"), kinds.count("host")) == (6, 12, 13)
    # Worst first, as the tiles.
    assert [i["path"] for i in found][:3] == ["Payment", "ERP", "Storage"]
    show_tip(page, "san-1")
    for line in ["san-1", "WARN", "3 hosts and services: 3 WARN", "In 3 aggregations", "Payment › san-1 Latency"]:
        expect(page.locator(".tip")).to_contain_text(line)
    links = page.evaluate("biCharts.chart.getOption().series[0].links.length")
    # Each aggregation to its 2 rules, each rule to its host, san-1 from 3 aggregations.
    assert links == 12 + 12 + 3


def test_sankey_click_on_a_host_shows_it(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=sankey")
    items(page, 6, "aggregation")
    item = next(i for i in items(page) if i["path"] == "Payment-1" and i["kind"] == "host")
    page.evaluate(
        "([s, d]) => biCharts.chart.dispatchAction({ type: 'showTip', seriesIndex: s, dataIndex: d })",
        [item["seriesIndex"], item["dataIndex"]],
    )
    expect(page.locator(".tip")).to_contain_text("2 hosts and services: 1 OK, 1 CRIT")


# --- refreshes, changes, patterns, screen readers, touch ------------------------------


def test_refresh_loads_a_tree_again_only_when_its_aggregation_changed(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=rings&refresh=1")
    items(page, SERVICES, "service")
    assert stub.tree_requests == 6
    page.wait_for_timeout(2500)
    assert stub.tree_requests == 6
    stub.aggregations["Shop"] = (2, False, False, "web")
    expect(page.locator("#list li", has_text="Shop")).to_have_count(1)
    assert stub.tree_requests == 7


def test_a_changed_state_is_marked(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles&refresh=1")
    items(page, 6, "aggregation")
    # The first load knows no change.
    expect(page.locator("#list li.changed")).to_have_count(0)
    stub.aggregations["Shop"] = (2, False, False, "web")
    # The time as the viewer's browser writes it, e.g. 14:05 or 2:05 PM.
    expect(page.locator("#list li.changed")).to_have_text(re.compile(r"CRIT\s*Shop\s*since \d\d?:\d\d"))
    show_tip(page, "Shop")
    expect(page.locator(".tip")).to_contain_text("Changed at")
    # Outlined among the tiles.
    assert page.evaluate("Array.from(document.querySelectorAll('#chart path[stroke-width=\"3\"]')).length") == 1


def test_patterns_1_marks_the_problem_states(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?patterns=1")
    items(page, 4, "state")
    decals = page.evaluate(
        "Object.fromEntries(biCharts.chart.getOption().series[0].data.map((d) => [d.name, Boolean(d.itemStyle.decal)]))"
    )
    assert decals == {"OK": False, "WARN": True, "CRIT": True, "UNKNOWN": True}
    page.goto(stub.page)
    items(page, 4, "state")
    assert not page.evaluate("biCharts.chart.getOption().series[0].data.some((d) => d.itemStyle.decal)")


def test_screen_readers_get_a_description(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tiles&title=Shop%20floor")
    items(page, 6, "aggregation")
    expect(page.locator("#chart")).to_have_attribute(
        "aria-label", re.compile("Shop floor, tiles: 6 aggregations, 3 OK, 1 WARN, 1 CRIT, 1 UNKNOWN")
    )


def test_a_tap_shows_the_details(browser: Browser, stub: Stub) -> None:
    context = browser.new_context(has_touch=True, viewport={"width": 900, "height": 700})
    page = context.new_page()
    page.goto(stub.page + "?view=tiles&animation=0")
    items(page, 6, "aggregation")
    item = next(i for i in items(page) if i["path"] == "Payment")
    x, y = page.evaluate(
        """([s, d]) => {
            const [x, y] = biCharts.chart.getOption().series[s].data[d].value;
            const box = document.getElementById("chart").getBoundingClientRect();
            return [box.left + x, box.top + y];
        }""",
        [item["seriesIndex"], item["dataIndex"]],
    )
    page.touchscreen.tap(x, y)
    expect(page.locator(".tip")).to_contain_text("CRIT, acknowledged")
    context.close()


# --- parameters, errors, theme ---------------------------------------------------------


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("?depth=0", "Parameter depth must be a positive integer.", id="depth zero"),
        pytest.param("?max=many", "Parameter max must be a positive integer.", id="max not a number"),
        pytest.param("?theme=blue", "Parameter theme must be dark or light.", id="unknown theme"),
        pytest.param(
            "?view=flow",
            "Parameter view must be one of pie, rings, treemap, tree, groups, bars, tiles, impact, sankey.",
            id="unknown view",
        ),
        pytest.param("?top=0", "Parameter top must be a positive integer.", id="top zero"),
        pytest.param("?by=host", "Parameter by must be one of group, pack.", id="unknown grouping"),
        pytest.param(
            "?colors=crit:red",
            "Parameter colors takes state:rrggbb pairs, e.g. ok:2e7d32,crit:c62828.",
            id="color not hex",
        ),
    ],
)
def test_invalid_parameter_is_reported(page: Page, stub: Stub, query: str, message: str) -> None:
    page.goto(stub.page + query)
    expect(page.locator("#msg.err")).to_have_text(message)
    expect(page.locator("#legend tr")).to_have_count(0)


def test_failed_refresh_removes_the_chart(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?refresh=1")
    items(page, 4)
    stub.state_status = 500
    expect(page.locator("#msg.err")).to_contain_text("REST API returned HTTP 500")
    assert items(page) == []
    expect(page.locator("#legend tr")).to_have_count(0)
    expect(page.locator("#list li")).to_have_count(0)
    expect(page.locator("#total")).to_have_text("?")


@pytest.mark.parametrize(
    "parent_theme, widget_query, light",
    [
        pytest.param("facelift", "", True, id="light Checkmk theme"),
        pytest.param("modern-dark", "", False, id="dark Checkmk theme"),
        pytest.param("facelift", "theme=dark", False, id="parameter wins"),
    ],
)
def test_theme_follows_the_embedding_page(
    page: Page, stub: Stub, parent_theme: str, widget_query: str, light: bool
) -> None:
    stub.parent_theme = parent_theme
    page.goto(f"{stub.base}dashboard.py?widget={widget_query}")
    widget = page.frame_locator("#widget")
    expect(widget.locator("#total")).to_have_text("6")
    expect(widget.locator("body.light")).to_have_count(1 if light else 0)


def test_names_are_inserted_as_text(page: Page, stub: Stub) -> None:
    name = '<img src=x onerror="document.title=1">'
    stub.aggregations = {name: (2, False, False, "web")}
    page.goto(stub.page)
    expect(page.locator("#list a")).to_have_text(name)
    expect(page.locator("#list img")).to_have_count(0)
    # The tooltip is HTML: the name goes in as text there too.
    items(page, 1)
    show_tip(page, "CRIT")
    expect(page.locator(".tip")).to_contain_text(name)
    expect(page.locator(".tip img")).to_have_count(0)
    assert page.title() == "BI aggregation states"
