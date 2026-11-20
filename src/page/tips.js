// The tooltips, as HTML (ECharts takes them so): names go in through esc().
import { changedAt, clock } from "./changes.js";
import { countStates, esc, flagsOf, severity, stateOf, stateSummary } from "./states.js";
import { leafStates } from "./tree.js";
import { ui } from "./ui.js";

export const swatch = (color) => '<i style="background:' + color + '"></i>';

// Details of one state: share of the aggregations and their names.
export function stateTip(state, aggrs) {
  const mine = aggrs.filter((a) => a.state === state.id).sort((a, b) => a.title.localeCompare(b.title));
  const share = aggrs.length ? (mine.length / aggrs.length * 100).toFixed(1) : "0.0";
  const shown = mine.slice(0, 8);
  let html = '<div class="head">' + swatch(state.color) + esc(state.label) + ": " + mine.length + " of " +
    aggrs.length + " aggregations (" + share + " %)</div><ul>" +
    shown.map((a) => "<li>" + esc(a.title) + ' <span class="more">' +
      esc(flagsOf(a).concat(changedAt(a.title) ? ["since " + clock(changedAt(a.title))] : []).join(", ")) +
      "</span></li>").join("") + "</ul>";
  if (mine.length > shown.length) html += '<div class="more">and ' + (mine.length - shown.length) + " more</div>";
  if (ui.last && ui.last.trees) {
    const leaves = new Map();
    for (const a of mine) leafStates(ui.last.trees.get(a.title), leaves);
    html += '<div class="more">Hosts and services below: ' + esc(stateSummary(leaves)) + "</div>";
  }
  return html;
}

// Details of one tree node: where it sits, what it is and what is below it.
export function nodeTip(shown, path) {
  const node = shown.full || shown;
  const state = stateOf(node.state);
  const kind = node.rule ? "Rule " + node.rule : node.service ? "Service on host " + node.host : "Host";
  let html = "";
  if (path.length > 1) html += '<div class="path">' + esc(path.slice(0, -1).join(" › ")) + "</div>";
  html += '<div class="head">' + swatch(state.color) + esc(node.name) + "</div>";
  html += "<div>" + esc([state.label].concat(flagsOf(node)).join(", ")) + "</div>";
  html += '<div class="more">' + esc(kind) + "</div>";
  if (path.length === 1) html += changedTip(node.name);
  if (node.children.length) {
    html += '<div class="more">' + node.leaves + " hosts and services below: " +
      esc(stateSummary(leafStates(node))) + "</div>";
  }
  return html;
}

// Since when an aggregation is in its state, if that changed while the page was open.
export function changedTip(title) {
  const at = changedAt(title);
  return at ? '<div class="more">Changed at ' + esc(clock(at)) + "</div>" : "";
}

// Details of one group: its states.
export function groupTip(group, aggrs) {
  const counts = countStates(aggrs);
  return '<div class="head">' + esc(group.name) + "</div><div>" + aggrs.length + " aggregations: " +
    esc(stateSummary(counts)) + "</div>";
}

// Details of one aggregation from its state alone.
export function aggrTip(aggr) {
  const state = stateOf(aggr.state);
  return '<div class="head">' + swatch(state.color) + esc(aggr.title) + "</div><div>" +
    esc([state.label].concat(flagsOf(aggr)).join(", ")) + "</div>" + changedTip(aggr.title);
}

// Details of one host or service of the view impact: its state and its aggregations.
export function impactTip(leaf) {
  const state = stateOf(leaf.node.state);
  const shown = leaf.list.slice(0, 8);
  let html = '<div class="head">' + swatch(state.color) + esc(leaf.name) + "</div><div>" +
    esc([state.label].concat(flagsOf(leaf.node)).join(", ")) + "</div><div>In " + leaf.list.length +
    (leaf.list.length === 1 ? " aggregation: " : " aggregations: ") + esc(stateSummary(countStates(leaf.list))) +
    "</div><ul>" + shown.map((a) => "<li>" + swatch(stateOf(a.state).color) + esc(a.title) + "</li>").join("") +
    "</ul>";
  if (leaf.list.length > shown.length) html += '<div class="more">and ' + (leaf.list.length - shown.length) + " more</div>";
  return html;
}

// Details of a host of the flow graph: its state, its hosts and services and the
// aggregations it is part of.
export function sankeyHostTip(entry) {
  const counts = new Map();
  for (const m of entry.members) counts.set(m.node.state, (counts.get(m.node.state) || 0) + 1);
  const state = stateOf(entry.node.state);
  const worst = entry.members.slice().sort((a, b) => severity(b.node.state) - severity(a.node.state)).slice(0, 8);
  let html = '<div class="head">' + swatch(state.color) + esc(entry.label) + "</div><div>" +
    esc(entry.members.length + (entry.members.length === 1 ? " host or service: " : " hosts and services: ") +
      stateSummary(counts)) + '</div><div class="more">In ' + entry.aggrs.size +
    (entry.aggrs.size === 1 ? " aggregation" : " aggregations") + "</div><ul>" +
    worst.map((m) => "<li>" + swatch(stateOf(m.node.state).color) + esc(m.path.join(" › ")) + "</li>").join("") +
    "</ul>";
  if (entry.members.length > worst.length) html += '<div class="more">and ' + (entry.members.length - worst.length) +
    " more</div>";
  return html;
}
