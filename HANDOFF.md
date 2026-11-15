# Project handoff: Fugazi Live Series map

## Goal

Create a browsable map of Fugazi performances using metadata published in Dischord Records' Fugazi Live Series archive. The key use case is finding different performances of a song and seeing when and where each one was played. Opening acts are part of the dataset too.

The project maps what Dischord provides. Missing archive fields are acceptable; do not fill gaps from other sources unless that scope changes. Do not download or stream music. Keep collection focused on public metadata and HTML pages.

## Current repo

- Git remote: `https://github.com/AaronMartin78/Fugazi_Live.git`
- Python environment and dependencies are managed with `uv`.
- `scrape_fugazi.py` crawls the archive itinerary and linked show pages.
- `build_graph.py` converts the show records into nodes and edges.
- `data/` and `.cache/` are ignored by Git. The scraped data is local unless deliberately added elsewhere.

## Current scrape

The most recent crawl found 1,049 show entries:

- 1,049 with a Dischord show ID, date, venue, city, and country
- 952 with setlists, containing 24,562 ordered track entries
- 967 with listed opening acts
- Graph export: 3,397 nodes and 28,310 edges

Generated files:

- `data/fugazi_shows.json` — source-shaped show records
- `data/fugazi_graph.json` — graph nodes and relationships

These files are ignored and should be regenerated if absent. The crawler caches HTML under `.cache/dischord`; a repeat run can use that cache. Its default delay is one second per uncached page. It checks the live `robots.txt` before crawling and requests HTML only.

## Data shape

Each show JSON record includes:

- `show_id`, the Dischord `FLS` identifier
- `slug`, the show-page URL slug
- `event_date` in ISO `YYYY-MM-DD` format
- `venue`, `city`, `subdivision`, and `country`
- `opening_acts` and `opening_acts_as_listed`
- `setlist`, an ordered list of `{position, title}` entries
- `source_url` and `listing_url`

The graph has `nodes` and `edges`. Show nodes connect to song nodes through `performed` edges, with track order on the edge. Shows also connect to venue, place, and opening-act nodes.

Keep each listed track title available as source data. The graph exporter currently creates song IDs by slugifying titles; this normalizes case and punctuation and may combine spellings that should remain distinct. If building canonical song identities or aliases, preserve the original title and make merges explicit and reviewable.

## Run commands

From the repository root in PowerShell:

```powershell
uv sync
uv run python scrape_fugazi.py
uv run python build_graph.py
```

Optional scrape settings:

```powershell
uv run python scrape_fugazi.py --output data/fugazi_shows.json --cache-dir .cache/dischord --delay 1.0
```

The full uncached scrape takes time because the crawler visits over a thousand show pages at a polite pace. Network access is required for a fresh crawl and dependency resolution.

## Future viewer direction

Build a local browser-based viewer that reads the generated JSON and supports:

1. Search for a song and list its performances by date.
2. Open a show to see the complete setlist in order, venue, city, country, and opening acts.
3. Filter by year, country, city, venue, and opening act.
4. Explore results on a timeline and map, with a network graph as an additional view.

The archive provides place names but not coordinates. Any geocoding should be a separate derived dataset with its own provenance; do not overwrite the archived city/country values. A map also needs a tile/source choice if it uses online map tiles. Keep the viewer local and do not add audio playback or download links.

## Possible Gephi path

Gephi is useful for exploratory network layouts and analysis. The current custom `fugazi_graph.json` is not a Gephi interchange format. If needed, add a separate GEXF exporter with show dates, places, and track positions as attributes. A temporal Gephi graph will need performance edges to carry a date or timestamp; the current graph only places dates on show nodes.

## Not implemented yet

- Obsidian Markdown-note export
- Gephi GEXF export
- Local interactive map/timeline/search viewer
- Geocoded coordinates
- Explicit canonical song/alias review workflow
