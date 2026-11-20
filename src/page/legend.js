// Legend: aggregations per state with their share and, in the views of the
// trees, the hosts and services per state across all loaded trees.
import { showLegend } from "./config.js";
import { $, el } from "./dom.js";
import { STATES, countStates } from "./states.js";
import { leafStates } from "./tree.js";
import { ui } from "./ui.js";

// select and fade (render.js) narrow the list to a row's state and fade the others.
export function renderLegend(aggrs, trees, { select, fade }) {
  if (!showLegend) {
    $("legend").replaceChildren();
    return;
  }
  const total = aggrs.length;
  const counts = countStates(aggrs);
  const leaves = new Map();
  if (trees) for (const tree of trees.values()) leafStates(tree, leaves);
  const head = el("tr", {}, el("th", {}), el("th", { textContent: "aggr." }), el("th", { textContent: "share" }),
    el("th", {}));
  if (trees) head.append(el("th", { textContent: "hosts/svc" }));
  const rows = STATES.filter((s) => counts.get(s.id) || leaves.get(s.id) || s.id >= 0 && s.id <= 2).map((s) => {
    const share = total ? counts.get(s.id) / total : 0;
    const mark = el("i", {});
    mark.style.background = s.color;
    const fillBar = el("span", { className: "fill" });
    fillBar.style.width = (share * 100).toFixed(1) + "%";
    fillBar.style.background = s.color;
    const row = el("tr", { className: ui.selected === s.id ? "active" : "" },
      el("td", {}, mark, s.label),
      el("td", { className: "n", textContent: counts.get(s.id) }),
      el("td", { className: "n pct", textContent: total ? (share * 100).toFixed(0) + " %" : "" }),
      el("td", { className: "bar" }, el("span", { className: "track" }, fillBar)));
    if (trees) row.append(el("td", { className: "n", textContent: leaves.get(s.id) || 0 }));
    row.addEventListener("click", () => select(s.id, null));
    row.addEventListener("mouseenter", () => fade(s.id));
    row.addEventListener("mouseleave", () => fade(null));
    row.title = s.label + ": " + counts.get(s.id) + " of " + total + " aggregations";
    return row;
  });
  $("legend").replaceChildren(el("thead", {}, head), el("tbody", {}, ...rows));
}
