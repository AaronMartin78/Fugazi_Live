"""Install the static app into the existing Quarto source tree."""
from pathlib import Path
import shutil

root = Path('D:/aaron-martin-phd.dev')
config = root / '_quarto.yml'
text = config.read_text(encoding='utf-8')
if '    - fugazi/**' not in text:
    if '  resources:\n' not in text:
        raise ValueError('Expected existing Quarto resources list')
    text = text.replace('  resources:\n', '  resources:\n    - fugazi/**\n', 1)
if 'href: fugazi/index.html' not in text:
    anchor = '      - href: about.qmd\n'
    if anchor not in text:
        raise ValueError('Expected About navbar item')
    text = text.replace(anchor, '      - href: fugazi/index.html\n        text: Fugazi Live\n' + anchor, 1)
destination = root / 'fugazi'
destination.mkdir(exist_ok=True)
for name in ['index.html', 'style.css', 'app.mjs', 'graph.mjs', 'search-ui.css', 'technical.html', 'technical.css', 'explore.html', 'explore.css', 'explore.mjs', 'metrics.mjs', 'cities.json', 'land.json', 'borders.json', 'map-projection.mjs', 'GEOGRAPHY.md']:
    source = Path('web') / name
    target = destination / name
    if not target.exists() or source.read_text(encoding='utf-8') != target.read_text(encoding='utf-8'):
        shutil.copyfile(source, target)
for name in ['data.json', 'manifest.json']:
    source = Path('data/web') / name
    target = destination / name
    if not target.exists() or source.read_text(encoding='utf-8') != target.read_text(encoding='utf-8'):
        shutil.copyfile(source, target)
config.write_text(text, encoding='utf-8')
home = root / 'index.qmd'
home_text = home.read_text(encoding='utf-8')
if '(fugazi/index.html)' not in home_text:
    home.write_text(home_text.rstrip() + '\n- [Fugazi Live](fugazi/index.html): search published show metadata, explore setlists,\n  and find recordings in the Dischord Live Series archive.\n', encoding='utf-8')
print('Installed static app and linked it from Quarto navigation and homepage.')
