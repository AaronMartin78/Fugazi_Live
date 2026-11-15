#!/usr/bin/env python3
"""Build a versioned graph with stable song and hierarchical location identities."""
import argparse
import json
from pathlib import Path
from identities import clean, entity_id, key, load_catalog

def load_shows(path):
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, list):
        raise ValueError(f'Expected a JSON array in {path}')
    return payload

def graph_for(shows, catalog=None):
    catalog = load_catalog() if catalog is None else catalog
    songs = {key(alias): song for song in catalog['songs']
             for alias in [song['title'], *song.get('aliases', [])]}
    albums = {a['id']: a for a in catalog['albums']}
    aliases = catalog.get('location_aliases', {})
    nodes, edges, locations, seen_shows = {}, [], set(), set()

    def node(identifier, kind, name, **props):
        nodes.setdefault(identifier, dict(id=identifier, type=kind, name=name, **props))
        return identifier

    def edge(source, relation, target, **props):
        edges.append(dict(source=source, relation=relation, target=target, **props))

    def location(kind, raw, parent, context):
        if not clean(raw):
            return None
        alias_key = json.dumps([*context, key(raw)], ensure_ascii=False)
        canonical = aliases.get(kind, {}).get(alias_key, clean(raw))
        identifier = entity_id(kind, *context, key(canonical))
        node(identifier, kind, canonical, parent_id=parent, names_as_listed=[],
             canonical_names=[])
        nodes[identifier]['canonical_names'].append(canonical)
        if raw not in nodes[identifier]['names_as_listed']:
            nodes[identifier]['names_as_listed'].append(raw)
        if parent and identifier not in locations:
            edge(identifier, 'part_of', parent)
        locations.add(identifier)
        return identifier

    for show in shows:
        show_key = clean(show.get('show_id') or show.get('slug') or show.get('source_url'))
        if not show_key:
            raise ValueError('Show requires a stable show_id, slug, or source_url')
        sid = entity_id('show', key(show_key))
        if sid in seen_shows:
            raise ValueError(f'Duplicate show identity: {show_key}')
        seen_shows.add(sid)
        node(sid, 'show', show_key, show_id=show.get('show_id'), date=show.get('event_date'),
             source_url=show.get('source_url'),
             location_as_listed={k: show.get(k) for k in ('country','subdivision','city','venue')})
        context, parent = [], None
        for kind, field in [('country','country'),('state','subdivision'),('city','city'),('venue','venue')]:
            loc = location(kind, show.get(field), parent, context)
            nodes[sid][f'{kind}_id'] = loc
            context.append(loc or f'missing:{kind}')
            if loc:
                edge(sid, 'played_at' if kind == 'venue' else 'happened_in', loc)
                parent = loc
        for act in sorted(set(show.get('opening_acts', []))):
            if clean(act):
                aid = entity_id('band', key(act))
                node(aid, 'band', clean(act))
                nodes[aid]['name'] = min(nodes[aid]['name'], clean(act))
                edge(sid, 'opened_by', aid)
        for track in show.get('setlist', []):
            title = track.get('title')
            if not clean(title):
                continue
            song = songs.get(key(title))
            song_id = song['id'] if song else entity_id('song', key(title))
            album_id = song.get('album_id') if song else None
            node(song_id, 'song', song['title'] if song else clean(title),
                 album_id=album_id, color=albums[album_id]['color'] if album_id else '#808080',
                 review_status=song.get('review_status','needs_review') if song else 'needs_review',
                 titles_as_listed=[])
            if title not in nodes[song_id]['titles_as_listed']:
                nodes[song_id]['titles_as_listed'].append(title)
            edge(sid, 'performed', song_id, position=track.get('position'), title_as_listed=title)
    for n in nodes.values():
        for field in ('titles_as_listed','names_as_listed'):
            if field in n:
                n[field].sort()
        if 'canonical_names' in n:
            n['name'] = min(n.pop('canonical_names'))
    return dict(schema_version=2, albums=catalog['albums'],
                nodes=sorted(nodes.values(), key=lambda n: n['id']),
                edges=sorted(edges, key=lambda e: json.dumps(e, sort_keys=True)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='data/fugazi_shows.json')
    parser.add_argument('--output', default='data/fugazi_graph.json')
    args = parser.parse_args()
    graph = graph_for(load_shows(Path(args.input)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges to {output}")

if __name__ == '__main__':
    main()
