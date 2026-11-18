import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createIndex, search, normalize} from './graph.mjs';
import {summarize, networkLayout, nodeRadius} from './metrics.mjs';

const read = path => JSON.parse(readFileSync(new URL(path,import.meta.url)));
const graph = read('../data/web/data.json'), source = read('../data/fugazi_shows.json');
const geography = read('cities.json'), index = createIndex(graph);
const metrics = summarize(index,index.shows,geography);
const catalog = read('../catalog.json');

test('song rankings match distinct source shows, with curated aliases and no unresolved labels',() => {
  const aliases = new Map(catalog.songs.flatMap(song => [song.title,...song.aliases || []].map(name => [normalize(name),song])));
  const expected = new Map();
  for (const show of source) {
    const songs = new Set(show.setlist.map(track => aliases.get(normalize(track.title))).filter(song => song?.album_id).map(song => song.id));
    for (const id of songs) expected.set(id,(expected.get(id) || 0)+1);
  }
  assert.deepEqual(new Map(metrics.songs.map(row => [row.id,row.count])),expected);
  assert.equal(metrics.songs[0].node.name,'Waiting Room');
  assert.equal(metrics.songs[0].count,674);
  assert.equal(metrics.setlists,952);
  assert.ok(metrics.songs.every(row => row.node.review_status === 'release_matched'));
});
test('opening-act frequency and pair weights agree with source bills',() => {
  const expected = new Map(), expectedPairs = new Map();
  for (const show of source) {
    const acts = [...new Set(show.opening_acts.map(normalize).filter(name => name !== '?'))].sort();
    for (const act of acts) expected.set(act,(expected.get(act) || 0)+1);
    for (let a=0;a<acts.length;a++) for (let b=a+1;b<acts.length;b++) {
      const key=JSON.stringify([acts[a],acts[b]]); expectedPairs.set(key,(expectedPairs.get(key) || 0)+1);
    }
  }
  assert.deepEqual(new Map(metrics.acts.map(row => [normalize(row.node.name),row.count])),expected);
  const actualPairs = new Map(metrics.pairs.map(pair => [JSON.stringify(pair.ids.map(id => normalize(index.nodes.get(id).name)).sort()),pair.count]));
  assert.deepEqual(actualPairs,expectedPairs);
  assert.equal(metrics.acts[0].node.name,'Branch Manager'); assert.equal(metrics.acts[0].count,33);
});
test('all three metrics respect the same year and country selection',() => {
  const country = graph.nodes.find(node => node.type === 'country' && node.name === 'Germany');
  const shows=search(index,{from:'1995',to:'1995',country:country.id});
  const subset=summarize(index,shows,geography);
  const expected=source.filter(show => show.event_date.startsWith('1995') && show.country==='Germany');
  assert.equal(subset.shows.length,expected.length);
  assert.equal(subset.setlists,expected.filter(show => show.setlist.length).length);
  assert.equal(subset.mappedShows + subset.unmapped.reduce((sum,row) => sum+row.count,0),expected.length);
  assert.ok(subset.songs.every(row => row.count<=expected.length));
  assert.ok(subset.acts.every(row => row.count<=expected.length));
});
test('map enrichment partitions all archive cities without changing source coordinates',() => {
  const known = new Set(geography.cities.map(city => city.city_id));
  const unresolved = new Set(geography.unresolved.map(city => city.city_id));
  assert.equal(known.size,geography.cities.length);
  for (const id of known) { assert.equal(index.nodes.get(id).type,'city'); assert.ok(!unresolved.has(id)); }
  for (const city of geography.cities) {
    assert.ok(city.latitude>=-90 && city.latitude<=90 && city.longitude>=-180 && city.longitude<=180);
    assert.match(city.geonames_id,/^\d+$/);
  }
  assert.equal(known.size+unresolved.size,419);
  assert.equal(metrics.mappedShows,1025);
  assert.equal(metrics.mappedShows+metrics.unmapped.reduce((sum,row) => sum+row.count,0),1049);
  const london=geography.cities.find(city => city.archive_city==='London' && city.archive_country==='England');
  assert.equal(london.geonames_id,'2643743');
});
test('network layout is deterministic, finite, and uses valid weighted edges',() => {
  const a=networkLayout(metrics.acts.slice(0,32),metrics.pairs), b=networkLayout(metrics.acts.slice(0,32),metrics.pairs);
  assert.deepEqual(a,b); const ids=new Set(a.nodes.map(node => node.id));
  for (const node of a.nodes) assert.ok(Number.isFinite(node.x) && Number.isFinite(node.y) && node.r>0);
  for (const pair of a.links) assert.ok(pair.count>0 && pair.ids.every(id => ids.has(id)));
  assert.ok(Math.abs(nodeRadius(4,16)**2/nodeRadius(1,16)**2-4)<1e-10);
});
test('empty selections have no invented chart values or graph nodes',() => {
  const empty=summarize(index,[],geography);
  assert.equal(empty.setlists,0); assert.equal(empty.mappedShows,0);
  assert.deepEqual(empty.songs,[]); assert.deepEqual(empty.acts,[]); assert.deepEqual(empty.pairs,[]);
});
