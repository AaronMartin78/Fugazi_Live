import {createIndex, search, suggestions, dischordUrl, cooccurrence} from './graph.mjs?v=song-regions-1';
import {regionGroups} from './regions.mjs';

const $ = selector => document.querySelector(selector);
const state = {selected: [], limit: 40, active: null, index: null, results: []};
const types = {song: 'Song / track', band: 'Opening act', city: 'City', state: 'Subdivision', country: 'Country', venue: 'Venue'};
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, handler, className = '') {
  const node = el('button', text, className);
  node.type = 'button';
  node.addEventListener('click', handler);
  return node;
}
function sourceLink(show, large = false) {
  const url = dischordUrl(show.source_url);
  if (!url) return el('p', 'Source link unavailable');
  const link = el('a', 'View on Dischord ↗', large ? 'source-link' : '');
  link.href = url;
  return link;
}
function location(show) {
  const raw = show.location_as_listed;
  return [raw.city, raw.subdivision, raw.country].filter(Boolean).join(', ');
}
function entityName(node) {
  const parent = node.parent_id && state.index.nodes.get(node.parent_id);
  return node.name + (parent ? ` · ${parent.name}` : '');
}
function choose(id) {
  if (!state.selected.includes(id)) state.selected.push(id);
  $('#query').value = '';
  state.active = null;
  state.limit = 40;
  update();
}
function filters() {
  return {query: $('#query').value, selected: state.selected, from: $('#from').value,
    to: $('#to').value, country: $('#country').value, region: $('#search-region').value, setlistsOnly: $('#setlists-only').checked};
}
function urlParams(show = state.active && state.index.nodes.get(state.active)) {
  const options = filters(), params = new URLSearchParams();
  for (const key of ['query', 'from', 'to', 'country']) if (options[key]) params.set(key, options[key]);
  if (options.region) params.set('region', options.region);
  for (const id of state.selected) params.append('entity', id);
  if (options.setlistsOnly) params.set('setlists', '1');
  if (show) params.set('show', show.show_id);
  return params;
}
function syncUrl(push = false) {
  const params = urlParams();
  const url = locationPath() + (params.size ? '?' + params : '');
  if (push && url !== window.location.pathname + window.location.search) history.pushState(null, '', url);
  else history.replaceState(null, '', url);
}
function openShow(show) {
  state.active = show.id;
  renderShows(); renderShow(show); syncUrl(true);
  $('#detail').focus({preventScroll: true});
  $('#detail').scrollIntoView({block: 'start', behavior: 'smooth'});
}
function setlistLink(show, text, className) {
  const link = el('a', text, className);
  link.href = locationPath() + '?' + urlParams(show);
  link.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); openShow(show);
  });
  return link;
}
function restoreUrl() {
  const params = new URLSearchParams(window.location.search);
  for (const key of ['query', 'from', 'to', 'country']) $('#' + key).value = params.get(key) || '';
  $('#search-region').value = regionGroups[params.get('region')] ? params.get('region') : '';
  state.selected = [...new Set(params.getAll('entity'))].filter(id => state.index.byEntity.has(id));
  $('#setlists-only').checked = params.get('setlists') === '1';
  state.active = state.index.shows.find(show => show.show_id === params.get('show') || show.id === params.get('show'))?.id || null;
  state.limit = 40;
}
function renderChoices() {
  const selected = $('#selected');
  selected.replaceChildren(...state.selected.map(id => {
    const node = state.index.nodes.get(id);
    const chip = button(`${types[node.type]}: ${entityName(node)} ×`, () => {
      state.selected = state.selected.filter(value => value !== id);
      state.active = null;
      update();
    }, 'entity');
    chip.setAttribute('aria-label', `Remove filter ${entityName(node)}`);
    return chip;
  }));
  $('#suggestions').replaceChildren(...suggestions(state.index, $('#query').value)
    .filter(node => !state.selected.includes(node.id)).map(node => {
      const choice = button(entityName(node) + ' ', () => choose(node.id), 'entity');
      choice.append(el('small', `${types[node.type]} · ${state.index.byEntity.get(node.id).size} shows`));
      return choice;
    }));
}
function renderShows() {
  const list = $('#show-list');
  list.replaceChildren();
  $('#result-count').textContent = `${state.results.length.toLocaleString()} matches`;
  if (!state.results.length) list.append(el('p', 'No shows match these filters. Try removing a term or selecting a suggested entity.', 'empty'));
  for (const show of state.results.slice(0, state.limit)) {
    const card = el('article', undefined, 'show' + (state.active === show.id ? ' active' : ''));
    card.id = 'show-' + show.show_id;
    card.addEventListener('click', event => { if (!event.target.closest('a, button')) openShow(show); });
    card.append(setlistLink(show, `${show.date} · ${show.show_id}`, 'date'));
    const title = setlistLink(show, show.location_as_listed.venue, 'show-title');
    title.setAttribute('aria-label', `Open setlist: ${show.date}, ${show.location_as_listed.venue}, ${location(show)}`);
    card.append(title, el('p', location(show)));
    const count = state.index.performances.get(show.id).length;
    card.append(el('p', count ? `${count} listed tracks` : 'Setlist not published'));
    const actions = el('div', undefined, 'show-actions');
    actions.append(setlistLink(show, count ? 'Setlist →' : 'Show details →', 'setlist-action'), sourceLink(show));
    card.append(actions);
    list.append(card);
  }
  $('#more').hidden = state.limit >= state.results.length;
}
function renderShow(show) {
  const detail = $('#detail');
  detail.replaceChildren(el('p', `${show.date} · ${show.show_id}`, 'detail-label'),
    el('h2', show.location_as_listed.venue), el('p', location(show), 'detail-meta'), sourceLink(show, true));
  const actions = el('div', undefined, 'detail-actions');
  const permalink = el('a', 'Link to this setlist');
  permalink.href = locationPath() + '?show=' + encodeURIComponent(show.show_id);
  const back = button('← Back to shows', () => {
    const target = document.getElementById('show-' + show.show_id)?.querySelector('.setlist-action') || $('#results');
    target.focus({preventScroll:true}); target.scrollIntoView({behavior:'smooth',block:'center'});
  }, 'quiet');
  actions.append(permalink, back); detail.append(actions);
  const acts = [...state.index.related.get(show.id)].map(id => state.index.nodes.get(id)).filter(node => node.type === 'band');
  if (acts.length) {
    detail.append(el('h3', 'Listed opening acts'));
    const group = el('div', undefined, 'suggestions');
    group.append(...acts.map(act => button(act.name, () => choose(act.id), 'entity')));
    detail.append(group);
  }
  const tracks = state.index.performances.get(show.id);
  detail.append(el('h3', 'Setlist as published'));
  if (!tracks.length) detail.append(el('p', 'No setlist is published in the collected archive data. This does not mean no songs were played.', 'empty'));
  if (tracks.some((track, index) => track.position !== index + 1)) detail.append(el('p', 'The source has duplicate or skipped track numbers. Entries are preserved as published.', 'warning'));
  const list = el('ol', undefined, 'tracks');
  for (const edge of tracks) {
    const song = state.index.nodes.get(edge.target);
    const item = el('li');
    const label = button(edge.title_as_listed, () => choose(song.id), 'track-button');
    label.setAttribute('aria-label', `Find shows containing ${song.name}`);
    const album = state.index.graph.albums.find(album => album.id === song.album_id);
    const content = el('div');
    content.append(label);
    if (album) content.append(el('span', album.title || album.name, 'album'));
    item.append(el('span', `${edge.position}.`, 'track-number'), content);
    list.append(item);
  }
  detail.append(list);
}
function renderOverview() {
  const detail = $('#detail');
  const songId = state.selected.find(id => state.index.nodes.get(id).type === 'song');
  if (!songId) {
    detail.replaceChildren(el('h2', 'Follow a connection'), el('p', 'Select a show to see its published setlist. Select a song or another entity to find the shows connected to it.', 'empty'));
    return;
  }
  const song = state.index.nodes.get(songId);
  const shows = state.results;
  detail.replaceChildren(el('p', 'SELECTED SONG / TRACK', 'detail-label'), el('h2', song.name));
  detail.append(el('p', `${shows.length} matching shows with this track listed. Counts below follow the current filters.`, 'detail-meta'));
  if (shows.length) detail.append(el('p', `First listed: ${shows[0].date} · Last listed: ${shows.at(-1).date}`, 'detail-meta'));
  detail.append(el('h3', 'Often in the same set'));
  const group = el('div', undefined, 'suggestions');
  for (const [id, count] of cooccurrence(state.index, songId, shows).slice(0, 10)) {
    const node = state.index.nodes.get(id);
    group.append(button(`${node.name} · ${count} shows`, () => choose(id), 'entity'));
  }
  detail.append(group, el('p', 'Select another track to find shows containing both. Co-occurrence counts each show once, including when the source repeats a track.', 'hint'));
}
function update({write = true} = {}) {
  if (!state.index) return;
  const options = filters();
  const invalid = options.from && options.to && Number(options.from) > Number(options.to);
  $('#filter-error').textContent = invalid ? 'From year must be no later than to year.' : '';
  state.results = invalid ? [] : search(state.index, options);
  renderChoices();
  renderShows();
  const show = state.active && state.results.find(show => show.id === state.active);
  if (show) renderShow(show); else { state.active = null; renderOverview(); }
  if (write) syncUrl();
}
function locationPath() { return window.location.pathname; }

async function init() {
  try {
    const response = await fetch('./data.json');
    if (!response.ok) throw new Error(`Data request failed (${response.status})`);
    const graph = await response.json();
    if (graph.schema_version !== 2) throw new Error('Unsupported graph schema');
    state.index = createIndex(graph);
    const years = state.index.shows.map(show => show.date.slice(0, 4)).sort();
    $('#summary').textContent = `${state.index.shows.length.toLocaleString()} shows · ${years[0]}–${years.at(-1)} · ${graph.nodes.filter(node => node.type === 'song').length} song / track labels`;
    for (const country of graph.nodes.filter(node => node.type === 'country').sort((a, b) => a.name.localeCompare(b.name))) {
      const option = el('option', country.name); option.value = country.id; $('#country').append(option);
    }
    for (const [id,region] of Object.entries(regionGroups)) { const option=el('option',region.name); option.value=id; $('#search-region').append(option); }
    restoreUrl();
    const missing = state.index.shows.filter(show => !state.index.performances.get(show.id).length).length;
    const review = graph.nodes.filter(node => node.type === 'song' && node.review_status === 'needs_review').length;
    $('#quality').append(el('p', `${missing} shows have no listed setlist; ${review} track labels require identity review. Source numbering anomalies are flagged in show details. Original fields remain unchanged.`));
    $('#query').disabled = false; $('#search-button').disabled = false;
    $('#detail').tabIndex = -1;
    $('#search-form').addEventListener('submit', event => { event.preventDefault(); state.active = null; state.limit = 40; update(); });
    let timer;
    $('#query').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { state.active = null; state.limit = 40; update(); }, 180); });
    for (const id of ['from', 'to', 'country', 'search-region', 'setlists-only']) $('#' + id).addEventListener('change', () => { state.active = null; state.limit = 40; update(); });
    $('#more').addEventListener('click', () => { state.limit += 40; renderShows(); });
    $('#reset').addEventListener('click', () => {
      state.selected = []; state.active = null; state.limit = 40;
      for (const id of ['query', 'from', 'to', 'country', 'search-region']) $('#' + id).value = '';
      $('#setlists-only').checked = false; update();
    });
    update();
    if (state.active) $('#detail').scrollIntoView({block:'start'});
    window.addEventListener('popstate', () => {
      restoreUrl(); update({write:false});
      if (state.active) $('#detail').scrollIntoView({block:'start'});
    });
  } catch (error) {
    $('#summary').textContent = 'The archive could not be loaded. Please reload the page or visit Dischord directly.';
    console.error(error);
  }
}
init();
