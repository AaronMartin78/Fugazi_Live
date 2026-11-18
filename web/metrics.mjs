// All metrics count distinct shows, not raw performance rows.
export function summarize(index, shows, geography) {
  const songCounts = new Map(), actCounts = new Map(), pairs = new Map(), cities = new Map();
  let setlists = 0, withOpeners = 0;
  for (const show of shows) {
    const tracks = index.performances.get(show.id);
    if (tracks.length) setlists++;
    for (const id of new Set(tracks.map(edge => edge.target))) {
      const song = index.nodes.get(id);
      if (song.review_status === 'release_matched' && song.album_id) songCounts.set(id, (songCounts.get(id) || 0) + 1);
    }
    const acts = [...index.related.get(show.id)].filter(id => index.nodes.get(id).type === 'band' && index.nodes.get(id).name.trim() !== '?').sort();
    if (acts.length) withOpeners++;
    for (const id of acts) actCounts.set(id, (actCounts.get(id) || 0) + 1);
    for (let a = 0; a < acts.length; a++) for (let b = a + 1; b < acts.length; b++) {
      const key = JSON.stringify([acts[a], acts[b]]);
      pairs.set(key, (pairs.get(key) || 0) + 1);
    }
    if (show.city_id) {
      if (!cities.has(show.city_id)) cities.set(show.city_id, []);
      cities.get(show.city_id).push(show);
    }
  }
  const rank = counts => [...counts].map(([id, count]) => ({id, count, node: index.nodes.get(id)}))
    .sort((a, b) => b.count - a.count || a.node.name.localeCompare(b.node.name) || a.id.localeCompare(b.id));
  const coordinates = new Map(geography.cities.map(city => [city.city_id, city]));
  const mapped = [], unmapped = [];
  for (const [id, cityShows] of cities) {
    const row = {id, count: cityShows.length, shows: cityShows, node: index.nodes.get(id), geo: coordinates.get(id)};
    (row.geo ? mapped : unmapped).push(row);
  }
  mapped.sort((a, b) => b.count - a.count || a.node.name.localeCompare(b.node.name));
  unmapped.sort((a, b) => a.node.name.localeCompare(b.node.name));
  return {shows, setlists, withOpeners, songs: rank(songCounts), acts: rank(actCounts),
    pairs: [...pairs].map(([key, count]) => ({ids: JSON.parse(key), count})).sort((a, b) => b.count - a.count || a.ids.join().localeCompare(b.ids.join())),
    mapped, unmapped, mappedShows: mapped.reduce((sum, city) => sum + city.count, 0)};
}

// Circle area, rather than radius, represents frequency.
export const nodeRadius = (count, max, radius = 30) => Math.sqrt(count / Math.max(1, max)) * radius;

export function networkLayout(rows, pairs, width = 960, height = 560) {
  const max = rows[0]?.count || 1;
  const nodes = rows.map((row, i) => ({...row, r: nodeRadius(row.count, max),
    x: width / 2 + Math.cos(i * 2.39996) * Math.sqrt(i + 1) * 36,
    y: height / 2 + Math.sin(i * 2.39996) * Math.sqrt(i + 1) * 26}));
  const byId = new Map(nodes.map(node => [node.id, node]));
  const links = pairs.filter(pair => pair.ids.every(id => byId.has(id)));
  for (let step = 0; step < 220; step++) {
    const alpha = .8 * (1 - step / 220) + .03;
    for (const node of nodes) { node.x += (width / 2 - node.x) * .003 * alpha; node.y += (height / 2 - node.y) * .003 * alpha; }
    for (let a = 0; a < nodes.length; a++) for (let b = a + 1; b < nodes.length; b++) {
      const first = nodes[a], second = nodes[b];
      let dx = second.x - first.x, dy = second.y - first.y;
      const distance = Math.hypot(dx, dy) || .1;
      const padding = first.r + second.r + 44;
      const push = Math.max(0, padding - distance) * .15 + 180 / (distance * distance);
      dx = dx / distance * push * alpha; dy = dy / distance * push * alpha;
      first.x -= dx; first.y -= dy; second.x += dx; second.y += dy;
    }
    for (const pair of links) {
      const a = byId.get(pair.ids[0]), b = byId.get(pair.ids[1]);
      const dx = b.x - a.x, dy = b.y - a.y, length = Math.hypot(dx, dy) || 1;
      const force = (length - 110) * .009 * alpha * Math.sqrt(pair.count);
      a.x += dx / length * force; a.y += dy / length * force;
      b.x -= dx / length * force; b.y -= dy / length * force;
    }
    for (const node of nodes) {
      node.x = Math.max(95, Math.min(width - 95, node.x));
      node.y = Math.max(55, Math.min(height - 55, node.y));
    }
  }
  return {nodes, links};
}
