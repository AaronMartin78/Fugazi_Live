import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mapProjection} from './map-projection.mjs';

test('world overview retains its original bounds and coordinates',() => {
  const project = mapProjection([-180,180,-60,85],false);
  assert.deepEqual(project([-180,85]),[0,0]);
  assert.deepEqual(project([180,-60]),[960,460]);
});
test('regional Mercator preserves local shapes instead of stretching each axis',() => {
  const project = mapProjection([-15,40,32,72],true,960,600);
  const center=project([10,50]), east=project([10.0001,50]), north=project([10,50.0001]);
  const ratio=(east[0]-center[0])/(center[1]-north[1]);
  assert.ok(Math.abs(ratio-Math.cos(50*Math.PI/180))<.00001);
  for (const coordinate of [[-15,72],[40,32]]) {
    const [x,y]=project(coordinate); assert.ok(x>=15.9 && x<=944.1 && y>=15.9 && y<=584.1);
  }
});
test('border overlay contains valid Natural Earth line geometry',() => {
  const borders=JSON.parse(readFileSync(new URL('borders.json',import.meta.url)));
  assert.ok(borders.features.length>100);
  for (const feature of borders.features) {
    assert.ok(['LineString','MultiLineString'].includes(feature.geometry.type));
    const lines=feature.geometry.type==='LineString'?[feature.geometry.coordinates]:feature.geometry.coordinates;
    for (const line of lines) for (const [lon,lat] of line) assert.ok(Number.isFinite(lon) && Number.isFinite(lat) && Math.abs(lon)<=180 && Math.abs(lat)<=90);
  }
});
