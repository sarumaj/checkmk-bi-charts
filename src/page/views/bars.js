import { showLabels } from "../config.js";
import { css } from "../dom.js";
import { paint } from "../paint.js";
import { STATES, countStates } from "../states.js";
import { groupTip } from "../tips.js";
import { ref, scope } from "../ui.js";
import { groupAggrs } from "./groups.js";

// One stacked bar per group, a segment per state.
export function barsOption(aggrs, groups) {
  const per = groups.map((g) => countStates(groupAggrs(aggrs, g)));
  return {
    grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: "value", minInterval: 1, axisLabel: { color: css("--muted") },
             splitLine: { lineStyle: { color: css("--ring") } } },
    yAxis: { type: "category", inverse: true, data: groups.map((g) => g.name),
             axisLabel: { color: css("--fg"), width: 160, overflow: "truncate" },
             axisLine: { lineStyle: { color: css("--ring") } }, axisTick: { show: false } },
    series: STATES.filter((s) => per.some((c) => c.get(s.id))).map((s) => ({
      type: "bar",
      name: s.label,
      stack: "states",
      barMaxWidth: 20,
      label: { show: showLabels, color: "#000", fontSize: 10, formatter: (p) => (p.value ? p.value : "") },
      data: groups.map((g, i) => ({
        value: per[i].get(s.id),
        id: ref({ path: [g.name, s.label], state: s.id, scope: scope(g.name, g.titles), kind: "group-state" }),
        stateId: s.id,
        group: g.name,
        itemStyle: { ...paint(s.id), borderRadius: 2 },
        tip: () => groupTip(g, groupAggrs(aggrs, g)),
      })),
    })),
  };
}
