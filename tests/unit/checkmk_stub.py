"""A stand-in for the Checkmk endpoints the page calls.

It answers with the response shapes found in the Checkmk 2.4 and 2.5 sources,
so the page's JavaScript runs in a real browser without a Checkmk site. The
tests under tests/integration check the same things against real sites.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PAGE = Path(__file__).parent.parent.parent / "src/web/htdocs/bi_pie/index.html"

# Aggregation title -> (state, acknowledged, in downtime, BI group).
AGGREGATIONS: dict[str, tuple[int, bool, bool, str]] = {
    "Shop": (0, False, False, "web"),
    "Wiki": (0, False, False, "web"),
    "Mail": (0, False, False, "infra"),
    "Storage": (1, False, True, "infra"),
    "Payment": (2, True, False, "web"),
    "ERP": (3, False, False, "infra"),
}


def _leaf(host: str, service: str, state: int) -> dict[str, object]:
    core = {"hostname": host, "service": service, "state": state, "in_downtime": 0, "acknowledged": False}
    return {"node_type": "bi_leaf", "name": f"{host} {service}", "type_specific": {"core": core}, "children": []}


def _rule(name: str, rule: str, state: int, children: list[dict[str, object]]) -> dict[str, object]:
    core = {"state": state, "in_downtime": 0, "acknowledged": False}
    return {
        "node_type": "bi_aggregator",
        "name": name,
        "rule_id": {"pack": "default", "rule": rule},
        "type_specific": {"core": core},
        "children": children,
    }


def tree(title: str) -> dict[str, object]:
    """Aggregation -> two host rules -> two services each; the first service has the state."""
    state, acknowledged, in_downtime, _group = AGGREGATIONS[title]
    hosts = [
        _rule(f"{title}-1", "host", state, [_leaf(f"{title}-1", "CPU", state), _leaf(f"{title}-1", "Memory", 0)]),
        _rule(f"{title}-2", "host", 0, [_leaf(f"{title}-2", "CPU", 0), _leaf(f"{title}-2", "Memory", 0)]),
    ]
    root = _rule(title, "application", state, hosts)
    # Checkmk reports acknowledgement and downtime on the tree's root as well.
    root["type_specific"] = {"core": {"state": state, "in_downtime": int(in_downtime), "acknowledged": acknowledged}}
    return root


class Stub(ThreadingHTTPServer):
    """Checkmk stand-in; the attributes let a test change its answers."""

    aggregations: dict[str, tuple[int, bool, bool, str]]
    state_status: int = 200
    tree_result_code: int = 0
    parent_theme: str = "modern-dark"
    tree_requests: int = 0

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/stub/check_mk/"

    @property
    def page(self) -> str:
        return self.base + "local/bi_pie/index.html"


class Handler(BaseHTTPRequestHandler):
    server: Stub

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = parse_qs(url.query)
        path = url.path.removeprefix("/stub/check_mk/")
        if path == "local/bi_pie/index.html":
            self._send(200, "text/html", PAGE.read_bytes())
        elif path == "dashboard.py":
            # Embedding page, as Checkmk renders it: themed <body>, widget in an iframe.
            html = (
                f'<!DOCTYPE html><body data-theme="{self.server.parent_theme}">'
                f'<iframe id="widget" src="local/bi_pie/index.html?{query.get("widget", [""])[0]}"></iframe>'
            )
            self._send(200, "text/html", html.encode())
        elif path == "api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke":
            names, groups = query.get("filter_names", []), query.get("filter_groups", [])
            answer = {
                "aggregations": {
                    title: {"state": state, "acknowledged": ack, "in_downtime": downtime, "hosts": [], "output": ""}
                    for title, (state, ack, downtime, group) in self.server.aggregations.items()
                    if (not names or title in names) and (not groups or group in groups)
                },
                "missing_sites": [],
                "missing_aggr": [],
            }
            self._send(self.server.state_status, "application/json", json.dumps(answer).encode())
        elif path == "ajax_fetch_aggregation_data.py":
            self.server.tree_requests += 1
            title = json.loads(query["aggregations"][0])[0]
            if self.server.tree_result_code:
                answer = {"result_code": 1, "result": "tree unavailable", "severity": "error"}
            else:
                answer = {"result_code": 0, "result": {"node_config": {"hierarchy": tree(title)}}, "severity": "success"}
            self._send(200, "application/json", json.dumps(answer).encode())
        else:
            self._send(404, "text/plain", b"not found")
