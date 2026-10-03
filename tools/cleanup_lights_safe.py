#!/usr/bin/env python3
"""
Safely clean up old lights/ directories.

For each lights/ directory:
1. Check if all files exist in sessions/ structure
2. If yes: remove the lights/ directory
3. If no: migrate missing files to sessions/ first, then remove
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

ASTRO_DIR = Path('/home/dlwiii/astro')
SESSIONS_DIR = ASTRO_DIR / 'sessions'
TARGETS_DIR = ASTRO_DIR / 'targets'

# Map targets to categories (same as reorganize script)
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
                'ext': ext
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
                'ext': ext
            }

    # Handle mosaic stacked files
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
                'ext': ext
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
                'ext': ext
            }

    return None

def find_in_sessions(filename, target_name):
    """Check if a file exists in the sessions structure."""
    # Search in all date folders for this target
    for date_dir in SESSIONS_DIR.glob('*/'):
        if not date_dir.is_dir():
            continue

        # Check in target/target_sub/ for light frames
        target_sub = date_dir / target_name / f"{target_name}_sub" / filename
        if target_sub.exists():
            return target_sub

        # Check in target/target/ for stacked files
        target_main = date_dir / target_name / target_name / filename
        if target_main.exists():
            return target_main

    return None

def migrate_files_to_sessions(files_to_migrate, target_name):
    """Migrate files from lights/ to sessions/ structure."""
    print(f"\n  📦 Migrating {len(files_to_migrate)} files to sessions/")

    # Group by date
    by_date = defaultdict(list)
    for filepath, parsed in files_to_migrate:
        if parsed:
            by_date[parsed['date']].append((filepath, parsed))

    migrated_count = 0
    for date, files in sorted(by_date.items()):
        session_target_path = SESSIONS_DIR / date / target_name
        session_target_path.mkdir(parents=True, exist_ok=True)

        # Create sub directory for light frames
        sub_path = session_target_path / f"{target_name}_sub"
        sub_path.mkdir(exist_ok=True)

        for filepath, parsed in files:
            dest = sub_path / filepath.name
            if not dest.exists():
                shutil.move(str(filepath), str(dest))
                migrated_count += 1
                print(f"    ✓ {filepath.name} → sessions/{date}/{target_name}/{target_name}_sub/")

        # Create symlink in targets if it doesn't exist
        target_map = build_target_category_map()
        if target_name in target_map:
            category, _ = target_map[target_name]
            target_link_path = TARGETS_DIR / category / target_name / date
            if not target_link_path.exists():
                rel_path = os.path.relpath(session_target_path, target_link_path.parent)
                target_link_path.symlink_to(rel_path)
                print(f"    ✓ Created symlink: targets/{category}/{target_name}/{date}")

    return migrated_count

def main():
    print("=" * 70)
    print("SAFE LIGHTS DIRECTORY CLEANUP")
    print("=" * 70)
    print()

    # Find all lights directories
    lights_dirs = list(TARGETS_DIR.glob('*/*/lights'))

    if not lights_dirs:
        print("No lights/ directories found. Nothing to clean up!")
        return

    print(f"Found {len(lights_dirs)} lights/ directories\n")

    total_removed = 0
    total_migrated = 0

    for lights_dir in sorted(lights_dirs):
        # Get target name from parent directory
        target_name = lights_dir.parent.name
        category = lights_dir.parent.parent.name

        print(f"📂 Checking {category}/{target_name}/lights/")

        # Get all files in lights directory
        files = [f for f in lights_dir.iterdir() if f.is_file()]

        if not files:
            print(f"  ⚠️  Empty directory, removing...")
            lights_dir.rmdir()
            total_removed += 1
            continue

        print(f"  Found {len(files)} files")

        # Check each file
        missing_files = []
        found_count = 0

        for filepath in files:
            parsed = parse_filename(filepath.name)
            session_path = find_in_sessions(filepath.name, target_name)

            if session_path:
                found_count += 1
            else:
                missing_files.append((filepath, parsed))

        print(f"  ✓ {found_count} files found in sessions/")

        if missing_files:
            print(f"  ⚠️  {len(missing_files)} files NOT in sessions/")
            migrated = migrate_files_to_sessions(missing_files, target_name)
            total_migrated += migrated

        # Now check if lights directory is empty or can be removed
        remaining = [f for f in lights_dir.iterdir() if f.is_file()]
        if not remaining:
            print(f"  ✓ All files migrated, removing lights/")
            lights_dir.rmdir()
            total_removed += 1
        else:
            print(f"  ⚠️  {len(remaining)} files still in lights/ (could not migrate)")

    print()
    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Lights directories removed: {total_removed}")
    print(f"Files migrated to sessions: {total_migrated}")
    print()

if __name__ == '__main__':
    main()
