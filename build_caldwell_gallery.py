#!/usr/bin/env python3
"""Build the Caldwell catalog progress page, matching messier_catalog.html.

Object data (designations, common names, types, Wikipedia links) comes from
targets/caldwell.json - no network access needed.

Images are matched to Caldwell numbers two ways:
  1. directories named for the Caldwell number: c1, c19, c20mex, c33_veil
  2. directories named for the NGC/IC designation, resolved through the
     designation_to_caldwell index - this is what finds C14 under ngc869/
     and C30 under ngc7331/, which a name-only match would miss.
"""
import json
import re
from pathlib import Path
from gallery_excludes import is_excluded
from urllib.parse import quote

from wikipedia_links import caldwell_url, anchor

CATALOG = Path('targets/caldwell.json')
TOTAL = 109


def load_catalog():
    doc = json.loads(CATALOG.read_text())
    objects = {e['number']: e for e in doc['objects']}
    return objects, doc['designation_to_caldwell']


def object_for_dir(dirname, reverse):
    """Caldwell number for a target directory name, or None."""
    d = dirname.lower()
    m = re.match(r'^c(\d{1,3})(?:[^0-9].*)?$', d)      # c1, c19, c20mex, c33_veil
    if m and 1 <= int(m.group(1)) <= TOTAL:
        return int(m.group(1))
    # NGC/IC directory names, via the cross-reference
    for key in (d.upper(), re.sub(r'^(ngc|ic)(\d+)$',
                                  lambda x: f'{x.group(1).upper()} {x.group(2)}', d)):
        if key in reverse:
            return int(reverse[key][1:])
    return None


def rank(path):
    """Higher is better: prefer PNG over JPG, and newer dates over older."""
    name = path.name
    date = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    date_str = date.group(1) if date else '0000-00-00'
    fmt = 2 if path.suffix.lower() == '.png' else 1
    stack = re.search(r'Stacked_(\d+)_', name)
    # obvious work-in-progress files lose to anything else for the same object
    not_test = 0 if re.search(r'test|tmp|draft', name, re.IGNORECASE) else 1
    return (not_test, fmt, date_str, int(stack.group(1)) if stack else 0, name)


def find_caldwell_images(reverse):
    """Caldwell number -> best image path."""
    best = {}
    for img in Path('targets').rglob('*'):
        if img.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            continue
        if '_thn' in img.name or '.thumb.' in img.name or 'lights' in str(img):
            continue
        if not img.exists():                      # skip broken symlinks
            continue
        if is_excluded(img):
            continue
        parts = img.parts
        if len(parts) < 3:
            continue
        num = object_for_dir(parts[2], reverse)
        if num is None:
            continue
        if num not in best or rank(img) > rank(best[num]):
            best[num] = img
    return {k: str(v) for k, v in best.items()}


def card_title(entry):
    """e.g. "C14 - Double Cluster" or "C3 - NGC 4236"."""
    label = entry['common_name'] or entry['primary_designation'] or entry['type']
    return f"{entry['caldwell']} - {label}"


def designation_line(entry):
    desigs = entry['ngc'] + entry['ic'] + entry['other_designations']
    return ', '.join(desigs) if desigs else '—'


def messier_style():
    """Reuse the Messier page's CSS so the two pages look identical."""
    src = Path(__file__).with_name('build_messier_gallery.py').read_text()
    style = re.search(r'<style>.*?</style>', src, re.DOTALL).group(0)
    return style.replace('{{', '{').replace('}}', '}').replace('messier-card', 'caldwell-card')


def generate_html():
    objects, reverse = load_catalog()
    images = find_caldwell_images(reverse)
    captured = len(images)
    percent = round(captured / TOTAL * 100, 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caldwell Catalog Progress</title>
    {messier_style()}
    <style>
        .designation {{
            font-size: 0.85em;
            opacity: 0.65;
            margin: -6px 0 8px 0;
        }}
    </style>
</head>
<body>
    <a href="index.html" class="nav-home">← Home</a>
    <h1>Caldwell Catalog Progress</h1>
    <div class="filter-box">
        <input type="text" id="filterInput" placeholder="Filter objects (e.g., C14, NGC 869, Galaxy, Nebula)..." onkeyup="filterGallery()">
    </div>
    <div class="stats">
        <strong>{captured}</strong> of <strong>{TOTAL}</strong> objects captured ({percent}%)
    </div>
    <div class="gallery">
"""

    for num in range(1, TOTAL + 1):
        entry = objects[num]
        name = card_title(entry)

        if num in images:
            img_path_encoded = quote(images[num])
            card_class = "caldwell-card captured"
            img_html = (f'<img src="{img_path_encoded}" alt="{name}" '
                        f'onclick="openModal(\'{img_path_encoded}\')">')
            status = '<div class="status">✓ Captured</div>'
        else:
            card_class = "caldwell-card"
            img_html = '<div class="placeholder">?</div>'
            status = '<div class="status not-captured">Not yet captured</div>'

        html += f"""        <div class="{card_class}">
            <h3>{anchor(caldwell_url(num), name)}</h3>
            <div class="designation">{designation_line(entry)} &middot; {entry['constellation']}</div>
            <div class="image-container">
                {img_html}
            </div>
            {status}
        </div>
"""

    html += """    </div>

    <!-- Modal for full-size image viewing -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        function filterGallery() {
            const filter = document.getElementById('filterInput').value.toLowerCase();
            const cards = document.querySelectorAll('.caldwell-card');

            cards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                const desig = card.querySelector('.designation').textContent.toLowerCase();
                if (title.includes(filter) || desig.includes(filter)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        function openModal(imagePath) {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.classList.add('active');
            modalImg.src = imagePath;
        }

        function closeModal() {
            const modal = document.getElementById('imageModal');
            modal.classList.remove('active');
        }

        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>
"""
    return html


if __name__ == '__main__':
    objects, reverse = load_catalog()
    images = find_caldwell_images(reverse)

    with open('caldwell_catalog.html', 'w') as f:
        f.write(generate_html())
    print("Created caldwell_catalog.html")

    print(f"\nCaptured {len(images)} of {TOTAL} objects:")
    for num in sorted(images):
        e = objects[num]
        via = Path(images[num]).parts[2]
        note = '' if via.lower().startswith('c') else f'   <- found via {via}/'
        print(f"  {e['caldwell']:5} {designation_line(e):22} {e['common_name'] or '':24}{note}")
