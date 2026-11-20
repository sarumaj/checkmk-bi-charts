import { depth, params, showLabels } from "../config.js";
import { css } from "../dom.js";
import { fill, paint } from "../paint.js";
import { countStates, esc, ordered, shortName, stateSummary } from "../states.js";
import { nodeTip } from "../tips.js";
import { ref } from "../ui.js";

// The BI trees as a tree of nodes, the aggregations at the root; nodes below
// depth start folded, a click opens or folds one.
export function treeOption(aggrs, trees) {
  function build(node, path) {
    const here = path.concat(node.name);
    const kind = path.length === 0 ? "aggregation" : node.children.length ? "rule" : node.service ? "service" : "host";
    return {
      name: shortName(node.name, path[path.length - 1]),
      id: ref({ path: here, node, kind }),
      itemStyle: { ...paint(node.state), borderColor: fill(node.state) },
      tip: () => nodeTip(node, here),
      children: node.children.map((c) => build(c, here)),
    };
  }
  const counts = countStates(aggrs);
  const root = {
    name: params.get("title") || "BI",
    itemStyle: { color: css("--muted"), borderColor: css("--muted") },
    tip: () => '<div class="head">' + aggrs.length + " aggregations</div><div>" +
      esc(stateSummary(counts)) + "</div>",
    children: ordered(aggrs).map((a) => build(trees.get(a.title), [])),
  };
  return {
    series: [{
      type: "tree",
      data: [root],
      top: "4%", bottom: "4%", left: "10%", right: "22%",
      // Filled: ECharts' default, an empty circle, leaves an open node without its color.
      symbol: "circle",
      symbolSize: 9,
      initialTreeDepth: depth,
      expandAndCollapse: true,
      roam: true,
      label: { show: showLabels, position: "left", verticalAlign: "middle", align: "right",
               color: css("--fg"), fontSize: 11 },
      leaves: { label: { position: "right", align: "left" } },
      lineStyle: { color: css("--ring"), width: 1.2 },
      emphasis: { focus: "descendant" },
    }],
  };
}
