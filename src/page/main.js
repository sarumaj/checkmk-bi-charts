// The page's entry point (scripts/build_page.mjs bundles from here). Importing
// config.js first checks the query parameters.
import { initChart } from "./chart.js";
import { drawArcs } from "./arcs.js";
import { params, refresh, theme, view } from "./config.js";
import { $ } from "./dom.js";
import { showDetail } from "./list.js";
import { load } from "./load.js";
import { render, select } from "./render.js";
import { ui } from "./ui.js";

if (theme() === "light") document.body.classList.add("light");
document.body.classList.add("view-" + view);
if (params.get("title")) {
  $("title").textContent = params.get("title");
  $("title").hidden = false;
}
const chart = initChart();

chart.on("finished", drawArcs);

chart.on("click", (p) => {
  const entry = p.data && p.data.id && ui.refs.get(p.data.id);
  if (!entry) return;
  if (entry.node) showDetail(entry);
  else select(entry.state, entry.scope || null);
});

// What the chart shows, for the tests and for debugging in the browser's
// console: each item's path, state, kind and where ECharts keeps it.
window.biCharts = {
  chart,
  items() {
    const found = [];
    // Nothing before the chart's first drawing.
    const model = chart.getModel();
    if (!model) return found;
    model.eachSeries((series) => {
      const data = series.getData();
      for (let i = 0; i < data.count(); i++) {
        const entry = ui.refs.get(data.getId(i));
        if (!entry) continue;
        const state = entry.node ? entry.node.state : entry.state;
        // Faded: drawn at less than a third of its opacity (paint.js, fill).
        const color = String(data.getItemVisual(i, "style").fill || "");
        const alpha = color.length === 9 ? parseInt(color.slice(7), 16) / 255 : 1;
        found.push({ path: entry.path.join(" › "), kind: entry.kind, state, color, faded: alpha < 0.3,
                     seriesIndex: series.seriesIndex, dataIndex: i });
      }
    });
    return found;
  },
};

load();
// The chart follows the widget's size, and the labels' room with it: drawn again
// when the chart's size changed, not for every change of the layout around it.
let drawnSize = "";
new ResizeObserver(() => {
  const size = $("chart").clientWidth + "x" + $("chart").clientHeight;
  if (size === drawnSize) return;
  drawnSize = size;
  render();
}).observe($("chart"));
if (refresh > 0) setInterval(load, refresh * 1000);
