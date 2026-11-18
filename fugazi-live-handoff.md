# Fugazi_Live: Agreed Edits and Deployment Plan

Handoff document. Context: the repo `github.com/AaronMartin78/Fugazi_Live` maps the public Fugazi Live Series archive (HTML metadata only) into a graph JSON file: shows (show ID, date, venue, city, subdivision, country, opening acts, ordered setlist, source page URLs), songs, and the edges between them. Roughly 1000 shows, band inactive since 2003, so the dataset is effectively final. Goals: (1) a searchable static web app hosted on the owner's personal website, (2) a presentable repo to pitch to Dischord Records as an optional addition to their Fugazi Live Series archive.

## 1. Architecture decision (already made, do not revisit)

Static export, no server, no database in production, no LLM/inference.

- The graph database remains the local authoring/build tool only.
- Export the full graph to JSON (nodes + edges). Expected size: low single-digit MB.
- Build a single-page static app (HTML/JS) that loads the JSON and does everything client-side:
  - Text search over shows, songs, venues, dates via a client-side search library (Fuse.js or FlexSearch).
  - Graph traversal as plain JS operations: filter over the edge list for "shows where song X was played", two-hop lookups for co-occurrence.
- No frameworks required; keep it plain and lightweight. This is deliberate: zero maintenance for any future host (Dischord), and the plain aesthetic fits their site.
- A live database container was considered and rejected for deployment. Docker/compose is only a fallback if Dischord explicitly asks to self-host a live backend.

## 2. README edits (agreed)

The current README already has the right tone (fan project, links Dischord, states the crawler requests HTML only and never audio/samples/images/purchase endpoints, archive mapped as published). Keep all of that. Add/change:

1. Live demo URL at the top, once deployed.
2. A screenshot of the search UI.
3. One line stating what the graph contains: N shows, N songs, years covered (fill in real numbers).
4. Change "I am trying to build" to present tense ("This is..."), since it works.
5. Document the exported JSON schema so the dataset is usable standalone; the JSON is a downloadable artifact in its own right.

Do not claim organic traction. Repo clone stats (28 clones / 22 unique cloners, ~1 page view) are almost certainly automated crawlers, not users.

## 3. Feature additions (agreed, priority order)

Priority if only two get built: items 1 and 4.

1. **Fugazi Live Series links**: link every show to its page on the Dischord Live Series store (source URLs are already collected). This makes the tool a discovery front-end for their archive and is the core of the Dischord pitch.
2. **Song pages**: first/last performance, play count, frequency over years, longest gap between performances. All derivable from existing data.
3. **Co-occurrence**: songs most often played in the same set as a given song (edge-list lookup).
4. **Map**: shows plotted by city/country with a time filter. Serves as the visual hook for README screenshot and pitch.
5. **Era/year-range filtering** across all views.
6. **Data-quality page**: shows with incomplete setlists or missing fields, explicitly framed as "mapped as published, gaps not filled from outside sources".

Rejected: anything touching audio (stays on Dischord's side), natural-language/LLM query layer (cost, maintenance, undercuts the zero-infrastructure pitch). A structured UI (search field, filters, clickable nodes) covers the use cases.

## 4. Deployment to the personal website

Target: aaron-martin-phd.dev, a Quarto site in the public repo `github.com/AaronMartin78/aaron-martin-phd.dev`, hosted on GitHub Pages, rendered and deployed by GitHub Actions on push to main (no local Quarto install).

Agreed approach (option 1 of 2): mount the app inside the existing Quarto site repo.

- Put the app files (HTML/JS plus `data.json`) into the site repo, e.g. under a `fugazi/` directory.
- Either write the page as a Quarto page carrying raw HTML/JS, or keep it as a plain `index.html` in that directory and link/iframe it from a Quarto page. Quarto copies non-.qmd resources through to the rendered site; verify the directory is included in the output (add it to `resources` in `_quarto.yml` if needed).
- Deployment then rides the existing push-to-main GitHub Actions flow. No new infrastructure, no cost.
- GitHub Pages file-size limit is 100 MB per file; the JSON is nowhere near it.
- Data updates: re-export JSON locally from the graph DB, commit, push.

Alternative (not chosen): separate repo with its own GitHub Pages, iframed from the site. Only worth switching to if the app grows substantially.

## 5. Dischord pitch (for context, not a coding task)

Sequence: deploy on the personal site first, then email Dischord a short note with the live link and the repo. Frame as an addition to their archive (a search layer for the Live Series), never as a fix for their dated website; their 2011-era design is deliberate identity. Offer to match their visual style. The same live deployment doubles as the demo and a portfolio piece; the project can exist on the personal site and at Dischord simultaneously. The README's data-provenance paragraph (HTML only, no audio, mapped as published) preempts scraping concerns; republishing rights for the compiled dataset are worth confirming with Dischord in that conversation.
