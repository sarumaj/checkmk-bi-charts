// The names bent along the rings of the pie and the rings.
import { chart } from "./chart.js";
import { showLabels } from "./config.js";
import { $ } from "./dom.js";
import { ui } from "./ui.js";

// The names bent along the ring of their slice or segment (an item's `arc` in refs:
// its text, color and size), from the layout ECharts computed: in an SVG over the
// chart, as ECharts writes text only straight. Each reads from left to right, so on
// the lower half it runs the other way round the circle; it shows where it fits whole
// or with at least six characters before the ellipsis. Drawn whenever the chart has
// finished drawing (resize, refresh, a fading legend row).
export function drawArcs() {
  const svg = $("arcs");
  svg.replaceChildren();
  const model = chart.getModel();
  if (!showLabels || !model) return;
  const SVG_NS = "http://www.w3.org/2000/svg";
  let count = 0;
  model.eachSeries((series) => {
    const data = series.getData();
    for (let i = 0; i < data.count(); i++) {
      const entry = ui.refs.get(data.getId(i));
      const layout = entry && entry.arc ? data.getItemLayout(i) : null;
      if (!layout || layout.r == null) continue;
      const r0 = layout.r0 || 0, middle = (r0 + layout.r) / 2;
      const size = entry.arc.size || Math.min(12, (layout.r - r0) * 0.5);
      if (size < 8) continue;
      let lo = Math.min(layout.startAngle, layout.endAngle), hi = Math.max(layout.startAngle, layout.endAngle);
      // A whole ring: its name over the top.
      if (hi - lo >= 2 * Math.PI - 1e-6) {
        lo = -Math.PI;
        hi = 0;
      }
      const text = entry.arc.text;
      const chars = Math.floor((hi - lo) * middle * 0.88 / (size * 0.6));
      if (chars < Math.min(text.length, 6)) continue;
      // Angles as ECharts lays them out: 0 to the right, growing clockwise (y down).
      const point = (a) => (layout.cx + middle * Math.cos(a)).toFixed(2) + "," +
        (layout.cy + middle * Math.sin(a)).toFixed(2);
      const large = hi - lo > Math.PI ? 1 : 0;
      const below = Math.sin((lo + hi) / 2) > 0.01;
      const arc = document.createElementNS(SVG_NS, "path");
      arc.id = "arc-" + count++;
      arc.setAttribute("fill", "none");
      arc.setAttribute("d", below
        ? "M" + point(hi) + "A" + middle + "," + middle + " 0 " + large + ",0 " + point(lo)
        : "M" + point(lo) + "A" + middle + "," + middle + " 0 " + large + ",1 " + point(hi));
      const label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("font-size", size.toFixed(1));
      label.setAttribute("fill", entry.arc.color);
      // Faded with its segment while a legend row is hovered.
      const fillColor = String(data.getItemVisual(i, "style").fill || "");
      if (fillColor.length === 9 && parseInt(fillColor.slice(7), 16) / 255 < 0.3) label.setAttribute("opacity", "0.3");
      const along = document.createElementNS(SVG_NS, "textPath");
      along.setAttribute("href", "#" + arc.id);
      along.setAttribute("startOffset", "50%");
      along.setAttribute("text-anchor", "middle");
      along.setAttribute("dominant-baseline", "central");
      along.textContent = text.length > chars ? text.slice(0, chars - 1) + "\u2026" : text;
      label.append(along);
      svg.append(arc, label);
    }
  });
}
