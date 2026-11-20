// The BI trees: what the views of the trees draw, worked out from them. No browser
// globals: the Node tests (tests/js) import this module as it is.
import { bySeverity, severity, shortName, stateOf } from "./states.js";

// Reduces a node of Checkmk's BI visualization data to what the charts need.
export function toNode(raw) {
  const core = (raw.type_specific && raw.type_specific.core) || {};
  const children = (raw.children || []).map(toNode);
  return {
    name: String(raw.name),
    state: stateOf(core.state) ? core.state : 3,
    acknowledged: Boolean(core.acknowledged),
    inDowntime: Boolean(core.in_downtime),
    // Rules are inner nodes; leaves are hosts or services.
    rule: raw.rule_id ? raw.rule_id.pack + " / " + raw.rule_id.rule : null,
    pack: raw.rule_id ? raw.rule_id.pack : null,
    host: core.hostname || null,
    service: core.service || null,
    children,
    // Size: every host or service counts once.
    leaves: children.length ? children.reduce((sum, c) => sum + c.leaves, 0) : 1,
    // Levels of rules from here down.
    ruleLevels: children.length ? 1 + Math.max(...children.map((c) => c.ruleLevels)) : 0,
  };
}

// The tree cut down to the paths that lead to something not OK (problems=1), or null
// when all of it is OK. A copy: the cut nodes keep their whole node as `full`, which the
// tooltips describe. A problem rule whose children are all OK keeps them, so that it
// still reads as a rule.
export function problemsOf(node) {
  if (!node.children.length) return node.state === 0 ? null : node;
  let children = node.children.map(problemsOf).filter(Boolean);
  if (!children.length) {
    if (node.state === 0) return null;
    children = node.children;
  }
  return { ...node, children, full: node.full || node,
           leaves: children.reduce((sum, c) => sum + c.leaves, 0),
           ruleLevels: 1 + Math.max(...children.map((c) => c.ruleLevels)) };
}

// Number of hosts and services per state below a node (the node itself if it is one).
export function leafStates(node, counts = new Map()) {
  if (!node.children.length) counts.set(node.state, (counts.get(node.state) || 0) + 1);
  for (const child of node.children) leafStates(child, counts);
  return counts;
}

// The hosts and services that are not OK, each with the aggregations it is part of,
// sorted by how many of those are not OK, then by how many there are: what to fix
// first. The same host or service in several aggregations counts once per aggregation.
export function impactOf(aggrs, trees) {
  const found = new Map();
  for (const aggr of aggrs) {
    const walk = (node) => {
      if (node.children.length) return node.children.forEach(walk);
      if (node.state === 0) return;
      const key = (node.host || node.name) + "\u0000" + (node.service || "");
      if (!found.has(key)) {
        const name = node.service ? (node.host ? node.host + " › " + node.service : node.name) : node.host || node.name;
        found.set(key, { key, name, node, aggrs: new Map() });
      }
      found.get(key).aggrs.set(aggr.title, aggr);
    };
    walk(trees.get(aggr.title));
  }
  return [...found.values()].map((leaf) => {
    const list = bySeverity([...leaf.aggrs.values()]);
    return { ...leaf, list, bad: list.filter((a) => a.state !== 0).length };
  }).sort((a, b) => b.bad - a.bad || b.list.length - a.list.length ||
    severity(b.node.state) - severity(a.node.state) || a.name.localeCompare(b.name));
}

// The BI trees as a flow graph: a column of aggregations, a column per level of rules
// up to depth, and the hosts last; every host or service flows by one from the rule
// above it to its host. A host in several aggregations is one node, so that what they
// share shows as flows meeting. Rules below depth are left out, their hosts hang from
// the rule above them. Nodes carry their key (unique: a rule's by its path), the column
// and what the tooltips need; links their size and the worst state flowing in them.
export function sankeyGraph(aggrs, trees, depth) {
  const rings = Math.max(1, Math.min(depth, Math.max(...aggrs.map((a) => trees.get(a.title).ruleLevels))));
  const nodes = new Map(), links = new Map();
  const worse = (a, b) => (severity(b) > severity(a) ? b : a);
  function link(source, target, value, state) {
    const key = source + "\u0000" + target;
    const found = links.get(key) || { source, target, value: 0, state: 0, leaves: [] };
    found.value += value;
    found.state = worse(found.state, state);
    links.set(key, found);
    return found;
  }
  function walk(node, level, path, parent) {
    const here = path.concat(node.name);
    if (!node.children.length) {
      const host = node.host || node.name;
      const key = "h:" + host;
      if (!nodes.has(key)) {
        nodes.set(key, { key, label: host, column: rings, path: [host], kind: "host",
                         node: { name: host, host, state: 0, acknowledged: false, inDowntime: false, children: [],
                                 leaves: 0 },
                         members: [], aggrs: new Set() });
      }
      const found = nodes.get(key);
      found.node.state = worse(found.node.state, node.state);
      found.node.leaves += 1;
      found.members.push({ node, path: here });
      found.aggrs.add(here[0]);
      link(parent, key, 1, node.state).leaves.push(node);
      return;
    }
    if (level >= rings) {
      for (const child of node.children) walk(child, level + 1, here, parent);
      return;
    }
    const key = (level === 0 ? "a:" : "r:") + here.join("\u0000");
    nodes.set(key, { key, label: shortName(node.name, path[path.length - 1]), column: level, path: here,
                     kind: level === 0 ? "aggregation" : "rule", node });
    if (parent) link(parent, key, node.leaves, node.state);
    for (const child of node.children) walk(child, level + 1, here, key);
  }
  for (const a of bySeverity(aggrs)) walk(trees.get(a.title), 0, [], null);
  return { rings, nodes, links };
}

// The nodes per column of the flow graph, for its height.
export function sankeyColumns(aggrs, trees, depth) {
  if (!aggrs.length) return [];
  const { rings, nodes } = sankeyGraph(aggrs, trees, depth);
  const counts = Array(rings + 1).fill(0);
  for (const n of nodes.values()) counts[n.column] += 1;
  return counts;
}
