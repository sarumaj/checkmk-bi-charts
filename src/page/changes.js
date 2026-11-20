// When each aggregation's state changed while the page is open. No browser globals.

// How long an aggregation whose state changed is marked.
const CHANGED_FOR = 10 * 60 * 1000;

const seen = new Map();       // aggregation title -> {state, since}: when its state last changed
export const litUp = new Set();  // "<title>@<since>" of the changes the list has lit up already

// Remembers the states of a load. The first load knows no change; an aggregation
// that appears later counts as changed.
export function noteChanges(aggrs, now = Date.now()) {
  const first = seen.size === 0;
  for (const a of aggrs) {
    const before = seen.get(a.title);
    if (!before) seen.set(a.title, { state: a.state, since: first ? null : now });
    else if (before.state !== a.state) seen.set(a.title, { state: a.state, since: now });
  }
}

// When an aggregation's state changed, if that was less than CHANGED_FOR ago.
export function changedAt(title, now = Date.now()) {
  const entry = seen.get(title);
  return entry && entry.since && now - entry.since < CHANGED_FOR ? entry.since : null;
}

export const clock = (time) => new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
