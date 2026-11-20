// The page's settings, from the query parameters that index.html lists. A
// parameter's mistake is shown in the widget, and the throw stops the script: this
// module runs first, before anything is drawn.
import { message } from "./dom.js";
import { STATES } from "./states.js";

export const VIEWS = ["pie", "rings", "treemap", "tree", "groups", "bars", "tiles", "impact", "sankey"];
// The views that need every aggregation's tree.
export const TREE_VIEWS = ["rings", "treemap", "tree", "impact", "sankey"];

export const params = new URLSearchParams(location.search);

// The page lives at /<site>/check_mk/local/bi_charts/, the GUI at /<site>/check_mk/.
export const GUI_BASE = new URL("../../", location.href);
export const groupsGiven = params.getAll("group");

export const view = choice("view", VIEWS, "pie");
export const by = choice("by", ["group", "pack"], groupsGiven.length ? "group" : "pack");
export const depth = positiveInt("depth", 3);      // rule levels drawn in the views of the trees
export const maxTrees = positiveInt("max", 40);    // one request per aggregation and refresh
export const topRows = positiveInt("top", 15);     // rows of the view impact
export const showList = params.get("list") !== "0";
export const showLegend = params.get("legend") !== "0";
export const showLabels = params.get("labels") !== "0";
export const muted = params.get("muted") !== "0";
export const patterns = params.get("patterns") === "1";
export const problemsOnly = params.get("problems") === "1";
export const animate = params.get("animation") !== "0";
export const refresh = params.has("refresh") ? Number(params.get("refresh")) : 60;
applyColors();

export function invalid(text) {
  message(text, true);
  throw new Error(text);
}

function positiveInt(name, fallback) {
  if (!params.has(name)) return fallback;
  const value = Number(params.get(name));
  if (!Number.isInteger(value) || value < 1) invalid("Parameter " + name + " must be a positive integer.");
  return value;
}

function choice(name, allowed, fallback) {
  if (!params.has(name)) return fallback;
  const value = params.get(name);
  if (!allowed.includes(value)) invalid("Parameter " + name + " must be one of " + allowed.join(", ") + ".");
  return value;
}

// colors=ok:2e7d32,crit:c62828
function applyColors() {
  if (!params.has("colors")) return;
  for (const pair of params.get("colors").split(",")) {
    const [key, hex] = pair.split(":");
    const state = STATES.find((s) => s.key === key);
    if (!state || !/^[0-9a-fA-F]{6}$/.test(hex || "")) {
      invalid("Parameter colors takes state:rrggbb pairs, e.g. ok:2e7d32,crit:c62828.");
    }
    state.color = "#" + hex;
  }
}

// Explicit theme parameter, else the theme of the embedding Checkmk page, which
// marks its <body> with data-theme (for example "modern-dark" or "facelift").
export function theme() {
  const explicit = params.get("theme");
  if (explicit === "dark" || explicit === "light") return explicit;
  if (explicit !== null) invalid("Parameter theme must be dark or light.");
  // Same origin when embedded in Checkmk; any other parent is not readable.
  let parentTheme;
  try {
    parentTheme = window.parent.document.body.dataset.theme;
  } catch (err) {
    parentTheme = undefined;
  }
  return parentTheme && !parentTheme.includes("dark") ? "light" : "dark";
}
