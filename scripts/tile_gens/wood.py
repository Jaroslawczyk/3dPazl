"""Wood surface generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import plank_rows, solid
from scripts.tilelib import _nearest_divisor, clamp_albedo, fbm, tileable_grid, tileable_noise


def _plank_fn(name, horizontal, rgb, gap, pw=0.14):
    def gen(size: int, seed: int, variant: int = 0) -> dict:
        a, h, r, m = plank_rows(size, seed + variant, 1.0, pw, horizontal, rgb, gap)
        return {"albedo": a, "height": h, "roughness": r, "metallic": m}

    gen.__name__ = name
    gen.tile_meters = 1.0
    return gen


wood_planks_horizontal = _plank_fn("wood_planks_horizontal", True, (0.58, 0.42, 0.28), (0.14, 0.11, 0.09))
wood_planks_vertical = _plank_fn("wood_planks_vertical", False, (0.55, 0.4, 0.28), (0.14, 0.11, 0.09))


def wood_planks_diagonal(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = plank_rows(size, seed + variant, 1.0, 0.14, True, (0.52, 0.38, 0.26), (0.12, 0.1, 0.08))
    rot = fbm(size, 16, 3, seed) * 0.05
    a = clamp_albedo(a + rot[..., None])
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


wood_planks_diagonal.tile_meters = 1.0


def wood_parquet_herringbone(size: int, seed: int, variant: int = 0) -> dict:
    bw, bh = size // 8, size // 32
    y, x = tileable_grid(size)
    cell_x = x.astype(int) // bw
    cell_y = y.astype(int) // bh
    diag = (cell_x + cell_y) % 2
    tone = tileable_noise(size, max(4, size // bw), seed + variant)
    base = 0.45 + tone * 0.15
    albedo = np.stack([base, base * 0.85, base * 0.65], axis=-1)
    gap = (x % bw < 1) | (y % bh < 1)
    albedo[gap] = 0.15
    height = np.where(gap, 0.1, 0.5 + tone * 0.12)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.55), "metallic": np.zeros((size, size))}


wood_parquet_herringbone.tile_meters = 1.0


def wood_parquet_strip(size: int, seed: int, variant: int = 0) -> dict:
    return wood_planks_horizontal(size, seed, variant)


wood_parquet_strip.tile_meters = 1.0


def _tone_wood(name, rgb, rough=0.55):
    def gen(size: int, seed: int, variant: int = 0) -> dict:
        n = fbm(size, 32, 5, seed + variant)
        grain = tileable_noise(size, max(8, size // 64), seed + 1)
        albedo = solid(size, rgb) * (0.9 + 0.12 * n[..., None] * grain[..., None])
        height = 0.45 + n * 0.15
        return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), rough), "metallic": np.zeros((size, size))}

    gen.__name__ = name
    gen.tile_meters = 1.0
    return gen


wood_oak_light = _tone_wood("wood_oak_light", (0.68, 0.52, 0.32))
wood_walnut_dark = _tone_wood("wood_walnut_dark", (0.35, 0.22, 0.14))
wood_pine_knotty = _tone_wood("wood_pine_knotty", (0.72, 0.58, 0.35))
wood_birch_pale = _tone_wood("wood_birch_pale", (0.82, 0.75, 0.62))
wood_weathered_grey = _tone_wood("wood_weathered_grey", (0.52, 0.5, 0.48), 0.7)


def wood_painted_white(size: int, seed: int, variant: int = 0) -> dict:
    peel = tileable_noise(size, _nearest_divisor(size, 16), seed + variant) > 0.55
    under, h, r, m = plank_rows(size, seed, 1.0, 0.14, True, (0.55, 0.42, 0.3), (0.2, 0.15, 0.12))
    albedo = solid(size, (0.9, 0.91, 0.92))
    albedo[peel] = under[peel]
    return {"albedo": clamp_albedo(albedo), "height": h, "roughness": np.where(peel, r, 0.4), "metallic": m}


wood_painted_white.tile_meters = 1.0


def wood_painted_red(size: int, seed: int, variant: int = 0) -> dict:
    peel = tileable_noise(size, _nearest_divisor(size, 16), seed + variant) > 0.5
    under, h, r, m = plank_rows(size, seed, 1.0, 0.14, True, (0.5, 0.38, 0.28), (0.18, 0.14, 0.12))
    albedo = solid(size, (0.62, 0.18, 0.15))
    albedo[peel] = under[peel]
    return {"albedo": clamp_albedo(albedo), "height": h, "roughness": np.where(peel, r, 0.45), "metallic": m}


wood_painted_red.tile_meters = 1.0


def wood_log_bark(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    grooves = np.sin(2 * np.pi * x / size * 24) * 0.5 + 0.5
    n = fbm(size, 16, 4, seed + variant)
    albedo = solid(size, (0.32, 0.22, 0.15)) * (0.85 + 0.2 * grooves[..., None] * n[..., None])
    height = 0.4 + grooves * 0.25 + n * 0.1
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.85), "metallic": np.zeros((size, size))}


wood_log_bark.tile_meters = 1.0


def wood_plywood(size: int, seed: int, variant: int = 0) -> dict:
    return wood_oak_light(size, seed, variant)


wood_plywood.tile_meters = 1.0


def wood_osb(size: int, seed: int, variant: int = 0) -> dict:
    ids, dist = __import__("scripts.tilelib", fromlist=["voronoi_wrap"]).voronoi_wrap(size, 120, seed + variant)
    tone = tileable_noise(size, 32, seed)
    base = 0.55 + tone * 0.2
    albedo = np.stack([base, base * 0.9, base * 0.75], axis=-1)
    height = 0.45 + (1 - dist / 8).clip(0, 1) * 0.15
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.75), "metallic": np.zeros((size, size))}


wood_osb.tile_meters = 1.0


wood_crate = wood_pine_knotty
wood_fence_boards = wood_planks_vertical
wood_deck = wood_planks_horizontal


def register(reg):
    fns = [
        wood_planks_horizontal,
        wood_planks_vertical,
        wood_planks_diagonal,
        wood_parquet_herringbone,
        wood_parquet_strip,
        wood_oak_light,
        wood_walnut_dark,
        wood_pine_knotty,
        wood_birch_pale,
        wood_weathered_grey,
        wood_painted_white,
        wood_painted_red,
        wood_log_bark,
        wood_plywood,
        wood_osb,
        wood_crate,
        wood_fence_boards,
        wood_deck,
    ]
    for fn in fns:
        reg("wood", fn.__name__, fn)
