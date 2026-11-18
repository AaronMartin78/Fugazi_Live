import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inRegion,regionGroups} from './regions.mjs';
import {createIndex,search} from './graph.mjs';
import {summarize} from './metrics.mjs';
const read=path=>JSON.parse(readFileSync(new URL(path,import.meta.url)));
const graph=read('../data/web/data.json'), source=read('../data/fugazi_shows.json'), geography=read('cities.json');
const index=createIndex(graph);
test('every archive country belongs to exactly one region',()=>{
 const countries=Object.values(regionGroups).flatMap(region=>region.countries);
 assert.equal(new Set(countries).size,countries.length);
 for(const node of graph.nodes.filter(n=>n.type==='country')) assert.equal(countries.filter(name=>name===node.name).length,1,node.name);
});
test('South America rankings and source drilldown retain exactly the regional shows',()=>{
 const selected=search(index,{region:'south-america'});
 const expected=source.filter(show=>['Argentina','Brazil','Chile'].includes(show.country));
 assert.deepEqual(selected.map(s=>s.show_id).sort(),expected.map(s=>s.show_id).sort());
 const metrics=summarize(index,selected,geography);
 assert.equal(metrics.setlists,expected.filter(s=>s.setlist.length).length);
 const waiting=graph.nodes.find(n=>n.type==='song'&&n.name==='Waiting Room');
 const results=search(index,{selected:[waiting.id],region:'south-america'});
 assert.equal(results.length,expected.filter(s=>s.setlist.some(t=>t.title==='Waiting Room')).length);
 assert.ok(results.every(s=>inRegion(s,'south-america')));
});
test('region intersects year and country and retains unmapped cities',()=>{
 const german=graph.nodes.find(n=>n.type==='country'&&n.name==='Germany');
 assert.equal(search(index,{country:german.id,region:'south-america'}).length,0);
 const european=search(index,{country:german.id,region:'europe',from:'1995',to:'1995'});
 assert.equal(european.length,source.filter(s=>s.country==='Germany'&&s.event_date.startsWith('1995')).length);
 const southern=search(index,{region:'south-america'}), known=new Set(geography.cities.map(c=>c.city_id));
 assert.ok(southern.some(s=>!known.has(s.city_id)));
});
