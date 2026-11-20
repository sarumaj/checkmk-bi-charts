// The requests to Checkmk, with the viewer's own GUI session.
import { GUI_BASE, params } from "./config.js";
import { stateOf } from "./states.js";
import { toNode } from "./tree.js";

const STATE_PATH = "api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke";
// How long a tree is reused while its aggregation's answer stays the same.
const TREE_MAX_AGE = 10 * 60 * 1000;
const treeCache = new Map();  // aggregation title -> {tree, answer, at}: trees reused across loads

async function getJson(url) {
  const resp = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (resp.status === 401 || resp.status === 403) {
    throw new Error("Not authorised (HTTP " + resp.status + "). Log in to Checkmk first.");
  }
  if (!resp.ok) throw new Error("REST API returned HTTP " + resp.status + ":\n" + (await resp.text()).slice(0, 400));
  return resp.json();
}

// The states of the aggregations of the given groups (all when empty).
export async function loadStates(groups) {
  const url = new URL(STATE_PATH, GUI_BASE);
  for (const g of groups) url.searchParams.append("filter_groups", g);
  for (const n of params.getAll("name")) url.searchParams.append("filter_names", n);
  const data = await getJson(url);
  // Expected: {aggregations: {<title>: {state, acknowledged, in_downtime, ...}},
  //            missing_sites: [...], missing_aggr: [...]}
  const body = data.aggregations ? data : (data.extensions || {});
  return {
    raw: data,
    aggrs: Object.entries(body.aggregations || {}).map(([title, a]) => ({
      title,
      state: stateOf(a.state) ? a.state : 3,
      acknowledged: Boolean(a.acknowledged),
      inDowntime: Boolean(a.in_downtime),
      // The whole answer, which also names the nodes that have a problem: when it
      // changes, so may the tree.
      answer: JSON.stringify(a),
    })),
    missingSites: body.missing_sites || [],
    missingAggr: body.missing_aggr || [],
  };
}

// The full tree of every aggregation, a few requests at a time. A tree loaded before
// is used again while its aggregation's answer from the REST API is the same and it
// is younger than TREE_MAX_AGE (a changed BI configuration shows after that), so that
// a refresh asks for few trees or none.
export async function loadTrees(aggrs) {
  const trees = new Map();
  const now = Date.now();
  const queue = [];
  for (const a of aggrs) {
    const cached = treeCache.get(a.title);
    if (cached && cached.answer === a.answer && now - cached.at < TREE_MAX_AGE) trees.set(a.title, cached.tree);
    else queue.push(a);
  }
  async function worker() {
    for (let a = queue.shift(); a !== undefined; a = queue.shift()) {
      const tree = await loadTree(a.title);
      trees.set(a.title, tree);
      treeCache.set(a.title, { tree, answer: a.answer, at: now });
    }
  }
  await Promise.all(Array.from({ length: Math.min(6, queue.length) }, worker));
  for (const title of treeCache.keys()) if (!trees.has(title)) treeCache.delete(title);
  // In the order of the aggregations, whichever request finished first.
  return new Map(aggrs.map((a) => [a.title, trees.get(a.title)]));
}

async function loadTree(title) {
  const url = new URL("ajax_fetch_aggregation_data.py", GUI_BASE);
  url.searchParams.set("aggregations", JSON.stringify([title]));
  const resp = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!resp.ok) throw new Error("HTTP " + resp.status + " for \"" + title + "\"");
  const answer = await resp.json();
  // Ajax pages answer {result_code, result}; a non-zero code carries the error text.
  if (answer.result_code !== 0) throw new Error(String(answer.result));
  const root = answer.result && answer.result.node_config && answer.result.node_config.hierarchy;
  if (!root) throw new Error("No tree returned for \"" + title + "\"");
  return toNode(root);
}
