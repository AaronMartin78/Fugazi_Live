import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_graph import graph_for
from export_neo4j import export, rows_for


class Neo4jExportTests(unittest.TestCase):
    def graph(self):
        return graph_for([dict(show_id='FLS0001', country='USA', city='Washington',
                               venue='A, "quoted" venue', setlist=[
                                   dict(position=1, title='Waiting Room'),
                                   dict(position=2, title='Waiting Room')])])

    def test_albums_and_relationships(self):
        nodes, edges = rows_for(self.graph())
        ids = {n['id'] for n in nodes}
        self.assertEqual(len(ids), len(nodes))
        self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in edges))
        self.assertEqual(sum(e['type'] == 'FIRST_RELEASED_ON' for e in edges), 1)
        self.assertEqual(sum(e['type'] == 'PERFORMED' for e in edges), 2)
        self.assertEqual(len({e['id'] for e in edges}), len(edges))

    def test_stable_ids_and_order(self):
        graph = self.graph()
        expected = rows_for(graph)
        graph['edges'].reverse()
        graph['nodes'].reverse()
        self.assertEqual(rows_for(graph), expected)

    def test_duplicate_track_occurrences_are_not_lost(self):
        graph = self.graph()
        track = next(e for e in graph['edges'] if e['relation'] == 'performed')
        graph['edges'].append(dict(track))
        _, edges = rows_for(graph)
        self.assertEqual(sum(e['type'] == 'PERFORMED' for e in edges), 3)
        self.assertEqual(len({e['id'] for e in edges}), len(edges))

    def test_csv_roundtrip_and_source_preservation(self):
        graph = self.graph()
        with tempfile.TemporaryDirectory() as folder:
            export(graph, Path(folder))
            with (Path(folder) / 'fugazi_nodes.csv').open(encoding='utf-8', newline='') as stream:
                nodes = list(csv.DictReader(stream))
            venue = next(n for n in nodes if n['label'] == 'Venue')
            self.assertEqual(venue['name'], 'A, "quoted" venue')
            self.assertEqual(json.loads(venue['names_as_listed_json']), ['A, "quoted" venue'])

    def test_dangling_edge_rejected(self):
        graph = self.graph()
        graph['edges'][0]['target'] = 'missing'
        with self.assertRaises(ValueError):
            rows_for(graph)


if __name__ == '__main__':
    unittest.main()
