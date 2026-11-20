import { $, css } from "../dom.js";
import { paint } from "../paint.js";
import { STATES, countStates } from "../states.js";
import { groupTip } from "../tips.js";
import { ref, scope } from "../ui.js";

// The groups' aggregations, in the order of the groups.
export function groupAggrs(aggrs, group) {
  return aggrs.filter((a) => group.titles.has(a.title));
}

// One donut per group: its OK share in the middle, its name below.
export function groupsOption(aggrs, groups) {
  const { columns, rows } = groupGrid(groups.length);
  const width = $("chart").clientWidth, height = $("chart").clientHeight;
  const cellWidth = width / columns, cellHeight = height / rows;
  const radius = Math.max(20, Math.min(cellWidth * 0.36, (cellHeight - 24) * 0.42));
  const series = [], titles = [];
  groups.forEach((group, i) => {
    const mine = groupAggrs(aggrs, group);
    const counts = countStates(mine);
    const x = (i % columns + 0.5) * cellWidth, y = Math.floor(i / columns) * cellHeight + radius + 6;
    const present = STATES.filter((s) => counts.get(s.id));
    series.push({
      type: "pie",
      center: [x, y],
      radius: [radius * 0.7, radius],
      padAngle: present.length > 1 ? 2 : 0,
      itemStyle: { borderRadius: 2 },
      label: { show: false },
      data: present.map((s) => ({
        name: s.label,
        value: counts.get(s.id),
        id: ref({ path: [group.name, s.label], state: s.id, scope: scope(group.name, group.titles),
                  kind: "group-state" }),
        stateId: s.id,
        group: group.name,
        itemStyle: paint(s.id),
        tip: () => groupTip(group, mine),
      })),
    });
    const ok = mine.length ? Math.round(counts.get(0) / mine.length * 100) : 0;
    const size = Math.round(Math.max(12, radius * 0.32));
    titles.push({
      text: mine.length ? ok + " %" : "\u2013",
      subtext: group.name,
      left: x, top: y - size * 0.6,
      textAlign: "center",
      // The name under the donut.
      itemGap: radius - size * 0.4 + 8,
      textStyle: { color: css("--fg"), fontSize: size, fontWeight: 700 },
      subtextStyle: { color: css("--fg"), fontSize: 12, width: cellWidth - 12, overflow: "truncate" },
    });
  });
  return { title: titles, series };
}

// The donuts' grid: wider than high.
export function groupGrid(count) {
  const columns = Math.max(1, Math.min(count, Math.ceil(Math.sqrt(count * 2.5))));
  return { columns, rows: Math.max(1, Math.ceil(count / columns)) };
}
