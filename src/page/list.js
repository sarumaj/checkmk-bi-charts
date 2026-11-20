// The list below the chart: the aggregations that are not OK, or those of the
// state and scope a click narrowed it to, each a link to Checkmk's own view.
import { changedAt, clock, litUp } from "./changes.js";
import { GUI_BASE, showList } from "./config.js";
import { $, el } from "./dom.js";
import { severity, stateOf } from "./states.js";
import { ui } from "./ui.js";

export function renderList(aggrs) {
  if (!showList) return;
  const titles = ui.selectedScope !== null ? ui.scopes.get(ui.selectedScope) || new Set() : null;
  const rows = aggrs
    .filter((a) => (ui.selected === null ? a.state !== 0 : a.state === ui.selected))
    .filter((a) => !titles || titles.has(a.title))
    .sort((a, b) => severity(b.state) - severity(a.state) || a.title.localeCompare(b.title));
  $("list").replaceChildren(...rows.map((a) => {
    const s = stateOf(a.state);
    const badge = el("span", { className: "badge", textContent: s.label });
    badge.style.background = s.color;
    const href = new URL("view.py", GUI_BASE);
    href.searchParams.set("view_name", "aggr_single");
    href.searchParams.set("aggr_name", a.title);
    // _parent: replace the dashboard in Checkmk's main frame, not this iframe.
    const link = el("a", { href: href.toString(), target: "_parent", textContent: a.title });
    const at = changedAt(a.title);
    const flags = [a.acknowledged && "ack", a.inDowntime && "downtime", at && "since " + clock(at)]
      .filter(Boolean).join(", ");
    // Lit up on the first drawing after the change only, not on every one after it.
    const fresh = at !== null && !litUp.has(a.title + "@" + at);
    if (fresh) litUp.add(a.title + "@" + at);
    return el("li", { className: at === null ? "" : fresh ? "changed new" : "changed" },
      badge, link, el("span", { className: "flag", textContent: flags }));
  }));
}

// A clicked node of a tree: its path and state below the chart.
export function showDetail(entry) {
  const node = entry.node;
  const state = stateOf(node.state);
  const flags = [node.acknowledged && "ack", node.inDowntime && "downtime",
                 node.rule && "rule " + node.rule].filter(Boolean).join(", ");
  $("detail").replaceChildren(
    el("span", { textContent: entry.path.join(" › ") + ": " + state.label + " " }),
    el("span", { className: "flag", textContent: flags }));
}
