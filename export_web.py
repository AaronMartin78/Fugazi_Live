"""Export the validated graph for a static browser application, without a database."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_graph import graph_for, load_shows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('data/web'))
    args = parser.parse_args()
    shows = load_shows(Path('data/fugazi_shows.json'))
    graph = json.loads(Path('data/fugazi_graph.json').read_text(encoding='utf-8'))
    if graph != graph_for(shows):
        raise ValueError('Saved graph differs from source records: rebuild before exporting')
    ids = {n['id'] for n in graph['nodes']}
    if len(ids) != len(graph['nodes']):
        raise ValueError('Duplicate node ID')
    if any(e['source'] not in ids or e['target'] not in ids for e in graph['edges']):
        raise ValueError('Dangling edge')
    payload = (json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    manifest = dict(schema_version=graph['schema_version'],
                    counts=dict(Counter(n['type'] for n in graph['nodes'])),
                    edges=len(graph['edges']),
                    date_range=[min(s['event_date'] for s in shows), max(s['event_date'] for s in shows)],
                    bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                    provenance='Dischord Fugazi Live Series public HTML metadata; gaps preserved as published.',
                    caveat='Track entities include intros, interludes, variants, and labels pending identity review.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'data.json').write_bytes(payload)
    (args.output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
