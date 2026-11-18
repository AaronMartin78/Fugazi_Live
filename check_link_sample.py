"""Check a reproducible random sample of Dischord show HTML pages."""
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from scrape_fugazi import USER_AGENT, detail_fields, load_robots


def main():
    shows = json.loads(Path('data/fugazi_shows.json').read_text(encoding='utf-8'))
    seed = 20261118
    sample = random.Random(seed).sample(sorted(shows, key=lambda s: s['show_id']), 20)
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT, 'Accept': 'text/html'})
    robots = load_robots(session)
    results = []
    for show in sample:
        result = dict(show_id=show['show_id'], url=show['source_url'])
        if not robots.can_fetch(USER_AGENT, show['source_url']):
            result.update(ok=False, error='Disallowed by robots.txt')
        else:
            time.sleep(1)
            try:
                response = session.get(show['source_url'], timeout=30)
                result.update(status=response.status_code, final_url=response.url)
                response.raise_for_status()
                if 'text/html' not in response.headers.get('content-type', '').lower():
                    raise ValueError('Expected HTML')
                fields = detail_fields(BeautifulSoup(response.text, 'html.parser'))
                result.update(actual_show_id=fields.get('show_id'),
                              actual_date=fields.get('event_date'),
                              ok=fields.get('show_id') == show['show_id']
                              and fields.get('event_date') == show['event_date'])
            except (requests.RequestException, ValueError) as exc:
                result.update(ok=False, error=str(exc))
        results.append(result)
        print(f"{result['show_id']}: {'PASS' if result['ok'] else 'FAIL'}", flush=True)
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), seed=seed,
                  population=len(shows), sample_size=len(sample), results=results)
    Path('data/link_sample_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return int(any(not r['ok'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
