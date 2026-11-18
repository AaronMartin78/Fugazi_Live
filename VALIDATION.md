# Archive validation — 2026-11-18

The 23 existing offline regression tests passed. `audit_graph.py` passed its
identity, endpoint, performance-count, and deterministic-build checks.

`validate_archive.py` compared all 1,049 source records with cached Dischord
HTML using the existing parser: zero field mismatches and zero missing cached
pages. The saved graph exactly equals a fresh build from the source records.
This is a consistency check, not an independent audit of the HTML parser.

- Coverage: 1987-09-03 through 2002-11-04.
- 3,529 nodes, 31,260 edges, and 24,562 listed track occurrences.
- 159 song/track entities; 69 labels still require identity/classification review.
- Every show has a unique ID, unique source URL, valid ISO date, venue, city,
  and country. Every source URL has the expected HTTPS Dischord show-page path.
- 97 shows have no published setlist in the collected data; 82 lack listed
  opening acts. Missing subdivision values are not necessarily errors.

## Review findings

Two setlists have nonsequential published numbering. The validator exits 1 to
draw attention to these findings; it does not change the archive data.

- FLS0082, London 1988-11-24: two entries numbered 1, both Intro.
  https://dischord.com/fugazi_live_series/london-england-112488
- FLS0436, Norwich 1992-05-07: numbering jumps from 25 to 27, with a repeated
  closing sequence. https://dischord.com/fugazi_live_series/norwich-england-50792

Both anomalies appear in cached HTML and were also checked against Dischord's
pages through the web tool. Preserve them as published and flag them in the UI.
Statistics must distinguish listed track occurrences from distinct shows.

## Link verification scope

Six Dischord pages were spot-checked through the web tool: FLS0001, FLS0003,
FLS0082, FLS0436, FLS1045, and FLS1055. The web tool may serve previously crawled
content. This does not establish current HTTP availability for all 1,049 URLs.
Per the owner's decision, a random sample replaces a full live-link check.
`check_link_sample.py` selects 20 shows without replacement using seed 20261118,
checks HTTP success and HTML content, and compares the published show ID and
date. Detailed results are saved to `data/link_sample_report.json`.
All 20 sampled pages passed on 2026-11-18: successful HTTP responses, HTML
content, and matching show IDs and dates. No full-archive live check is required.

FLS0003 explicitly states that no recording is available. The app should label
links 'View on Dischord', without implying every show has a purchasable recording.

## Reproduce

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe audit_graph.py
.\.venv\Scripts\python.exe validate_archive.py
```

Detailed generated results: `data/validation_report.json` and
`data/normalization_review.json` (ignored local artifacts).

## Deployed search app

Published at https://aaron-martin-phd.dev/fugazi/ on 2026-11-18, website commit
`98158bfb762d660e34805ac40307fb8ecab33c32`. The existing GitHub Actions render
and Pages deployment both succeeded (run 44372695253).

Six additional JavaScript tests passed: every source show link and ordered
setlist survives the viewer index; combined song/place/year queries and song
intersections match source records; year/setlist filters agree with source;
co-occurrence counts distinct shows; unrelated outbound URLs are rejected.
Browser checks confirmed search, setlists, source links, and song intersections
locally. The live site also returned the expected four Waiting Room/Berlin
matches and displayed the 1995-07-02 TU Mensa show with its original source link.

## Explore metrics

Twelve JavaScript tests now cover search plus the three Explore views. New
checks compare song and opener/pair frequencies with original source records,
verify common country/year scopes, validate the coordinate partition, verify
deterministic finite network layouts and proportional node areas, and exercise
empty selections. Waiting Room appears at 674 distinct shows; Branch Manager
is listed at 33. The coordinate layer covers 1,025 shows, with the other 24
explicitly unplotted. Original archive data and show links are unchanged.

Browser checks exercised song/city/act selections and Dischord links, regional
map changes, desktop and narrow-screen layouts, shared 1995/Germany filters
(9 shows, 9 published setlists, 9 mapped shows), and an empty 1987/Germany
selection. GeoNames (CC BY 4.0) and Natural Earth (public domain) are attributed
on the page and in the bundled geography documentation.

Explore deployed successfully on 2026-11-18 at
https://aaron-martin-phd.dev/fugazi/explore.html (website commit
`bad93e6d5dea714b5ac52202a6f2fa0891f5c6cd`, Actions run 44388370071).
The published page loaded all three views; live selections for Waiting Room,
Washington DC, and Branch Manager displayed their source shows and Dischord links.

## Regional map correction

Regional views now use uniformly scaled Mercator instead of stretching longitude
and latitude independently. Natural Earth country borders appear only in regional
views; the world overview retains its original projection and no borders. Three
focused checks passed for world coordinates, local projection proportions, and
valid border geometry. Browser checks confirmed zero border paths in World and
331 clipped boundary paths in regional views. Modern borders are labeled as
orientation aids, with historical archive country labels preserved.

Deployed via commit `4925dc6a3a978d94af9cbcd64e49b9c8502aebd8`, Actions run
44390482839. A versioned script URL avoids stale browser caches. The live site
was verified with zero World borders and visible Europe borders/projection note.

## Documentation and reviewer improvements

Added the Technical note tab and a Fugazi project section under Homelab/Projects.
README images now use a compact search capture ending after the search bar and
separate map/network crops. The project story received light copy edits, retaining
the author's voice and linking back to Dischord.

Show dates and visible Setlist links open the detail, which now writes a human
show ID into the URL. Reload and browser Back restore the selected show/search.
Details are explicitly beside results on wide screens and above results in a
bounded scrolling panel on narrow screens, with a Back to shows control.
Browser checks passed on four-result and full 1,049-result searches, including
a bare `?show=FLS0927` link. A compact relationship diagram explains the graph
beside Search. All 23 Python and 16 JavaScript checks passed, including a new
five-song intersection comparison against original source records.
