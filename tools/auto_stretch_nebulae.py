#!/usr/bin/env python3
"""
Auto-stretch nebula stacked images using Siril
Outputs: <target>_<date>_auto.png in each target folder
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Configuration
NEBULAE_DIR = Path("/home/dlwiii/astro/targets/nebulae")
SIRIL_CLI = "siril-cli"

def find_stacked_fits(target_dir):
    """Find stacked FIT files in target directory"""
    stacked_files = []

    # Common patterns for stacked files
    patterns = [
        "*stacked*.fit",
        "*Stacked*.fit",
        "*_og.fit",  # Original stacks
        "*drizzle*.fit"
    ]

    for pattern in patterns:
        for fit_file in target_dir.glob(pattern):
            # Skip if already processed (has _auto.png)
            auto_png = fit_file.parent / f"{target_dir.name}_{datetime.now().strftime('%Y-%m-%d')}_auto.png"
            if not auto_png.exists():
                stacked_files.append(fit_file)

    # Also check dated subfolders
    for subdir in target_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith("20"):  # Dated folder
            for pattern in patterns:
                for fit_file in subdir.glob(pattern):
                    stacked_files.append(fit_file)

    return list(set(stacked_files))  # Remove duplicates

def create_siril_script(fit_file, output_png, stretch_method="asinh"):
    """Create Siril script for auto-stretching"""
    script_content = f"""# Auto-stretch script
load {fit_file.stem}
cd {fit_file.parent}

# Auto-stretch using {stretch_method}
"""

    if stretch_method == "asinh":
        script_content += """asinh stretch=3 bp=0.15
"""
    elif stretch_method == "autostretch":
        script_content += """autostretch
"""
    else:  # clahe
        script_content += """clahe 2.0 8
"""

    script_content += f"""
# Save as PNG
savepng {output_png.stem}

close
"""

    return script_content

def process_target(target_dir, dry_run=False, stretch_method="asinh"):
    """Process all stacked images in a target directory"""
    print(f"\n{'='*60}")
    print(f"Processing: {target_dir.name}")
    print(f"{'='*60}")

    stacked_files = find_stacked_fits(target_dir)

    if not stacked_files:
        print(f"  No stacked FIT files found")
        return 0

    print(f"  Found {len(stacked_files)} stacked file(s)")

    processed = 0
    for fit_file in stacked_files:
        # Generate output filename
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_png = target_dir / f"{target_dir.name}_{date_str}_auto.png"

        print(f"\n  Processing: {fit_file.name}")
        print(f"  Output: {output_png.name}")

        if dry_run:
            print(f"  [DRY RUN] Would process with {stretch_method}")
            continue

        # Create temporary Siril script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ssf', delete=False) as script_file:
            script_content = create_siril_script(fit_file, output_png, stretch_method)
            script_file.write(script_content)
            script_path = script_file.name

        try:
            # Run Siril CLI
            cmd = [SIRIL_CLI, "-s", script_path]
            result = subprocess.run(
                cmd,
                cwd=fit_file.parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0 and output_png.exists():
                size_mb = output_png.stat().st_size / (1024 * 1024)
                print(f"  ✓ Success! ({size_mb:.1f} MB)")
                processed += 1
            else:
                print(f"  ✗ Failed: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout (>5 minutes)")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        finally:
            # Clean up temp script
            try:
                os.unlink(script_path)
            except:
                pass

    return processed

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-stretch nebula images using Siril')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
    parser.add_argument('--method', choices=['asinh', 'autostretch', 'clahe'],
                       default='asinh', help='Stretch method (default: asinh)')
    parser.add_argument('--target', help='Process only this target (e.g., m42)')
    parser.add_argument('--skip-check', action='store_true', help='Skip Siril installation check')

    args = parser.parse_args()

    # Check if siril-cli is available
    if not args.skip_check:
        try:
            result = subprocess.run([SIRIL_CLI, '--version'],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                print(f"Error: {SIRIL_CLI} not found or not working")
                print("Install Siril or use --skip-check to bypass this check")
                return 1
        except FileNotFoundError:
            print(f"Error: {SIRIL_CLI} not found in PATH")
            print("Install Siril CLI or add it to your PATH")
            return 1
        except Exception as e:
            print(f"Error checking Siril: {e}")
            return 1

    print("="*60)
    print("NEBULA AUTO-STRETCH PROCESSOR")
    print(f"Method: {args.method}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PROCESSING'}")
    print("="*60)

    if not NEBULAE_DIR.exists():
        print(f"Error: Nebulae directory not found: {NEBULAE_DIR}")
        return 1

    total_processed = 0

    # Process specific target or all targets
    if args.target:
        target_dir = NEBULAE_DIR / args.target
        if not target_dir.exists():
            print(f"Error: Target not found: {args.target}")
            return 1
        total_processed = process_target(target_dir, args.dry_run, args.method)
    else:
        # Process all nebula targets
        for target_dir in sorted(NEBULAE_DIR.iterdir()):
            if not target_dir.is_dir():
                continue

            # Skip if no lights folder
            if not (target_dir / "lights").exists():
                continue

            processed = process_target(target_dir, args.dry_run, args.method)
            total_processed += processed

    print(f"\n{'='*60}")
    print(f"SUMMARY: Processed {total_processed} image(s)")
    print("="*60)

    return 0

if __name__ == '__main__':
    sys.exit(main())
