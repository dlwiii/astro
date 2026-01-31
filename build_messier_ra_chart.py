#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Find all stacked Messier images
def find_messier_images():
    messier_images = {}

    # Search for stacked images
    for jpg in Path('targets').rglob('Stacked_*M*.jpg'):
        if '_thn.jpg' in str(jpg):
            continue

        # Extract Messier number from filename
        match = re.search(r'[_\s]M\s+(\d{1,3})[\s_\.]', str(jpg), re.IGNORECASE)
        if match:
            m_num = int(match.group(1))
            if m_num < 1 or m_num > 110:
                continue

            # Extract stack count
            stack_match = re.search(r'Stacked_(\d+)_', str(jpg))
            stack_count = int(stack_match.group(1)) if stack_match else 0

            # Keep the highest stack count image
            if m_num not in messier_images or stack_count > messier_images[m_num][1]:
                messier_images[m_num] = (str(jpg), stack_count)

    return {k: v[0] for k, v in messier_images.items()}

# Messier objects with RA (hours), Dec (degrees), and names
# RA is in decimal hours, Dec is in decimal degrees
messier_data = {
    1: {"name": "Crab Nebula", "ra": 5.575, "dec": 22.017},
    2: {"name": "Globular Cluster", "ra": 21.558, "dec": -0.823},
    3: {"name": "Globular Cluster", "ra": 13.703, "dec": 28.377},
    4: {"name": "Globular Cluster", "ra": 16.393, "dec": -26.525},
    5: {"name": "Globular Cluster", "ra": 15.308, "dec": 2.081},
    6: {"name": "Butterfly Cluster", "ra": 17.667, "dec": -32.217},
    7: {"name": "Ptolemy Cluster", "ra": 17.897, "dec": -34.817},
    8: {"name": "Lagoon Nebula", "ra": 18.061, "dec": -24.383},
    9: {"name": "Globular Cluster", "ra": 17.318, "dec": -18.517},
    10: {"name": "Globular Cluster", "ra": 16.950, "dec": -4.100},
    11: {"name": "Wild Duck Cluster", "ra": 18.850, "dec": -6.267},
    12: {"name": "Globular Cluster", "ra": 16.783, "dec": -1.950},
    13: {"name": "Hercules Cluster", "ra": 16.694, "dec": 36.460},
    14: {"name": "Globular Cluster", "ra": 17.628, "dec": -3.250},
    15: {"name": "Globular Cluster", "ra": 21.500, "dec": 12.167},
    16: {"name": "Eagle Nebula", "ra": 18.314, "dec": -13.783},
    17: {"name": "Omega Nebula", "ra": 18.344, "dec": -16.183},
    18: {"name": "Open Cluster", "ra": 18.333, "dec": -17.117},
    19: {"name": "Globular Cluster", "ra": 17.044, "dec": -26.267},
    20: {"name": "Trifid Nebula", "ra": 18.035, "dec": -23.033},
    21: {"name": "Open Cluster", "ra": 18.079, "dec": -22.500},
    22: {"name": "Sagittarius Cluster", "ra": 18.605, "dec": -23.900},
    23: {"name": "Open Cluster", "ra": 17.950, "dec": -19.017},
    24: {"name": "Sagittarius Star Cloud", "ra": 18.283, "dec": -18.417},
    25: {"name": "Open Cluster", "ra": 18.528, "dec": -19.250},
    26: {"name": "Open Cluster", "ra": 18.758, "dec": -9.400},
    27: {"name": "Dumbbell Nebula", "ra": 19.992, "dec": 22.717},
    28: {"name": "Globular Cluster", "ra": 18.408, "dec": -24.867},
    29: {"name": "Open Cluster", "ra": 20.397, "dec": 38.533},
    30: {"name": "Globular Cluster", "ra": 21.673, "dec": -23.183},
    31: {"name": "Andromeda Galaxy", "ra": 0.712, "dec": 41.269},
    32: {"name": "Dwarf Galaxy", "ra": 0.712, "dec": 40.867},
    33: {"name": "Triangulum Galaxy", "ra": 1.564, "dec": 30.660},
    34: {"name": "Open Cluster", "ra": 2.708, "dec": 42.767},
    35: {"name": "Open Cluster", "ra": 6.148, "dec": 24.333},
    36: {"name": "Open Cluster", "ra": 5.602, "dec": 34.133},
    37: {"name": "Open Cluster", "ra": 5.875, "dec": 32.550},
    38: {"name": "Open Cluster", "ra": 5.478, "dec": 35.833},
    39: {"name": "Open Cluster", "ra": 21.533, "dec": 48.433},
    40: {"name": "Winnecke 4", "ra": 12.367, "dec": 58.083},
    41: {"name": "Open Cluster", "ra": 6.783, "dec": -20.750},
    42: {"name": "Orion Nebula", "ra": 5.588, "dec": -5.400},
    43: {"name": "De Mairan's Nebula", "ra": 5.592, "dec": -5.267},
    44: {"name": "Beehive Cluster", "ra": 8.667, "dec": 19.983},
    45: {"name": "Pleiades", "ra": 3.783, "dec": 24.117},
    46: {"name": "Open Cluster", "ra": 7.698, "dec": -14.817},
    47: {"name": "Open Cluster", "ra": 7.608, "dec": -14.500},
    48: {"name": "Open Cluster", "ra": 8.227, "dec": -5.800},
    49: {"name": "Elliptical Galaxy", "ra": 12.498, "dec": 8.000},
    50: {"name": "Open Cluster", "ra": 7.053, "dec": -8.333},
    51: {"name": "Whirlpool Galaxy", "ra": 13.498, "dec": 47.195},
    52: {"name": "Open Cluster", "ra": 23.408, "dec": 61.583},
    53: {"name": "Globular Cluster", "ra": 13.213, "dec": 18.167},
    54: {"name": "Globular Cluster", "ra": 18.917, "dec": -30.483},
    55: {"name": "Globular Cluster", "ra": 19.667, "dec": -30.967},
    56: {"name": "Globular Cluster", "ra": 19.278, "dec": 30.183},
    57: {"name": "Ring Nebula", "ra": 18.892, "dec": 33.033},
    58: {"name": "Barred Spiral Galaxy", "ra": 12.620, "dec": 11.817},
    59: {"name": "Elliptical Galaxy", "ra": 12.703, "dec": 11.650},
    60: {"name": "Elliptical Galaxy", "ra": 12.728, "dec": 11.550},
    61: {"name": "Spiral Galaxy", "ra": 12.365, "dec": 4.467},
    62: {"name": "Globular Cluster", "ra": 17.017, "dec": -30.117},
    63: {"name": "Sunflower Galaxy", "ra": 13.260, "dec": 42.033},
    64: {"name": "Black Eye Galaxy", "ra": 12.943, "dec": 21.683},
    65: {"name": "Spiral Galaxy", "ra": 11.308, "dec": 13.100},
    66: {"name": "Spiral Galaxy", "ra": 11.333, "dec": 12.983},
    67: {"name": "Open Cluster", "ra": 8.850, "dec": 11.800},
    68: {"name": "Globular Cluster", "ra": 12.658, "dec": -26.750},
    69: {"name": "Globular Cluster", "ra": 18.517, "dec": -32.350},
    70: {"name": "Globular Cluster", "ra": 18.723, "dec": -32.283},
    71: {"name": "Globular Cluster", "ra": 19.897, "dec": 18.783},
    72: {"name": "Globular Cluster", "ra": 20.892, "dec": -12.533},
    73: {"name": "Asterism", "ra": 20.980, "dec": -12.633},
    74: {"name": "Spiral Galaxy", "ra": 1.614, "dec": 15.783},
    75: {"name": "Globular Cluster", "ra": 20.101, "dec": -21.917},
    76: {"name": "Little Dumbbell Nebula", "ra": 1.703, "dec": 51.575},
    77: {"name": "Spiral Galaxy", "ra": 2.713, "dec": -0.013},
    78: {"name": "Reflection Nebula", "ra": 5.775, "dec": 0.050},
    79: {"name": "Globular Cluster", "ra": 5.405, "dec": -24.533},
    80: {"name": "Globular Cluster", "ra": 16.283, "dec": -22.983},
    81: {"name": "Bode's Galaxy", "ra": 9.928, "dec": 69.067},
    82: {"name": "Cigar Galaxy", "ra": 9.928, "dec": 69.683},
    83: {"name": "Southern Pinwheel", "ra": 13.617, "dec": -29.867},
    84: {"name": "Lenticular Galaxy", "ra": 12.423, "dec": 12.883},
    85: {"name": "Lenticular Galaxy", "ra": 12.425, "dec": 18.192},
    86: {"name": "Lenticular Galaxy", "ra": 12.433, "dec": 12.950},
    87: {"name": "Virgo A", "ra": 12.514, "dec": 12.392},
    88: {"name": "Spiral Galaxy", "ra": 12.533, "dec": 14.417},
    89: {"name": "Elliptical Galaxy", "ra": 12.592, "dec": 12.550},
    90: {"name": "Spiral Galaxy", "ra": 12.610, "dec": 13.167},
    91: {"name": "Barred Spiral Galaxy", "ra": 12.590, "dec": 14.500},
    92: {"name": "Globular Cluster", "ra": 17.283, "dec": 43.133},
    93: {"name": "Open Cluster", "ra": 7.745, "dec": -23.867},
    94: {"name": "Spiral Galaxy", "ra": 12.850, "dec": 41.120},
    95: {"name": "Barred Spiral Galaxy", "ra": 10.738, "dec": 11.700},
    96: {"name": "Spiral Galaxy", "ra": 10.775, "dec": 11.817},
    97: {"name": "Owl Nebula", "ra": 11.247, "dec": 55.017},
    98: {"name": "Spiral Galaxy", "ra": 12.230, "dec": 14.900},
    99: {"name": "Spiral Galaxy", "ra": 12.315, "dec": 14.417},
    100: {"name": "Spiral Galaxy", "ra": 12.373, "dec": 15.817},
    101: {"name": "Pinwheel Galaxy", "ra": 14.053, "dec": 54.350},
    102: {"name": "Spindle Galaxy", "ra": 15.100, "dec": 55.750},
    103: {"name": "Open Cluster", "ra": 1.558, "dec": 60.667},
    104: {"name": "Sombrero Galaxy", "ra": 12.667, "dec": -11.617},
    105: {"name": "Elliptical Galaxy", "ra": 10.788, "dec": 12.583},
    106: {"name": "Spiral Galaxy", "ra": 12.317, "dec": 47.300},
    107: {"name": "Globular Cluster", "ra": 16.542, "dec": -13.050},
    108: {"name": "Spiral Galaxy", "ra": 11.193, "dec": 55.667},
    109: {"name": "Barred Spiral Galaxy", "ra": 11.958, "dec": 53.383},
    110: {"name": "Dwarf Galaxy", "ra": 0.672, "dec": 41.683}
}

def generate_ra_chart_html():
    images = find_messier_images()

    # Organize objects by RA hour (0-23)
    ra_columns = {hour: [] for hour in range(24)}

    for m_num, data in messier_data.items():
        ra_hour = int(data['ra']) % 24
        ra_columns[ra_hour].append({
            'num': m_num,
            'name': data['name'],
            'ra': data['ra'],
            'dec': data['dec'],
            'image': images.get(m_num)
        })

    # Sort each column by declination (highest/north at top)
    for hour in ra_columns:
        ra_columns[hour].sort(key=lambda x: x['dec'], reverse=True)

    captured = len(images)
    percent = round(captured / 110 * 100, 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messier Catalog by Right Ascension</title>
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
        .stats {{
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.2em;
        }}
        .scroll-wrapper-top {{
            overflow-x: auto;
            overflow-y: hidden;
            margin-bottom: 10px;
        }}
        .scroll-content-top {{
            height: 20px;
        }}
        /* Custom scrollbar styling */
        .scroll-wrapper-top::-webkit-scrollbar,
        .ra-grid::-webkit-scrollbar {{
            height: 12px;
        }}
        .scroll-wrapper-top::-webkit-scrollbar-track,
        .ra-grid::-webkit-scrollbar-track {{
            background: #0a0a0a;
            border-radius: 10px;
        }}
        .scroll-wrapper-top::-webkit-scrollbar-thumb,
        .ra-grid::-webkit-scrollbar-thumb {{
            background: linear-gradient(90deg, #4a9eff, #2a5eff);
            border-radius: 10px;
        }}
        .scroll-wrapper-top::-webkit-scrollbar-thumb:hover,
        .ra-grid::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(90deg, #6ab5ff, #4a7eff);
        }}
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.95);
            cursor: pointer;
        }}
        .modal.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-content {{
            max-width: 90%;
            max-height: 90vh;
            object-fit: contain;
            border: 3px solid #4a9eff;
            border-radius: 8px;
            box-shadow: 0 0 30px rgba(74, 158, 255, 0.5);
        }}
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 35px;
            color: #fff;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
        .modal-close:hover {{
            color: #4a9eff;
        }}
        .ra-grid {{
            display: grid;
            grid-template-columns: repeat(24, 1fr);
            gap: 10px;
            margin: 0 auto;
            overflow-x: auto;
        }}
        .ra-column {{
            min-width: 120px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #0a0a0a;
        }}
        .ra-header {{
            background: #1a1a1a;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            border-bottom: 2px solid #333;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .messier-item {{
            padding: 8px;
            margin: 5px;
            background: #1a1a1a;
            border-radius: 4px;
            border: 1px solid #333;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .messier-item:hover {{
            background: #252525;
            border-color: #555;
        }}
        .messier-item.captured {{
            border-color: #4a9eff;
            background: #1a2a3a;
        }}
        .messier-number {{
            font-weight: bold;
            color: #4a9eff;
            font-size: 0.95em;
        }}
        .messier-name {{
            font-size: 0.75em;
            color: #aaa;
            margin-top: 2px;
        }}
        .coords {{
            font-size: 0.7em;
            color: #666;
            margin-top: 2px;
        }}
        .thumbnail {{
            width: 100%;
            height: 80px;
            object-fit: cover;
            border-radius: 3px;
            margin-top: 5px;
        }}
        .placeholder {{
            width: 100%;
            height: 80px;
            background: #0a0a0a;
            border-radius: 3px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
            font-size: 2em;
            margin-top: 5px;
        }}
        @media (max-width: 1400px) {{
            .ra-grid {{
                grid-template-columns: repeat(12, 1fr);
            }}
        }}
        @media (max-width: 800px) {{
            .ra-grid {{
                grid-template-columns: repeat(6, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <h1>Messier Catalog by Right Ascension</h1>
    <div class="stats">
        <strong>{captured}</strong> of <strong>110</strong> objects captured ({percent}%)
        <br>
        <span style="font-size: 0.8em; color: #888;">24 columns for RA hours 0-23, sorted by declination (north at top)</span>
    </div>
    <div class="scroll-wrapper-top" id="scrollTop">
        <div class="scroll-content-top" id="scrollContentTop"></div>
    </div>
    <div class="ra-grid" id="raGrid">
"""

    # Start at RA 20h and increase, wrapping around: 20, 21, 22, 23, 0, 1, 2, ... 18, 19
    hour_order = list(range(20, 24)) + list(range(0, 20))

    for hour in hour_order:
        html += f"""        <div class="ra-column">
            <div class="ra-header">RA {hour}h</div>
"""
        for obj in ra_columns[hour]:
            m_num = obj['num']
            name = obj['name']
            ra = obj['ra']
            dec = obj['dec']
            image_path = obj['image']

            item_class = "messier-item captured" if image_path else "messier-item"

            # Format coordinates
            ra_h = int(ra)
            ra_m = int((ra - ra_h) * 60)
            dec_sign = '+' if dec >= 0 else ''
            dec_d = int(abs(dec))
            dec_m = int((abs(dec) - dec_d) * 60)

            coord_str = f"RA {ra_h}h{ra_m}m, Dec {dec_sign}{int(dec)}°"

            if image_path:
                img_html = f'<img src="{image_path}" class="thumbnail" alt="M{m_num}" onclick="openModal(\'{image_path}\')" style="cursor: pointer;">'
            else:
                img_html = '<div class="placeholder">?</div>'

            html += f"""            <div class="{item_class}">
                <div class="messier-number">M{m_num}</div>
                <div class="messier-name">{name}</div>
                <div class="coords">{coord_str}</div>
                {img_html}
            </div>
"""

        html += """        </div>
"""

    html += """    </div>

    <!-- Modal for full-size image viewing -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        // Sync scroll bars
        const scrollTop = document.getElementById('scrollTop');
        const raGrid = document.getElementById('raGrid');
        const scrollContentTop = document.getElementById('scrollContentTop');

        // Set the width of top scroller to match content width
        function updateScrollWidth() {
            scrollContentTop.style.width = raGrid.scrollWidth + 'px';
        }

        // Sync scroll positions
        scrollTop.addEventListener('scroll', function() {
            raGrid.scrollLeft = scrollTop.scrollLeft;
        });

        raGrid.addEventListener('scroll', function() {
            scrollTop.scrollLeft = raGrid.scrollLeft;
        });

        // Update on load and resize
        window.addEventListener('load', updateScrollWidth);
        window.addEventListener('resize', updateScrollWidth);
        updateScrollWidth();

        // Modal functions
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

        // Close modal on Escape key
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
    html = generate_ra_chart_html()
    output_file = 'messier_ra_chart.html'
    with open(output_file, 'w') as f:
        f.write(html)
    print(f"Created {output_file}")

    # Print summary by RA hour
    images = find_messier_images()
    hour_order = list(range(20, 24)) + list(range(0, 20))
    print(f"\nMessier objects organized by RA hour (20h → 23h → 0h → 19h):")
    for hour in hour_order:
        objects_in_hour = [m for m, data in messier_data.items() if int(data['ra']) % 24 == hour]
        captured_in_hour = [m for m in objects_in_hour if m in images]
        if objects_in_hour:
            print(f"  RA {hour}h: {len(captured_in_hour)}/{len(objects_in_hour)} captured")
