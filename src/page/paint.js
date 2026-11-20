// The colors and patterns of the chart items.
import { muted, patterns } from "./config.js";
import { stateOf } from "./states.js";
import { ui } from "./ui.js";

// A pattern per problem state (patterns=1), for those who tell the colors apart badly:
// none on OK, so that the problems stand out the more.
const DECALS = {
  1: { symbol: "rect", symbolSize: 1, dashArrayX: [1, 0], dashArrayY: [2, 5], rotation: Math.PI / 4 },
  2: { symbol: "rect", symbolSize: 1, dashArrayX: [1, 0], dashArrayY: [2, 4], rotation: -Math.PI / 4 },
  3: { symbol: "circle", symbolSize: 0.8, dashArrayX: [[6, 6], [0, 6, 6, 0]], dashArrayY: [6, 0] },
  "-1": { symbol: "rect", symbolSize: 1, dashArrayX: [1, 0], dashArrayY: [2, 5], rotation: Math.PI / 2 },
};

// A state's fill: OK paler than the problem states, so that those stand out; a
// state other than the one of a hovered legend row faded.
export function fill(id) {
  const color = stateOf(id).color;
  let alpha = muted && id === 0 ? 0.55 : 1;
  if (ui.faded !== null && id !== ui.faded) alpha *= 0.2;
  return alpha === 1 ? color : color + Math.round(alpha * 255).toString(16).padStart(2, "0");
}

// A state's fill and, with patterns=1, its pattern: for a chart item's itemStyle.
export function paint(id) {
  const style = { color: fill(id) };
  if (patterns && DECALS[id]) style.decal = { ...DECALS[id], color: "#00000040" };
  return style;
}

// A name's color on a state's fill: black on the bright problem colors and on OK in
// a light theme, light on the pale OK of a dark one.
export function labelColor(stateId) {
  const dark = stateId === 0 && muted && !document.body.classList.contains("light");
  return dark ? "#e8e8e8" : "#000000cc";
}
