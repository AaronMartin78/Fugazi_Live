"""Export schema-2 graph JSON to CSV and Cypher for Neo4j Desktop (5.26+)."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from identities import entity_id

LABELS = {kind: kind.title() for kind in
          ('show', 'song', 'venue', 'city', 'state', 'country', 'band', 'album')}
RELATIONS = {r: r.upper() for r in
             ('performed', 'played_at', 'happened_in', 'opened_by', 'part_of', 'first_released_on')}


def rows_for(graph):
    if graph.get('schema_version') != 2:
        raise ValueError('Expected schema version 2; run build_graph.py first')
    nodes = []
    for source in [*graph['nodes'], *[dict(a, type='album') for a in graph['albums']]]:
        row = {'label': LABELS[source['type']]}
        for field, value in source.items():
            if field == 'type':
                continue
            if isinstance(value, (dict, list)):
                row[field + '_json'] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            else:
                row[field] = value
        nodes.append(row)
    ids = [n['id'] for n in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate node IDs')
    known = set(ids)
    source_edges = list(graph['edges'])
    for song in graph['nodes']:
        if song['type'] == 'song' and song.get('album_id'):
            source_edges.append(dict(source=song['id'], relation='first_released_on', target=song['album_id']))
    edges, occurrences = [], Counter()
    for e in sorted(source_edges, key=lambda e: json.dumps(e, sort_keys=True)):
        if e['source'] not in known or e['target'] not in known:
            raise ValueError('Relationship references a missing node')
        signature = json.dumps(e, ensure_ascii=False, sort_keys=True)
        occurrences[signature] += 1
        edges.append(dict(id=entity_id('relationship', signature, str(occurrences[signature])),
                          source=e['source'], target=e['target'], type=RELATIONS[e['relation']],
                          position=e.get('position'), title_as_listed=e.get('title_as_listed')))
    return sorted(nodes, key=lambda n: n['id']), edges


def export(graph, output):
    nodes, edges = rows_for(graph)
    output.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for n in nodes for k in n})
    for filename, rows, columns in [('fugazi_nodes.csv', nodes, fields),
                                    ('fugazi_edges.csv', edges, ['id', 'source', 'target', 'type', 'position', 'title_as_listed'])]:
        with (output / filename).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    setters = ',\n    '.join(f'n.{f} = CASE WHEN row.{f} = \'\' THEN null ELSE row.{f} END'
                              for f in fields if f not in ('id', 'label'))
    script = f'''// Run each numbered block separately in Desktop Query, in order.
// Copy fugazi_nodes.csv and fugazi_edges.csv to this instance's import folder first.
// 1. Enforce unique IDs for imported entities (demo nodes are separate).
CREATE CONSTRAINT fugazi_entity_id IF NOT EXISTS
FOR (n:FugaziEntity) REQUIRE n.id IS UNIQUE;

// 2. Import nodes. JSON-suffixed properties preserve nested source data as text.
LOAD CSV WITH HEADERS FROM 'file:///fugazi_nodes.csv' AS row
MERGE (n:FugaziEntity {{id: row.id}})
SET n:$(row.label)
SET {setters}
RETURN count(n) AS imported_nodes;

// 3. Import connections. Stable relationship IDs make reruns safe.
LOAD CSV WITH HEADERS FROM 'file:///fugazi_edges.csv' AS row
MATCH (source:FugaziEntity {{id: row.source}})
MATCH (target:FugaziEntity {{id: row.target}})
MERGE (source)-[r:$(row.type) {{id: row.id}}]->(target)
SET r.position = toInteger(row.position),
    r.title_as_listed = CASE WHEN row.title_as_listed = '' THEN null ELSE row.title_as_listed END
RETURN count(r) AS imported_relationships;

// 4. Verify imported entities by type (excludes the earlier demo).
MATCH (n:FugaziEntity)
RETURN [label IN labels(n) WHERE label <> 'FugaziEntity'][0] AS type, count(*) AS count
ORDER BY type;

// 5. Display songs linked to 13 Songs.
MATCH path = (s:Song:FugaziEntity)-[:FIRST_RELEASED_ON]->(a:Album {{id: 'album:13-songs'}})
RETURN path;

// Expected for this export: {len(nodes)} imported nodes, {len(edges)} imported relationships.
// Reruns update/add; they do not remove records deleted from a later source export.
'''
    (output / 'import.cypher').write_text(script, encoding='utf-8')
    counts = dict(Counter(n['label'] for n in nodes))
    (output / 'manifest.json').write_text(json.dumps(dict(nodes=len(nodes), relationships=len(edges), counts=counts), indent=2) + '\n', encoding='utf-8')
    return len(nodes), len(edges)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='data/fugazi_graph.json')
    parser.add_argument('--output', default='data/neo4j')
    args = parser.parse_args()
    graph = json.loads(Path(args.input).read_text(encoding='utf-8'))
    nodes, edges = export(graph, Path(args.output))
    print(f'Exported {nodes} nodes and {edges} relationships to {args.output}')
