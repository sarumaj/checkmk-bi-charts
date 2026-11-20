import { depth, showLabels } from "../config.js";
import { css } from "../dom.js";
import { fill, paint } from "../paint.js";
import { esc } from "../states.js";
import { nodeTip, sankeyHostTip } from "../tips.js";
import { sankeyGraph } from "../tree.js";
import { ref } from "../ui.js";

// The BI trees as flows (tree.js, sankeyGraph).
export function sankeyOption(aggrs, trees) {
  const { nodes, links } = sankeyGraph(aggrs, trees, depth);
  // ECharts finds a link's ends by the nodes' ids (else their names): the ids of refs.
  const ids = new Map([...nodes.keys()].map((key) => [key, null]));
  const data = [...nodes.values()].map((n) => ({
    name: n.key,
    depth: n.column,
    id: ids.set(n.key, ref({ path: n.path, node: n.node, kind: n.kind })).get(n.key),
    itemStyle: { ...paint(n.node.state), borderWidth: 0 },
    label: { formatter: () => n.label },
    tip: () => (n.kind === "host" ? sankeyHostTip(n) : nodeTip(n.node, n.path)),
  }));
  const linkData = [...links.values()].map((l) => {
    const from = nodes.get(l.source), to = nodes.get(l.target);
    return {
      source: ids.get(l.source),
      target: ids.get(l.target),
      value: l.value,
      lineStyle: { color: fill(l.state), opacity: l.state === 0 ? 0.25 : 0.55 },
      tip: () => '<div class="path">' + esc(from.path.join(" › ")) + '</div><div class="head">' + esc(to.label) +
        "</div><div>" + l.value + (l.value === 1 ? " host or service" : " hosts and services") + "</div>",
    };
  });
  return {
    series: [{
      type: "sankey",
      data,
      links: linkData,
      left: 8, right: "18%", top: 8, bottom: 8,
      nodeWidth: 10,
      nodeGap: 6,
      draggable: false,
      emphasis: { focus: "adjacency" },
      label: { show: showLabels, color: css("--fg"), fontSize: 11, width: 220, overflow: "truncate" },
      lineStyle: { curveness: 0.5 },
    }],
  };
}
