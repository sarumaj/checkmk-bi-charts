// What the page shows now, shared by its modules, which change these fields: a
// module's own variable could not be assigned from another.
export const ui = {
  selected: null,        // state id the list is narrowed to, or null for all non-OK
  selectedScope: null,   // key of the scope the list is narrowed to (a group, a host)
  scopes: new Map(),     // scope key -> the titles of its aggregations, from the last drawing
  faded: null,           // state id a hovered legend row leaves in full color
  last: null,            // what the last load found: {aggrs, trees, groups}
  refs: new Map(),       // chart item id -> {path, node or state or group}
};

// Registers what a chart item stands for; its id finds it again (clicks, tests).
export function ref(entry) {
  const id = "i" + ui.refs.size;
  ui.refs.set(id, entry);
  return id;
}

// Registers a set of aggregations a click narrows the list to; the key stays the
// same across refreshes, the titles are those of the last drawing.
export function scope(key, titles) {
  ui.scopes.set(key, titles);
  return key;
}
