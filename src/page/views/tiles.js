import { changedAt } from "../changes.js";
import { showLabels } from "../config.js";
import { $, css } from "../dom.js";
import { fill, labelColor, paint } from "../paint.js";
import { bySeverity } from "../states.js";
import { aggrTip } from "../tips.js";
import { ref, ui } from "../ui.js";

// The tiles' size (the hexagons' outer radius) and how many fit in a row: as large
// as 46 pixels, smaller where the widget is too narrow for one.
export function tileGrid(count) {
  const width = $("chart").clientWidth - 8;
  const size = Math.max(12, Math.min(46, width / (Math.sqrt(3) * 1.5)));
  const fit = Math.floor(width / (Math.sqrt(3) * size) - (count > 1 ? 0.5 : 0));
  return { size, columns: Math.max(1, Math.min(count, fit)) };
}

// One hexagon per aggregation, the worst first, its name inside: the states of many
// aggregations at a glance, without loading their trees. Rows are offset by half a
// tile, as in a honeycomb.
export function tilesOption(aggrs) {
  const list = bySeverity(aggrs);
  const { columns, size } = tileGrid(list.length);
  const width = Math.sqrt(3) * size;
  const fontSize = Math.min(12, size * 0.27);
  const data = list.map((a, i) => {
    const row = Math.floor(i / columns), column = i % columns;
    return {
      name: a.title,
      value: [4 + (column + 0.5 + (row % 2) * 0.5) * width, 4 + size + row * size * 1.5],
      id: ref({ path: [a.title], node: a, kind: "aggregation" }),
      itemStyle: { color: fill(a.state) },
      tip: () => aggrTip(a),
    };
  });
  const corners = [0, 1, 2, 3, 4, 5].map((k) => (Math.PI / 3) * k - Math.PI / 2);
  return {
    series: [{
      type: "custom",
      coordinateSystem: "none",
      data,
      renderItem: (p, api) => {
        const x = api.value(0), y = api.value(1), r = size - 1.5;
        const aggr = list[p.dataIndex];
        const flags = [aggr.acknowledged && "ack", aggr.inDowntime && "downtime"].filter(Boolean).join(", ");
        const named = showLabels && fontSize >= 8;
        // Changed while the page was open: outlined.
        const changed = changedAt(aggr.title) !== null;
        return {
          type: "polygon",
          shape: { points: corners.map((a) => [x + r * Math.cos(a), y + r * Math.sin(a)]) },
          style: { fill: api.visual("color"), stroke: changed ? css("--fg") : null, lineWidth: changed ? 3 : 0,
                   decal: paint(aggr.state).decal },
          emphasis: { style: { stroke: css("--fg"), lineWidth: 2 } },
          textContent: named ? {
            style: { text: aggr.title + (flags ? "\n" + flags : ""), fill: labelColor(aggr.state),
                     opacity: ui.faded !== null && aggr.state !== ui.faded ? 0.3 : 1, fontSize,
                     fontWeight: 700, align: "center", lineHeight: fontSize * 1.2,
                     // Wrapped to the tile's width, at most three lines.
                     width: width * 0.8, overflow: "break", height: fontSize * 1.2 * 3, lineOverflow: "truncate" },
          } : undefined,
          textConfig: { position: "inside" },
        };
      },
    }],
  };
}
