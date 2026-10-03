#!/usr/bin/env python3
"""Enhance M97 Owl Nebula JPG using astro-style image processing."""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import sys

INPUT = "/home/dlwiii/astro/targets/nebulae/m97/m97_2026-04-18.jpg"
OUTPUT = "/home/dlwiii/astro/targets/nebulae/m97/m97_2026-04-18_enhanced.jpg"


def stretch_channel(arr, black_point, white_point, stretch_factor=4.0):
    """Asinh stretch between black_point and white_point."""
    channel = arr.astype(np.float64)
    stretched = (channel - black_point) / max(white_point - black_point, 1.0)
    stretched = np.clip(stretched, 0, 1)
    result = np.arcsinh(stretch_factor * stretched) / np.arcsinh(stretch_factor)
    return np.clip(result, 0, 1)


def process():
    img = Image.open(INPUT)
    arr = np.array(img, dtype=np.float64)

    # Use luminance to find black/white points
    lum = arr.mean(axis=2).flatten()
    # Black point: just above noise floor — p30 of all pixels
    # (most pixels are dark sky, so p30 is still background)
    black_point = np.percentile(lum, 30)
    # White point: p99.7 — let bright star cores clip, preserve nebula range
    white_point = np.percentile(lum, 99.7)
    print(f"black_point={black_point:.1f}  white_point={white_point:.1f}")

    out = np.zeros_like(arr)
    for ch in range(3):
        out[:, :, ch] = stretch_channel(arr[:, :, ch], black_point, white_point, stretch_factor=5.0)

    out8 = (out * 255).astype(np.uint8)
    result = Image.fromarray(out8)

    # Unsharp mask for nebula shell detail
    result = result.filter(ImageFilter.UnsharpMask(radius=2, percent=110, threshold=5))

    # Saturation boost for nebula color
    result = ImageEnhance.Color(result).enhance(1.4)

    result.save(OUTPUT, quality=95)
    print(f"Saved: {OUTPUT}")

    out_arr = np.array(result)
    print(f"Output mean: {out_arr.mean():.1f}")


if __name__ == "__main__":
    process()
