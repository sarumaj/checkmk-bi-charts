// The page's modules without a browser: what the views of the trees work out from
// the BI trees (src/page/tree.js) and the states' order (src/page/states.js).
// Run with `npm test`; the browser tests (tests/unit/test_page.py) check the drawing.
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { bySeverity, esc, shortName, stateSummary } from "../../src/page/states.js";
import { impactOf, leafStates, problemsOf, sankeyColumns, sankeyGraph, toNode } from "../../src/page/tree.js";

// A node as ajax_fetch_aggregation_data.py answers it (node_config.hierarchy).
const leaf = (host, service, state) => ({ name: service ? `${host} ${service}` : host,
  type_specific: { core: { hostname: host, service, state } } });
const rule = (name, state, children) => ({ name, rule_id: { pack: "default", rule: name },
  type_specific: { core: { state } }, children });

// Shop: two rules, one with a CRIT service; Wiki shares the host web1, all OK.
const shop = toNode(rule("Shop", 2, [
  rule("Shop Frontend", 2, [leaf("web1", "HTTP", 2), leaf("web1", "CPU", 0)]),
  rule("Shop Backend", 0, [leaf("db1", "MySQL", 0), leaf("db1", null, 0)]),
]));
const wiki = toNode(rule("Wiki", 0, [rule("Wiki Web", 0, [leaf("web1", "Wiki", 0)])]));
const trees = new Map([["Shop", shop], ["Wiki", wiki]]);
const aggrs = [{ title: "Wiki", state: 0 }, { title: "Shop", state: 2 }];

describe("toNode", () => {
  it("counts the hosts and services and the levels of rules", () => {
    assert.equal(shop.leaves, 4);
    assert.equal(shop.ruleLevels, 2);
    assert.equal(shop.rule, "default / Shop");
    assert.deepEqual([shop.children[0].children[0].host, shop.children[0].children[0].service], ["web1", "HTTP"]);
  });

  it("takes an unknown state for UNKNOWN", () => {
    assert.equal(toNode({ name: "x", type_specific: { core: { state: 7 } } }).state, 3);
  });
});

describe("problemsOf", () => {
  it("keeps the paths down to what is not OK", () => {
    const cut = problemsOf(shop);
    assert.deepEqual(cut.children.map((c) => c.name), ["Shop Frontend"]);
    assert.deepEqual(cut.children[0].children.map((c) => c.service), ["HTTP"]);
    assert.equal(cut.leaves, 1);
    assert.equal(cut.full, shop);
  });

  it("drops a tree that is OK throughout", () => {
    assert.equal(problemsOf(wiki), null);
  });
});

describe("leafStates", () => {
  it("counts the hosts and services per state", () => {
    assert.deepEqual([...leafStates(shop)].sort(), [[0, 3], [2, 1]]);
    assert.equal(stateSummary(leafStates(shop)), "3 OK, 1 CRIT");
  });
});

describe("sankeyGraph", () => {
  const { rings, nodes, links } = sankeyGraph(aggrs, trees, 5);

  it("ends in the hosts, one node for a host in several aggregations", () => {
    const hosts = [...nodes.values()].filter((n) => n.kind === "host");
    assert.deepEqual(hosts.map((n) => n.label).sort(), ["db1", "web1"]);
    const web1 = nodes.get("h:web1");
    assert.equal(web1.column, rings);
    assert.equal(web1.node.state, 2);
    assert.deepEqual([...web1.aggrs].sort(), ["Shop", "Wiki"]);
  });

  it("has no services as nodes", () => {
    assert.ok([...nodes.values()].every((n) => ["aggregation", "rule", "host"].includes(n.kind)));
  });

  it("sizes the links by hosts and services, colored by the worst state in them", () => {
    const front = links.get("r:Shop\u0000Shop Frontend\u0000h:web1");
    assert.deepEqual([front.value, front.state], [2, 2]);
  });

  it("hangs the hosts of the rules below depth from the rule above them", () => {
    const flat = sankeyGraph(aggrs, trees, 1);
    assert.equal(flat.rings, 1);
    assert.ok(flat.links.has("a:Shop\u0000h:web1"));
    assert.deepEqual(sankeyColumns(aggrs, trees, 1), [2, 2]);
  });
});

describe("impactOf", () => {
  it("lists what is not OK with the aggregations it is in", () => {
    const found = impactOf(aggrs, trees);
    assert.deepEqual(found.map((f) => f.name), ["web1 › HTTP"]);
    assert.deepEqual(found[0].list.map((a) => a.title), ["Shop"]);
  });
});

describe("states", () => {
  it("orders by severity, then by title", () => {
    const list = [{ title: "b", state: 0 }, { title: "a", state: 1 }, { title: "c", state: 2 }, { title: "d", state: 3 }];
    assert.deepEqual(bySeverity(list).map((a) => a.title), ["c", "d", "a", "b"]);
  });

  it("shortens a name by its parent's", () => {
    assert.equal(shortName("Web Shop Frontend", "Web Shop"), "Frontend");
    assert.equal(shortName("Web Shop", "Web Shop"), "Web Shop");
  });

  it("escapes names for the tooltips", () => {
    assert.equal(esc('<b a="1">&\''), "&lt;b a=&quot;1&quot;&gt;&amp;&#39;");
  });
});
