# bi_pie: BI aggregation state pie for Checkmk

A dashboard element that shows the state distribution of Checkmk BI
aggregations as a pie chart, with a list of the aggregations that are not OK.
Checkmk has no pie chart for BI and no way to add custom widget types in 2.5,
so this package embeds a small static page instead.

![Widget with sample data](docs/screenshot.png)

*Rendered from the page with sample data, not taken from a live site.*

## Requirements

- Checkmk 2.4.0 or 2.5.0, any edition
- Viewers need access to BI and the permission to see packaged dashboards

## Install

As the site user:

```
mkp add bi_pie-0.1.0.mkp
mkp enable bi_pie 0.1.0
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

Clicking a slice or a legend entry narrows the list to that state. Each entry
links to the aggregation's BI view.

## How it works

The page calls
`GET /api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke`
with the viewer's GUI session, so every user sees only the aggregations they
are permitted to see. No data is stored and no automation user is needed.

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
- the page renders correctly against a mocked REST response

Still to verify on live 2.4 and 2.5 sites:

- [ ] `mkp add` / `mkp enable` install both files
- [ ] the REST endpoint accepts the GUI session cookie
- [ ] the response has the shape the page expects (`debug=1` shows it)
- [ ] the packaged dashboard appears, and on 2.5 its widget is converted
- [ ] the list links open the right BI view
- [ ] the package survives the update from 2.4 to 2.5

`version.usable_until` is set to 2.6.0 because the packaged dashboard format
and the local htdocs path are Checkmk internals that were only checked against
the 2.4 and 2.5 sources.

## Build and test

```
./build.py           # writes dist/bi_pie-<version>.mkp, no Checkmk site needed
python3 -m pytest
```

The build is reproducible: identical sources give a byte-identical archive.

## License

GPL-2.0, see [LICENSE](LICENSE).
