Fugazi is my favorite band. Ian MacKaye is a legend. I am trying to build a Knowledge Graph that will let people identify which songs were played in which sets. I don't know, it might also look cool when it it finished.

Go and visit [Dischord Records](https://dischord.com/) and find some good music.

# Fugazi Live Series metadata map

Collects metadata from the public [Fugazi Live Series archive](https://dischord.com/fugazi_live_series) and converts it into a simple graph JSON file. The crawler requests HTML pages only. It does not request audio, samples, images, or purchase/download endpoints.

The collected fields prioritize the show ID, date, venue, city, subdivision, country, opening acts, ordered setlist, and source page URLs. Missing fields are left empty; the archive is mapped as published rather than filled from outside sources.

## Setup

```powershell
uv sync
```

## Collect show metadata

```powershell
uv run python scrape_fugazi.py
```

The default output is `data/fugazi_shows.json`. HTML responses are cached in `.cache/dischord` so interrupted or repeated runs can reuse pages. The crawler reads `robots.txt` before making archive requests and uses a one-second delay before each uncached page request.

Options:

```powershell
uv run python scrape_fugazi.py --output data/fugazi_shows.json --cache-dir .cache/dischord --delay 1.0
```

## Build graph data

```powershell
uv run python build_graph.py
```

The default output is `data/fugazi_graph.json` (schema version 2), with `nodes`, `edges`, and an album palette. Each show links to separate country, state/subdivision, city, and venue nodes. Locations have deterministic UUID-based IDs scoped by their parent locations. Missing levels remain missing; historical country labels stay as published.

Songs use explicit IDs and canonical display titles from the tracked `catalog.json`. Editing a song's title while keeping its ID preserves identity. Case, Unicode composition, and whitespace normalize automatically; punctuation is preserved unless an explicit alias says otherwise. Venue display names normalize whitespace and case variants within the same location. Substantive spelling changes and cross-city venue aliases require review, rather than fuzzy matching. Original location text stays on show nodes; every performance edge retains its original title and position.

Album grouping follows the first official release, with **13 Songs** combining the first two EPs by project preference. Its color is dark pink/purple (`#8B2F60`). Other colors are editable cover-inspired drafts. Verified release matches have album IDs and colors; unverified tracks use neutral gray. Live instrumental variants and generic labels such as Intro remain separate and need review rather than automatically inheriting an album. The catalog stores official Fugazi Bandcamp source URLs for release matches; this is derived enrichment separate from the untouched archive records.

Schema 2 replaces the original slug IDs and combined place nodes. Regenerate downstream exports; old graph IDs are not compatible. Location aliases can be configured in `catalog.json`: each key is a JSON array of parent IDs (or `missing:<type>` markers) followed by the normalized raw name, and its value is the canonical name. Canonical location renames change derived IDs, so add aliases and rebuild dependent exports together. Song IDs are stored and must not be regenerated when changing display labels.

## Regression tests and normalization review

```powershell
uv run python -m unittest -v
uv run python audit_graph.py
```

The audit checks unique IDs, valid edge endpoints, preservation of all performances, and deterministic output independent of show order. It writes `data/normalization_review.json` with unmatched track labels and standardized location variants. The tests use synthetic shows and HTML and require no crawl or local dataset.

Before visualization, review uncertain track identities, assign their release groups where supported, and confirm the cover palette. Unknown does not mean unreleased; covers, unreleased songs, and spoken/interlude labels need explicit classification. A viewer should show album labels alongside color so meaning does not depend on color alone.
