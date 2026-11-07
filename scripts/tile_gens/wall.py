"""Wall tile generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import mortar_bricks, plank_rows, solid
from scripts.tilelib import clamp_albedo, fbm, px_per_m, tileable_grid, tileable_noise, voronoi_wrap


def wall_brick_red(size: int, seed: int, variant: int = 0) -> dict:
    s = seed + variant * 101
    albedo, height, rough, metal = mortar_bricks(
        size, s, 1.0, (0.065, 0.21), 0.01, (0.75, 0.73, 0.68), (0.55, 0.22, 0.14)
    )
    return {"albedo": albedo, "height": height, "roughness": rough, "metallic": metal}


wall_brick_red.tile_meters = 1.0


def wall_brick_old(size: int, seed: int, variant: int = 0) -> dict:
    s = seed + variant * 101
    albedo, height, rough, metal = mortar_bricks(
        size, s, 1.0, (0.065, 0.21), 0.01, (0.62, 0.6, 0.55), (0.38, 0.18, 0.12), wear=0.35
    )
    streak = fbm(size, 16, 3, s + 50) > 0.55
    albedo[streak] *= 0.82
    height[streak] -= 0.05
    return {"albedo": albedo, "height": height, "roughness": rough + 0.05, "metallic": metal}


wall_brick_old.tile_meters = 1.0


def wall_stucco_white(size: int, seed: int, variant: int = 0) -> dict:
    sand = variant == 1
    base = (0.88, 0.85, 0.78) if sand else (0.93, 0.92, 0.9)
    grain = fbm(size, 32, 5, seed + variant)
    wave = tileable_noise(size, 64, seed + 2)
    albedo = solid(size, base) * (0.97 + 0.06 * grain[..., None]) + (wave[..., None] - 0.5) * 0.02
    height = 0.48 + grain * 0.1 + wave * 0.04
    rough = 0.75 + grain * 0.12
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


wall_stucco_white.tile_meters = 1.0


def wall_concrete(size: int, seed: int, variant: int = 0) -> dict:
    albedo = solid(size, (0.62, 0.61, 0.59))
    grain = fbm(size, 32, 4, seed + variant)
    pores = tileable_noise(size, 128, seed + 3) > 0.72
    albedo[..., 0] += (grain - 0.5) * 0.08
    albedo[pores] *= 0.9
    from scripts.tilelib import _nearest_divisor

    ppm = px_per_m(size, 1.0)
    panel = _nearest_divisor(size, int(ppm))
    y, x = tileable_grid(size)
    seam = (x % panel < 2) | (y % panel < 2)
    height = 0.45 + grain * 0.12
    height[seam] = 0.2
    rough = 0.65 + grain * 0.2
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


wall_concrete.tile_meters = 1.0


def wall_stone_blocks(size: int, seed: int, variant: int = 0) -> dict:
    ids, dist = voronoi_wrap(size, 48, seed + variant)
    rng = np.random.default_rng(seed + variant)
    palette = rng.uniform(0.35, 0.55, (48, 3))
    edge = dist < 3.5
    albedo = palette[ids]
    mortar = (0.5, 0.48, 0.45)
    albedo = albedo.copy()
    albedo[edge] = mortar
    height = np.where(edge, 0.12, 0.5 + tileable_noise(size, 16, seed) * 0.15)
    rough = np.where(edge, 0.85, 0.7)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


wall_stone_blocks.tile_meters = 1.5


def wall_cobble_rubble(size: int, seed: int, variant: int = 0) -> dict:
    ids, dist = voronoi_wrap(size, 96, seed + variant)
    tone = tileable_noise(size, 32, seed + 1)
    base = 0.4 + tone * 0.15
    albedo = np.stack([base, base * 0.95, base * 0.9], axis=-1)
    edge = dist < 4
    albedo[edge] = 0.25
    height = np.where(edge, 0.1, 0.55 + tone * 0.2)
    rough = 0.8 - tone * 0.1
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


wall_cobble_rubble.tile_meters = 1.0


def wall_wood_planks_vertical(size: int, seed: int, variant: int = 0) -> dict:
    albedo, height, rough, metal = plank_rows(
        size, seed + variant, 1.0, 0.14, False, (0.55, 0.4, 0.28), (0.15, 0.12, 0.1)
    )
    return {"albedo": albedo, "height": height, "roughness": rough, "metallic": metal}


wall_wood_planks_vertical.tile_meters = 1.0


def wall_tiles_ceramic(size: int, seed: int, variant: int = 0) -> dict:
    from scripts.tilelib import _nearest_divisor

    ppm = px_per_m(size, 1.0)
    tw = _nearest_divisor(size, max(8, int(round(0.2 * ppm))))
    n = size // tw
    gap = max(1, int(0.002 * ppm))
    y, x = tileable_grid(size)
    gx = (x % tw) < gap
    gy = (y % tw) < gap
    grout = gx | gy
    tile = tileable_noise(size, max(2, n), seed + variant)
    albedo = np.zeros((size, size, 3))
    albedo[:] = (0.82, 0.84, 0.86)
    albedo += (tile[..., None] - 0.5) * 0.05
    albedo[grout] = (0.55, 0.55, 0.54)
    height = np.where(grout, 0.1, 0.55)
    rough = np.where(grout, 0.9, 0.2 + tile * 0.1)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


wall_tiles_ceramic.tile_meters = 1.0


def wall_siding_vinyl(size: int, seed: int, variant: int = 0) -> dict:
    albedo, height, rough, metal = plank_rows(
        size, seed + variant, 1.0, 0.2, True, (0.78, 0.8, 0.82), (0.35, 0.35, 0.36)
    )
    return {"albedo": albedo, "height": height, "roughness": rough, "metallic": metal}


wall_siding_vinyl.tile_meters = 1.0


def register(reg):
    for fn in (
        wall_brick_red,
        wall_brick_old,
        wall_stucco_white,
        wall_concrete,
        wall_stone_blocks,
        wall_cobble_rubble,
        wall_wood_planks_vertical,
        wall_tiles_ceramic,
        wall_siding_vinyl,
    ):
        reg("wall", fn.__name__, fn)
