import {createIndex, search, dischordUrl} from './graph.mjs';
import {summarize, networkLayout, nodeRadius} from './metrics.mjs';
import {mapProjection} from './map-projection.mjs';

const $ = value => document.querySelector(value);
const state = {index: null, geography: null, land: null, borders: null, metrics: null, selectedAct: null, applied: {}};
const regions = {world: [-180,180,-60,85], 'north-america':[-170,-50,8,75], europe:[-15,40,32,72], 'south-america':[-85,-30,-60,15], 'asia-oceania':[80,180,-50,65]};
const number = value => value.toLocaleString();
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, handler, className) {
  const node = el('button', text, className);
  node.type = 'button'; node.addEventListener('click', handler);
  return node;
}
function svg(tag, attributes = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key,value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}
function svgTitle(node, value) { const title = svg('title'); title.textContent = value; node.append(title); }
function activate(node, handler) {
  node.addEventListener('click', handler);
  node.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handler(); } });
}
function options() { return {from: $('#from').value, to: $('#to').value, country: $('#country').value}; }
function searchUrl(entities) {
  const params = new URLSearchParams();
  for (const [key,value] of Object.entries(state.applied)) if (value) params.set(key,value);
  for (const id of entities) params.append('entity',id);
  return 'index.html?' + params;
}
function entityShows(ids) { return state.metrics.shows.filter(show => ids.every(id => state.index.byEntity.get(id)?.has(show.id))); }
function selection(target, title, shows, entities, note) {
  const container = $(target); container.hidden = false;
  container.replaceChildren(el('h3', title), el('p', `${number(shows.length)} shows in this selection. ${note || ''}`));
  const list = el('ul', undefined, 'show-links');
  for (const show of shows.slice(0, 6)) {
    const raw = show.location_as_listed;
    const row = el('li');
    row.append(el('span', `${show.date} · ${raw.venue} · ${raw.city}, ${raw.country}`));
    const url = dischordUrl(show.source_url);
    if (url) { const link = el('a', 'View on Dischord ↗'); link.href = url; row.append(link); }
    list.append(row);
  }
  const link = el('a', `Explore all ${number(shows.length)} shows in Search →`, 'all-shows'); link.href = searchUrl(entities);
  container.append(list, link);
  return container;
}
function renderSongs() {
  const metrics = state.metrics, rows = metrics.songs.slice(0,20), chart = $('#song-chart');
  chart.replaceChildren(); $('#song-selection').hidden = true;
  $('#song-insight').textContent = rows.length ? `${rows[0].node.name} leads this selection: listed at ${number(rows[0].count)} of ${number(metrics.setlists)} shows with setlists (${(100 * rows[0].count / metrics.setlists).toFixed(1)}%).` : 'No release-matched songs are listed for this selection.';
  if (!rows.length) chart.append(el('p', 'Try a different year range or country.', 'empty-chart'));
  for (const [position,row] of rows.entries()) {
    const bar = button('', () => {
      for (const other of chart.querySelectorAll('button')) other.setAttribute('aria-pressed','false');
      bar.setAttribute('aria-pressed','true');
      selection('#song-selection', row.node.name, entityShows([row.id]), [row.id], 'Counted once per show; missing setlists remain unknown.');
    }, 'song-row');
    bar.setAttribute('aria-pressed','false');
    bar.setAttribute('aria-label', `${position + 1}. ${row.node.name}, ${row.count} shows. View shows.`);
    const track = el('span', undefined, 'bar-track'), fill = el('span', undefined, 'bar');
    fill.style.width = `${100 * row.count / rows[0].count}%`; track.append(fill);
    track.setAttribute('aria-hidden','true');
    bar.append(el('span',String(position + 1).padStart(2,'0'),'rank'), el('span',row.node.name), track, el('span',number(row.count),'bar-count'));
    chart.append(bar);
  }
  $('#song-note').textContent = `Distinct shows, not raw track rows. Ranking uses release-matched songs only. ${number(metrics.shows.length - metrics.setlists)} of ${number(metrics.shows.length)} selected shows have no published setlist and cannot contribute to this chart.`;
}
function citySelect(rows) {
  const shows = rows.flatMap(row => row.shows).sort((a,b) => a.date.localeCompare(b.date));
  const ids = rows.map(row => row.id);
  const title = [rows[0].node.name, rows[0].shows[0].location_as_listed.subdivision, [...new Set(rows.map(row => row.geo.archive_country))].join(' / ')].filter(Boolean).join(' · ');
  const container = selection('#city-selection',title,shows,ids.length === 1 ? ids : [],'Plotted at a derived city center, not a venue address.');
  // A geographic marker can combine historical labels; Search must use OR, not an AND of city IDs.
  if (ids.length > 1) {
    container.querySelector('.all-shows').remove();
    for (const row of rows) {
      const link = el('a', `Search ${row.geo.archive_city}, ${row.geo.archive_country} (${row.count}) →`, 'all-shows');
      link.href = searchUrl([row.id]); container.append(link,el('br'));
    }
  }
}
function renderMap() {
  $('#city-selection').hidden = true;
  const metrics = state.metrics;
  const [west,east,south,north] = regions[$('#region').value];
  const regional = $('#region').value !== 'world';
  const width = 960, height = regional ? 600 : 460;
  const project = mapProjection([west,east,south,north],regional,width,height);
  const canvas = svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'group','aria-label':'Shows by city. Select a circle or a city button below.'});
  const defs = svg('defs'), clip = svg('clipPath',{id:'map-clip'}); clip.append(svg('rect',{width,height})); defs.append(clip); canvas.append(defs);
  const scene = svg('g',{'clip-path':'url(#map-clip)'}); canvas.append(scene);
  for (let lon = -180; lon <= 180; lon += 30) { const [x] = project([lon,0]); scene.append(svg('line',{x1:x,x2:x,y1:0,y2:height,class:'graticule'})); }
  for (let lat = -60; lat <= 90; lat += 30) { const [,y] = project([0,lat]); scene.append(svg('line',{x1:0,x2:width,y1:y,y2:y,class:'graticule'})); }
  for (const feature of state.land.features) {
    const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    const d = polygons.map(polygon => polygon.map(ring => ring.map((coordinate,i) => `${i?'L':'M'}${project(coordinate).map(value => value.toFixed(2)).join(',')}`).join('')+'Z').join('')).join('');
    scene.append(svg('path',{d,class:'land'}));
  }
  if (regional) for (const feature of state.borders.features) {
    const lines = feature.geometry.type === 'LineString' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    const d = lines.map(line => line.map((coordinate,i) => `${i?'L':'M'}${project(coordinate).map(value => value.toFixed(2)).join(',')}`).join('')).join('');
    scene.append(svg('path',{d,class:'country-border',fill:'none',stroke:'#8d9587','stroke-width':'.9','vector-effect':'non-scaling-stroke','pointer-events':'none','aria-hidden':'true'}));
  }
  let borderNote = $('#border-note');
  if (!borderNote) {
    borderNote = el('p','Regional views use Mercator projection and modern country borders for orientation. Archive country labels remain as published.','caption');
    borderNote.id = 'border-note'; $('#map').after(borderNote);
  }
  borderNote.hidden = !regional;
  const regionRows = metrics.mapped.filter(row => row.geo.longitude >= west && row.geo.longitude <= east && row.geo.latitude >= south && row.geo.latitude <= north);
  const groups = new Map();
  for (const row of regionRows) {
    const id = row.geo.geonames_id;
    if (!groups.has(id)) groups.set(id, []);
    groups.get(id).push(row);
  }
  const markers = [...groups.values()].map(rows => ({rows,count:rows.reduce((sum,row) => sum+row.count,0)})).sort((a,b) => b.count-a.count);
  // Draw larger circles first so small nearby markers remain selectable.
  for (const marker of markers) {
    const row = marker.rows[0], [cx,cy] = project([row.geo.longitude,row.geo.latitude]);
    const dot = svg('circle',{cx,cy,r:nodeRadius(marker.count,markers[0]?.count || 1,23),class:'city-dot',tabindex:'0',role:'button','aria-label':`${row.node.name}, ${marker.count} shows. View shows.`});
    svgTitle(dot,`${row.node.name} · ${marker.count} shows`); activate(dot,() => citySelect(marker.rows)); scene.append(dot);
  }
  $('#map').replaceChildren(canvas);
  $('#map-coverage').textContent = `${number(metrics.mappedShows)} of ${number(metrics.shows.length)} selected shows mapped · ${number(metrics.shows.length - metrics.mappedShows)} unplotted`;
  const cityList = $('#city-list'); cityList.replaceChildren();
  const addButtons = rows => { for (const row of rows) {
    const subdivision = row.shows[0].location_as_listed.subdivision;
    cityList.append(button(`${row.node.name}${subdivision ? ', ' + subdivision.trim() : ''} · ${row.count}`,() => citySelect([row])));
  } };
  addButtons(regionRows.slice(0,12));
  if (regionRows.length > 12) {
    const more = button(`Show all ${regionRows.length} cities in this region`, () => { more.remove(); addButtons(regionRows.slice(12)); }); cityList.append(more);
  }
  if (!regionRows.length) cityList.append(el('p','No mapped cities in this region for the selected filters.','caption'));
  $('#unmapped-summary').textContent = `${metrics.unmapped.length} locations not plotted in this selection`;
  const missing = $('#unmapped-list'); missing.replaceChildren();
  for (const row of metrics.unmapped) {
    const show = row.shows[0], raw = show.location_as_listed;
    const link = el('a',`${raw.city}, ${raw.country} (${row.count})`); link.href = searchUrl([row.id]); missing.append(link);
  }
  if (!metrics.unmapped.length) missing.append(el('p','Every selected show has a matched city coordinate.'));
}
function highlightAct(id, layout) {
  state.selectedAct = id;
  const neighbors = new Set([id]);
  for (const pair of layout.links) if (pair.ids.includes(id)) for (const neighbor of pair.ids) neighbors.add(neighbor);
  $('#network').classList.add('has-selection');
  for (const node of $('#network').querySelectorAll('.network-node')) node.classList.toggle('connected',neighbors.has(node.dataset.id));
  for (const link of $('#network').querySelectorAll('.network-link')) link.classList.toggle('connected',JSON.parse(link.dataset.ids).includes(id));
  for (const choice of $('#act-list').querySelectorAll('button')) choice.setAttribute('aria-pressed',String(choice.dataset.id === id));
  const row = state.metrics.acts.find(row => row.id === id);
  const container = selection('#act-selection',row.node.name,entityShows([id]),[id],'Appearances as a listed opening act, not a measure of collaboration.');
  const partners = state.metrics.pairs.filter(pair => pair.ids.includes(id)).slice(0,8);
  container.append(el('h3','Other acts on the same bills'));
  const group = el('div',undefined,'pair-links');
  for (const pair of partners) {
    const other = state.index.nodes.get(pair.ids.find(value => value !== id));
    const link = el('a',`${other.name} · ${pair.count} shared ${pair.count === 1?'bill':'bills'} →`);
    link.href = searchUrl(pair.ids); group.append(link,el('br'));
  }
  if (!partners.length) group.append(el('p','No other identified opening acts are listed on these shows.'));
  container.append(group);
}
function renderNetwork() {
  $('#act-selection').hidden = true; state.selectedAct = null;
  const metrics = state.metrics, limit = Number($('#network-limit').value);
  const rows = metrics.acts.slice(0,limit), layout = networkLayout(rows,metrics.pairs);
  const canvas = svg('svg',{viewBox:'0 0 960 560',role:'group','aria-label':'Opening-act network. Circle area shows appearances with Fugazi; lines show shared bills.'});
  const byId = new Map(layout.nodes.map(node => [node.id,node]));
  const maxPair = Math.max(1,...layout.links.map(pair => pair.count));
  for (const pair of layout.links) {
    const a = byId.get(pair.ids[0]), b = byId.get(pair.ids[1]);
    const link = svg('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,'stroke-width':.8 + 4 * pair.count / maxPair,class:'network-link','data-ids':JSON.stringify(pair.ids)});
    svgTitle(link,`${a.node.name} + ${b.node.name}: ${pair.count} shared bills`); canvas.append(link);
  }
  for (const row of layout.nodes) {
    const group = svg('g',{class:'network-node',transform:`translate(${row.x},${row.y})`,tabindex:'0',role:'button','data-id':row.id,'aria-label':`${row.node.name}, ${row.count} shows with Fugazi. View connections.`});
    svgTitle(group,`${row.node.name} · ${row.count} shows`); group.append(svg('circle',{r:row.r}));
    const label = svg('text',{x:0,y:row.r+15,'text-anchor':'middle'}); label.textContent = row.node.name; group.append(label);
    activate(group,() => highlightAct(row.id,layout)); canvas.append(group);
  }
  $('#network').classList.remove('has-selection'); $('#network').replaceChildren(canvas);
  $('#network-summary').textContent = `${rows.length} of ${number(metrics.acts.length)} identified acts shown · ${layout.links.length} co-bill connections · ${number(metrics.withOpeners)} shows with identified openers`;
  const choices = $('#act-list'); choices.replaceChildren();
  for (const row of rows) {
    const choice = button(`${row.node.name} · ${row.count}`,() => highlightAct(row.id,layout)); choice.dataset.id = row.id; choice.setAttribute('aria-pressed','false'); choices.append(choice);
  }
  if (!rows.length) $('#network').replaceChildren(el('p','No identified opening acts are listed for this selection.','empty-chart'));
}
function update() {
  if (!state.index) return;
  const values = options(), from = Number(values.from), to = Number(values.to);
  if (!Number.isInteger(from) || !Number.isInteger(to) || from < 1987 || to > 2002 || from > to) {
    $('#scope-error').textContent = 'Choose a valid year range between 1987 and 2002, with the first year no later than the last.';
    return;
  }
  $('#scope-error').textContent = '';
  state.applied = values;
  const shows = search(state.index,values);
  state.metrics = summarize(state.index,shows,state.geography);
  $('#scope-summary').textContent = `${number(shows.length)} shows · ${number(state.metrics.setlists)} published setlists · ${from}–${to} · ${values.country ? state.index.nodes.get(values.country).name : 'Everywhere'}`;
  const params = new URLSearchParams(Object.entries(values).filter(([,value]) => value));
  history.replaceState(null,'',window.location.pathname+'?'+params);
  renderSongs(); renderMap(); renderNetwork();
}
async function load(path) { const response = await fetch(path); if (!response.ok) throw new Error(`${path}: ${response.status}`); return response.json(); }
async function init() {
  try {
    const [graph,geography,land,borders] = await Promise.all([load('data.json'),load('cities.json'),load('land.json'),load('borders.json')]);
    state.index = createIndex(graph); state.geography = geography; state.land = land; state.borders = borders;
    for (const country of graph.nodes.filter(node => node.type === 'country').sort((a,b) => a.name.localeCompare(b.name))) {
      const option = el('option',country.name); option.value = country.id; $('#country').append(option);
    }
    const params = new URLSearchParams(window.location.search);
    for (const key of ['from','to','country']) if (params.has(key)) $('#'+key).value = params.get(key);
    $('#apply').disabled = false;
    $('#scope-form').addEventListener('submit',event => { event.preventDefault(); update(); });
    $('#reset').addEventListener('click',() => { $('#from').value = '1987'; $('#to').value = '2002'; $('#country').value = ''; update(); });
    $('#region').addEventListener('change',renderMap); $('#network-limit').addEventListener('change',renderNetwork);
    update();
  } catch (error) {
    $('#scope-summary').textContent = 'The archive could not be loaded. Reload the page or visit the Search tab.';
    console.error(error);
  }
}
init();
