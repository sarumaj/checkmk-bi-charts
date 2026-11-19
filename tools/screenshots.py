#!/usr/bin/env python3
"""Renders the README's screenshots from sample data, without a Checkmk site.

    python3 tools/screenshots.py     # writes docs/screenshot*.png

Serves the page with the stand-in for Checkmk's endpoints the unit tests use
(tests/unit/checkmk_stub.py), filled with made-up aggregations and trees, and
shoots it in Chromium with Playwright (requirements-test.txt). The pictures
say that they show sample data.
"""

import random
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tests" / "unit"))

import checkmk_stub  # noqa: E402

# Title -> (state, acknowledged, in downtime, BI group).
SAMPLE: dict[str, tuple[int, bool, bool, str]] = {
    "Core Network East": (2, False, False, "network"),
    "Core Network West": (0, False, False, "network"),
    "Payment API": (2, True, False, "web"),
    "Legacy ERP": (3, False, False, "business"),
    "Container Registry": (1, False, False, "platform"),
    "Object Storage": (1, False, True, "platform"),
    "Reporting Database": (1, False, False, "business"),
    "Web Shop": (0, False, False, "web"),
    "Customer Portal": (0, False, False, "web"),
    "Mail": (0, False, False, "business"),
    "Directory": (0, False, False, "platform"),
    "Backup": (0, False, False, "platform"),
    "VPN": (0, False, False, "network"),
    "DNS": (0, False, False, "network"),
    "Monitoring": (0, False, False, "platform"),
    "Wiki": (0, False, False, "business"),
    "Ticketing": (0, False, False, "business"),
    "CI Runners": (0, False, False, "platform"),
    "Search": (0, False, False, "web"),
    "File Shares": (0, False, False, "business"),
}
SERVICES = ["CPU load", "Memory", "Filesystem /", "Interface eth0", "NTP", "HTTPS", "Uptime"]
LAYERS = ["Frontend", "Application", "Database", "Storage", "Network"]
# Hosts and services that several aggregations share: (host, service, state, aggregations).
SHARED: list[tuple[str, str, int, set[str]]] = [
    ("core-sw1", "Interface uplink", 2, {"Core Network East", "Payment API", "Web Shop", "Customer Portal", "VPN"}),
    ("san-01", "Volume latency", 1, {"Object Storage", "Reporting Database", "Legacy ERP", "Backup"}),
    ("dc-01", "NTP", 1, {"Directory", "Mail"}),
]


def sample_tree(title: str) -> dict[str, object]:
    """An aggregation of 2 to 4 layers of 1 to 3 hosts with 2 to 5 services each;
    a problem state sits on one service and the rules above it."""
    state, acknowledged, in_downtime, _group = SAMPLE[title]
    chance = random.Random(title)
    layers = []
    for index, layer in enumerate(chance.sample(LAYERS, chance.randint(2, 4))):
        hosts = []
        for number in range(1, chance.randint(1, 3) + 1):
            host = f"{title.split()[0].lower()}-{layer[:2].lower()}{number}"
            bad = state if index == 0 and number == 1 else 0
            services = [
                checkmk_stub._leaf(host, service, bad if position == 0 else 0)
                for position, service in enumerate(chance.sample(SERVICES, chance.randint(2, 5)))
            ]
            hosts.append(checkmk_stub._rule(host, "host", bad, services))
        layers.append(checkmk_stub._rule(f"{title} {layer}", "layer", state if index == 0 else 0, hosts))
    shared = [(host, service, bad) for host, service, bad, titles in SHARED if title in titles]
    if shared:
        # The rule as bad as its worst; the aggregation above may still be OK (redundancy).
        leaves = [checkmk_stub._leaf(*leaf) for leaf in shared]
        layers.append(checkmk_stub._rule(f"{title} Shared", "shared", max(bad for _, _, bad in shared), leaves))
    root = checkmk_stub._rule(title, "application", state, layers)
    root["type_specific"] = {"core": {"state": state, "in_downtime": int(in_downtime), "acknowledged": acknowledged}}
    return root


# The frame around the widgets: two dashboard elements side by side.
FRAME = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; padding: 14px 18px; background: #1b2128; font: 13px Arial, sans-serif; color: #9aa3ad; }}
.row {{ display: flex; gap: 16px; margin-top: 10px; }}
.box {{ flex: 1; background: #232d36; border: 1px solid #33404c; }}
.box h2 {{ margin: 0; padding: 8px 12px; font-size: 13px; color: #e8e8e8; border-bottom: 1px solid #33404c; }}
iframe {{ border: 0; width: 100%; height: {height}px; display: block; }}
</style></head><body>Rendered with sample data, not from a live Checkmk site
<div class="row">{boxes}</div></body></html>"""


def frame(stub: checkmk_stub.Stub, widgets: list[tuple[str, str]], height: int) -> str:
    boxes = "".join(
        f'<div class="box"><h2>{title}</h2><iframe src="{stub.page}?{query}"></iframe></div>'
        for title, query in widgets
    )
    return FRAME.format(height=height, boxes=boxes)


GROUPS = "group=network&group=web&group=platform&group=business"
# Picture -> the widgets side by side, their height, the path whose tooltip shows.
SHOTS: dict[str, tuple[list[tuple[str, str]], int, str | None]] = {
    "screenshot.png": ([("BI aggregation states", ""), ("Web applications", "group=web")], 420, None),
    "screenshot-rings.png": (
        [("view=rings", "view=rings"), ("Payment API (view=rings&depth=4)", "view=rings&depth=4&name=Payment%20API")],
        560,
        None,
    ),
    "screenshot-treemap.png": ([("view=treemap&depth=2", "view=treemap&depth=2&list=0")], 520, None),
    "screenshot-tree.png": ([("view=tree&depth=4&problems=1", "view=tree&depth=4&problems=1&list=0")], 520, None),
    "screenshot-sankey.png": ([("view=sankey&problems=1", "view=sankey&problems=1&list=0")], 520, None),
    "screenshot-groups.png": (
        [("view=groups", "view=groups&list=0&" + GROUPS), ("view=bars", "view=bars&list=0&" + GROUPS)],
        420,
        None,
    ),
    "screenshot-tiles.png": (
        [("view=tiles", "view=tiles&list=0"), ("view=impact", "view=impact&list=0")],
        480,
        None,
    ),
    "screenshot-hover.png": (
        [("Payment API (view=rings&depth=4)", "view=rings&depth=4&name=Payment%20API&list=0")],
        560,
        "Payment API › Payment API Network",
    ),
}


def main() -> None:
    checkmk_stub.tree = sample_tree
    stub = checkmk_stub.Stub(("127.0.0.1", 0), checkmk_stub.Handler)
    stub.aggregations = dict(SAMPLE)
    threading.Thread(target=stub.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1250, "height": 640})
            for name, (widgets, height, tip) in SHOTS.items():
                page.set_content(frame(stub, [(t, q + "&refresh=0&animation=0") for t, q in widgets], height))
                for widget in page.frames[1:]:
                    widget.wait_for_function("window.biCharts && biCharts.items().length > 0")
                # Settled: drawn again after its size was known.
                page.wait_for_timeout(500)
                if tip:
                    # The mouse onto the middle of the ring segment, from the layout
                    # ECharts computed for it, as a person would hover it.
                    x, y = page.frames[1].evaluate(
                        """(path) => {
                            const item = biCharts.items().find((i) => i.path.startsWith(path));
                            const data = biCharts.chart.getModel().getSeriesByIndex(item.seriesIndex).getData();
                            const l = data.getItemLayout(item.dataIndex);
                            const angle = (l.startAngle + l.endAngle) / 2, r = (l.r0 + l.r) / 2;
                            const box = document.getElementById("chart").getBoundingClientRect();
                            return [box.left + l.cx + r * Math.cos(angle), box.top + l.cy + r * Math.sin(angle)];
                        }""",
                        tip,
                    )
                    frame_box = page.locator("iframe").first.bounding_box()
                    assert frame_box
                    page.mouse.move(frame_box["x"] + x, frame_box["y"] + y)
                page.wait_for_timeout(600)
                # The whole page, but at the window's size where a tooltip shows: a
                # full-page shot resizes the window, which hides it.
                page.screenshot(path=ROOT / "docs" / name, full_page=not tip)
                print(ROOT / "docs" / name)
            browser.close()
    finally:
        stub.shutdown()


if __name__ == "__main__":
    main()
