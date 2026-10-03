#!/usr/bin/env python3
"""
Seestar Import to Sessions (Hard Link Version)

Imports data from Seestar directly to sessions folder with hard links to targets.

Structure:
  1. Copy from Seestar → sessions/YYYY-MM-DD/target/ (primary storage)
  2. Hard link from sessions → targets/category/target/YYYY-MM-DD (target-organized view)

Usage:
  seestar_import_sessions.py                    # List available targets
  seestar_import_sessions.py "M 44"             # Import target (auto-detect type)
  seestar_import_sessions.py "NGC 2238"         # Import target (auto-detect type)
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from collections import defaultdict

# Configuration
def _find_seestar_mount():
    """Locate the Seestar's MyWorks folder.

    Override with the SEESTAR_PATH env var. Otherwise try the udisks mount
    point used on Arch/Omarchy (/run/media/$USER) and the Debian/Mint one
    (/media/$USER), for any volume whose name starts with "Seestar".
    """
    env = os.environ.get("SEESTAR_PATH")
    if env:
        return Path(env)
    user = os.environ.get("USER", "dlwiii")
    for base in (Path("/run/media") / user, Path("/media") / user):
        if base.is_dir():
            for vol in sorted(base.iterdir()):
                if vol.name.lower().startswith("seestar") and (vol / "MyWorks").is_dir():
                    return vol / "MyWorks"
    return Path("/run/media") / user / "Seestar" / "MyWorks"


def _find_astro_root():
    """Walk up from this file to the directory holding sessions/ and targets/.

    Works whether the script runs from ~/astro/scripts (a symlink) or from its
    real home in the gallery repo's tools/ folder. ASTRO_DIR env var overrides.
    """
    env = os.environ.get("ASTRO_DIR")
    if env:
        return Path(env)
    for p in Path(__file__).resolve().parents:
        if (p / "sessions").is_dir() and (p / "targets").is_dir():
            return p
    return Path.home() / "astro"


SEESTAR_MOUNT = _find_seestar_mount()
ASTRO_DIR = _find_astro_root()  # ~/astro, i.e. /mnt/media2/astro
SESSIONS_DIR = ASTRO_DIR / "sessions"
TARGETS_DIR = ASTRO_DIR / "targets"
CATALOG_FILE = TARGETS_DIR / "CATALOG.md"

# Colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

# Built-in target type lookup (from original seestar_import.sh)
BUILTIN_TARGET_TYPES = {
    # Clusters
    "M 13": "cluster", "M 15": "cluster", "M 44": "cluster",
    "M 45": "cluster", "M 39": "cluster", "M 35": "cluster",
    "M 36": "cluster", "M 37": "cluster", "M 38": "cluster",
    "M 46": "cluster", "M 47": "cluster", "M 48": "cluster",
    "M 67": "cluster", "M 92": "cluster", "M 103": "cluster",
    "NGC 869": "cluster", "NGC 884": "cluster",

    # Galaxies
    "M 31": "galaxy", "M 32": "galaxy", "M 33": "galaxy",
    "M 51": "galaxy", "M 63": "galaxy", "M 64": "galaxy",
    "M 65": "galaxy", "M 66": "galaxy", "M 74": "galaxy",
    "M 77": "galaxy", "M 81": "galaxy", "M 82": "galaxy",
    "M 83": "galaxy", "M 94": "galaxy", "M 101": "galaxy",
    "M 104": "galaxy", "M 106": "galaxy", "M 108": "galaxy",
    "M 110": "galaxy", "NGC 891": "galaxy", "NGC 7331": "galaxy",

    # Nebulae
    "M 1": "nebula", "M 8": "nebula", "M 16": "nebula",
    "M 17": "nebula", "M 20": "nebula", "M 27": "nebula",
    "M 42": "nebula", "M 43": "nebula", "M 57": "nebula",
    "M 76": "nebula", "M 78": "nebula", "M 97": "nebula",
    "NGC 281": "nebula", "NGC 281W": "nebula",
    "NGC 1499": "nebula", "NGC 2024": "nebula",
    "NGC 6960": "nebula", "NGC 6992": "nebula", "NGC 6995": "nebula",
    "NGC 7000": "nebula", "NGC 7023": "nebula", "NGC 7380": "nebula",
    "IC 434": "nebula", "IC 1318": "nebula", "IC 1396": "nebula", "IC 1805": "nebula",
    "IC 1848": "nebula", "IC 2118": "nebula",
    "C 20": "nebula", "C 33": "nebula", "C 34": "nebula",
    "Alnitak": "nebula", "AE Aurigae": "nebula", "Unknown": "nebula",
    "IC 447": "nebula", "NGC 2392": "nebula", "C 9": "nebula", "C 1": "cluster",

    # Solar system
    "Jupiter": "solar_system", "Saturn": "solar_system", "Uranus": "solar_system",
    "Neptune": "solar_system", "Mars": "solar_system", "Venus": "solar_system",
    "Moon": "solar_system", "Sun": "solar_system",

    # Stars (single stars, doubles, asterisms)
    "M 40": "star", "M 73": "star",
    "Deneb": "star", "Sadr": "star", "Dabih": "star", "HIP 106890": "star",
    "V429 Cephei": "star", "Zeta Capricorni": "star", "Theta Capricorni": "star",
    "Phi Aurigae": "star",
}

TYPE_DIRS = {
    "cluster": "clusters",
    "galaxy": "galaxies",
    "nebula": "nebulae",
    "solar_system": "solar_system",
    "star": "stars",
}


def parse_catalog_file():
    """Parse CATALOG.md to extract target types."""
    catalog_types = {}

    if not CATALOG_FILE.exists():
        return catalog_types

    current_category = None
    current_target = None

    with open(CATALOG_FILE, 'r') as f:
        for line in f:
            line = line.strip()

            # Detect category sections
            if line == "## Galaxies":
                current_category = "galaxy"
            elif line == "## Star Clusters":
                current_category = "cluster"
            elif line == "## Nebulae":
                current_category = "nebula"
            elif line.startswith("## "):
                current_category = None

            # Extract target designations
            if current_category and line.startswith("### "):
                # Parse target name from header (e.g., "### M31 - Andromeda Galaxy")
                target_name = line[4:].split(" - ")[0].strip()
                current_target = target_name
                catalog_types[target_name] = current_category

            # Extract additional designations (Messier, NGC, IC, Caldwell)
            elif current_category and current_target:
                if line.startswith("- **Messier:**"):
                    messier = line.split("**Messier:**")[1].strip()
                    catalog_types[messier] = current_category
                elif line.startswith("- **NGC:**"):
                    ngc = line.split("**NGC:**")[1].split(",")[0].strip()
                    if ngc and ngc != "None" and not ngc.startswith("("):
                        catalog_types[ngc] = current_category
                elif line.startswith("- **IC:**"):
                    ic = line.split("**IC:**")[1].split(",")[0].strip()
                    if ic and ic != "None":
                        catalog_types[ic] = current_category
                elif line.startswith("- **Caldwell:**"):
                    caldwell = line.split("**Caldwell:**")[1].split(",")[0].strip()
                    if caldwell and caldwell != "None":
                        catalog_types[caldwell] = current_category

    return catalog_types


def get_target_type(target_name, catalog_types):
    """
    Determine target type using multiple sources:
    1. Built-in lookup table
    2. CATALOG.md file
    3. Ask user if unknown
    """
    # Try built-in table first
    if target_name in BUILTIN_TARGET_TYPES:
        return BUILTIN_TARGET_TYPES[target_name]

    # Try catalog file
    if target_name in catalog_types:
        return catalog_types[target_name]

    # Ask user
    print(f"{Colors.YELLOW}Unknown target type for '{target_name}'{Colors.NC}")
    print("Please specify: cluster, galaxy, nebula, solar_system, or star")

    while True:
        target_type = input("Type: ").strip().lower()
        if target_type in TYPE_DIRS:
            return target_type
        print(f"{Colors.RED}Invalid type. Must be one of: {', '.join(TYPE_DIRS)}.{Colors.NC}")


def normalize_target_name(target_name):
    """Normalize target name for directory names."""
    # Remove spaces, lowercase
    return target_name.replace(" ", "").lower()


def parse_filename(filename):
    """Parse Seestar filename to extract target, date, and type."""
    # Handle mosaic lights
    if filename.startswith('Light_mosaic_'):
        match = re.match(r'Light_mosaic_(.+?)_[\d.]+s_\w+_(\d{8})-\d+\.(\w+)$', filename)
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
            }

    # Handle regular lights
    elif filename.startswith('Light_'):
        match = re.match(r'Light_(.+?)_[\d.]+s_\w+_(\d{8})-\d+\.(\w+)$', filename)
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
            }

    # Handle mosaic stacked
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
            }

    # Handle regular stacked
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
            }

    return None


def list_targets():
    """List all available targets on Seestar."""
    print(f"{Colors.BLUE}=== Available Targets on Seestar ==={Colors.NC}\n")

    # Collect all target names: from *_sub folders and standalone main folders
    seen_targets = set()
    target_names = []
    for d in sorted(SEESTAR_MOUNT.iterdir()):
        if not d.is_dir():
            continue
        if d.name.endswith("_sub"):
            name = d.name[:-4]
        else:
            name = d.name
        if name not in seen_targets:
            seen_targets.add(name)
            target_names.append(name)

    found_any = False
    for target_name in sorted(target_names):
        sub_dir = SEESTAR_MOUNT / f"{target_name}_sub"
        main_dir = SEESTAR_MOUNT / target_name

        # Count .fit files in subs folder
        fit_count = len(list(sub_dir.glob("*.fit"))) if sub_dir.exists() else 0

        # Count files in main folder
        main_count = 0
        jpg_count = 0
        if main_dir.exists():
            main_count = len(list(main_dir.glob("*.fit")))
            jpg_count = len(list(main_dir.glob("*.jpg")))

        # Skip if no files
        if fit_count == 0 and main_count == 0 and jpg_count == 0:
            continue

        # Get dates from filenames
        all_files = list(sub_dir.glob("*.fit"))
        if main_dir.exists():
            all_files.extend(list(main_dir.glob("*.fit")))

        dates = set()
        for f in all_files:
            parsed = parse_filename(f.name)
            if parsed:
                dates.add(parsed['date'])

        dates_str = ", ".join(sorted(dates))
        session_count = len(dates)

        # Get target type
        catalog_types = parse_catalog_file()
        target_type = BUILTIN_TARGET_TYPES.get(target_name,
                     catalog_types.get(target_name, "unknown"))

        # Format output
        if main_count > 0 and jpg_count > 0:
            print(f"  {target_name:<20} {fit_count:4d} subs + {main_count} main + {jpg_count} jpg, "
                  f"{session_count} session(s): {dates_str}  [{target_type}]")
        elif main_count > 0:
            print(f"  {target_name:<20} {fit_count:4d} subs + {main_count} main, "
                  f"{session_count} session(s): {dates_str}  [{target_type}]")
        elif jpg_count > 0:
            print(f"  {target_name:<20} {fit_count:4d} subs + {jpg_count} jpg, "
                  f"{session_count} session(s): {dates_str}  [{target_type}]")
        else:
            print(f"  {target_name:<20} {fit_count:4d} subs, "
                  f"{session_count} session(s): {dates_str}  [{target_type}]")

    if not found_any:
        print(f"{Colors.RED}No targets found on Seestar{Colors.NC}")

    print()


def import_target(target_name):
    """Import a target from Seestar to sessions structure."""
    source_sub = SEESTAR_MOUNT / f"{target_name}_sub"
    source_main = SEESTAR_MOUNT / target_name

    # Check if at least one source exists
    if not source_sub.exists() and not source_main.exists():
        print(f"{Colors.RED}Error: Cannot find '{source_sub}' or '{source_main}'{Colors.NC}\n")
        list_targets()
        return 1

    has_sub = source_sub.exists()
    has_main = source_main.exists()

    # Ensure directories exist
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Get target type
    catalog_types = parse_catalog_file()
    target_type = get_target_type(target_name, catalog_types)
    type_dir = TYPE_DIRS[target_type]

    # Clean target name for directory
    target_clean = normalize_target_name(target_name)

    print(f"{Colors.BLUE}=== Seestar Import (Sessions + Hard Links) ==={Colors.NC}")
    print(f"Target: {Colors.GREEN}{target_name}{Colors.NC} -> {target_clean} ({target_type})")
    print(f"Primary storage: {Colors.GREEN}{SESSIONS_DIR}{Colors.NC}")
    if has_sub and has_main:
        print("Sources: subs + main folders")
    elif has_sub:
        print("Sources: subs folder only")
    else:
        print("Sources: main folder only")
    print()

    # Parse all files to get dates
    all_files = []
    if has_sub:
        all_files.extend(source_sub.glob("*.fit"))
    if has_main:
        all_files.extend(source_main.glob("*.fit"))

    files_by_date = defaultdict(lambda: {'light': [], 'stacked': []})
    for filepath in all_files:
        parsed = parse_filename(filepath.name)
        if parsed:
            files_by_date[parsed['date']][parsed['type']].append(filepath)

    if not files_by_date:
        print(f"{Colors.RED}No .fit files found{Colors.NC}")
        return 1

    print("Sessions found:")
    for i, (date, files) in enumerate(sorted(files_by_date.items()), 1):
        sub_count = len(files['light'])
        main_count = len(files['stacked'])
        total = sub_count + main_count
        if main_count > 0:
            print(f"  [{i}] {date}: {sub_count} subs + {main_count} main = {total} frames")
        else:
            print(f"  [{i}] {date}: {total} frames")
    print()

    # Copy files directly to sessions
    print(f"{Colors.YELLOW}Copying files to sessions...{Colors.NC}")

    total_copied = 0

    # Copy files for each date
    for date in sorted(files_by_date.keys()):
        print(f"Processing date: {Colors.GREEN}{date}{Colors.NC}")

        # Create session directory structure
        session_target_path = SESSIONS_DIR / date / target_clean
        session_target_path.mkdir(parents=True, exist_ok=True)

        # Copy light frames to target_sub/
        if files_by_date[date]['light']:
            sub_path = session_target_path / f"{target_clean}_sub"
            sub_path.mkdir(exist_ok=True)

            for source_file in files_by_date[date]['light']:
                dest_file = sub_path / source_file.name

                if not dest_file.exists():
                    shutil.copy2(source_file, dest_file)
                    total_copied += 1

            print(f"  ✓ sessions/{date}/{target_clean}/{target_clean}_sub/ "
                  f"({len(files_by_date[date]['light'])} lights)")

        # Copy stacked files to target/
        if files_by_date[date]['stacked']:
            stacked_path = session_target_path / target_clean
            stacked_path.mkdir(exist_ok=True)

            for source_file in files_by_date[date]['stacked']:
                dest_file = stacked_path / source_file.name

                if not dest_file.exists():
                    shutil.copy2(source_file, dest_file)
                    total_copied += 1

            print(f"  ✓ sessions/{date}/{target_clean}/{target_clean}/ "
                  f"({len(files_by_date[date]['stacked'])} stacked)")

        # Copy JPG files if in main folder
        if has_main:
            jpg_files = list((SEESTAR_MOUNT / target_name).glob("*.jpg"))
            if jpg_files:
                stacked_path = session_target_path / target_clean
                stacked_path.mkdir(exist_ok=True)

                for source_file in jpg_files:
                    # Check if this JPG matches the current date
                    parsed = parse_filename(source_file.name)
                    if parsed and parsed['date'] == date:
                        dest_file = stacked_path / source_file.name

                        if not dest_file.exists():
                            shutil.copy2(source_file, dest_file)
                            total_copied += 1

    print()
    print(f"{Colors.YELLOW}Creating hard links in targets...{Colors.NC}")

    total_linked = 0

    # Create hard links in targets for each date
    for date in sorted(files_by_date.keys()):
        session_target_path = SESSIONS_DIR / date / target_clean

        # Create target category directory
        target_category_path = TARGETS_DIR / type_dir / target_clean
        target_category_path.mkdir(parents=True, exist_ok=True)

        # Create date folder in targets
        target_date_path = target_category_path / date
        target_date_path.mkdir(exist_ok=True)

        # Hard link all files from sessions to targets
        for session_file in session_target_path.rglob("*"):
            if session_file.is_file():
                # Calculate relative path within the session target
                rel_path = session_file.relative_to(session_target_path)
                target_file = target_date_path / rel_path

                # Create parent directory if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)

                if not target_file.exists():
                    os.link(session_file, target_file)
                    total_linked += 1

        print(f"  ✓ Hard linked: targets/{type_dir}/{target_clean}/{date}/")

    print()
    print(f"{Colors.GREEN}=== Import Complete ==={Colors.NC}")
    print(f"Files copied to sessions: {total_copied}")
    print(f"Hard links created in targets: {total_linked}")
    print()

    print("Session folders:")
    for date in sorted(files_by_date.keys()):
        print(f"  sessions/{date}/{target_clean}/")
    print()

    print("Target view:")
    print(f"  targets/{type_dir}/{target_clean}/")
    print()

    return 0


def main():
    import sys

    # Check if Seestar is mounted
    if not SEESTAR_MOUNT.exists():
        print(f"{Colors.RED}Error: Seestar not found at {SEESTAR_MOUNT}{Colors.NC}")
        print("Make sure Seestar is connected and mounted, or set SEESTAR_PATH.")
        return 1

    if len(sys.argv) == 1:
        # No arguments - list targets
        list_targets()
        print("Usage: seestar_import_sessions.py \"TARGET_NAME\"")
        print("Example: seestar_import_sessions.py \"M 44\"")
        print("         seestar_import_sessions.py \"NGC 281\"")
        return 0
    else:
        # Import specified target
        target_name = sys.argv[1]
        return import_target(target_name)


if __name__ == "__main__":
    exit(main())
