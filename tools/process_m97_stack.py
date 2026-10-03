#!/usr/bin/env python3
"""
Full processing pipeline for M97 Owl Nebula - 2026-04-18 stack.

Steps:
  1. Stack 60 raw FIT frames via Siril (debayer, register, reject-stack)
  2. Background gradient extraction via Siril
  3. Locate nebula, crop to field of view
  4. Asinh stretch with per-channel background estimation
  5. Color balance, saturation, unsharp mask
  6. Save final JPG alongside original Seestar JPEG for comparison
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from PIL import Image, ImageEnhance, ImageFilter

# ── Paths ──────────────────────────────────────────────────────────────────────
TARGET_DIR   = Path("/home/dlwiii/astro/targets/nebulae/m97")
RAW_DIR      = TARGET_DIR / "2026-04-18/m97_sub"
PROCESS_DIR  = TARGET_DIR / "process"
STACKED_FIT  = TARGET_DIR / "m97_stacked_2026-04-18.fit"
BGE_FIT      = TARGET_DIR / "m97_stacked_bge.fit"
OUTPUT_JPG   = TARGET_DIR / "m97_stacked_2026-04-18.jpg"   # new output
COMPARE_JPG  = TARGET_DIR / "m97_2026-04-18_enhanced.jpg"  # existing — untouched

# Nebula center in stacked full-frame (1080x1920), found by visual inspection
NEBULA_Y, NEBULA_X = 875, 575
# Crop half-size (gives ~500x500 crop, similar to Seestar JPEG)
CROP_HALF = 264


# ── Step 1: Stack ──────────────────────────────────────────────────────────────
def run_siril(script: str):
    result = subprocess.run(
        ["siril-cli", "-s", "-"],
        input=script, capture_output=True, text=True
    )
    # Print key log lines
    for line in result.stdout.splitlines():
        if any(k in line for k in ["log:", "error", "Error", "failed", "stacked", "Saving"]):
            print(line)
    return result.returncode == 0


def step_stack():
    """Convert, register, and stack raw FIT frames."""
    PROCESS_DIR.mkdir(exist_ok=True)

    # Skip if already done
    if STACKED_FIT.exists():
        print(f"[stack] {STACKED_FIT.name} exists, skipping.")
        return True

    script = f"""requires 1.2.0
set16bits
setext fit
cd {RAW_DIR}
convert light -debayer -out={PROCESS_DIR}
cd {PROCESS_DIR}
register light
stack r_light_ rej 3 3 -norm=addscale -out={STACKED_FIT.with_suffix('')}
"""
    print("[stack] Running Siril stack...")
    ok = run_siril(script)
    if ok:
        print(f"[stack] Done → {STACKED_FIT.name}")
    return ok


# ── Step 2: Background extraction ─────────────────────────────────────────────
def step_bge():
    """Subtract background gradient using Siril polynomial fit."""
    if BGE_FIT.exists():
        print(f"[bge] {BGE_FIT.name} exists, skipping.")
        return True

    script = f"""requires 1.2.0
cd {TARGET_DIR}
load {STACKED_FIT.stem}
subsky 2 -samples=20 -tolerance=2.0
save {BGE_FIT.stem}
"""
    print("[bge] Running background extraction...")
    ok = run_siril(script)
    if ok:
        print(f"[bge] Done → {BGE_FIT.name}")
    return ok


# ── Step 3: Stretch and export ─────────────────────────────────────────────────
def sigma_clip_stats(ch: np.ndarray, sigma: float = 2.5, iters: int = 5):
    """Return sigma-clipped (median, std) of array."""
    flat = ch.flatten()
    for _ in range(iters):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < sigma * std
        if mask.sum() < 100:
            break
        flat = flat[mask]
    return np.median(flat), np.std(flat)


def asinh_stretch(ch: np.ndarray, bg: float, bg_std: float,
                  stretch_factor: float = 5.0,
                  noise_sigma: float = 3.0,
                  white_pct: float = 99.5) -> np.ndarray:
    """
    Asinh stretch for 16-bit linear FITS data.
    bg / bg_std come from luminance so all channels share the same zero point.
    noise_sigma: how many sigmas above bg to set the black point.
    """
    # Black point: noise_sigma above background
    black_point = bg + noise_sigma * bg_std

    s = ch - black_point
    s = np.clip(s, 0, None)

    signal = s[s > 0]
    scale  = np.percentile(signal, white_pct) if signal.size > 0 else 1.0
    s     /= max(scale, 1.0)

    result = np.arcsinh(stretch_factor * s) / np.arcsinh(stretch_factor)
    return np.clip(result, 0, 1)


def step_export():
    """Stretch, crop, enhance, and save final JPG."""
    from scipy.ndimage import median_filter

    print("[export] Loading BGE-subtracted stack...")
    with fits.open(BGE_FIT) as hdul:
        data = hdul[0].data.astype(np.float64)  # (3, H, W)

    # Compute background stats from luminance (shared zero point across channels)
    lum = data.mean(axis=0)
    bg, bg_std = sigma_clip_stats(lum)
    # White point: top 0.1% of full image — captures nebula without anchoring to bright stars
    white_point = np.percentile(lum, 99.9)
    signal_range = white_point - bg
    print(f"[export] bg={bg:.1f}  white_point={white_point:.1f}  signal_range={signal_range:.1f}")

    # Noise reduction: median filter size 5 smooths Bayer noise from few-frame stack
    data_nr = np.stack([median_filter(data[i], size=5) for i in range(3)])

    # Use a gentler noise_sigma so faint nebula isn't clipped, and low white_pct
    # to not anchor the scale to bright stars
    r = asinh_stretch(data_nr[0], bg, bg_std, stretch_factor=8.0, noise_sigma=0.5, white_pct=99.8)
    g = asinh_stretch(data_nr[1], bg, bg_std, stretch_factor=8.0, noise_sigma=0.5, white_pct=99.8)
    b = asinh_stretch(data_nr[2], bg, bg_std, stretch_factor=8.0, noise_sigma=0.5, white_pct=99.8)

    rgb = np.stack([r, g, b], axis=2)           # (H, W, 3)
    rgb8 = (rgb * 255).astype(np.uint8)
    img = Image.fromarray(rgb8)

    # Crop around nebula center
    cy, cx = NEBULA_Y, NEBULA_X
    h = CROP_HALF
    box = (cx - h, cy - h, cx + h, cy + h)
    img = img.crop(box)

    # Unsharp mask — sharpens nebula shell without over-ringing stars
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=110, threshold=4))

    # Saturation: nebula has real OIII blue-green emission
    img = ImageEnhance.Color(img).enhance(1.5)

    img.save(OUTPUT_JPG, quality=95)
    print(f"[export] Saved → {OUTPUT_JPG}")
    print(f"         Compare with → {COMPARE_JPG}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not step_stack():
        sys.exit("Stack step failed")
    if not step_bge():
        sys.exit("BGE step failed")
    step_export()
