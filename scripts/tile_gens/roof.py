"""Roof tile generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import plank_rows, sinus_waves, solid
from scripts.tilelib import clamp_albedo, fbm, px_per_m, tileable_grid, tileable_noise


def roof_clay_tile(size: int, seed: int, variant: int = 0) -> dict:
    rows = 5
    rh = size // rows
    wave = sinus_waves(size, rows * 2, "x")
    y, x = tileable_grid(size)
    row = (y.astype(int) // rh) % rows
    shift = (row % 2) * (rh // 2)
    crest = np.sin(2 * np.pi * (x + shift) / size * rows * 4) * 0.5 + 0.5
    tint = tileable_noise(size, rows, seed + variant)
    albedo = solid(size, (0.62, 0.28, 0.15)) * (0.92 + 0.1 * tint[..., None])
    moss = (tint > 0.7) & (crest < 0.25)
    albedo[moss] = (0.35, 0.42, 0.22)
    height = 0.35 + crest * 0.35 + wave * 0.05
    rough = 0.65 + (1 - crest) * 0.2
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


roof_clay_tile.tile_meters = 1.0


def roof_shingle_dark(size: int, seed: int, variant: int = 0) -> dict:
    albedo, height, rough, metal = plank_rows(
        size, seed + variant, 1.0, 0.17, True, (0.22, 0.22, 0.24), (0.12, 0.12, 0.13)
    )
    grit = tileable_noise(size, 64, seed) * 0.06
    albedo = np.clip(albedo + grit[..., None], 0, 1)
    return {"albedo": albedo, "height": height + grit * 0.1, "roughness": rough, "metallic": metal}


roof_shingle_dark.tile_meters = 1.0


def roof_metal_standing_seam(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 1.0)
    seam_w = max(2, int(0.02 * ppm))
    pitch = size // 2
    y, x = tileable_grid(size)
    seam = (x.astype(int) % pitch) < seam_w
    wave = sinus_waves(size, 8, "y")
    albedo = solid(size, (0.55, 0.56, 0.58)) + (wave[..., None] - 0.5) * 0.04
    height = 0.5 + wave * 0.08
    height[seam] += 0.12
    rough = np.where(seam, 0.45, 0.35)
    return {
        "albedo": clamp_albedo(albedo),
        "height": height,
        "roughness": rough,
        "metallic": np.ones((size, size)),
    }


roof_metal_standing_seam.tile_meters = 1.0


def roof_thatch(size: int, seed: int, variant: int = 0) -> dict:
    f = fbm(size, 16, 6, seed + variant)
    ang = tileable_noise(size, 32, seed + 1)
    y, x = tileable_grid(size)
    strands = np.sin((x + y) / size * np.pi * 80 + ang * 12) * 0.5 + 0.5
    albedo = solid(size, (0.62, 0.48, 0.22)) * (0.9 + 0.12 * f[..., None] * strands[..., None])
    height = 0.4 + f * 0.35 + strands * 0.15
    rough = 0.85
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), rough), "metallic": np.zeros((size, size))}


roof_thatch.tile_meters = 1.0


def roof_slate(size: int, seed: int, variant: int = 0) -> dict:
    from scripts.tilelib import _nearest_divisor

    tw = _nearest_divisor(size, size // 6)
    th = _nearest_divisor(size, size // 8)
    y, x = tileable_grid(size)
    row = (y.astype(int) // th)
    shift = (row % 2) * (tw // 2)
    tone = tileable_noise(size, max(tw, th), seed + variant)
    t = 0.28 + tone * 0.14
    albedo = np.stack([t, t * 1.02, t * 1.05], axis=-1)
    gap = (y % th < 1) | ((x.astype(int) + shift) % tw < 1)
    height = np.where(gap, 0.1, 0.55)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.55), "metallic": np.zeros((size, size))}


roof_slate.tile_meters = 1.0


def roof_wood_shake(size: int, seed: int, variant: int = 0) -> dict:
    albedo, height, rough, metal = plank_rows(
        size, seed + variant, 1.0, 0.12, True, (0.45, 0.38, 0.3), (0.2, 0.18, 0.15)
    )
    return {"albedo": albedo, "height": height, "roughness": rough, "metallic": metal}


roof_wood_shake.tile_meters = 1.0


def register(reg):
    for fn in (
        roof_clay_tile,
        roof_shingle_dark,
        roof_metal_standing_seam,
        roof_thatch,
        roof_slate,
        roof_wood_shake,
    ):
        reg("roof", fn.__name__, fn)
