import { depth, params, showLabels } from "../config.js";
import { css } from "../dom.js";
import { fill, paint } from "../paint.js";
import { bySeverity, shortName } from "../states.js";
import { nodeTip } from "../tips.js";
import { ref } from "../ui.js";

// The BI trees as nested rectangles, sized by hosts and services, the worst aggregations
// first (top left), as the tiles; below them the BI order. Clicking one zooms into it,
// the path above leads back. A rectangle lies on its parent's: the pale OK adds up to a
// brighter one each level down, which sets the levels apart.
export function treemapOption(aggrs, trees) {
  function build(node, path) {
    const here = path.concat(node.name);
    const kind = path.length === 0 ? "aggregation" : node.children.length ? "rule" : node.service ? "service" : "host";
    return {
      name: shortName(node.name, path[path.length - 1]),
      value: node.leaves,
      id: ref({ path: here, node, kind }),
      itemStyle: { ...paint(node.state), borderColor: fill(node.state) },
      tip: () => nodeTip(node, here),
      children: node.children.length ? node.children.map((c) => build(c, here)) : undefined,
    };
  }
  const gap = css("--gap");
  return {
    series: [{
      type: "treemap",
      // The root of the path below the rectangles.
      name: params.get("title") || "BI",
      data: bySeverity(aggrs).map((a) => build(trees.get(a.title), [])),
      sort: false,
      roam: false,
      leafDepth: depth,
      nodeClick: "zoomToNode",
      // Room for the names: the zoom is the rectangle's own (nodeClick).
      drillDownIcon: "",
      left: 0, right: 0, top: 0, bottom: 32,
      visibleMin: 30,
      label: { show: showLabels, color: "#000", fontSize: 11, overflow: "truncate" },
      upperLabel: { show: showLabels, height: 18, color: "#000", fontWeight: 700, overflow: "truncate" },
      breadcrumb: { show: true, bottom: 0, itemStyle: { color: css("--ring"), textStyle: { color: css("--fg") } } },
      levels: [
        { itemStyle: { gapWidth: 4, borderWidth: 0, borderColor: gap } },
        { itemStyle: { gapWidth: 2, borderWidth: 2 } },
        { itemStyle: { gapWidth: 1, borderWidth: 1 } },
      ],
    }],
  };
}
