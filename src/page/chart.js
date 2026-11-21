// The chart, and what every view's options share. ECharts is its release's own
// echarts.min.js beside the page, loaded before the page's script, unchanged, so that
// a reviewer can compare it with the release: it is not bundled into the page.
import { animate } from "./config.js";
import { $, css } from "./dom.js";

const { echarts } = globalThis;

// Created by initChart once the page has its theme and view, which size the chart.
export let chart = null;

export function initChart() {
  chart = echarts.init($("chart"), null, { renderer: "svg" });
  return chart;
}

export function base() {
  return {
    backgroundColor: "transparent",
    animation: animate,
    textStyle: { fontFamily: getComputedStyle(document.body).fontFamily, color: css("--fg") },
    tooltip: {
      confine: true,
      className: "tip",
      backgroundColor: css("--tip-bg"),
      borderColor: css("--ring"),
      textStyle: { color: css("--fg"), fontSize: 12 },
      extraCssText: "box-shadow: 0 2px 8px rgba(0, 0, 0, .35);",
      formatter: (p) => (p.data && p.data.tip ? p.data.tip() : ""),
    },
  };
}

// In place of the chart of the trees when problems=1 leaves nothing to draw.
export function allOkOption() {
  return { title: { text: "All hosts and services are OK", left: "center", top: "middle",
                    textStyle: { color: css("--muted"), fontSize: 13, fontWeight: 400 } } };
}
