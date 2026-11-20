// Draws what the last load found in the chosen view.
import { allOkOption, base, chart } from "./chart.js";
import { TREE_VIEWS, VIEWS, depth, params, problemsOnly, topRows, view } from "./config.js";
import { $ } from "./dom.js";
import { renderLegend } from "./legend.js";
import { renderList } from "./list.js";
import { countStates, stateSummary } from "./states.js";
import { impactOf, problemsOf, sankeyColumns } from "./tree.js";
import { ui } from "./ui.js";
import { barsOption } from "./views/bars.js";
import { groupGrid, groupsOption } from "./views/groups.js";
import { impactOption } from "./views/impact.js";
import { pieOption } from "./views/pie.js";
import { ringsOption } from "./views/rings.js";
import { sankeyOption } from "./views/sankey.js";
import { tileGrid, tilesOption } from "./views/tiles.js";
import { treeOption } from "./views/tree.js";
import { treemapOption } from "./views/treemap.js";

// Draws the chart and, unless only the chart changes (a legend row's fading,
// which must not replace the row under the pointer), the legend and the list.
export function render(chartOnly) {
  if (!ui.last) return;
  ui.refs = new Map();
  ui.scopes = new Map();
  const { aggrs, trees, groups } = ui.last;
  const shown = TREE_VIEWS.includes(view) && !trees ? "pie" : (view === "groups" || view === "bars") && !groups
    ? "pie" : view;
  document.body.classList.toggle("view-pie", shown === "pie");
  for (const v of VIEWS) if (v !== "pie") document.body.classList.toggle("view-" + v, shown === v);
  // problems=1: the trees cut down to their problems, without the aggregations that are
  // OK throughout.
  const cut = trees && problemsOnly
    ? new Map([...trees].map(([title, tree]) => [title, problemsOf(tree)]).filter(([, tree]) => tree)) : trees;
  const cutAggrs = cut ? aggrs.filter((a) => cut.has(a.title)) : aggrs;
  $("chart").style.height = heightOf(shown, cutAggrs, cut) || "";
  chart.resize();
  const ofTrees = (draw) => () => (cutAggrs.length ? draw(cutAggrs, cut) : allOkOption());
  const option = Object.assign(base(), {
    pie: () => pieOption(aggrs),
    rings: ofTrees(ringsOption),
    treemap: ofTrees(treemapOption),
    tree: ofTrees(treeOption),
    groups: () => groupsOption(aggrs, groups),
    bars: () => barsOption(aggrs, groups),
    tiles: () => tilesOption(aggrs),
    impact: () => impactOption(aggrs, trees),
    sankey: ofTrees(sankeyOption),
  }[shown]());
  // For screen readers, in place of the shapes: what the chart is about. ECharts writes it
  // into the chart's aria-label.
  option.aria = { enabled: true, label: { description: (params.get("title") || "BI aggregation states") + ", " +
    shown + ": " + aggrs.length + " aggregations, " + stateSummary(countStates(aggrs)) + "." } };
  $("arcs").replaceChildren();
  chart.setOption(option, { notMerge: true });

  const total = aggrs.length;
  $("total").textContent = total;
  $("sub").textContent = total === 1 ? "aggregation" : "aggregations";
  const size = $("chart").clientWidth;
  $("total").style.fontSize = Math.round(size * (shown === "rings" ? 0.09 : 0.16)) + "px";
  $("sub").style.fontSize = Math.max(10, Math.round(size * (shown === "rings" ? 0.032 : 0.055))) + "px";
  if (chartOnly) return;
  renderLegend(aggrs, trees, { select, fade });
  renderList(aggrs);
}

// The height the views of many rows need, or null for the stylesheet's; the views of
// the trees get the aggregations and trees they draw (problems=1 cuts them down).
function heightOf(shown, cutAggrs, cut) {
  const { aggrs, trees, groups } = ui.last;
  if (shown === "groups") return groupGrid(groups.length).rows * 170 + "px";
  if (shown === "bars") return Math.max(120, groups.length * 34 + 40) + "px";
  if (shown === "tiles") {
    const { columns, size } = tileGrid(aggrs.length);
    const rows = Math.max(1, Math.ceil(aggrs.length / columns));
    return Math.ceil(rows * size * 1.5 + size * 0.5 + 8) + "px";
  }
  if (shown === "impact") return Math.max(120, Math.min(topRows, impactOf(aggrs, trees).length) * 26 + 50) + "px";
  if (shown === "tree") {
    // A row per node at the unfolded depth, and per host or service above it: room
    // for a line of text each.
    const rows = (node, level) => (level === depth || !node.children.length ? 1
      : node.children.reduce((sum, c) => sum + rows(c, level + 1), 0));
    const count = cutAggrs.reduce((sum, a) => sum + rows(cut.get(a.title), 1), 0);
    return Math.max(240, count * 20 + 40) + "px";
  }
  if (shown === "sankey") {
    // A line of text per node of the fullest column.
    const columns = sankeyColumns(cutAggrs, cut, depth);
    return Math.max(240, Math.max(0, ...columns) * 18 + 40) + "px";
  }
  return null;
}

// Narrows the list to a state (and a scope), or widens it again on a second click.
export function select(stateId, scopeKey) {
  const same = ui.selected === stateId && ui.selectedScope === scopeKey;
  ui.selected = same ? null : stateId;
  ui.selectedScope = same ? null : scopeKey;
  render();
}

function fade(stateId) {
  ui.faded = stateId;
  render(true);
}
