# bi_charts: charts of Checkmk BI aggregations

A dashboard element with charts of Checkmk BI aggregations: their states as a
pie or as tiles, the BI trees as rings, a treemap, a tree of nodes or flows,
the states per group as donuts or bars, and the hosts and services that drag
the most aggregations down, with a list of the aggregations that are not OK.
Checkmk has no such charts for BI and no way to add custom widget types in 2.5,
so this package embeds a static page instead. It draws with
[Apache ECharts](https://echarts.apache.org/), which the package includes.

![The pie with sample data](docs/screenshot.png)

![The rings with sample data](docs/screenshot-rings.png)

![The treemap with sample data](docs/screenshot-treemap.png)

![The tree, problems only, with sample data](docs/screenshot-tree.png)

![The flows, problems only, with sample data](docs/screenshot-sankey.png)

![Donuts and bars per group with sample data](docs/screenshot-groups.png)

![Tiles and impact with sample data](docs/screenshot-tiles.png)

![Hover details with sample data](docs/screenshot-hover.png)

*All rendered from the page with sample data by `tools/screenshots.py`, not
taken from a live site.*

## Requirements

- Checkmk 2.4.0 or 2.5.0, any edition: every version Checkmk maintains (2.3 left
  maintenance on 2026-10-29). CI checks this every week against Checkmk's list of
  releases and fails once a new version is out and not yet tested.
- Viewers need access to BI. The shipped dashboard is a packaged one; with
  Checkmk's default permissions every role may see it.

## Install

As the site user:

```
mkp add bi_charts-0.2.1.mkp
mkp enable bi_charts 0.2.1
```

The package then provides:

- the dashboard **BI aggregation states** (`dashboard.py?name=bi_charts`)
- the page `local/bi_charts/index.html`, for use in your own dashboards

## Use it in your own dashboards

Add a custom URL element (2.4) or an Embed URL widget (2.5) with a
site-relative URL. Checkmk's documentation lists them among the built-in
elements of a dashboard:
[Custom URL in 2.4](https://docs.checkmk.com/2.4.0/en/dashboards.html#builtin_dashlets),
[Embed URL in 2.5](https://docs.checkmk.com/latest/en/dashboards.html#builtin_widgets)
(the current documentation; Checkmk publishes no separate 2.5 address).

```
local/bi_charts/index.html?group=WebApp&title=Web%20applications
local/bi_charts/index.html?view=rings&depth=4&name=Payment%20API
local/bi_charts/index.html?view=bars&group=WebApp&group=Storage&group=Network
```

| Parameter     | Meaning                                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| `view`        | `pie` (default), `rings`, `treemap`, `tree`, `groups`, `bars`, `tiles`, `impact` or `sankey`, see below       |
| `group`       | BI aggregation group to include, repeatable; the groups of `groups` and `bars`                                |
| `name`        | Aggregation title to include, repeatable                                                                      |
| `by`          | `groups`, `bars`: `group` (default when `group` is given) or `pack` (BI pack, otherwise)                      |
| `depth`       | `rings`, `treemap`, `tree`, `sankey`: levels of rules shown, default 3                                        |
| `problems=1`  | `rings`, `treemap`, `tree`, `sankey`: only the paths down to what is not OK                                   |
| `max`         | Views of the trees: most aggregations to load, default 40                                                     |
| `top`         | `impact`: most hosts and services shown, default 15                                                           |
| `title`       | Heading above the chart                                                                                       |
| `refresh`     | Reload interval in seconds, default 60, `0` disables                                                          |
| `theme`       | `dark` or `light`; default: the Checkmk theme of the embedding page                                           |
| `colors`      | Other state colors, e.g. `ok:2e7d32,crit:c62828` (`ok`, `warn`, `crit`, `unknown`, `pending`)                 |
| `muted=0`     | OK in full color; by default it is paler than the problem states                                              |
| `patterns=1`  | A pattern per problem state besides its color: stripes for WARN and CRIT (each its own way), dots for UNKNOWN |
| `labels=0`    | No names on the chart                                                                                         |
| `legend=0`    | Hide the legend                                                                                               |
| `list=0`      | Hide the list of non-OK aggregations                                                                          |
| `animation=0` | No animation                                                                                                  |
| `debug=1`     | Show the raw REST API response                                                                                |

Clicking a state (a slice, a donut's or bar's segment, a legend row) narrows
the list to it; in `groups` and `bars` also to that group. Each entry of the
list links to the aggregation's BI view.

## Views

| View      | Shows                                                                                                                             | Best for                                                  |
| --------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `pie`     | One slice per state, its name and count along the ring where they fit, the number of aggregations in the middle                   | A small element, any number of aggregations               |
| `rings`   | The BI trees as rings, hosts and services as pills around them                                                                    | Following a problem from an aggregation down to a service |
| `treemap` | The BI trees as nested rectangles, sized by hosts and services; a click zooms in                                                  | Many aggregations at once                                 |
| `tree`    | The BI trees as a tree of nodes, folded below `depth`; a click opens or folds a node                                              | Reading the structure of a few aggregations               |
| `groups`  | One donut per group, its OK share in the middle                                                                                   | Comparing groups at a glance                              |
| `bars`    | One stacked bar per group, a segment per state                                                                                    | Comparing groups by the number of aggregations            |
| `tiles`   | One hexagon per aggregation, the worst first, its name inside                                                                     | Many aggregations at a glance, on a wall screen           |
| `impact`  | One bar per host or service that is not OK, as long as the aggregations it is part of, a segment per state of those               | What to fix first                                         |
| `sankey`  | The BI trees as flows from the aggregations through their rules to their hosts; a host shared by several aggregations is one node | Seeing what aggregations share                            |

**Rings:** the innermost ring holds the aggregations, in the same order as the
pie. Each further ring, up to `depth`, is the next level of rules: the rules
an aggregation is built from and the rules those call (also across BI packs).
Every segment's angle is its share of the hosts and services. The hosts and
services themselves are pills in a thin band around the rings, however deep
they sit in the tree, so the band shows every problem even when the rings stop
early. A segment wide enough carries its name: straight along the radius in a
narrow segment, bent along the ring in a wide one, and never upside down. A
name is left out where it would be cut to fewer than eight characters (six when
bent), so how many names show depends on the element's size. Hovering a segment keeps its path to the aggregation in full
color. Where the band has too little room (less than six pixels a pill), the
hosts and services next to each other below the same rule that share a state
are one pill, and its details name them. A rule's hosts and services that sit
higher up than the deepest ring leave its outer rings empty.

**Names in the trees:** a rule named after its parent plus a word (*Web Shop
Frontend* below *Web Shop*) shows only that word in the rings, the treemap, the
tree and the flows; the details give the whole name. The treemap and the flows
put the worst aggregations first, as the tiles do.

**Problems only (`problems=1`):** the views of the trees leave out what is OK
throughout and keep the paths down to every host or service that is not OK,
also in an aggregation that is OK itself (a rule that tolerates a failed
member). Below the chart the page says how many aggregations it left out. The
details of a node still count all the hosts and services below it.

**Sankey:** a column of aggregations, one per level of rules up to `depth`, and
the hosts last. Each host or service flows from the rule above it to its host,
so a host's node is as high as its services in all the aggregations shown, and
a host in several aggregations (a core switch, a storage system) gathers flows
from all of them. A flow has the color of the worst state in it. Rules below
`depth` are left out; their hosts hang from the rule above. Many aggregations
make a long column of hosts: narrow the filter or use `problems=1`.

**Changes:** an aggregation whose state changed while the page is open is
marked for ten minutes: in bold with *since* and the time in the list (lit up
once when it happens), outlined among the tiles, and with the time in its
details. The page remembers nothing between visits, so the first load marks
nothing.

**Tiles:** need only the states, not the trees, so they work for any number
of aggregations. A tile also says when its aggregation is acknowledged or in
downtime; clicking it shows its state below the chart.

**Impact:** walks the trees for the hosts and services that are not OK, and
ranks them by how many of their aggregations are not OK, then by how many
aggregations they are part of. A host or service shared by many aggregations
(a core switch, a storage system) comes first. The dot before a name is its
own state; the segments are the states of its aggregations, and clicking one
narrows the list to those. `top` sets the number of rows. Being part of an
aggregation that is not OK does not prove it is the cause: a rule may tolerate
one failed member.

**Groups and bars:** the state endpoint does not say which group an
aggregation belongs to, so `by=group` asks once per `group` given, and
`by=pack` groups by the BI pack of each aggregation's top rule, which needs the
trees (as the views of the trees, up to `max`).

Loading the trees takes one request per aggregation. A refresh loads a tree
again only when its aggregation's answer from the state endpoint changed (which
names the nodes that have a problem) or the tree is ten minutes old, so that a
changed BI configuration shows within ten minutes. Above `max` aggregations the
page shows the pie and says so, instead of drawing a partial set of trees.

## Hover details and legend

Hovering, or tapping on a touch screen, shows a details box next to the
pointer:

- **State (slice, legend row):** the state's count and share, and the
  aggregations in that state with their acknowledged / downtime flags (the
  first eight, then a count of the rest).
- **Node of a tree (rings, treemap, tree, sankey):** the path down to the node,
  its state and flags, whether it is a rule (with BI pack and rule ID), a host
  or a service, and how many hosts and services sit below it per state. Clicking
  it keeps its path on display below the chart.
- **Group (donut, bar):** the group's aggregations per state.
- **Tile:** the aggregation's state and flags.
- **Impact bar:** the host's or service's state, and its aggregations per
  state (the first eight, worst first).
- **Host of the flows:** its state, its hosts and services per state, the
  aggregations it is in, and its hosts and services, the worst first.

Hovering a legend row fades everything of another state.

The legend lists each state's aggregation count and share, the share also as a
bar. In the views of the trees it adds a column with the hosts and services per
state across all loaded trees.

OK is drawn paler than the problem states, and small gaps separate the slices
and segments, so that problems stand out (`muted=0` turns this off). For screen
readers the chart's description says the view and the states of the
aggregations.

## How it works

The page calls
`GET /api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke`
with the viewer's GUI session, so every user sees only the aggregations they
are permitted to see. No data is stored and no automation user is needed.

That endpoint only reports the nodes that have a problem, so the views of the
trees also call `ajax_fetch_aggregation_data.py`, the GUI endpoint behind Checkmk's
own BI visualization, once per aggregation. It is not a public API; it is the
same in the 2.4 and 2.5 sources.

One package covers both versions because it avoids version-specific code:

| Part  | Content                                                                  | Why it works on 2.4 and 2.5                                                 |
| ----- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `web` | `htdocs/bi_charts/`: the page, ECharts bundled into it, and its licenses | Both serve `~/local/share/check_mk/web/htdocs` at `/<site>/check_mk/local/` |
| `gui` | `dashboard/bi_charts`                                                    | Packaged dashboard in the 2.4 format, which 2.5 converts when loading       |

Dashboard filters do not reach the page, because the embed element does not
pass them on. Put the filter into the URL instead.

## Known limitations

- **Duplicate titles:** Checkmk's state endpoint keys aggregations by title, so
  two aggregations with the same title count as one.
- **Sizes:** the rings, the treemap and the groups' charts weigh aggregations
  differently: the rings and the treemap by hosts and services, the pie and the
  groups by aggregations.
- **Load:** every open widget asks once per refresh, and each request makes
  Checkmk compute all matching aggregations; the views of the trees add one
  request per aggregation whose state changed (and per aggregation every ten
  minutes), `by=group` one per group. Raise `refresh` or narrow the filter on
  large setups.
- **Internals:** the tree endpoint, the packaged dashboard format and the local
  htdocs path are not public interfaces. `version.usable_until` is therefore
  set to 2.6.0; they were only checked for 2.4 and 2.5.
- **Touch devices:** a tap shows the details, and on a state also narrows the
  list; fading by a legend row needs a pointer.
- When a request fails, the page shows the error and removes the chart, so that
  outdated data is never mistaken for the current state.

## Tests

```
npm ci                             # esbuild and the chart library the page bundles
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'           # the project, with build-mkp and the test tools
playwright install chromium        # or: pytest --browser-channel chrome

npm test                           # the page's modules in Node.js, under a second
python3 -m pytest                  # unit tests, a few seconds
python3 -m pytest tests/integration   # real Checkmk 2.4 and 2.5 in Docker
```

| Suite                               | What it checks                                                                                            | Needs                        |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `tests/js/`                         | what the views of the trees work out from the BI trees, without a browser                                 | Node.js, `npm ci`            |
| `tests/unit/test_package.py`        | package sources and the built MKP                                                                         | Node.js, `npm ci`            |
| `tests/unit/test_page.py`           | every view in a real browser, against a stand-in for the Checkmk endpoints                                | a browser, Node.js, `npm ci` |
| `tests/integration/test_checkmk.py` | install, both endpoints with a session cookie, the dashboard and the page in a browser, on 2.4 and on 2.5 | Docker                       |
| `tests/integration/test_update.py`  | the same site updated from 2.4 to 2.5                                                                     | Docker                       |

The integration tests install Checkmk from its own packages: the newest patch
release of 2.4 (Raw edition) and of 2.5 (Community edition), as listed in
[stable_downloads.json](https://download.checkmk.com/stable_downloads.json),
for Debian 12. Each package is checked against the SHA-256 given there and kept
in `~/.cache/bi-charts` (`BI_CHARTS_CACHE`). Both go into one Docker image
(`tests/integration/image/Dockerfile`), built on the first run (about 600 MB of
downloads, several minutes) and again only for a new patch release. Every test
module creates its sites in containers of that image; the update test runs
`omd update` in the container of the 2.4 site, as on a server.
`BI_CHARTS_PACKAGE_2_4` and `BI_CHARTS_PACKAGE_2_5` name a package file to use
instead, e.g. an older patch release.

## CI and releases

`.forgejo/workflows/ci.yml` runs on every push to `main`, every pull request,
every tag and every Monday, so that a new Checkmk patch release is tested before
anyone updates to it:

| Job                               | What it does                                                        |
| --------------------------------- | ------------------------------------------------------------------- |
| `unit`                            | the unit tests, and the MKP, kept as the run's artifact for 14 days |
| `integration (Checkmk 2.4)`       | `test_checkmk.py` on a 2.4 site                                     |
| `integration (Checkmk 2.5)`       | `test_checkmk.py` on a 2.5 site                                     |
| `integration (update 2.4 to 2.5)` | `test_update.py`                                                    |
| `release`                         | for a tag only, once all of the above passed: the MKP as a release  |

Each integration job builds an image with only its versions
(`BI_CHARTS_VERSIONS`, default `2.4 2.5`); a new Checkmk version is one more entry
in the matrix.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). The
release bot tags the releases due from them (`tool.commitizen` in
`pyproject.toml`), writing the version into `pyproject.toml` (the MKP's too) and
the install commands above. The tag runs the whole
pipeline, and its `release` job publishes the MKP with its SHA-256 as a release.
The upload to the [Checkmk Exchange](https://exchange.checkmk.com/) stays by
hand: it has no API, and Checkmk reviews every version. Renovate keeps the test
tools in `pyproject.toml` and ECharts in `package-lock.json` up to date.

## Verification status

Checked against the Checkmk 2.4 and 2.5 sources:

- session cookies are a documented authentication scheme of the REST API
- both endpoints return the fields the page reads
- both versions serve the local htdocs directory and load packaged dashboards
  from the same directory; 2.5 converts the 2.4 dashboard format when loading
- the archive is accepted by Checkmk's own MKP manifest parser (2.5)

Checked by the unit tests: the page's behavior in a browser, against a stand-in
that answers like those sources.

Checked by the integration tests, on sites installed from Checkmk's packages
(2.4.0p41 Raw and 2.5.0p20 Community when this was written; CI tests the
newest patch releases every week): the installation, both endpoints with a
session cookie, the packaged dashboard, the page in a browser, and the update of
a site with the package from 2.4 to 2.5.

## Build

```
npm ci               # esbuild and ECharts, in the versions package-lock.json pins
pip install -e .     # the project: the command build-mkp (scripts/build_mkp.py)
build-mkp            # writes dist/bi_charts-<version>.mkp, no Checkmk site needed
npm run build        # the page alone: build/bi_charts/index.html
```

`python3 scripts/build_mkp.py` does the same without installing the project.
The project is installed editable, so that `build-mkp` reads `src/`,
`node_modules/` and `build/` of the checkout. The version is `project.version` in
`pyproject.toml`; `build-mkp --version` prints it.

The page's sources are ES modules in `src/page/`, and `build-mkp` builds the page
from them first (`scripts/build_page.mjs`): [esbuild](https://esbuild.github.io/)
bundles them from `main.js` with the parts of ECharts they import, and inlines the
bundle and `style.css` into `index.html` at its build markers. The page is one file,
so that a browser never pairs a cached script with a newer page after an update.

| Module                                       | What it holds                                                                                                         |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `config.js`                                  | the query parameters, checked first; the views' names                                                                 |
| `states.js`, `tree.js`, `changes.js`         | the states, the BI trees and what the views work out from them, the changes of state; no browser globals (`tests/js`) |
| `api.js`, `load.js`                          | the requests to Checkmk, and a load drawn or failed                                                                   |
| `ui.js`                                      | what the page shows now (selection, fading, the chart items), shared by the modules                                   |
| `chart.js`, `paint.js`, `tips.js`, `arcs.js` | the chart and what every view shares: colors and patterns, tooltips, the bent names                                   |
| `views/*.js`                                 | one module per view: its ECharts options                                                                              |
| `render.js`, `legend.js`, `list.js`          | the drawing, the legend, the list and the detail line                                                                 |
| `main.js`                                    | the entry point: theme, events, `window.biCharts`, refresh                                                            |

The build is reproducible: identical sources give a byte-identical page and archive.

## License

GPL-2.0-or-later, see [LICENSE](LICENSE) (the text of version 2).

The page includes the parts of [Apache ECharts](https://echarts.apache.org/)
it uses, under the Apache License 2.0, and of zrender, which ECharts builds on,
under the BSD 3-Clause license (and tslib's helpers, 0BSD); their license texts
and notice ship beside the page
(`LICENSE-echarts.txt`, `NOTICE-echarts.txt`, `LICENSE-zrender.txt`). The
Apache License 2.0 is compatible with version 3 of the GPL, not with version 2
alone, which is why the package is GPL-2.0-or-later.
