"""Prepare the requested project text, tabs and documentation without publishing."""
from pathlib import Path

web = Path('web')
for name in ['index.html', 'explore.html']:
    path = web / name
    text = path.read_text(encoding='utf-8')
    nav_end = '</a></nav>'
    nav_start = text.index('<nav class="archive-nav"')
    nav_close = text.index('</nav>',nav_start)
    if 'technical.html' not in text[nav_start:nav_close]:
        text = text[:nav_close] + '<a href="technical.html">Technical note</a>' + text[nav_close:]
    if name == 'index.html':
        text = text.replace('src="app.mjs"', 'src="app.mjs?v=show-links-1"')
        if 'href="search-ui.css"' not in text:
            text = text.replace('<link rel="stylesheet" href="explore.css">','<link rel="stylesheet" href="explore.css">\n  <link rel="stylesheet" href="search-ui.css">')
        if 'class="graph-hint"' not in text:
            marker = '    <div class="workspace">'
            hint = '''    <div class="graph-hint"><div class="connections" aria-label="Example graph: a show links to songs and cities"><span>Song</span> ← performed — <span>Show</span> — happened_in → <span>City</span></div><p>A show connects to its listed songs, venue, location, and opening acts. Select multiple entities to find shows linked to all of them. <a href="technical.html#search">How search works →</a></p></div>\n'''
            if marker not in text: raise ValueError('Expected search layout marker')
            text = text.replace(marker,hint+marker,1)
    path.write_text(text,encoding='utf-8')

root = Path('D:/aaron-martin-phd.dev')
project = root / 'homelab/index.qmd'
text = project.read_text(encoding='utf-8')
if '{#fugazi-live-series}' not in text:
    project.write_text(text.rstrip()+'\n\n'+Path('docs/fugazi-project.qmd').read_text(encoding='utf-8'),encoding='utf-8')
for name in ['index.html','explore.html','app.mjs','search-ui.css','technical.html','technical.css']:
    (root/'fugazi'/name).write_text((web/name).read_text(encoding='utf-8'),encoding='utf-8')

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
if not text.startswith('# Fugazi Live Series'):
    text = '# Fugazi Live Series: search and explore\n\n'+text
text = text.replace('[Live archive search](https://aaron-martin-phd.dev/fugazi/)', '[Search](https://aaron-martin-phd.dev/fugazi/) · [Explore](https://aaron-martin-phd.dev/fugazi/explore.html) · [Technical note](https://aaron-martin-phd.dev/fugazi/technical.html)')
text = text.replace('![Fugazi Live archive search showing Berlin results and a published setlist](docs/fugazi-live.png)','<img src="docs/fugazi-search.png" width="900" alt="Fugazi Live archive search, cropped immediately after the search bar">')
text = text.replace('# Fugazi Live Series metadata map','## Archive metadata and provenance')
marker = '## Setup\n'
if '## Current features' not in text:
    overview = '''## Current features

The public site is live on the owner's Quarto / GitHub Pages website. Python builds the graph; plain JavaScript searches and summarizes it in the visitor's browser. There is no production database, backend, LLM, embedding model or inference service.

| View | What it does |
| --- | --- |
| Search | Match songs, shows, places, venues and opening acts; intersect multiple selections; filter by year/country; inspect ordered setlists and follow original Dischord links. Each show now has a shareable URL and a visible Setlist control. |
| Explore | Top 20 release-matched songs by distinct shows; city map with region views; opening-act network with weighted shared-bill connections. Shared year/country filters apply to all three. |
| Technical note | Collection, provenance, graph schema, exact search behavior, metric definitions, validation and Neo4j visualization limits. |

The current graph has **3,529 nodes and 31,260 edges**, covering **1,049 shows from 1987–2002**, **159 song/track labels**, and **24,562 listed track occurrences**. There are 97 shows without listed setlists and 69 labels requiring review; missing data remains unknown. The map covers 1,025 shows across 400 matched city records; 24 shows / 19 unresolved locations remain unplotted.

<table><tr><td><img src="docs/fugazi-map.png" width="440" alt="European show map with country borders"></td><td><img src="docs/fugazi-openers.png" width="440" alt="Opening-act network with node areas based on appearances with Fugazi"></td></tr><tr><td>Derived city coordinates; modern borders only in regional maps.</td><td>Node area = appearances with Fugazi; links = shared bills.</td></tr></table>

Search reads the full graph; the opener visualization is a derived slice, not a drawing of the entire database. Text matching is deterministic, with exact entity names, explicit selections and substring fallback—not semantic similarity. Selecting five songs returns the shows linked to all five. Exclusions, free-form instructions and track-order queries are not implemented.

Read [why I built this](https://aaron-martin-phd.dev/homelab/#fugazi-live-series) for the personal story. This is an independent fan project, unaffiliated with Fugazi or Dischord Records. Recordings and purchases stay with Dischord.

'''
    text = text.replace(marker,overview+marker,1)
text = text.replace('node --test web/graph.test.mjs web/metrics.test.mjs','node --test web/graph.test.mjs web/metrics.test.mjs web/map-projection.test.mjs')
if '### Exploring the full network' not in text:
    anchor = '## Regression tests and normalization review'
    section = '''### Exploring the full network

The complete graph is available for local analysis and as downloadable JSON. Neo4j Browser's display limits are separate from database/import limits: [current documentation](https://neo4j.com/docs/browser/operations/browser-settings/) lists default limits of 1,000 visualized nodes and 1,000 fetched records; [legacy versions](https://neo4j.com/docs/browser/legacy/operations/browser-settings/) use an initial 300-node display limit. Check the installed version and settings before diagnosing a truncated picture.

Verify import totals against the Neo4j manifest in table view, then explore a bounded neighborhood or time range. Aggregate/table queries should answer full-dataset questions; a rendered slice should not be used to infer totals. The [technical note](https://aaron-martin-phd.dev/fugazi/technical.html#full-network) includes example Cypher queries. A general expandable full-graph viewer is not implemented.

'''
    text = text.replace(anchor,section+anchor,1)
readme.write_text(text,encoding='utf-8')
print('Prepared three-tab navigation, search affordances, technical note, project story and README.')
