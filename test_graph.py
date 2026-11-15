import copy
import json
import unittest

from build_graph import graph_for
from identities import entity_id, key, load_catalog
from scrape_fugazi import detail_fields, normalize_date
from bs4 import BeautifulSoup


def show(identifier='FLS0001', **changes):
    return dict(show_id=identifier, country='USA', subdivision='GA', city='Atlanta',
                venue='Masquerade', setlist=[{'position': 1, 'title': 'Waiting Room'}], **changes)


class GraphRegressionTests(unittest.TestCase):
    def nodes(self, graph, kind):
        return [n for n in graph['nodes'] if n['type'] == kind]

    def test_shared_venue_names_do_not_merge(self):
        other = show('FLS0002')
        other.update(city='Tampa', subdivision='FL')
        g = graph_for([show(), other])
        self.assertEqual(len(self.nodes(g, 'venue')), 2)
        self.assertEqual(len(self.nodes(g, 'country')), 1)
        self.assertEqual(len(self.nodes(g, 'state')), 2)
        self.assertEqual(len(self.nodes(g, 'city')), 2)

    def test_state_names_scoped_to_country(self):
        other = show('FLS0002')
        other.update(country='Australia', subdivision='WA')
        first = show()
        first['subdivision'] = 'WA'
        self.assertEqual(len(self.nodes(graph_for([first, other]), 'state')), 2)

    def test_city_names_scoped_to_state(self):
        a, b = show(), show('FLS0002')
        a.update(city='Springfield', subdivision='IL')
        b.update(city='Springfield', subdivision='MA')
        self.assertEqual(len(self.nodes(graph_for([a, b]), 'city')), 2)

    def test_whitespace_case_and_unicode_normalize(self):
        a, b = show(), show('FLS0002')
        a.update(venue=' Cafe\u0301 ', subdivision='GA ')
        b.update(venue='CAFÉ', subdivision='GA')
        g = graph_for([a, b])
        self.assertEqual(len(self.nodes(g, 'venue')), 1)
        self.assertEqual(len(self.nodes(g, 'state')), 1)
        self.assertEqual(self.nodes(g, 'show')[0]['location_as_listed']['country'], 'USA')

    def test_punctuation_does_not_create_identity_collision(self):
        self.assertNotEqual(entity_id('song', key('A-B')), entity_id('song', key('A B')))

    def test_aliases_preserve_performance_text_and_repetitions(self):
        a = show()
        a['setlist'] = [{'position': 1, 'title': 'Glueman'},
                        {'position': 2, 'title': 'Glue Man'},
                        {'position': 3, 'title': 'Glueman'}]
        g = graph_for([a])
        songs = self.nodes(g, 'song')
        self.assertEqual(len(songs), 1)
        self.assertEqual(songs[0]['name'], 'Glue Man')
        tracks = sorted([e for e in g['edges'] if e['relation'] == 'performed'], key=lambda e: e['position'])
        self.assertEqual([e['title_as_listed'] for e in tracks], ['Glueman', 'Glue Man', 'Glueman'])

    def test_live_variants_not_silently_merged(self):
        a = show()
        a['setlist'] = [{'position': i, 'title': title} for i, title in enumerate(['Break', 'Break-In', 'Break Instrumental'], 1)]
        self.assertEqual(len(self.nodes(graph_for([a]), 'song')), 3)

    def test_unknown_song_is_neutral_and_reviewable(self):
        a = show()
        a['setlist'] = [{'position': 1, 'title': 'Unknown Song'}]
        n = self.nodes(graph_for([a]), 'song')[0]
        self.assertIsNone(n['album_id'])
        self.assertEqual(n['review_status'], 'needs_review')

    def test_13_songs_color_and_release(self):
        n = self.nodes(graph_for([show()]), 'song')[0]
        self.assertEqual(n['album_id'], 'album:13-songs')
        self.assertEqual(n['color'], '#8B2F60')

    def test_missing_locations_not_invented(self):
        a = show()
        a.update(country=None, subdivision=None, city=None, venue=None)
        self.assertEqual({n['type'] for n in graph_for([a])['nodes']}, {'show', 'song'})

    def test_order_independent_and_no_input_mutation(self):
        data = [show(), show('FLS0002')]
        before = copy.deepcopy(data)
        self.assertEqual(graph_for(data), graph_for(list(reversed(data))))
        self.assertEqual(data, before)

    def test_duplicate_show_rejected(self):
        with self.assertRaises(ValueError):
            graph_for([show(), show()])

    def test_band_display_names_are_order_independent(self):
        a, b = show(), show('FLS0002')
        a['opening_acts'] = ['BAND']
        b['opening_acts'] = ['Band']
        self.assertEqual(graph_for([a, b]), graph_for([b, a]))

    def test_venue_alias_is_scoped_and_keeps_raw_names(self):
        a, b = show(), show('FLS0002')
        b['venue'] = 'The Masquerade'
        catalog = load_catalog()
        original = graph_for([a])
        sn = self.nodes(original, 'show')[0]
        context = [sn['country_id'], sn['state_id'], sn['city_id']]
        catalog['location_aliases']['venue'][json.dumps([*context, key(b['venue'])])] = 'Masquerade'
        venues = self.nodes(graph_for([a, b], catalog), 'venue')
        self.assertEqual(len(venues), 1)
        self.assertEqual(venues[0]['name'], 'Masquerade')
        self.assertEqual(venues[0]['names_as_listed'], ['Masquerade', 'The Masquerade'])

    def test_missing_state_does_not_merge_with_known_state(self):
        a, b = show(), show('FLS0002')
        b['subdivision'] = None
        self.assertEqual(len(self.nodes(graph_for([a, b]), 'city')), 2)

    def test_every_edge_has_valid_endpoints(self):
        g = graph_for([show()])
        ids = {n['id'] for n in g['nodes']}
        self.assertEqual(len(ids), len(g['nodes']))
        self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in g['edges']))

    def test_display_title_change_keeps_catalog_id(self):
        catalog = load_catalog()
        song = next(s for s in catalog['songs'] if s['title'] == 'Waiting Room')
        original = song['id']
        song.update(title='Waiting Room (Display Label)', aliases=['Waiting Room'])
        self.assertEqual(self.nodes(graph_for([show()], catalog), 'song')[0]['id'], original)

    def test_scraper_preserves_track_order_and_labels(self):
        soup = BeautifulSoup('<div class="productInfo"><h1>FLS0001</h1><table><tr><td>1</td><td>Glueman</td></tr><tr><td>2</td><td>Break-In</td></tr></table></div>', 'html.parser')
        fields = detail_fields(soup)
        self.assertEqual([(t.position, t.title) for t in fields['setlist']], [(1, 'Glueman'), (2, 'Break-In')])
        self.assertEqual(normalize_date('November 15, 1990'), '1990-11-15')


if __name__ == '__main__':
    unittest.main()
