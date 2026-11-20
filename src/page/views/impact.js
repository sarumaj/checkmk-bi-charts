import { allOkOption } from "../chart.js";
import { showLabels, topRows } from "../config.js";
import { css } from "../dom.js";
import { labelColor, paint } from "../paint.js";
import { STATES, countStates } from "../states.js";
import { impactTip } from "../tips.js";
import { impactOf } from "../tree.js";
import { ref, scope } from "../ui.js";

// One bar per host or service that is not OK, as long as the aggregations it is
// part of, a segment per state of those; a dot in the host's or service's own state
// before its name.
export function impactOption(aggrs, trees) {
  const leaves = impactOf(aggrs, trees).slice(0, topRows);
  if (!leaves.length) return allOkOption();
  const per = leaves.map((leaf) => countStates(leaf.list));
  const rich = Object.fromEntries(STATES.map((s) => ["s" + (s.id < 0 ? "p" : s.id), { color: s.color, fontSize: 13 }]));
  // Braces would start rich text of their own.
  const names = leaves.map((leaf) => leaf.name.replace(/[{}|]/g, "_"));
  return {
    grid: { left: 8, right: 16, top: 8, bottom: 24, containLabel: true },
    xAxis: { type: "value", minInterval: 1, name: "aggregations", nameLocation: "middle", nameGap: 22,
             nameTextStyle: { color: css("--muted") }, axisLabel: { color: css("--muted") },
             splitLine: { lineStyle: { color: css("--ring") } } },
    yAxis: { type: "category", inverse: true, data: names,
             axisLabel: { color: css("--fg"), width: 220, overflow: "truncate", rich,
                          formatter: (name, i) => "{s" + (leaves[i].node.state < 0 ? "p" : leaves[i].node.state) +
                            "|●} " + name },
             axisLine: { lineStyle: { color: css("--ring") } }, axisTick: { show: false } },
    series: STATES.filter((s) => per.some((c) => c.get(s.id))).map((s) => ({
      type: "bar",
      name: s.label,
      stack: "states",
      barMaxWidth: 18,
      label: { show: showLabels, color: labelColor(s.id), fontSize: 10, formatter: (p) => (p.value ? p.value : "") },
      data: leaves.map((leaf, i) => ({
        value: per[i].get(s.id),
        id: ref({ path: [leaf.name, s.label], state: s.id, kind: "impact",
                  scope: scope("leaf:" + leaf.key, new Set(leaf.list.map((a) => a.title))) }),
        itemStyle: { ...paint(s.id), borderRadius: 2 },
        tip: () => impactTip(leaf),
      })),
    })),
  };
}
