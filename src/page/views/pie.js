import { showLabels } from "../config.js";
import { css } from "../dom.js";
import { labelColor, paint } from "../paint.js";
import { STATES, countStates } from "../states.js";
import { stateTip } from "../tips.js";
import { ref, ui } from "../ui.js";

// The states of the aggregations as a donut.
export function pieOption(aggrs) {
  const counts = countStates(aggrs);
  const present = STATES.filter((s) => counts.get(s.id));
  return {
    series: [{
      type: "pie",
      radius: ["62%", "82%"],
      padAngle: present.length > 1 ? 2 : 0,
      itemStyle: { borderRadius: 3 },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 4 },
      data: present.map((s) => ({
        name: s.label,
        value: counts.get(s.id),
        id: ref({ path: [s.label], state: s.id, kind: "state",
                  arc: showLabels ? { text: s.label + " " + counts.get(s.id), color: labelColor(s.id) } : undefined }),
        stateId: s.id,
        itemStyle: { ...paint(s.id), borderColor: ui.selected === s.id ? css("--fg") : "transparent",
                     borderWidth: ui.selected === s.id ? 2 : 0 },
        tip: () => stateTip(s, aggrs),
      })),
    }],
  };
}
