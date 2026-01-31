#!/usr/bin/env python3
import os
import re
from pathlib import Path
from urllib.parse import quote

# Find all stacked Messier images
def find_messier_images():
    messier_images = {}

    # Priority 1: Look for final processed PNG files (M##_YYYY-MM-DD.png or M##.png)
    all_pngs = list(Path('targets').rglob('M*.png')) + list(Path('targets').rglob('m*.png'))
    for png in all_pngs:
        # Try to match dated pattern first: M31_2026-01-30.png
        match = re.search(r'M(\d{1,3})_(\d{4}-\d{2}-\d{2})\.png$', str(png), re.IGNORECASE)
        if match:
            m_num = int(match.group(1))
            date_str = match.group(2)

            # Only accept valid Messier numbers (1-110)
            if m_num < 1 or m_num > 110:
                continue

            # Keep the most recent date (highest date string)
            if m_num not in messier_images or date_str > messier_images[m_num][1]:
                messier_images[m_num] = (str(png), date_str, 'png')
        else:
            # Try undated pattern: M33.png
            match = re.search(r'M(\d{1,3})\.png$', str(png), re.IGNORECASE)
            if match:
                m_num = int(match.group(1))

                # Only accept valid Messier numbers (1-110)
                if m_num < 1 or m_num > 110:
                    continue

                # Only use if we don't already have a dated PNG
                if m_num not in messier_images or messier_images[m_num][2] != 'png':
                    messier_images[m_num] = (str(png), '0000-00-00', 'png')

    # Priority 2: Fallback to stacked JPG images (only if no PNG exists)
    for jpg in Path('targets').rglob('Stacked_*M*.jpg'):
        if '_thn.jpg' in str(jpg):
            continue

        # Extract Messier number from filename
        match = re.search(r'[_\s]M\s+(\d{1,3})[\s_\.]', str(jpg), re.IGNORECASE)
        if match:
            m_num = int(match.group(1))
            # Only accept valid Messier numbers (1-110)
            if m_num < 1 or m_num > 110:
                continue

            # Skip if we already have a PNG for this object
            if m_num in messier_images and messier_images[m_num][2] == 'png':
                continue

            # Extract stack count
            stack_match = re.search(r'Stacked_(\d+)_', str(jpg))
            stack_count = int(stack_match.group(1)) if stack_match else 0

            # Keep the highest stack count image
            if m_num not in messier_images or stack_count > messier_images[m_num][1]:
                messier_images[m_num] = (str(jpg), stack_count, 'jpg')

    return {k: v[0] for k, v in messier_images.items()}

# Messier object names
messier_names = {
    1: "M1 - Crab Nebula", 2: "M2 - Globular Cluster", 3: "M3 - Globular Cluster",
    4: "M4 - Globular Cluster", 5: "M5 - Globular Cluster", 6: "M6 - Butterfly Cluster",
    7: "M7 - Ptolemy Cluster", 8: "M8 - Lagoon Nebula", 9: "M9 - Globular Cluster",
    10: "M10 - Globular Cluster", 11: "M11 - Wild Duck Cluster", 12: "M12 - Globular Cluster",
    13: "M13 - Hercules Cluster", 14: "M14 - Globular Cluster", 15: "M15 - Globular Cluster",
    16: "M16 - Eagle Nebula", 17: "M17 - Omega Nebula", 18: "M18 - Open Cluster",
    19: "M19 - Globular Cluster", 20: "M20 - Trifid Nebula", 21: "M21 - Open Cluster",
    22: "M22 - Sagittarius Cluster", 23: "M23 - Open Cluster", 24: "M24 - Sagittarius Star Cloud",
    25: "M25 - Open Cluster", 26: "M26 - Open Cluster", 27: "M27 - Dumbbell Nebula",
    28: "M28 - Globular Cluster", 29: "M29 - Open Cluster", 30: "M30 - Globular Cluster",
    31: "M31 - Andromeda Galaxy", 32: "M32 - Dwarf Galaxy", 33: "M33 - Triangulum Galaxy",
    34: "M34 - Open Cluster", 35: "M35 - Open Cluster", 36: "M36 - Open Cluster",
    37: "M37 - Open Cluster", 38: "M38 - Open Cluster", 39: "M39 - Open Cluster",
    40: "M40 - Winnecke 4", 41: "M41 - Open Cluster", 42: "M42 - Orion Nebula",
    43: "M43 - De Mairan's Nebula", 44: "M44 - Beehive Cluster", 45: "M45 - Pleiades",
    46: "M46 - Open Cluster", 47: "M47 - Open Cluster", 48: "M48 - Open Cluster",
    49: "M49 - Elliptical Galaxy", 50: "M50 - Open Cluster", 51: "M51 - Whirlpool Galaxy",
    52: "M52 - Open Cluster", 53: "M53 - Globular Cluster", 54: "M54 - Globular Cluster",
    55: "M55 - Globular Cluster", 56: "M56 - Globular Cluster", 57: "M57 - Ring Nebula",
    58: "M58 - Barred Spiral Galaxy", 59: "M59 - Elliptical Galaxy", 60: "M60 - Elliptical Galaxy",
    61: "M61 - Spiral Galaxy", 62: "M62 - Globular Cluster", 63: "M63 - Sunflower Galaxy",
    64: "M64 - Black Eye Galaxy", 65: "M65 - Spiral Galaxy", 66: "M66 - Spiral Galaxy",
    67: "M67 - Open Cluster", 68: "M68 - Globular Cluster", 69: "M69 - Globular Cluster",
    70: "M70 - Globular Cluster", 71: "M71 - Globular Cluster", 72: "M72 - Globular Cluster",
    73: "M73 - Asterism", 74: "M74 - Spiral Galaxy", 75: "M75 - Globular Cluster",
    76: "M76 - Little Dumbbell Nebula", 77: "M77 - Spiral Galaxy", 78: "M78 - Reflection Nebula",
    79: "M79 - Globular Cluster", 80: "M80 - Globular Cluster", 81: "M81 - Bode's Galaxy",
    82: "M82 - Cigar Galaxy", 83: "M83 - Southern Pinwheel", 84: "M84 - Lenticular Galaxy",
    85: "M85 - Lenticular Galaxy", 86: "M86 - Lenticular Galaxy", 87: "M87 - Virgo A",
    88: "M88 - Spiral Galaxy", 89: "M89 - Elliptical Galaxy", 90: "M90 - Spiral Galaxy",
    91: "M91 - Barred Spiral Galaxy", 92: "M92 - Globular Cluster", 93: "M93 - Open Cluster",
    94: "M94 - Spiral Galaxy", 95: "M95 - Barred Spiral Galaxy", 96: "M96 - Spiral Galaxy",
    97: "M97 - Owl Nebula", 98: "M98 - Spiral Galaxy", 99: "M99 - Spiral Galaxy",
    100: "M100 - Spiral Galaxy", 101: "M101 - Pinwheel Galaxy", 102: "M102 - Spindle Galaxy",
    103: "M103 - Open Cluster", 104: "M104 - Sombrero Galaxy", 105: "M105 - Elliptical Galaxy",
    106: "M106 - Spiral Galaxy", 107: "M107 - Globular Cluster", 108: "M108 - Spiral Galaxy",
    109: "M109 - Barred Spiral Galaxy", 110: "M110 - Dwarf Galaxy"
}

def generate_html():
    images = find_messier_images()
    captured = len(images)
    percent = round(captured / 110 * 100, 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messier Catalog Progress</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #000;
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .filter-box {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .filter-box input {{
            padding: 10px;
            width: 300px;
            font-size: 16px;
            border: 2px solid #4a9eff;
            border-radius: 5px;
            background: #1a1a1a;
            color: #fff;
        }}
        .filter-box input:focus {{
            outline: none;
            border-color: #6bb6ff;
        }}
        .stats {{
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.2em;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .messier-card {{
            background: #1a1a1a;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            border: 2px solid #333;
        }}
        .messier-card.captured {{
            border-color: #4a9eff;
        }}
        .messier-card h3 {{
            margin: 0 0 10px 0;
            font-size: 1.1em;
        }}
        .image-container {{
            width: 100%%;
            height: 250px;
            background: #0a0a0a;
            border-radius: 4px;
            text-align: center;
            line-height: 250px;
        }}
        .image-container a {{
            display: inline-block;
            cursor: pointer;
        }}
        .image-container img {{
            max-width: 100%%;
            max-height: 250px;
            vertical-align: middle;
            transition: opacity 0.2s;
        }}
        .image-container img:hover {{
            opacity: 0.8;
        }}
        .placeholder {{
            color: #555;
            font-size: 3em;
        }}
        .status {{
            margin-top: 10px;
            font-size: 0.9em;
            color: #4a9eff;
        }}
        .status.not-captured {{
            color: #666;
        }}
        .nav-home {{
            position: fixed;
            top: 20px;
            left: 20px;
            padding: 10px 20px;
            background: #1a1a1a;
            border: 2px solid #4a9eff;
            border-radius: 5px;
            color: #4a9eff;
            text-decoration: none;
            font-size: 0.9em;
            transition: all 0.2s;
            z-index: 100;
        }}
        .nav-home:hover {{
            background: #4a9eff;
            color: #000;
        }}
    </style>
</head>
<body>
    <a href="index.html" class="nav-home">← Home</a>
    <h1>Messier Catalog Progress</h1>
    <div class="filter-box">
        <input type="text" id="filterInput" placeholder="Filter objects (e.g., M31, Galaxy, Nebula)..." onkeyup="filterGallery()">
    </div>
    <div class="stats">
        <strong>{captured}</strong> of <strong>110</strong> objects captured ({percent}%)
    </div>
    <div class="gallery">
"""

    for m_num in range(1, 111):
        name = messier_names.get(m_num, f"M{m_num}")

        if m_num in images:
            img_path = images[m_num]
            img_path_encoded = quote(img_path)
            card_class = "messier-card captured"
            img_html = f'<a href="{img_path_encoded}" target="_blank"><img src="{img_path_encoded}" alt="{name}"></a>'
            status = '<div class="status">✓ Captured</div>'
        else:
            card_class = "messier-card"
            img_html = '<div class="placeholder">?</div>'
            status = '<div class="status not-captured">Not yet captured</div>'

        html += f"""        <div class="{card_class}">
            <h3>{name}</h3>
            <div class="image-container">
                {img_html}
            </div>
            {status}
        </div>
"""

    html += """    </div>
    <script>
        function filterGallery() {
            const filter = document.getElementById('filterInput').value.toLowerCase();
            const cards = document.querySelectorAll('.messier-card');

            cards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                if (title.includes(filter)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

    return html

if __name__ == '__main__':
    html = generate_html()
    output_file = 'messier_catalog.html'
    with open(output_file, 'w') as f:
        f.write(html)
    print(f"Created {output_file}")

    # Print summary
    images = find_messier_images()
    print(f"\nCaptured {len(images)} objects:")
    for m_num in sorted(images.keys()):
        print(f"  M{m_num}")
