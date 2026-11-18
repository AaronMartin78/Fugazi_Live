# Map data and provenance

Archive city, subdivision and country strings remain unchanged in the graph.
`cities.json` is a separate derived coordinate layer produced by `build_map.py`.
It records the matched GeoNames ID, coordinates, country/admin code, matching
method and source checksum; unmatched or ambiguous city records are retained
in `unresolved`. The build timestamp and source URLs are recorded in the file.

## Sources and licenses

- GeoNames cities5000 worldwide gazetteer: https://download.geonames.org/export/dump/cities5000.zip
- GeoNames format/license: https://download.geonames.org/export/dump/readme.txt
- Attribution: GeoNames, https://www.geonames.org/ — CC BY 4.0.
- Land geometry: Natural Earth 1:110m land, public domain;
  https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson
- Natural Earth terms: https://www.naturalearthdata.com/about/terms-of-use/

`land.json` strips unrelated feature properties. Regional views add modern
country boundary lines from Natural Earth's 1:110m admin-0 land boundaries,
also public domain, via `borders.json`. These lines are for orientation and do
not relabel the historical archive or assert historical borders.
Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_boundary_lines_land.geojson

The world overview keeps its equirectangular projection and has no country
borders. Regional views use Mercator with a uniform horizontal/vertical scale
fitted within the map, avoiding independently stretched continental outlines.
No tiles, external geocoding calls, or third-party scripts load at runtime.

## Coordinate matching

Names normalize Unicode accents, case and whitespace. Matches are constrained
to the recorded country and, where available, supported subdivision codes.
A unique primary name (including the gazetteer's ASCII form) takes precedence
over aliases; otherwise only a unique alias match is accepted. Historical
Czechoslovakia and Yugoslavia labels search their successor-country candidates;
UK constituent-country labels constrain the country subdivision. None of this
renames the archived fields. Conflicting or unknown subdivisions are unresolved.
These are gazetteer matches, not manually verified venue positions.

Current output: 400 of 419 archive city records matched, covering 1,025 of 1,049
shows. The other 19 city records / 24 shows remain unplotted and are listed in
the interface. Some labels describe neighborhoods, islands, small settlements
or misspellings absent from this gazetteer. Coordinates are not guessed.

Markers combine records only when they resolve to the same GeoNames city ID.
Their show lists retain the separate archive identities. Region selection
changes the viewport, not the year/country scope; map coverage reports the
entire filtered scope. Circle area scales to the largest count in the region.
