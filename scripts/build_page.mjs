#!/usr/bin/env node
// Builds the page from src/page/ into build/bi_charts/index.html: the modules from
// main.js bundled with the parts of ECharts they import (esbuild), and the stylesheet,
// both inlined into the template at its build markers. One file: a browser cannot
// pair a cached script with a newer page after an update of the package.
//
//     npm run build        # or: node scripts/build_page.mjs
//
// scripts/build_mkp.py runs it before it packs the page. Identical sources give a
// byte-identical page, as the MKP must be reproducible.
import { build } from "esbuild";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const page = join(root, "src/page");
const target = join(root, "build/bi_charts/index.html");

const bundle = await build({
  entryPoints: [join(page, "main.js")],
  bundle: true,
  format: "iife",
  minify: true,
  // The license texts ship as files beside the page (scripts/build_mkp.py).
  legalComments: "none",
  // Checkmk's supported browsers are evergreen; this keeps the code as written.
  target: "es2022",
  write: false,
  logLevel: "warning",
});
const script = bundle.outputFiles[0].text;
// An inline script ends at the first "</script", wherever it stands.
if (/<\/script/i.test(script)) throw new Error("The bundle contains </script, which would end the inline script");

const template = readFileSync(join(page, "index.html"), "utf8");
const style = readFileSync(join(page, "style.css"), "utf8");
const markers = { "<!-- build: style -->": `<style>\n${style}</style>`, "<!-- build: script -->": `<script>${script}</script>` };
let html = template;
for (const [marker, content] of Object.entries(markers)) {
  if (html.split(marker).length !== 2) throw new Error(`src/page/index.html needs the marker ${marker} once`);
  // A function, so that "$&" and the like in the bundle stay as they are.
  html = html.replace(marker, () => content);
}
mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, html);
console.log(`${target.slice(root.length + 1)}: ${(html.length / 1024).toFixed(0)} KiB`);
