#!/usr/bin/env python3
"""
Path A: Process Seestar's own 60-frame stacked FITS for M97.

Source:  sessions/2026-04-18/m97/m97/Stacked_60_M 97_10.0s_LP_20260418-220604.fit
BGE:     targets/nebulae/m97/m97_seestar_stack_bge.fit
Output:  targets/nebulae/m97/m97_pathA_2026-04-18.jpg
Ref:     targets/nebulae/m97/m97_2026-04-18b.jpg  ← do not touch
"""

import subprocess, sys
from pathlib import Path
import numpy as np
from astropy.io import fits
from PIL import Image, ImageEnhance, ImageFilter
from scipy.ndimage import median_filter, gaussian_filter

# ── Paths ──────────────────────────────────────────────────────────────────────
SRC_FIT  = Path("/home/dlwiii/astro/sessions/2026-04-18/m97/m97/Stacked_60_M 97_10.0s_LP_20260418-220604.fit")
BGE_FIT  = Path("/home/dlwiii/astro/targets/nebulae/m97/m97_seestar_stack_bge.fit")
NR_FIT   = Path("/home/dlwiii/astro/targets/nebulae/m97/m97_seestar_stack_bge_nr.fit")
OUTPUT   = Path("/home/dlwiii/astro/targets/nebulae/m97/m97_pathA_2026-04-18.jpg")
REF      = Path("/home/dlwiii/astro/targets/nebulae/m97/m97_2026-04-18b.jpg")  # never written

# Nebula center in full 1080×1920 frame (found via Siril autostretch)
NEBULA_Y, NEBULA_X = 964, 549
CROP_HALF = 264   # → 528×528 output, matching "b" dimensions


# ── Step 1: Background extraction ─────────────────────────────────────────────
def step_bge():
    if BGE_FIT.exists():
        print(f"[bge] {BGE_FIT.name} exists, skipping.")
        return
    print("[bge] Running Siril background extraction...")
    script = f'requires 1.2.0\nload "{SRC_FIT}"\nsubsky 2 -samples=25 -tolerance=2.0\nsave "{BGE_FIT.with_suffix("")}"\n'
    r = subprocess.run(["siril-cli", "-s", "-"], input=script, capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if any(k in line for k in ["log:", "Error", "failed"]):
            print(line)


# ── Step 2: Stretch ────────────────────────────────────────────────────────────
def sigma_clip(arr, sigma=2.5, iters=5):
    flat = arr.flatten()
    for _ in range(iters):
        med, std = np.median(flat), np.std(flat)
        mask = np.abs(flat - med) < sigma * std
        if mask.sum() < 100: break
        flat = flat[mask]
    return np.median(flat), np.std(flat)


def stretch_channel(ch_raw, ch_nr, bg, bg_std, stretch_factor, noise_sigma, scale_adu):
    """
    Stretch ch_nr using a directly-specified scale in ADU above background.
    scale_adu: the signal range (in raw ADU) that maps to ~1.0 output.
    This avoids the scale being swamped by star dynamic range.
    """
    black = bg + noise_sigma * bg_std
    s = np.clip(ch_nr - black, 0, None) / max(scale_adu, 1.0)
    return np.clip(np.arcsinh(stretch_factor * s) / np.arcsinh(stretch_factor), 0, 1)


def step_export(stretch_factor=6.0, noise_sigma=0.5, scale_adu=30,
                saturation=1.5, usm_radius=2, usm_pct=120, usm_thresh=3):
    print("[export] Loading NL-Bayes denoised stack...")
    with fits.open(NR_FIT) as h:
        data = h[0].data.astype(np.float64)   # (3, H, W), R=0 G=1 B=2

    # Per-channel background stats — critical for correct color balance
    for i, name in enumerate("RGB"):
        bg, std = sigma_clip(data[i])
        print(f"[export] {name}: bg={bg:.1f}  std={std:.2f}  black={bg + noise_sigma*std:.1f}")

    # Light Gaussian on NL-Bayes output to suppress residual per-pixel chromatic noise.
    # sigma=1.5 kills 1-px speckle without bloating stars (was sigma=4 before, 7x less spread).
    data_nr = np.stack([gaussian_filter(data[i], sigma=1.5) for i in range(3)])

    channels = []
    for i in range(3):
        bg, bg_std = sigma_clip(data[i])
        channels.append(stretch_channel(data[i], data_nr[i], bg, bg_std, stretch_factor, noise_sigma, scale_adu))
    rgb = np.stack(channels, axis=2)
    img = Image.fromarray((rgb * 255).astype(np.uint8))

    # Crop to nebula
    cy, cx, h = NEBULA_Y, NEBULA_X, CROP_HALF
    img = img.crop((cx - h, cy - h, cx + h, cy + h))

    # Unsharp mask
    img = img.filter(ImageFilter.UnsharpMask(radius=usm_radius, percent=usm_pct, threshold=usm_thresh))

    # Saturation
    img = ImageEnhance.Color(img).enhance(saturation)

    img.save(OUTPUT, quality=95)
    print(f"[export] Saved → {OUTPUT}")
    print(f"         Reference → {REF}")
    return img


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    step_bge()
    step_export(
        stretch_factor = 7.0,
        noise_sigma    = 0.5,
        scale_adu      = 30,
        saturation     = 1.5,
        usm_radius     = 2,
        usm_pct        = 120,
        usm_thresh     = 3,
    )
