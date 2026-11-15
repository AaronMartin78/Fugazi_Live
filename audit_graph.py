"""Validate graph integrity and write an actionable local normalization report."""
import argparse
import json
from collections import Counter
from pathlib import Path

from build_graph import graph_for, load_shows


def audit(shows):
    graph = graph_for(shows)
    nodes = {n['id']: n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        raise ValueError('Duplicate entity IDs')
    if any(e['source'] not in nodes or e['target'] not in nodes for e in graph['edges']):
        raise ValueError('Dangling graph edge')
    performances = [e for e in graph['edges'] if e['relation'] == 'performed']
    if len(performances) != sum(len(s.get('setlist', [])) for s in shows):
        raise ValueError('Track count mismatch: empty titles or lost performances')
    if graph != graph_for(list(reversed(shows))):
        raise ValueError('Graph depends on input order')
    return dict(
        counts=dict(Counter(n['type'] for n in nodes.values())),
        performances=len(performances),
        album_matched_performances=sum(bool(nodes[e['target']]['album_id']) for e in performances),
        needs_review=[dict(id=n['id'], title=n['name']) for n in nodes.values()
                      if n['type'] == 'song' and n['review_status'] == 'needs_review'],
        standardized_locations=[n for n in nodes.values()
                                if n['type'] in ('country', 'state', 'city', 'venue')
                                and len(n['names_as_listed']) > 1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='data/fugazi_shows.json')
    parser.add_argument('--output', default='data/normalization_review.json')
    args = parser.parse_args()
    report = audit(load_shows(Path(args.input)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('needs_review', 'standardized_locations')}))
    print(f"{len(report['needs_review'])} track labels need review; report: {output}")
