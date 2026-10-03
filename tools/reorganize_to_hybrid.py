#!/usr/bin/env python3
"""
Reorganize astro data into hybrid structure:

Primary storage (chronological):
  sessions/YYYY-MM-DD/[target]/[target]/ and [target]_sub/

Working view (target-organized):
  targets/[category]/[target]/YYYY-MM-DD -> symlink to sessions
  targets/[category]/[target]/final_outputs.png (permanent)
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

ASTRO_DIR = Path('/home/dlwiii/astro')
RAW_DIR = ASTRO_DIR / 'seestar_s30' / 'raw'
SESSIONS_DIR = ASTRO_DIR / 'sessions'
TARGETS_DIR = ASTRO_DIR / 'targets'

# Map targets to categories based on existing structure
def build_target_category_map():
    """Build a map of target names to categories."""
    target_map = {}

    for category in ['galaxies', 'clusters', 'nebulae']:
        category_path = TARGETS_DIR / category
        if category_path.exists():
            for target_dir in category_path.iterdir():
                if target_dir.is_dir():
                    target_map[target_dir.name.lower()] = (category, target_dir.name)

    return target_map

def normalize_target_name(raw_name):
    """Normalize target name from filename to directory name."""
    name = raw_name.strip().lower().replace(' ', '')
    return name

def parse_filename(filename):
    """Parse seestar filename to extract target, date, and type."""
    # Light_C 5_10.0s_IRCUT_20260204-193622.fit
    # Light_mosaic_NGC 2238_10.0s_LP_20260206-212344.fit
    # Stacked_269_C 5_10.0s_IRCUT_20260204-200746.jpg

    # Handle mosaic lights (target name comes after "mosaic_")
    if filename.startswith('Light_mosaic_'):
        match = re.match(r'Light_mosaic_(.+?)_[\d.]+s_\w+_(\d{8})-\d+(?:_thn)?\.(\w+)$', filename)
        if match:
            target = match.group(1)
            date_str = match.group(2)
            ext = match.group(3)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return {
                'target': target,
                'target_norm': normalize_target_name(target) + '_mosaic',
                'date': date,
                'type': 'light',
                'ext': ext,
                'filename': filename
            }

    elif filename.startswith('Light_'):
        match = re.match(r'Light_(.+?)_[\d.]+s_\w+_(\d{8})-\d+(?:_thn)?\.(\w+)$', filename)
        if match:
            target = match.group(1)
            date_str = match.group(2)
            ext = match.group(3)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return {
                'target': target,
                'target_norm': normalize_target_name(target),
                'date': date,
                'type': 'light',
                'ext': ext,
                'filename': filename
            }

    # Handle mosaic stacked files (target name comes after "mosaic_")
    elif filename.startswith('Stacked_') and '_mosaic_' in filename:
        match = re.match(r'Stacked_\d+_mosaic_(.+?)_[\d.]+s_\w+_(\d{8})-\d+.*\.(\w+)$', filename)
        if match:
            target = match.group(1)
            date_str = match.group(2)
            ext = match.group(3)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return {
                'target': target,
                'target_norm': normalize_target_name(target) + '_mosaic',
                'date': date,
                'type': 'stacked',
                'ext': ext,
                'filename': filename
            }

    elif filename.startswith('Stacked_'):
        match = re.match(r'Stacked_\d+_(.+?)_[\d.]+s_\w+_(\d{8})-\d+.*\.(\w+)$', filename)
        if match:
            target = match.group(1)
            date_str = match.group(2)
            ext = match.group(3)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return {
                'target': target,
                'target_norm': normalize_target_name(target),
                'date': date,
                'type': 'stacked',
                'ext': ext,
                'filename': filename
            }

    return None

def find_final_outputs():
    """Find final output files in existing targets structure."""
    final_outputs = []

    for category in ['galaxies', 'clusters', 'nebulae']:
        category_path = TARGETS_DIR / category
        if not category_path.exists():
            continue

        for target_dir in category_path.iterdir():
            if not target_dir.is_dir():
                continue

            # Look for final outputs (PNGs, processed FITs with dates in name)
            for item in target_dir.iterdir():
                if item.is_file():
                    # Match: c5_2026-02-04.png or c5_316x10sec_*.fit
                    if (item.suffix in ['.png', '.jpg'] or
                        ('x' in item.stem and 'sec' in item.stem)):
                        final_outputs.append({
                            'path': item,
                            'category': category,
                            'target': target_dir.name
                        })

    return final_outputs

def main():
    print("=" * 70)
    print("HYBRID STRUCTURE REORGANIZATION")
    print("=" * 70)
    print()

    # Build target category map
    print("Building target category map...")
    target_map = build_target_category_map()
    print(f"Found {len(target_map)} existing targets")
    print()

    # Scan raw files
    print(f"Scanning {RAW_DIR}...")
    if not RAW_DIR.exists():
        print(f"Error: {RAW_DIR} does not exist")
        return

    raw_files = [f for f in RAW_DIR.iterdir() if f.is_file()]
    print(f"Found {len(raw_files)} files in raw directory")
    print()

    # Parse and group files by date and target
    print("Parsing filenames...")
    files_by_date_target = defaultdict(lambda: {'light': [], 'stacked': []})
    unparsed = []

    for filepath in raw_files:
        parsed = parse_filename(filepath.name)
        if parsed:
            key = (parsed['date'], parsed['target_norm'], parsed['target'])
            files_by_date_target[key][parsed['type']].append(filepath)
        else:
            unparsed.append(filepath.name)

    total_parsed = sum(len(v['light']) + len(v['stacked'])
                      for v in files_by_date_target.values())
    print(f"Parsed {total_parsed} files")
    print(f"Unparsed: {len(unparsed)} files")

    if unparsed and len(unparsed) <= 20:
        print("\nUnparsed files:")
        for f in unparsed:
            print(f"  - {f}")
    elif unparsed:
        print(f"\nFirst 10 unparsed files:")
        for f in unparsed[:10]:
            print(f"  - {f}")

    # Find existing final outputs
    print("\nScanning for existing final outputs...")
    final_outputs = find_final_outputs()
    print(f"Found {len(final_outputs)} final output files")

    print()
    print("=" * 70)
    print("REORGANIZATION PLAN")
    print("=" * 70)
    print()

    # Group by date for display
    by_date = defaultdict(list)
    for (date, target_norm, target_raw), files in files_by_date_target.items():
        if target_norm in target_map:
            category, target_dir = target_map[target_norm]
            by_date[date].append((target_dir, files, category))

    for date in sorted(by_date.keys()):
        print(f"📅 {date}/")
        for target_dir, files, category in sorted(by_date[date]):
            light_count = len(files['light'])
            stacked_count = len(files['stacked'])
            print(f"   {target_dir}/")
            if stacked_count:
                print(f"     {target_dir}/      ({stacked_count} stacked)")
            if light_count:
                print(f"     {target_dir}_sub/  ({light_count} lights)")
            # Show symlink that will be created
            print(f"   → targets/{category}/{target_dir}/{date} (symlink)")
        print()

    if final_outputs:
        print("📁 Final outputs to keep in targets/:")
        for output in final_outputs[:10]:
            print(f"   {output['category']}/{output['target']}/{output['path'].name}")
        if len(final_outputs) > 10:
            print(f"   ... and {len(final_outputs) - 10} more")
        print()

    print("=" * 70)
    response = input("Proceed with reorganization? (yes/no): ")

    if response.lower() != 'yes':
        print("Cancelled.")
        return

    print()
    print("Reorganizing...")
    print()

    # Create sessions directory
    SESSIONS_DIR.mkdir(exist_ok=True)

    # Execute reorganization
    moved_count = 0

    for (date, target_norm, target_raw), files in sorted(files_by_date_target.items()):
        if target_norm not in target_map:
            print(f"⚠️  Skipping unknown target: {target_norm}")
            continue

        category, target_dir = target_map[target_norm]

        # Create session directory structure
        session_target_path = SESSIONS_DIR / date / target_dir
        session_target_path.mkdir(parents=True, exist_ok=True)

        # Move light frames to target_sub/
        if files['light']:
            sub_path = session_target_path / f"{target_dir}_sub"
            sub_path.mkdir(exist_ok=True)

            for filepath in files['light']:
                dest = sub_path / filepath.name
                shutil.move(str(filepath), str(dest))
                moved_count += 1

            print(f"✓ sessions/{date}/{target_dir}/{target_dir}_sub/ ({len(files['light'])} lights)")

        # Move stacked files to target/
        if files['stacked']:
            stacked_path = session_target_path / target_dir
            stacked_path.mkdir(exist_ok=True)

            for filepath in files['stacked']:
                dest = stacked_path / filepath.name
                shutil.move(str(filepath), str(dest))
                moved_count += 1

            print(f"✓ sessions/{date}/{target_dir}/{target_dir}/ ({len(files['stacked'])} stacked)")

        # Create symlink in targets
        target_link_path = TARGETS_DIR / category / target_dir / date
        if not target_link_path.exists():
            # Calculate relative path for symlink
            rel_path = os.path.relpath(session_target_path, target_link_path.parent)
            target_link_path.symlink_to(rel_path)
            print(f"✓ Created symlink: targets/{category}/{target_dir}/{date}")

    print()
    print(f"✓ Moved {moved_count} files to sessions/")
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Verify the structure looks correct:")
    print(f"   ls -la {SESSIONS_DIR}/")
    print(f"   ls -la {TARGETS_DIR}/galaxies/c5/")
    print()
    print("2. Remove old lights/ directories:")
    print(f"   find {TARGETS_DIR} -type d -name 'lights' -exec rm -rf {{}} +")
    print()
    print("3. Check for any remaining files in seestar/raw:")
    print(f"   ls {RAW_DIR}/")
    print()
    print("=" * 70)

if __name__ == '__main__':
    main()
