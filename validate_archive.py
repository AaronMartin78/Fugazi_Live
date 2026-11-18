"""Compare the saved graph and source records with cached Dischord HTML."""
import json
import re
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from build_graph import graph_for
from scrape_fugazi import detail_fields


def main():
    shows = json.loads(Path('data/fugazi_shows.json').read_text(encoding='utf-8'))
    graph = json.loads(Path('data/fugazi_graph.json').read_text(encoding='utf-8'))
    errors, mismatches, missing_cache, bad_positions = [], [], [], []
    for field in ('show_id', 'source_url', 'slug'):
        for value, count in Counter(s.get(field) for s in shows).items():
            if not value or count > 1:
                errors.append(dict(field=field, value=value, count=count))
    checked = 0
    for index, show in enumerate(shows, 1):
        url = urlparse(show['source_url'])
        if (url.scheme != 'https' or url.netloc != 'dischord.com'
                or url.path != '/fugazi_live_series/' + show['slug']
                or url.query or url.fragment):
            errors.append(dict(show_id=show['show_id'], field='source_url'))
        try:
            date.fromisoformat(show['event_date'])
        except (ValueError, TypeError):
            errors.append(dict(show_id=show['show_id'], field='event_date'))
        tracks = show['setlist']
        if [t['position'] for t in tracks] != list(range(1, len(tracks) + 1)):
            bad_positions.append(show['show_id'])
        filename = re.sub(r'[^A-Za-z0-9._-]+', '_', url.path.strip('/')) + '.html'
        cache = Path('.cache/dischord') / filename
        if not cache.exists():
            missing_cache.append(show['show_id'])
            continue
        checked += 1
        fields = detail_fields(BeautifulSoup(cache.read_text(encoding='utf-8'), 'html.parser'))
        for field, value in fields.items():
            if field == 'setlist':
                value = [asdict(track) for track in value]
            if show.get(field) != value:
                mismatches.append(dict(show_id=show['show_id'], field=field))
        if not fields.get('show_id'):
            mismatches.append(dict(show_id=show['show_id'], field='missing cached identity'))
        if index % 200 == 0:
            print(f'Checked {index}/{len(shows)} cached pages', flush=True)
    report = dict(
        shows=len(shows),
        date_range=[min(s['event_date'] for s in shows), max(s['event_date'] for s in shows)],
        node_counts=dict(Counter(n['type'] for n in graph['nodes'])),
        edges=len(graph['edges']), performances=sum(len(s['setlist']) for s in shows),
        shows_without_setlists=[s['show_id'] for s in shows if not s['setlist']],
        missing_field_counts={k: sum(not s.get(k) for s in shows) for k in
                              ('show_id', 'event_date', 'venue', 'city', 'country',
                               'subdivision', 'source_url', 'opening_acts')},
        saved_graph_matches_rebuild=graph == graph_for(shows),
        cached_pages_checked=checked, missing_cache=missing_cache,
        nonsequential_setlists=bad_positions, cached_metadata_mismatches=mismatches,
        errors=errors, live_links_checked=False,
        limitation='Cached HTML comparison uses the existing parser; not an independent parser audit or full live-link check.')
    Path('data/validation_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return int(bool(errors or mismatches or missing_cache or bad_positions
                    or not report['saved_graph_matches_rebuild']))


if __name__ == '__main__':
    raise SystemExit(main())
