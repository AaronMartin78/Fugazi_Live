import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createIndex, search, cooccurrence, dischordUrl} from './graph.mjs';

const source = JSON.parse(readFileSync(new URL('../data/fugazi_shows.json', import.meta.url)));
const index = createIndex(JSON.parse(readFileSync(new URL('../data/web/data.json', import.meta.url))));
const ids = shows => shows.map(show => show.show_id).sort();

test('every show retains its source link and ordered track entries', () => {
  const original = new Map(source.map(show => [show.show_id, show]));
  assert.equal(index.shows.length, source.length);
  for (const show of index.shows) {
    const record = original.get(show.show_id);
    assert.equal(dischordUrl(show.source_url), record.source_url);
    assert.deepEqual(index.performances.get(show.id).map(edge => ({position: edge.position, title: edge.title_as_listed})), record.setlist);
  }
});
test('song and place queries agree with source records', () => {
  const expected = source.filter(show => show.setlist.some(track => track.title === 'Waiting Room') && show.city.toLowerCase() === 'berlin');
  assert.deepEqual(ids(search(index, {query: 'Waiting Room Berlin'})), ids(expected));
  assert.deepEqual(ids(search(index, {query: '"Waiting Room" Berlin'})), ids(expected));
  assert.deepEqual(ids(search(index, {query: 'Berlin 1995'})), ids(source.filter(show => show.city.toLowerCase() === 'berlin' && show.event_date.startsWith('1995'))));
});
test('selected songs intersect actual graph relationships', () => {
  const a = index.entities.find(node => node.type === 'song' && node.name === 'Waiting Room');
  const b = index.entities.find(node => node.type === 'song' && node.name === 'Merchandise');
  const expected = source.filter(show => ['Waiting Room', 'Merchandise'].every(title => show.setlist.some(track => track.title === title)));
  assert.deepEqual(ids(search(index, {selected: [a.id, b.id]})), ids(expected));
});
test('year range and missing-setlist filter agree with source', () => {
  assert.deepEqual(ids(search(index, {from: 1992, to: 1993, setlistsOnly: true})), ids(source.filter(show => show.event_date >= '1992-01-01' && show.event_date <= '1993-12-31' && show.setlist.length)));
});
test('co-occurrence counts distinct shows, including repeated source entries', () => {
  const intro = index.entities.find(node => node.type === 'song' && node.name === 'Intro');
  const expected = new Map();
  for (const show of index.shows) {
    const unique = new Set(index.graph.edges.filter(edge => edge.relation === 'performed' && edge.source === show.id).map(edge => edge.target));
    if (unique.has(intro.id)) for (const id of unique) if (id !== intro.id) expected.set(id, (expected.get(id) || 0) + 1);
  }
  assert.deepEqual(new Map(cooccurrence(index, intro.id, index.shows)), expected);
});
test('outbound links reject unrelated domains, credentials, and executable schemes', () => {
  for (const url of ['javascript:alert(1)', 'https://dischord.com.evil.test/fugazi_live_series/show', 'https://user@dischord.com/fugazi_live_series/show', 'https://dischord.com/store', 'http://dischord.com/fugazi_live_series/show']) assert.equal(dischordUrl(url), null);
});
