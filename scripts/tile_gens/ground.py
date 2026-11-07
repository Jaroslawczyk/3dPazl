"""Ground / pavement generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import asphalt_base, solid
from scripts.tilelib import _nearest_divisor, clamp_albedo, fbm, px_per_m, tileable_grid, tileable_noise, voronoi_wrap


def _noise_ground(size, seed, variant, rgb, rough=0.8):
    n = fbm(size, 32, 5, seed + variant)
    albedo = solid(size, rgb) * (0.92 + 0.12 * n[..., None])
    height = 0.42 + n * 0.2
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), rough), "metallic": np.zeros((size, size))}


def asphalt_clean(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = asphalt_base(size, seed + variant)
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


asphalt_clean.tile_meters = 2.0


def asphalt_worn(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = asphalt_base(size, seed + variant)
    crack = fbm(size, 8, 4, seed + 50) > 0.62
    h[crack] -= 0.15
    a[crack] *= 0.85
    patch = tileable_noise(size, 16, seed + 60) > 0.75
    a[patch] = a[patch] * 0.9 + 0.05
    oil = tileable_noise(size, 32, seed + 70) > 0.8
    r[oil] = 0.2
    a[oil] *= 0.7
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


asphalt_worn.tile_meters = 2.0


def asphalt_wet(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = asphalt_base(size, seed + variant, wet=True)
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


asphalt_wet.tile_meters = 2.0


def concrete_slab_sidewalk(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 2.0)
    slab = _nearest_divisor(size, int(ppm))
    y, x = tileable_grid(size)
    seam = (x % slab < 3) | (y % slab < 3)
    n = tileable_noise(size, 32, seed + variant)
    albedo = solid(size, (0.7, 0.69, 0.67)) * (0.96 + 0.06 * n[..., None])
    height = np.where(seam, 0.15, 0.5 + n * 0.08)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.65), "metallic": np.zeros((size, size))}


concrete_slab_sidewalk.tile_meters = 2.0


def paving_stone_grey(size: int, seed: int, variant: int = 0) -> dict:
    bw = _nearest_divisor(size, size // 10)
    bh = _nearest_divisor(size, size // 20)
    y, x = tileable_grid(size)
    row = y.astype(int) // bh
    herring = ((row + (x.astype(int) // bw)) % 2) * (bw // 2)
    col2 = (x.astype(int) + herring) // bw
    tone = tileable_noise(size, max(4, size // bw), seed + variant)
    base = 0.45 + tone * 0.12
    albedo = np.stack([base, base, base * 1.02], axis=-1)
    gap = (y % bh < 2) | ((x + herring) % bw < 2)
    height = np.where(gap, 0.1, 0.52)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.7), "metallic": np.zeros((size, size))}


paving_stone_grey.tile_meters = 2.0


def cobblestone(size: int, seed: int, variant: int = 0) -> dict:
    _, dist = voronoi_wrap(size, 80, seed + variant)
    tone = fbm(size, 16, 3, seed)
    base = 0.38 + tone * 0.15
    albedo = np.stack([base, base * 0.98, base * 0.95], axis=-1)
    edge = dist < 5
    albedo[edge] = 0.22
    height = np.where(edge, 0.08, 0.5 + tone * 0.25)
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.82), "metallic": np.zeros((size, size))}


cobblestone.tile_meters = 2.0


def gravel(size: int, seed: int, variant: int = 0) -> dict:
    return _noise_ground(size, seed, variant, (0.52, 0.5, 0.48), 0.9)


gravel.tile_meters = 2.0


def sand(size: int, seed: int, variant: int = 0) -> dict:
    return _noise_ground(size, seed, variant, (0.76, 0.68, 0.52), 0.95)


sand.tile_meters = 2.0


def dirt_dry(size: int, seed: int, variant: int = 0) -> dict:
    return _noise_ground(size, seed, variant, (0.42, 0.32, 0.22), 0.88)


dirt_dry.tile_meters = 2.0


def mud(size: int, seed: int, variant: int = 0) -> dict:
    return _noise_ground(size, seed, variant, (0.32, 0.26, 0.18), 0.75)


mud.tile_meters = 2.0


def grass_short(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 5, seed + variant)
    blade = tileable_noise(size, _nearest_divisor(size, 128), seed + 1)
    albedo = solid(size, (0.28, 0.48, 0.18)) * (0.9 + 0.15 * n[..., None] * blade[..., None])
    height = 0.38 + n * 0.15 + blade * 0.08
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.9), "metallic": np.zeros((size, size))}


grass_short.tile_meters = 2.0


def grass_dry(size: int, seed: int, variant: int = 0) -> dict:
    return _noise_ground(size, seed, variant, (0.55, 0.52, 0.28), 0.92)


grass_dry.tile_meters = 2.0


def snow(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 4, seed + variant) * 0.05
    albedo = solid(size, (0.92, 0.94, 0.96)) + n[..., None]
    height = 0.5 + n * 0.5
    return {"albedo": np.clip(albedo, 0.85, 1.0), "height": height, "roughness": np.full((size, size), 0.75), "metallic": np.zeros((size, size))}


snow.tile_meters = 2.0


def forest_floor(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 16, 5, seed + variant)
    leaf = tileable_noise(size, _nearest_divisor(size, 64), seed + 2) > 0.55
    albedo = solid(size, (0.28, 0.22, 0.15)) * (0.9 + 0.15 * n[..., None])
    albedo[leaf] = (0.35, 0.42, 0.18)
    height = 0.4 + n * 0.2
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.88), "metallic": np.zeros((size, size))}


forest_floor.tile_meters = 2.0


def curb_stone(size: int, seed: int, variant: int = 0) -> dict:
    n = tileable_noise(size, 32, seed + variant)
    curb = tileable_noise(size, _nearest_divisor(size, 256), seed + 17)
    curb = np.clip(curb * 1.4 - 0.35, 0, 1)
    road = np.array([0.35, 0.34, 0.33])
    stone = np.array([0.55, 0.54, 0.52])
    albedo = road * (1 - curb[..., None]) + stone * curb[..., None] * (0.95 + 0.08 * n[..., None])
    height = 0.35 + curb * 0.22 + n * 0.05
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.7), "metallic": np.zeros((size, size))}


curb_stone.tile_meters = 2.0


def register(reg):
    for fn in (
        asphalt_clean,
        asphalt_worn,
        asphalt_wet,
        concrete_slab_sidewalk,
        paving_stone_grey,
        cobblestone,
        gravel,
        sand,
        dirt_dry,
        mud,
        grass_short,
        grass_dry,
        snow,
        forest_floor,
        curb_stone,
    ):
        reg("ground", fn.__name__, fn)
