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
- Viewers need access to BI and the permission to see packaged dashboards

## Install

As the site user:

```
mkp add bi_pie-0.3.0.mkp
mkp enable bi_pie 0.3.0
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
| `theme`   | `dark` (default) or `light` |
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

## Status

Verified without a Checkmk site:

- the archive is accepted by Checkmk's own MKP manifest parser (2.5 source)
- both views render correctly against mocked responses
- the response shapes the page parses match the 2.4 and 2.5 sources

Still to verify on live 2.4 and 2.5 sites:

- [ ] `mkp add` / `mkp enable` install both files
- [ ] the REST endpoint accepts the GUI session cookie
- [ ] both endpoints answer as the sources suggest (`debug=1` shows the REST one)
- [ ] the layered view loads at an acceptable speed with real aggregation counts
- [ ] the packaged dashboard appears, and on 2.5 its widget is converted
- [ ] the list links open the right BI view
- [ ] the package survives the update from 2.4 to 2.5

`version.usable_until` is set to 2.6.0 because the packaged dashboard format,
the local htdocs path and the tree endpoint are Checkmk internals that were
only checked against the 2.4 and 2.5 sources.

## Build and test

```
./build.py           # writes dist/bi_pie-<version>.mkp, no Checkmk site needed
python3 -m pytest
```

The build is reproducible: identical sources give a byte-identical archive.

## License

GPL-2.0, see [LICENSE](LICENSE).
