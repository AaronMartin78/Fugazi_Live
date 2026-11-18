// Pure graph indexing and deterministic search. No services or inference.
export const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();

export function createIndex(graph) {
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const shows = graph.nodes.filter(node => node.type === 'show');
  const related = new Map(shows.map(show => [show.id, new Set([show.id])]));
  const performances = new Map(shows.map(show => [show.id, []]));
  const byEntity = new Map();
  for (const edge of graph.edges) {
    if (!related.has(edge.source)) continue;
    related.get(edge.source).add(edge.target);
    if (edge.relation === 'performed') performances.get(edge.source).push(edge);
  }
  for (const [showId, entities] of related) for (const id of entities) {
    if (!byEntity.has(id)) byEntity.set(id, new Set());
    byEntity.get(id).add(showId);
  }
  for (const edges of performances.values()) edges.sort((a, b) => a.position - b.position);
  const labels = node => [node.name, ...(node.titles_as_listed || []), ...(node.names_as_listed || [])].map(normalize);
  const entities = graph.nodes.filter(node => byEntity.has(node.id)).map(node => ({...node, labels: labels(node)}));
  const haystacks = new Map(shows.map(show => [show.id, normalize([
    show.show_id, show.date, ...Object.values(show.location_as_listed || {}),
    ...[...related.get(show.id)].flatMap(id => labels(nodes.get(id)))
  ].join(' '))]));
  const aliases = new Set(entities.flatMap(node => node.labels));
  return {graph, nodes, shows, related, performances, byEntity, entities, haystacks, aliases};
}

export function search(index, {query = '', selected = [], from = '', to = '', country = '', setlistsOnly = false} = {}) {
  // Quoted text stays together. Each term and selected entity must match.
  const tokens = [...query.matchAll(/"([^"]+)"|(\S+)/g)].map(match => ({text: normalize(match[1] || match[2]), quoted: !!match[1]}));
  const terms = [];
  for (let i = 0; i < tokens.length;) {
    let end = i + 1;
    if (!tokens[i].quoted) {
      for (let j = i + 1; j <= tokens.length; j++) {
        if (tokens.slice(i, j).some(token => token.quoted)) break;
        if (index.aliases.has(tokens.slice(i, j).map(token => token.text).join(' '))) end = j;
      }
    }
    terms.push(tokens.slice(i, end).map(token => token.text).join(' '));
    i = end;
  }
  const groups = terms.map(term => {
    const exact = index.entities.filter(node => node.labels.includes(term));
    if (!exact.length) return {term};
    const showIds = new Set(exact.flatMap(node => [...index.byEntity.get(node.id)]));
    return {term, showIds};
  });
  return index.shows.filter(show => {
    const year = show.date?.slice(0, 4);
    if (from && year < String(from) || to && year > String(to)) return false;
    if (country && show.country_id !== country) return false;
    if (setlistsOnly && !index.performances.get(show.id).length) return false;
    if (!selected.every(id => index.byEntity.get(id)?.has(show.id))) return false;
    return groups.every(({term, showIds}) => showIds ? showIds.has(show.id)
      : /^\d{4}$/.test(term) ? year === term : index.haystacks.get(show.id).includes(term));
  }).sort((a, b) => a.date.localeCompare(b.date) || a.show_id.localeCompare(b.show_id));
}

export function suggestions(index, query) {
  const term = normalize(query.replaceAll('"', ''));
  if (!term) return [];
  return index.entities.filter(node => node.type !== 'show' && node.labels.some(label => label.includes(term)))
    .sort((a, b) => Number(b.labels.includes(term)) - Number(a.labels.includes(term)) || a.name.localeCompare(b.name)).slice(0, 12);
}

export function dischordUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === 'dischord.com' && !url.username && !url.password
      && !url.port && url.pathname.startsWith('/fugazi_live_series/') ? url.href : null;
  } catch { return null; }
}

export function cooccurrence(index, songId, filteredShows) {
  const counts = new Map();
  for (const show of filteredShows) {
    const songs = new Set(index.performances.get(show.id).map(edge => edge.target));
    if (!songs.has(songId)) continue;
    for (const id of songs) if (id !== songId) counts.set(id, (counts.get(id) || 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1] || index.nodes.get(a[0]).name.localeCompare(index.nodes.get(b[0]).name));
}
