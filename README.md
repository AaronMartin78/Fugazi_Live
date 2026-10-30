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

The default output is `data/fugazi_graph.json`, with `nodes` and `edges`. Each show connects to its venue and place, its setlist songs in position order, and any listed opening acts. Song nodes use the listed title as their initial identity; ambiguous titles are not automatically merged.
