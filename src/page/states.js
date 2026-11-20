// Checkmk's monitoring states and what the views say about them. No browser
// globals: the Node tests (tests/js) import this module as it is.

// Checkmk monitoring states; -1 is PENDING. Order is the draw order. colors= in the
// URL changes the colors (config.js).
export const STATES = [
  { id: 0,  key: "ok",      label: "OK",      color: "#13d389" },
  { id: 1,  key: "warn",    label: "WARN",    color: "#ffd703" },
  { id: 2,  key: "crit",    label: "CRIT",    color: "#ff3232" },
  { id: 3,  key: "unknown", label: "UNKNOWN", color: "#ff8800" },
  { id: -1, key: "pending", label: "PENDING", color: "#8a949e" },
];

export const stateOf = (id) => STATES.find((s) => s.id === id);

// CRIT > UNKNOWN > WARN > PENDING > OK, matching Checkmk's worst-state ordering.
export function severity(state) {
  return { 2: 4, 3: 3, 1: 2, "-1": 1, 0: 0 }[state];
}

export function flagsOf(item) {
  return [item.acknowledged && "acknowledged", item.inDowntime && "in downtime"].filter(Boolean);
}

// "12 OK, 1 WARN", in the fixed state order.
export function stateSummary(counts) {
  return STATES.filter((s) => counts.get(s.id)).map((s) => counts.get(s.id) + " " + s.label).join(", ");
}

export function countStates(aggrs) {
  const counts = new Map(STATES.map((s) => [s.id, 0]));
  for (const a of aggrs) counts.set(a.state, counts.get(a.state) + 1);
  return counts;
}

// The aggregations in state order, as the pie and the inner ring show them.
export function ordered(aggrs) {
  return aggrs.slice().sort((a, b) =>
    STATES.findIndex((s) => s.id === a.state) - STATES.findIndex((s) => s.id === b.state) ||
    a.title.localeCompare(b.title));
}

// The aggregations worst first (as the list), then by title.
export function bySeverity(aggrs) {
  return aggrs.slice().sort((a, b) => severity(b.state) - severity(a.state) || a.title.localeCompare(b.title));
}

// A node's name without its parent's in front, for labels: "Frontend" below "Web Shop"
// instead of "Web Shop Frontend". The tooltips keep the whole name.
export function shortName(name, parent) {
  return parent && name.startsWith(parent + " ") && name.length > parent.length + 1
    ? name.slice(parent.length + 1) : name;
}

// For the tooltips, which ECharts takes as HTML: names come from the BI
// configuration and are inserted as text.
export function esc(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;",
    "\"": "&quot;", "'": "&#39;" })[c]);
}
