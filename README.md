# bi_pie: BI aggregation state pie for Checkmk

A dashboard element that shows the state distribution of Checkmk BI
aggregations as a pie chart, with a list of the aggregations that are not OK.
An optional layered view adds one ring per level of the BI tree, down to hosts
and services.
Checkmk has no pie chart for BI and no way to add custom widget types in 2.5,
so this package embeds a small static page instead.

![Widget with sample data](docs/screenshot.png)

![Layered view with sample data](docs/screenshot-tree.png)

![Hover details with sample data](docs/screenshot-hover.png)

*All rendered from the page with sample data, not taken from a live site.*

## Requirements

- Checkmk 2.4.0 or 2.5.0, any edition
- Viewers need access to BI. The shipped dashboard is a packaged one; with
  Checkmk's default permissions every role may see it.

## Install

As the site user:

```
mkp add bi_pie-0.4.0.mkp
mkp enable bi_pie 0.4.0
```

The package then provides:

- the dashboard **BI aggregation states** (`dashboard.py?name=bi_pie`)
- the page `local/bi_pie/index.html`, for use in your own dashboards

## Use it in your own dashboards

Add a custom URL element (2.4) or an Embed URL widget (2.5) with a
site-relative URL:

```
local/bi_pie/index.html?group=WebApp&title=Web%20applications
```

| Parameter | Meaning |
|-----------|---------|
| `group`   | BI aggregation group to include, repeatable |
| `name`    | Aggregation title to include, repeatable |
| `title`   | Heading above the chart |
| `refresh` | Reload interval in seconds, default 60, `0` disables |
| `theme`   | `dark` or `light`; default: the Checkmk theme of the embedding page |
| `list=0`  | Hide the list of non-OK aggregations |
| `debug=1` | Show the raw REST API response |
| `view=tree` | Layered view, see below |
| `depth`   | Layered view: number of rings, default 3 |
| `max`     | Layered view: most aggregations to load, default 40 |

Clicking a slice or a legend row narrows the list to that state. Each entry
links to the aggregation's BI view.

## Hover details and legend

Hovering shows a details box next to the pointer:

- **Slice or legend row:** the state's count and share, and the aggregations in
  that state with their acknowledged / downtime flags (the first eight, then a
  count of the rest).
- **Ring segment (layered view):** the path down to the node, its state and
  flags, whether it is a rule (with BI pack and rule ID), a host or a service,
  and how many hosts and services sit below it per state.

Hovering a legend row also fades every slice and segment of another state.

The legend lists each state's aggregation count and share. In the layered view
it adds a column with the hosts and services per state across all loaded trees.

## Layered view

```
local/bi_pie/index.html?view=tree&group=WebApp
local/bi_pie/index.html?view=tree&depth=4&name=Payment%20API
```

The innermost ring holds one equal segment per aggregation, in the same order
as the flat pie. Each further ring is the next level of the BI tree: the rules
an aggregation is built from, the rules those call (also across BI packs), and
finally hosts and services. Children share their parent's angle by the number
of hosts and services below them, and every segment has the color of its own
state, so a problem can be followed from the outside in.

Clicking a segment keeps its path, state and, for rules, the BI pack and rule
ID on display below the chart.

Loading a tree takes one request per aggregation on every refresh. Above `max`
aggregations the page shows the flat pie and says so, instead of drawing a
partial set of trees.

## How it works

The page calls
`GET /api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke`
with the viewer's GUI session, so every user sees only the aggregations they
are permitted to see. No data is stored and no automation user is needed.

That endpoint only reports the nodes that have a problem, so the layered view
also calls `ajax_fetch_aggregation_data.py`, the GUI endpoint behind Checkmk's
own BI visualization, once per aggregation. It is not a public API; it is the
same in the 2.4 and 2.5 sources.

One package covers both versions because it avoids version-specific code:

| Part  | Content | Why it works on 2.4 and 2.5 |
|-------|---------|-----------------------------|
| `web` | `htdocs/bi_pie/index.html` | Both serve `~/local/share/check_mk/web/htdocs` at `/<site>/check_mk/local/` |
| `gui` | `dashboard/bi_pie` | Packaged dashboard in the 2.4 format, which 2.5 converts when loading |

Dashboard filters do not reach the page, because the embed element does not
pass them on. Put the filter into the URL instead.

## Known limitations

- **Duplicate titles:** Checkmk's state endpoint keys aggregations by title, so
  two aggregations with the same title count as one.
- **Ring proportions:** the innermost ring gives every aggregation the same
  angle, outer rings divide by hosts and services. Segment sizes are therefore
  not comparable across rings.
- **Load:** every open widget asks once per refresh, and each request makes
  Checkmk compute all matching aggregations; the layered view adds one request
  per aggregation. Raise `refresh` or narrow the filter on large setups.
- **Internals:** the tree endpoint, the packaged dashboard format and the local
  htdocs path are not public interfaces. `version.usable_until` is therefore
  set to 2.6.0; they were only checked for 2.4 and 2.5.
- **Touch devices:** the hover details need a pointer.
- When a request fails, the page shows the error and removes the chart, so that
  outdated data is never mistaken for the current state.

## Tests

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-test.txt
playwright install chromium        # or: pytest --browser-channel chrome

python3 -m pytest                  # unit tests, a few seconds
python3 -m pytest tests/integration   # real Checkmk 2.4 and 2.5 in Docker
```

| Suite | What it checks | Needs |
|-------|----------------|-------|
| `tests/unit/test_package.py` | package sources and the built MKP | nothing |
| `tests/unit/test_page.py` | the page in a real browser, against a stand-in for the Checkmk endpoints | a browser |
| `tests/integration/test_checkmk.py` | install, both endpoints with a session cookie, the dashboard and the page in a browser, on 2.4 and on 2.5 | Docker |
| `tests/integration/test_update.py` | the same site updated from 2.4 to 2.5 | Docker |

The integration tests install Checkmk from its own packages: the newest patch
release of 2.4 (Raw edition) and of 2.5 (Community edition), as listed in
[stable_downloads.json](https://download.checkmk.com/stable_downloads.json),
for Debian 12. Each package is checked against the SHA-256 given there and kept
in `~/.cache/bi-pie` (`BI_PIE_CACHE`). Both go into one Docker image
(`tests/integration/image/Dockerfile`), built on the first run (about 600 MB of
downloads, several minutes) and again only for a new patch release. Every test
module creates its sites in containers of that image; the update test runs
`omd update` in the container of the 2.4 site, as on a server.
`BI_PIE_PACKAGE_2_4` and `BI_PIE_PACKAGE_2_5` name a package file to use
instead, e.g. an older patch release.

## CI and releases

`.forgejo/workflows/ci.yml` runs the unit tests, builds the MKP (kept as the
run's artifact for 14 days) and then runs the integration tests, on every push
to `main`, every pull request and every Monday, so that a new Checkmk patch
release is tested before anyone updates to it.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). The
release bot tags the releases due from them (`.cz.toml`), writing the version
into `build.py` and the install commands above; the tag then publishes the MKP
with its SHA-256 as a release (`.forgejo/workflows/release.yml`). Renovate keeps
the test tools in `requirements-test.txt` up to date.

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
./build.py           # writes dist/bi_pie-<version>.mkp, no Checkmk site needed
```

The build is reproducible: identical sources give a byte-identical archive.

## License

GPL-2.0, see [LICENSE](LICENSE).
