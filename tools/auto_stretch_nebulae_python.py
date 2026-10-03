#!/usr/bin/env python3
"""
Auto-stretch nebula stacked images using Python (no Siril needed)
Outputs: <target>_<date>_auto.png in each target folder
"""

import sys
import numpy as np
from pathlib import Path
from datetime import datetime

try:
    from astropy.io import fits
    from PIL import Image
except ImportError:
    print("Error: Required libraries not installed")
    print("Install with: pip install astropy pillow")
    sys.exit(1)

# Configuration
NEBULAE_DIR = Path("/home/dlwiii/astro/targets/nebulae")

def asinh_stretch(data, stretch=15, black_point=None):
    """Apply asinh stretch to image data with proper background subtraction"""
    # Remove negative values
    data = np.clip(data, 0, None)

    # Calculate background (median of lower values)
    background = np.median(data[data < np.percentile(data, 50)])

    # Subtract background
    data = data - background
    data = np.clip(data, 0, None)

    # Normalize using the signal range (not the max)
    # Use 98th percentile to avoid hot pixels
    signal_max = np.percentile(data, 98)
    if signal_max > 0:
        data = data / signal_max

    # Clip to 0-1 range
    data = np.clip(data, 0, 1)

    # Asinh stretch - very aggressive for faint nebulae
    stretched = np.arcsinh(data * stretch) / np.arcsinh(stretch)

    # Gamma adjustment for better midtones (lower = brighter)
    stretched = np.power(stretched, 0.6)

    return stretched

def process_fit_to_png(fit_file, output_png, stretch_method="asinh"):
    """Convert FIT file to auto-stretched PNG"""
    try:
        # Read FIT file
        with fits.open(fit_file) as hdul:
            data = hdul[0].data.astype(float)

        # Handle different data shapes
        if data.ndim == 2:
            # Grayscale
            stretched = asinh_stretch(data)
            # Convert to 8-bit
            img_data = (stretched * 255).astype(np.uint8)
            img = Image.fromarray(img_data, mode='L')
        elif data.ndim == 3:
            # RGB or multi-channel
            if data.shape[0] == 3:  # CxHxW format
                data = np.transpose(data, (1, 2, 0))  # Convert to HxWxC

            # Stretch each channel
            stretched = np.zeros_like(data)
            for i in range(min(3, data.shape[2])):
                stretched[:, :, i] = asinh_stretch(data[:, :, i])

            # Convert to 8-bit RGB
            img_data = (stretched[:, :, :3] * 255).astype(np.uint8)
            img = Image.fromarray(img_data, mode='RGB')
        else:
            raise ValueError(f"Unexpected data shape: {data.shape}")

        # Save PNG
        img.save(output_png, 'PNG', optimize=True)
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def find_stacked_fits(target_dir):
    """Find stacked FIT files in target directory"""
    stacked_files = []

    # Common patterns for stacked files
    patterns = [
        "*stacked*.fit",
        "*Stacked*.fit",
        "*_og.fit",
        "*drizzle*.fit"
    ]

    for pattern in patterns:
        for fit_file in target_dir.glob(pattern):
            stacked_files.append(fit_file)

    # Also check dated subfolders
    for subdir in target_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith("20"):
            for pattern in patterns:
                for fit_file in subdir.glob(pattern):
                    stacked_files.append(fit_file)

    return list(set(stacked_files))

def process_target(target_dir, dry_run=False):
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

        # Use more descriptive name if multiple files
        if len(stacked_files) > 1:
            # Extract key part of filename
            name_part = fit_file.stem.replace('Stacked_', '').replace('stacked', '')
            name_part = name_part.replace(target_dir.name.upper(), '').replace(target_dir.name, '')
            name_part = ''.join(c for c in name_part if c.isalnum() or c in ['_', '-'])[:20]
            if name_part:
                output_png = target_dir / f"{target_dir.name}_{date_str}_{name_part}_auto.png"
            else:
                output_png = target_dir / f"{target_dir.name}_{date_str}_auto.png"
        else:
            output_png = target_dir / f"{target_dir.name}_{date_str}_auto.png"

        # Skip if already exists
        if output_png.exists():
            print(f"\n  Skipping: {fit_file.name}")
            print(f"  Output exists: {output_png.name}")
            continue

        print(f"\n  Processing: {fit_file.name}")
        print(f"  Output: {output_png.name}")

        if dry_run:
            print(f"  [DRY RUN] Would process with asinh")
            continue

        # Process the file
        if process_fit_to_png(fit_file, output_png):
            size_mb = output_png.stat().st_size / (1024 * 1024)
            print(f"  ✓ Success! ({size_mb:.1f} MB)")
            processed += 1

    return processed

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-stretch nebula images using Python')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
    parser.add_argument('--target', help='Process only this target (e.g., m42)')

    args = parser.parse_args()

    print("="*60)
    print("NEBULA AUTO-STRETCH PROCESSOR (Python)")
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
        total_processed = process_target(target_dir, args.dry_run)
    else:
        # Process all nebula targets
        for target_dir in sorted(NEBULAE_DIR.iterdir()):
            if not target_dir.is_dir():
                continue

            # Skip if no lights folder
            if not (target_dir / "lights").exists():
                continue

            processed = process_target(target_dir, args.dry_run)
            total_processed += processed

    print(f"\n{'='*60}")
    print(f"SUMMARY: Processed {total_processed} image(s)")
    print("="*60)

    return 0

if __name__ == '__main__':
    sys.exit(main())
