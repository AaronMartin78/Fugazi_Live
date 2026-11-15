"""Stable entity IDs independent of display spelling."""
import json
import unicodedata
from pathlib import Path
from uuid import UUID, uuid5

NAMESPACE = UUID('64bf958b-9603-4c89-96e7-3bc7f443d732')

def clean(value):
    return ' '.join(unicodedata.normalize('NFC', value or '').split())

def key(value):
    return clean(value).casefold()

def entity_id(kind, *parts):
    return f'{kind}:{uuid5(NAMESPACE, json.dumps(parts, ensure_ascii=False))}'

def load_catalog():
    catalog = json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))
    seen, aliases = set(), {}
    albums = {a['id'] for a in catalog['albums']}
    if len(albums) != len(catalog['albums']):
        raise ValueError('Duplicate album ID')
    for song in catalog['songs']:
        if song['id'] in seen:
            raise ValueError('Duplicate song ID')
        seen.add(song['id'])
        if song.get('album_id') and song['album_id'] not in albums:
            raise ValueError('Unknown album ID')
        for title in [song['title'], *song.get('aliases', [])]:
            normalized = key(title)
            if normalized in aliases and aliases[normalized] != song['id']:
                raise ValueError(f'Ambiguous song alias: {title}')
            aliases[normalized] = song['id']
    return catalog

