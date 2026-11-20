// Loads the states (and the trees and groups the view needs) and draws them.
import { loadStates, loadTrees } from "./api.js";
import { noteChanges } from "./changes.js";
import { chart } from "./chart.js";
import { TREE_VIEWS, by, groupsGiven, maxTrees, params, problemsOnly, view } from "./config.js";
import { $, message } from "./dom.js";
import { render } from "./render.js";
import { problemsOf } from "./tree.js";
import { ui } from "./ui.js";

// Removes the chart, so that outdated data is never mistaken for the current state.
function fail(text) {
  ui.last = null;
  ui.refs = new Map();
  if (chart) chart.clear();
  for (const id of ["legend", "list", "detail"]) $(id).replaceChildren();
  $("total").textContent = "?";
  message(text, true);
}

export async function load() {
  let found, trees = null, groups = null;
  const notes = [];
  try {
    found = await loadStates(groupsGiven);
    if (params.get("debug") === "1") {
      $("debug").hidden = false;
      $("debug").textContent = JSON.stringify(found.raw, null, 2);
    }
    const needTrees = TREE_VIEWS.includes(view) || (["groups", "bars"].includes(view) && by === "pack");
    if (needTrees && found.aggrs.length > maxTrees) {
      // Refuse instead of loading a partial tree set that would look complete.
      notes.push("The " + view + " view is limited to " + maxTrees + " aggregations, " + found.aggrs.length +
        " matched. Showing the pie; narrow with group= / name= or raise max=.");
    } else if (needTrees) {
      try {
        trees = await loadTrees(found.aggrs);
      } catch (err) {
        fail("Loading the aggregation trees failed: " + String(err.message || err));
        return;
      }
    }
    if (view === "groups" || view === "bars") {
      if (by === "group") {
        // The state endpoint does not say an aggregation's group: one request per group.
        if (!groupsGiven.length) notes.push("Name the groups with group=, or use by=pack.");
        const answers = await Promise.all(groupsGiven.map((g) => loadStates([g])));
        groups = groupsGiven.map((g, i) => ({ name: g, titles: new Set(answers[i].aggrs.map((a) => a.title)) }));
      } else if (trees) {
        const packs = new Map();
        for (const [title, tree] of trees) {
          const pack = tree.pack || "(no pack)";
          if (!packs.has(pack)) packs.set(pack, new Set());
          packs.get(pack).add(title);
        }
        groups = [...packs].sort((a, b) => a[0].localeCompare(b[0])).map(([name, titles]) => ({ name, titles }));
      }
    }
  } catch (err) {
    fail(String(err.message || err));
    return;
  }
  noteChanges(found.aggrs);
  ui.last = { aggrs: found.aggrs, trees, groups };
  render();

  if (!found.aggrs.length) notes.push("No aggregations matched.");
  if (problemsOnly && trees) {
    const ok = [...trees.values()].filter((tree) => !problemsOf(tree)).length;
    if (ok) notes.push("Problems only: " + ok + (ok === 1 ? " aggregation" : " aggregations") + " OK throughout left out.");
  }
  if (found.missingSites.length) notes.push("Missing sites: " + found.missingSites.join(", "));
  if (found.missingAggr.length) notes.push("Missing aggregations: " + found.missingAggr.join(", "));
  message(notes.join("\n"), false);
}
