// The chart, and what every view's options share. Only the parts of ECharts the
// views use go into the page.
import { BarChart, CustomChart, PieChart, SankeyChart, SunburstChart, TreeChart, TreemapChart } from "echarts/charts";
import { AriaComponent, GridComponent, TitleComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { animate } from "./config.js";
import { $, css } from "./dom.js";

echarts.use([BarChart, CustomChart, PieChart, SankeyChart, SunburstChart, TreeChart, TreemapChart,
             AriaComponent, GridComponent, TitleComponent, TooltipComponent, SVGRenderer]);

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
