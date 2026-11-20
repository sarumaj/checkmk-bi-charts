import { depth, showLabels } from "../config.js";
import { $, css } from "../dom.js";
import { labelColor, paint } from "../paint.js";
import { esc, ordered, shortName } from "../states.js";
import { nodeTip } from "../tips.js";
import { ref } from "../ui.js";

// The BI trees as rings: the innermost one per aggregation, each further ring
// the next level of rules, children sharing their parent's angle by the hosts
// and services below them. The hosts and services themselves are pills in a
// thin band around the rings, below rules of any depth: invisible spacers lift
// a host or service that sits higher up to the band.
export function ringsOption(aggrs, trees) {
  const list = ordered(aggrs);
  const rings = Math.max(1, Math.min(depth, Math.max(...list.map((a) => trees.get(a.title).ruleLevels))));
  const radius = Math.min($("chart").clientWidth, $("chart").clientHeight) / 2;
  const inner = 0.3, outer = 0.86, step = (outer - inner) / rings;
  const allLeaves = list.reduce((sum, a) => sum + trees.get(a.title).leaves, 0);
  // Below a rule of an upper ring: in the ring's own background color, which reads as
  // room left free rather than as a crack through the rings.
  function spacer(child, from) {
    let item = child;
    for (let level = rings; level > from; level--) {
      item = { name: "", value: child.value, children: [item], itemStyle: { color: css("--ring"), borderWidth: 0 },
               label: { show: false }, emphasis: { disabled: true }, tooltip: { show: false }, cursor: "default" };
    }
    return item;
  }

  // A pill narrower than a few pixels is mostly the gap around it: too many hosts and
  // services for the band. Then neighbours below the same rule that share a state
  // (and its flags) are one pill, its tooltip naming them.
  const crowded = 2 * Math.PI * 0.93 * radius / allLeaves < 6;
  const same = (a, b) => a.state === b.state && a.acknowledged === b.acknowledged && a.inDowntime === b.inDowntime;
  function runs(children) {
    const found = [];
    for (const child of children) {
      const run = found[found.length - 1];
      if (crowded && !child.children.length && run && !run[0].children.length && same(run[0], child)) run.push(child);
      else found.push([child]);
    }
    return found;
  }

  function pill(run, level, path) {
    if (run.length === 1) {
      const node = run[0], here = path.concat(node.name);
      return spacer({ name: node.name, value: 1, id: ref({ path: here, node, kind: node.service ? "service" : "host" }),
                      itemStyle: paint(node.state), label: { show: false }, tip: () => nodeTip(node, here) }, level);
    }
    const first = run[0];
    const node = { name: run.length + " hosts and services", state: first.state, acknowledged: first.acknowledged,
                   inDowntime: first.inDowntime, children: [], leaves: run.length };
    const here = path.concat(node.name);
    const tip = () => {
      const shown = run.slice(0, 8).map((n) => "<li>" + esc(n.service && n.host ? n.host + " › " + n.service : n.name) +
        "</li>");
      return nodeTip(node, here) + "<ul>" + shown.join("") + "</ul>" +
        (run.length > shown.length ? '<div class="more">and ' + (run.length - shown.length) + " more</div>" : "");
    };
    return spacer({ name: node.name, value: run.length, id: ref({ path: here, node, kind: "leaves" }),
                    itemStyle: paint(node.state), label: { show: false }, tip }, level);
  }

  function label(node, level, text) {
    if (!showLabels) return { show: false };
    const r0 = (inner + level * step) * radius, r1 = r0 + step * radius;
    const arc = 2 * Math.PI * node.leaves / allLeaves * (r0 + r1) / 2;
    const deep = r1 - r0;
    // Along the radius in a narrow segment; bent along the ring in a wide one, which
    // drawArcs draws once ECharts has laid the segment out.
    const along = arc > 2.5 * deep;
    if (along) {
      const size = Math.min(11, deep * 0.55);
      return size < 8 ? { show: false } : { show: false, curve: { text, size, color: labelColor(node.state) } };
    }
    const width = along ? arc * 0.85 : deep - 6;
    const size = Math.min(11, Math.max(8, (along ? deep : arc) * 0.55));
    const fits = Math.floor(width / (size * 0.6));
    // Whole, or at least 8 characters before the ellipsis; else none.
    if (fits < Math.min(text.length, 8) || (along ? deep : arc) < 9) return { show: false };
    return { show: true, formatter: () => text, rotate: "radial", width, overflow: "truncate", fontSize: size, fontWeight: 700,
             color: labelColor(node.state) };
  }

  function build(node, level, path) {
    const here = path.concat(node.name);
    if (!node.children.length) return [pill([node], level, path)];
    const children = runs(node.children).flatMap((run) =>
      run.length === 1 && run[0].children.length ? build(run[0], level + 1, here) : [pill(run, level + 1, here)]);
    if (level >= rings) return children;
    const named = label(node, level, shortName(node.name, path[path.length - 1]));
    return [{
      name: node.name,
      id: ref({ path: here, node, kind: level === 0 ? "aggregation" : "rule", arc: named.curve }),
      itemStyle: paint(node.state),
      label: { ...named, curve: undefined },
      // Hovered, ECharts would show a hidden label after all: over a bent name, the whole name.
      emphasis: { label: { show: Boolean(named.show) } },
      tip: () => nodeTip(node, here),
      children,
    }];
  }

  const data = list.flatMap((a) => build(trees.get(a.title), 0, []));
  const levels = [{}];
  for (let i = 0; i < rings; i++) {
    levels.push({ r0: ((inner + i * step) * 100) + "%", r: ((inner + (i + 1) * step) * 100) + "%",
                  itemStyle: { borderColor: css("--gap"), borderWidth: 1.5 } });
  }
  // The band: rounded pills with a gap between them.
  levels.push({ r0: "90%", r: "96%", itemStyle: { borderColor: css("--gap"), borderWidth: 2, borderRadius: 6 },
                label: { show: false } });
  return {
    series: [{
      type: "sunburst",
      data,
      sort: null,
      radius: ["0%", "96%"],
      nodeClick: false,
      emphasis: { focus: "ancestor" },
      levels,
    }],
  };
}
