"""Browser tests of the page against the stub in checkmk_stub.py.

Needs pytest-playwright and a browser (``playwright install chromium``, or
``pytest --browser-channel chrome`` to use an installed Chrome).
"""

import pytest
from playwright.sync_api import Page, expect

from checkmk_stub import Stub


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


def test_flat_pie_has_one_slice_per_state_present(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    expect(page.locator("#total")).to_have_text("6")
    expect(page.locator("circle.slice")).to_have_count(4)
    expect(page.locator("path.seg")).to_have_count(0)


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


@pytest.mark.parametrize(
    "depth, segments",
    [
        # 6 aggregations, each with 2 host rules of 2 services.
        pytest.param(1, 6, id="aggregations only"),
        pytest.param(2, 18, id="plus host rules"),
        pytest.param(5, 18, id="deeper than the rules"),
    ],
)
def test_tree_view_draws_one_ring_per_rule_level(page: Page, stub: Stub, depth: int, segments: int) -> None:
    page.goto(f"{stub.page}?view=tree&depth={depth}")
    expect(page.locator("path.seg")).to_have_count(segments)
    # Every service is a pill in the outer band, however few rings are drawn.
    expect(page.locator("path.leaf")).to_have_count(24)
    expect(page.locator("circle.slice")).to_have_count(0)


def test_pills_have_the_state_of_their_service(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tree&depth=1")
    expect(page.locator('path.leaf[data-state="2"]')).to_have_count(1)
    expect(page.locator('path.leaf[aria-label="Payment › Payment-1 › Payment-1 CPU: CRIT"]')).to_have_count(1)


def test_wide_segments_carry_their_name(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=tree&depth=2")
    expect(page.locator("text.label").first).to_be_attached()
    names = page.locator("text.label").all_text_contents()
    assert {"Payment", "ERP"} <= set(names), names
    # A name cut short keeps at least five characters before its ellipsis.
    assert all(not name.endswith("…") or len(name) >= 6 for name in names), names
    # No name upside down: on screen, each one's reading direction points right
    # (or straight up or down, where both are readable).
    directions = page.locator("text.label").evaluate_all("(ts) => ts.map((t) => t.getScreenCTM().a)")
    assert directions and all(a > -0.01 for a in directions), directions


def test_labels_can_be_turned_off(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(stub.page + "?view=tree&labels=0")
    expect(page.locator("path.seg")).to_have_count(18)
    expect(page.locator("text.label")).to_have_count(0)


def test_labels_leave_out_what_would_be_unreadable(page: Page, stub: Stub) -> None:
    page.set_viewport_size({"width": 200, "height": 200})
    page.goto(stub.page + "?view=tree&depth=3")
    expect(page.locator("path.seg")).to_have_count(18)
    expect(page.locator("text.label")).to_have_count(0)


def test_legend_bars_show_the_shares(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    expect(page.locator("#legend .fill")).to_have_count(4)
    widths = page.locator("#legend .fill").evaluate_all("(fills) => fills.map((f) => parseFloat(f.style.width))")
    assert widths == [50, 16.7, 16.7, 16.7]


def test_tree_view_legend_counts_hosts_and_services(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tree")
    # 24 services in total; each non-OK aggregation has exactly one bad service.
    expect(page.locator("#legend tbody tr")).to_have_text(
        ["OK 3 50 % 21", "WARN 1 17 % 1", "CRIT 1 17 % 1", "UNKNOWN 1 17 % 1"], use_inner_text=True
    )


@pytest.mark.parametrize(
    "label, expected",
    [
        pytest.param(
            "Payment: CRIT",
            ["Payment", "CRIT, acknowledged", "Rule default / application", "4 hosts and services below: 3 OK, 1 CRIT"],
            id="aggregation",
        ),
        pytest.param(
            "Payment › Payment-1: CRIT",
            ["Payment", "Payment-1", "CRIT", "Rule default / host", "2 hosts and services below: 1 OK, 1 CRIT"],
            id="rule",
        ),
        pytest.param(
            "Payment › Payment-1 › Payment-1 CPU: CRIT",
            ["Payment › Payment-1", "Payment-1 CPU", "CRIT", "Service on host Payment-1"],
            id="service",
        ),
    ],
)
def test_hover_on_segment_shows_its_details(page: Page, stub: Stub, label: str, expected: list[str]) -> None:
    page.goto(stub.page + "?view=tree")
    page.locator(f'[aria-label="{label}"]').hover()
    expect(page.locator("#tip")).to_be_visible()
    for line in expected:
        expect(page.locator("#tip")).to_contain_text(line)


def test_hover_on_slice_lists_its_aggregations(page: Page, stub: Stub) -> None:
    page.goto(stub.page)
    # A slice is a dashed stroke on a full circle, so the pointer has to go onto
    # the stroke itself: WARN covers 50 % to 66.7 % of the circumference.
    x, y = page.locator('circle.slice[data-state="1"]').evaluate(
        """(circle) => {
            const point = circle.getPointAtLength(circle.getTotalLength() * 0.58);
            const onScreen = point.matrixTransform(circle.getScreenCTM());
            return [onScreen.x, onScreen.y];
        }"""
    )
    page.mouse.move(x, y)
    expect(page.locator("#tip")).to_contain_text("WARN: 1 of 6 aggregations (16.7 %)")
    expect(page.locator("#tip")).to_contain_text("Storage in downtime")


def test_hover_on_legend_row_fades_other_states(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tree&depth=2")
    page.locator("#legend tbody tr", has_text="CRIT").hover()
    expect(page.locator("#tip")).to_contain_text("CRIT: 1 of 6 aggregations")
    expect(page.locator("#slices.dim")).to_have_count(1)
    # Payment and its failing host rule.
    expect(page.locator("path.seg.hl")).to_have_count(2)
    page.locator("#total").hover()
    expect(page.locator("#slices.dim")).to_have_count(0)
    expect(page.locator("#tip")).to_be_hidden()


def test_tree_view_refuses_more_aggregations_than_max(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?view=tree&max=5")
    expect(page.locator("#msg")).to_contain_text("Tree view is limited to 5 aggregations, 6 matched")
    expect(page.locator("circle.slice")).to_have_count(4)
    assert stub.tree_requests == 0


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("?depth=0", "Parameter depth must be a positive integer.", id="depth zero"),
        pytest.param("?max=many", "Parameter max must be a positive integer.", id="max not a number"),
        pytest.param("?theme=blue", "Parameter theme must be dark or light.", id="unknown theme"),
    ],
)
def test_invalid_parameter_is_reported(page: Page, stub: Stub, query: str, message: str) -> None:
    page.goto(stub.page + query)
    expect(page.locator("#msg.err")).to_have_text(message)
    expect(page.locator("circle.slice")).to_have_count(0)


def test_failed_refresh_removes_the_chart(page: Page, stub: Stub) -> None:
    page.goto(stub.page + "?refresh=1")
    expect(page.locator("circle.slice")).to_have_count(4)
    stub.state_status = 500
    expect(page.locator("#msg.err")).to_contain_text("REST API returned HTTP 500")
    expect(page.locator("circle.slice")).to_have_count(0)
    expect(page.locator("#legend tr")).to_have_count(0)
    expect(page.locator("#list li")).to_have_count(0)
    expect(page.locator("#total")).to_have_text("?")


def test_failed_tree_request_is_reported(page: Page, stub: Stub) -> None:
    stub.tree_result_code = 1
    page.goto(stub.page + "?view=tree")
    expect(page.locator("#msg.err")).to_have_text("Loading the aggregation trees failed: tree unavailable")
    expect(page.locator("path.seg")).to_have_count(0)


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
    stub.aggregations = {'<img src=x onerror="document.title=1">': (2, False, False, "web")}
    page.goto(stub.page)
    expect(page.locator("#list a")).to_have_text('<img src=x onerror="document.title=1">')
    expect(page.locator("#list img")).to_have_count(0)
    assert page.title() == "BI aggregation states"
