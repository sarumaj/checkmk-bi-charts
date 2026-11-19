# bi_charts: charts of Checkmk BI aggregations

A dashboard element with charts of Checkmk BI aggregations: their states as a
pie or as tiles, the BI trees as rings, a treemap or a tree of nodes, the states
per group as donuts or bars, and the hosts and services that drag the most
aggregations down, with a list of the aggregations that are not OK.
Checkmk has no such charts for BI and no way to add custom widget types in 2.5,
so this package embeds a static page instead. It draws with
[Apache ECharts](https://echarts.apache.org/), which the package includes.

![The pie with sample data](docs/screenshot.png)

![The rings with sample data](docs/screenshot-rings.png)

![The treemap with sample data](docs/screenshot-treemap.png)

![The tree with sample data](docs/screenshot-tree.png)

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
mkp add bi_charts-0.4.0.mkp
mkp enable bi_charts 0.4.0
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

| Parameter | Meaning |
|-----------|---------|
| `view` | `pie` (default), `rings`, `treemap`, `tree`, `groups`, `bars`, `tiles` or `impact`, see below |
| `group` | BI aggregation group to include, repeatable; the groups of `groups` and `bars` |
| `name` | Aggregation title to include, repeatable |
| `by` | `groups`, `bars`: `group` (default when `group` is given) or `pack` (BI pack, otherwise) |
| `depth` | `rings`, `treemap`, `tree`: levels of rules shown, default 3 |
| `max` | Views of the trees: most aggregations to load, default 40 |
| `top` | `impact`: most hosts and services shown, default 15 |
| `title` | Heading above the chart |
| `refresh` | Reload interval in seconds, default 60, `0` disables |
| `theme` | `dark` or `light`; default: the Checkmk theme of the embedding page |
| `colors` | Other state colors, e.g. `ok:2e7d32,crit:c62828` (`ok`, `warn`, `crit`, `unknown`, `pending`) |
| `muted=0` | OK in full color; by default it is paler than the problem states |
| `labels=0` | No names on the chart |
| `legend=0` | Hide the legend |
| `list=0` | Hide the list of non-OK aggregations |
| `animation=0` | No animation |
| `debug=1` | Show the raw REST API response |

Clicking a state (a slice, a donut's or bar's segment, a legend row) narrows
the list to it; in `groups` and `bars` also to that group. Each entry of the
list links to the aggregation's BI view.

## Views

| View | Shows | Best for |
|------|-------|----------|
| `pie` | One slice per state, its name and count along the ring where they fit, the number of aggregations in the middle | A small element, any number of aggregations |
| `rings` | The BI trees as rings, hosts and services as pills around them | Following a problem from an aggregation down to a service |
| `treemap` | The BI trees as nested rectangles, sized by hosts and services; a click zooms in | Many aggregations at once |
| `tree` | The BI trees as a tree of nodes, folded below `depth`; a click opens or folds a node | Reading the structure of a few aggregations |
| `groups` | One donut per group, its OK share in the middle | Comparing groups at a glance |
| `bars` | One stacked bar per group, a segment per state | Comparing groups by the number of aggregations |
| `tiles` | One hexagon per aggregation, the worst first, its name inside | Many aggregations at a glance, on a wall screen |
| `impact` | One bar per host or service that is not OK, as long as the aggregations it is part of, a segment per state of those | What to fix first |

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
color.

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

Loading the trees takes one request per aggregation on every refresh. Above
`max` aggregations the page shows the pie and says so, instead of drawing a
partial set of trees.

## Hover details and legend

Hovering shows a details box next to the pointer:

- **State (slice, legend row):** the state's count and share, and the
  aggregations in that state with their acknowledged / downtime flags (the
  first eight, then a count of the rest).
- **Node of a tree (rings, treemap, tree):** the path down to the node, its
  state and flags, whether it is a rule (with BI pack and rule ID), a host or a
  service, and how many hosts and services sit below it per state. Clicking it
  keeps its path on display below the chart.
- **Group (donut, bar):** the group's aggregations per state.
- **Tile:** the aggregation's state and flags.
- **Impact bar:** the host's or service's state, and its aggregations per
  state (the first eight, worst first).

Hovering a legend row fades everything of another state.

The legend lists each state's aggregation count and share, the share also as a
bar. In the views of the trees it adds a column with the hosts and services per
state across all loaded trees.

OK is drawn paler than the problem states, and small gaps separate the slices
and segments, so that problems stand out (`muted=0` turns this off).

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

| Part  | Content | Why it works on 2.4 and 2.5 |
|-------|---------|-----------------------------|
| `web` | `htdocs/bi_charts/`: the page, ECharts and its licenses | Both serve `~/local/share/check_mk/web/htdocs` at `/<site>/check_mk/local/` |
| `gui` | `dashboard/bi_charts` | Packaged dashboard in the 2.4 format, which 2.5 converts when loading |

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
  request per aggregation, `by=group` one per group. Raise `refresh` or narrow the filter on large setups.
- **Internals:** the tree endpoint, the packaged dashboard format and the local
  htdocs path are not public interfaces. `version.usable_until` is therefore
  set to 2.6.0; they were only checked for 2.4 and 2.5.
- **Touch devices:** the hover details need a pointer.
- When a request fails, the page shows the error and removes the chart, so that
  outdated data is never mistaken for the current state.

## Tests

```
npm ci                             # the chart library, which the MKP ships
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-test.txt
playwright install chromium        # or: pytest --browser-channel chrome

python3 -m pytest                  # unit tests, a few seconds
python3 -m pytest tests/integration   # real Checkmk 2.4 and 2.5 in Docker
```

| Suite | What it checks | Needs |
|-------|----------------|-------|
| `tests/unit/test_package.py` | package sources and the built MKP | nothing |
| `tests/unit/test_page.py` | every view in a real browser, against a stand-in for the Checkmk endpoints | a browser, `npm ci` |
| `tests/integration/test_checkmk.py` | install, both endpoints with a session cookie, the dashboard and the page in a browser, on 2.4 and on 2.5 | Docker |
| `tests/integration/test_update.py` | the same site updated from 2.4 to 2.5 | Docker |

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

| Job | What it does |
|-----|--------------|
| `unit` | the unit tests, and the MKP, kept as the run's artifact for 14 days |
| `integration (Checkmk 2.4)` | `test_checkmk.py` on a 2.4 site |
| `integration (Checkmk 2.5)` | `test_checkmk.py` on a 2.5 site |
| `integration (update 2.4 to 2.5)` | `test_update.py` |
| `release` | for a tag only, once all of the above passed: the MKP as a release |

Each integration job builds an image with only its versions
(`BI_CHARTS_VERSIONS`, default `2.4 2.5`); a new Checkmk version is one more entry
in the matrix.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). The
release bot tags the releases due from them (`.cz.toml`), writing the version
into `build.py` and the install commands above. The tag runs the whole
pipeline, and its `release` job publishes the MKP with its SHA-256 as a release.
The upload to the [Checkmk Exchange](https://exchange.checkmk.com/) stays by
hand: it has no API, and Checkmk reviews every version. Renovate keeps the test
tools in `requirements-test.txt` and ECharts in `package-lock.json` up to date.

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
npm ci               # ECharts, in the version package-lock.json pins
./build.py           # writes dist/bi_charts-<version>.mkp, no Checkmk site needed
```

The build is reproducible: identical sources give a byte-identical archive.

## License

GPL-2.0-or-later, see [LICENSE](LICENSE) (the text of version 2).

The package includes [Apache ECharts](https://echarts.apache.org/) under the
Apache License 2.0, and zrender, which ECharts bundles, under the BSD 3-Clause
license; their license texts and notice ship beside the page
(`LICENSE-echarts.txt`, `NOTICE-echarts.txt`, `LICENSE-zrender.txt`). The
Apache License 2.0 is compatible with version 3 of the GPL, not with version 2
alone, which is why the package is GPL-2.0-or-later.
