"""Build separate city-coordinate enrichment from GeoNames, never alter archive fields."""
import argparse
from datetime import datetime, timezone
from collections import defaultdict, Counter
import hashlib
import io
import json
from pathlib import Path
import unicodedata
import zipfile

import requests

CACHE = Path('.cache/geography')
COUNTRIES = dict(USA='US', Canada='CA', Australia='AU', Argentina='AR', Austria='AT',
    Belgium='BE', Brazil='BR', Chile='CL', Denmark='DK', England='GB', Finland='FI',
    France='FR', Germany='DE', Hungary='HU', Iceland='IS', Ireland='IE', Italy='IT',
    Japan='JP', Malaysia='MY', Netherlands='NL', Norway='NO', Poland='PL', Portugal='PT',
    Scotland='GB', Singapore='SG', Slovenia='SI', Spain='ES', Sweden='SE', Switzerland='CH', Wales='GB')
COUNTRIES.update({'Czech Republic':'CZ', 'Czechoslovakia':'CZ', 'Hong Kong':'HK',
    'New Zealand':'NZ', 'Northern Ireland':'GB', 'Spain/Basque':'ES', 'Yugoslavia':'SI'})
CANADA = dict(AB='01',BC='02',MB='03',NB='04',NS='07',ON='08',QC='10',SK='11')
AUSTRALIA = dict(NSW='02',QLD='04',SA='05',TAS='06',VIC='07')
SOURCES = {
    'cities5000.zip':'https://download.geonames.org/export/dump/cities5000.zip',
    'land.geojson':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson',
    'borders.geojson':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_boundary_lines_land.geojson',
}

def key(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if not unicodedata.combining(c)).split())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        path = CACHE / name
        if args.download or not path.exists():
            response = requests.get(url, timeout=90)
            response.raise_for_status()
            path.write_bytes(response.content)
    gazetteer = defaultdict(dict)
    with zipfile.ZipFile(io.BytesIO((CACHE/'cities5000.zip').read_bytes())) as archive:
        for line in archive.read('cities5000.txt').decode('utf-8').splitlines():
            fields = line.split('\t')
            if fields[7] in ('PPLX', 'PPLH', 'PPLQ', 'PPLW'):
                continue
            row = dict(geonames_id=fields[0], name=fields[1], ascii_name=fields[2], latitude=float(fields[4]),
                       longitude=float(fields[5]), country_code=fields[8], admin1=fields[10])
            for name in {fields[1], fields[2], *fields[3].split(',')}:
                if name: gazetteer[(fields[8], key(name))][fields[0]] = row
    graph = json.loads(Path('data/fugazi_graph.json').read_text(encoding='utf-8'))
    shows_by_city = defaultdict(list)
    for node in graph['nodes']:
        if node['type'] == 'show' and node['city_id']:
            shows_by_city[node['city_id']].append(node)
    matches, unresolved = [], []
    for city_id, shows in sorted(shows_by_city.items()):
        raw = shows[0]['location_as_listed']
        country = COUNTRIES.get(raw['country'])
        country_codes = {'Yugoslavia':['SI','HR','RS','BA','ME','MK','XK'], 'Czechoslovakia':['CZ','SK']}.get(raw['country'], [country])
        candidates = [row for code in country_codes for row in gazetteer.get((code, key(raw['city'])), {}).values()]
        admin = (raw.get('subdivision') or '').strip()
        if country == 'US' and admin:
            candidates = [row for row in candidates if row['admin1'] == admin]
        elif country == 'CA' and admin:
            candidates = [row for row in candidates if row['admin1'] == CANADA.get(admin)]
        elif country == 'AU' and admin:
            candidates = [row for row in candidates if row['admin1'] == AUSTRALIA.get(admin)]
        # UK constituent-country names are retained in the archive but constrain current coordinates.
        elif country == 'GB':
            admin_code = {'England':'ENG','Scotland':'SCT','Wales':'WLS','Northern Ireland':'NIR'}[raw['country']]
            candidates = [row for row in candidates if row['admin1'] == admin_code]
        primary = [row for row in candidates if key(raw['city']) in (key(row['name']), key(row['ascii_name']))]
        if primary:
            candidates = primary
        if len(candidates) == 1:
            matches.append(dict(city_id=city_id, archive_city=raw['city'], archive_country=raw['country'],
                                method='unique exact normalized primary name, else unique alias, within country/subdivision',
                                **candidates[0]))
        else:
            unresolved.append(dict(city_id=city_id, city=raw['city'], country=raw['country'],
                                   subdivision=admin, shows=len(shows),
                                   reason='ambiguous' if candidates else 'no exact match',
                                   candidates=[dict(name=c['name'],geonames_id=c['geonames_id'],admin1=c['admin1']) for c in candidates[:8]]))
    output = dict(generated_at=datetime.now(timezone.utc).isoformat(), source='GeoNames cities5000', source_url=SOURCES['cities5000.zip'],
                  license='CC BY 4.0', attribution_url='https://www.geonames.org/',
                  gazetteer_sha256=hashlib.sha256((CACHE/'cities5000.zip').read_bytes()).hexdigest(),
                  land_source_url=SOURCES['land.geojson'], land_license='public domain',
                  note='Derived city centers, not venue coordinates. Exact gazetteer matches are not manual verification. Historical archive labels are unchanged; current coordinates use modern country codes.',
                  cities=matches, unresolved=unresolved)
    Path('web/cities.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    land = json.loads((CACHE/'land.geojson').read_text(encoding='utf-8'))
    # Keep just geometry: no political borders or unrelated feature properties.
    geometry = dict(type='FeatureCollection', features=[dict(type='Feature',properties={},geometry=f['geometry']) for f in land['features']])
    Path('web/land.json').write_text(json.dumps(geometry,separators=(',',':'))+'\n',encoding='utf-8')
    borders = json.loads((CACHE/'borders.geojson').read_text(encoding='utf-8'))
    lines = dict(type='FeatureCollection', source_url=SOURCES['borders.geojson'], license='public domain',
                 features=[dict(type='Feature',properties={},geometry=f['geometry']) for f in borders['features']])
    Path('web/borders.json').write_text(json.dumps(lines,separators=(',',':'))+'\n',encoding='utf-8')
    print(f'{len(matches)} cities matched; {len(unresolved)} unresolved; {sum(len(shows_by_city[c["city_id"]]) for c in matches)} shows mapped')
    print(json.dumps(unresolved,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
