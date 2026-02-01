#!/usr/bin/env python3
import os
import re
from pathlib import Path
from urllib.parse import quote

def find_all_target_images():
    """Find the best image for each target across all categories."""
    target_images = {}

    # Define target categories
    categories = {
        'galaxies': 'Galaxy',
        'clusters': 'Cluster',
        'nebulae': 'Nebula'
    }

    for category, obj_type in categories.items():
        category_path = Path('targets') / category
        if not category_path.exists():
            continue

        # Get all target directories
        for target_dir in sorted(category_path.iterdir()):
            if not target_dir.is_dir():
                continue

            target_name = target_dir.name
            best_image = None
            best_priority = 999
            best_date = ''

            # Priority 1: Dated PNG files (name_YYYY-MM-DD.png)
            for png in target_dir.rglob('*.png'):
                # Skip thumbnails and intermediate files
                if '_thn.png' in str(png) or 'process' in str(png) or 'lights' in str(png):
                    continue

                # Skip broken symlinks
                if not png.exists():
                    continue

                # Match dated pattern: targetname_YYYY-MM-DD.png
                match = re.search(r'(\w+)_(\d{4}-\d{2}-\d{2})\.png$', png.name, re.IGNORECASE)
                if match and match.group(1).lower() in target_name.lower():
                    date_str = match.group(2)
                    if best_priority > 1 or (best_priority == 1 and date_str > best_date):
                        best_image = str(png)
                        best_priority = 1
                        best_date = date_str

            # Priority 2: Undated PNG files (targetname.png)
            if best_priority > 2:
                for png in target_dir.rglob('*.png'):
                    if '_thn.png' in str(png) or 'process' in str(png) or 'lights' in str(png):
                        continue

                    # Skip broken symlinks
                    if not png.exists():
                        continue

                    # Prefer exact match first
                    if png.stem.lower() == target_name.lower():
                        best_image = str(png)
                        best_priority = 2
                        best_date = ''
                        break
                    # Then partial match
                    elif png.stem.lower() in target_name.lower() or target_name.lower() in png.stem.lower():
                        if best_priority > 2:
                            best_image = str(png)
                            best_priority = 2
                            best_date = ''

            # Priority 3: Dated JPG files (name_YYYY-MM-DD.jpg)
            if best_priority > 3:
                for jpg in target_dir.rglob('*.jpg'):
                    # Skip thumbnails and intermediate files
                    if '_thn.jpg' in str(jpg) or 'process' in str(jpg) or 'lights' in str(jpg):
                        continue

                    # Skip broken symlinks
                    if not jpg.exists():
                        continue

                    # Match dated pattern: targetname_YYYY-MM-DD.jpg
                    match = re.search(r'(\w+)_(\d{4}-\d{2}-\d{2})\.jpg$', jpg.name, re.IGNORECASE)
                    if match and match.group(1).lower() in target_name.lower():
                        date_str = match.group(2)
                        if best_priority > 3 or (best_priority == 3 and date_str > best_date):
                            best_image = str(jpg)
                            best_priority = 3
                            best_date = date_str

            # Priority 4: Stacked JPG files (highest stack count)
            if best_priority > 4:
                max_stack = 0
                for jpg in target_dir.rglob('Stacked_*.jpg'):
                    if '_thn.jpg' in str(jpg) or 'lights' in str(jpg):
                        continue

                    # Skip broken symlinks
                    if not jpg.exists():
                        continue

                    stack_match = re.search(r'Stacked_(\d+)_', jpg.name)
                    if stack_match:
                        stack_count = int(stack_match.group(1))
                        if stack_count > max_stack:
                            best_image = str(jpg)
                            best_priority = 4
                            max_stack = stack_count

            if best_image:
                target_images[target_name] = {
                    'path': best_image,
                    'type': obj_type,
                    'category': category,
                    'display_name': format_target_name(target_name)
                }

    return target_images

def format_target_name(name):
    """Format target name for display."""
    # Handle Messier objects
    if name.lower().startswith('m') and name[1:].split('_')[0].isdigit():
        m_num = name[1:].split('_')[0]
        return f'M{m_num}'

    # Handle NGC objects
    if 'ngc' in name.lower():
        ngc_match = re.search(r'ngc(\d+)', name, re.IGNORECASE)
        if ngc_match:
            return f'NGC {ngc_match.group(1)}'

    # Handle IC objects
    if 'ic' in name.lower():
        ic_match = re.search(r'ic(\d+)', name, re.IGNORECASE)
        if ic_match:
            return f'IC {ic_match.group(1)}'

    # Handle Caldwell objects
    if name.lower().startswith('c') and name[1:].split('_')[0].isdigit():
        c_num = name[1:].split('_')[0]
        return f'C{c_num}'

    # Otherwise, title case with underscores replaced by spaces
    return name.replace('_', ' ').title()

def generate_html():
    """Generate HTML for all targets gallery."""
    targets = find_all_target_images()

    # Group by category
    galaxies = {k: v for k, v in targets.items() if v['category'] == 'galaxies'}
    clusters = {k: v for k, v in targets.items() if v['category'] == 'clusters'}
    nebulae = {k: v for k, v in targets.items() if v['category'] == 'nebulae'}

    total_count = len(targets)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Targets Gallery</title>
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
            margin-bottom: 15px;
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
            margin-bottom: 20px;
            font-size: 1.2em;
        }}
        .category-section {{
            margin-bottom: 40px;
        }}
        .category-header {{
            font-size: 1.8em;
            margin-bottom: 15px;
            padding: 10px;
            background: #1a1a1a;
            border-left: 4px solid #4a9eff;
        }}
        .target-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .target-card {{
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .target-card:hover {{
            border-color: #4a9eff;
            transform: scale(1.02);
        }}
        .target-name {{
            font-weight: bold;
            color: #4a9eff;
            margin-bottom: 5px;
            text-align: center;
        }}
        .target-type {{
            font-size: 0.8em;
            color: #888;
            text-align: center;
            margin-bottom: 8px;
        }}
        .target-image {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-radius: 4px;
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
    </style>
</head>
<body>
    <a href="index.html" class="nav-home">← Home</a>
    <h1>All Targets Gallery</h1>
    <div class="filter-box">
        <input type="text" id="filterInput" placeholder="Filter targets (e.g., M31, NGC, Nebula)..." onkeyup="filterTargets()">
    </div>
    <div class="stats">
        <strong>{total_count}</strong> targets captured
    </div>
"""

    # Add galaxies section
    if galaxies:
        html += f"""
    <div class="category-section">
        <div class="category-header">Galaxies ({len(galaxies)})</div>
        <div class="target-grid">
"""
        for name, info in sorted(galaxies.items(), key=lambda x: x[1]['display_name']):
            path_encoded = quote(info['path'])
            html += f"""
            <div class="target-card" data-name="{name}" data-type="galaxy" onclick="openModal('{path_encoded}')">
                <div class="target-name">{info['display_name']}</div>
                <div class="target-type">Galaxy</div>
                <img src="{path_encoded}" class="target-image" alt="{info['display_name']}">
            </div>
"""
        html += """
        </div>
    </div>
"""

    # Add clusters section
    if clusters:
        html += f"""
    <div class="category-section">
        <div class="category-header">Clusters ({len(clusters)})</div>
        <div class="target-grid">
"""
        for name, info in sorted(clusters.items(), key=lambda x: x[1]['display_name']):
            path_encoded = quote(info['path'])
            html += f"""
            <div class="target-card" data-name="{name}" data-type="cluster" onclick="openModal('{path_encoded}')">
                <div class="target-name">{info['display_name']}</div>
                <div class="target-type">Cluster</div>
                <img src="{path_encoded}" class="target-image" alt="{info['display_name']}">
            </div>
"""
        html += """
        </div>
    </div>
"""

    # Add nebulae section
    if nebulae:
        html += f"""
    <div class="category-section">
        <div class="category-header">Nebulae ({len(nebulae)})</div>
        <div class="target-grid">
"""
        for name, info in sorted(nebulae.items(), key=lambda x: x[1]['display_name']):
            path_encoded = quote(info['path'])
            html += f"""
            <div class="target-card" data-name="{name}" data-type="nebula" onclick="openModal('{path_encoded}')">
                <div class="target-name">{info['display_name']}</div>
                <div class="target-type">Nebula</div>
                <img src="{path_encoded}" class="target-image" alt="{info['display_name']}">
            </div>
"""
        html += """
        </div>
    </div>
"""

    html += """
    <!-- Modal for full-size image viewing -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        function openModal(imagePath) {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.classList.add('active');
            modalImg.src = decodeURIComponent(imagePath);
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

        // Filter function
        function filterTargets() {
            const filter = document.getElementById('filterInput').value.toLowerCase();
            const cards = document.querySelectorAll('.target-card');

            cards.forEach(card => {
                const name = card.dataset.name.toLowerCase();
                const type = card.dataset.type.toLowerCase();
                const text = name + ' ' + type;

                if (text.includes(filter)) {
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
    # Change to parent directory to access targets
    os.chdir('/home/dlwiii/astro')
    html = generate_html()

    output_path = Path('gallery/all_targets.html')
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated {output_path}")
