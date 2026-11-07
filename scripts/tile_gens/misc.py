"""Miscellaneous tile generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import solid
from scripts.tilelib import clamp_albedo, fbm, tileable_grid, tileable_noise, voronoi_wrap


def _checker(size, c1, c2, n=8):
    y, x = tileable_grid(size)
    chk = ((x.astype(int) // (size // n)) + (y.astype(int) // (size // n))) % 2
    albedo = np.zeros((size, size, 3))
    albedo[chk == 0] = c1
    albedo[chk == 1] = c2
    return clamp_albedo(albedo), np.full((size, size), 0.5), np.full((size, size), 0.6), np.zeros((size, size))


def tile_floor_checker(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = _checker(size, (0.85, 0.85, 0.87), (0.15, 0.15, 0.17))
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


tile_floor_checker.tile_meters = 1.0


def tile_floor_terrazzo(size: int, seed: int, variant: int = 0) -> dict:
    ids, _ = voronoi_wrap(size, 80, seed + variant)
    rng = np.random.default_rng(seed + variant)
    chips = rng.uniform(0.2, 0.8, (80, 3))
    base = solid(size, (0.82, 0.8, 0.78))
    albedo = chips[ids]
    albedo = 0.55 * base + 0.45 * albedo
    n = tileable_noise(size, 32, seed)
    height = 0.48 + n * 0.08
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.35), "metallic": np.zeros((size, size))}


tile_floor_terrazzo.tile_meters = 1.0


def marble_white(size: int, seed: int, variant: int = 0) -> dict:
    veins = fbm(size, 8, 4, seed + variant)
    albedo = solid(size, (0.9, 0.9, 0.88)) + (veins[..., None] - 0.5) * 0.08
    return {"albedo": clamp_albedo(albedo), "height": 0.5 + veins * 0.05, "roughness": np.full((size, size), 0.25), "metallic": np.zeros((size, size))}


marble_white.tile_meters = 1.0


def marble_black_gold(size: int, seed: int, variant: int = 0) -> dict:
    veins = fbm(size, 8, 4, seed + variant)
    albedo = solid(size, (0.12, 0.12, 0.14))
    gold = veins > 0.55
    albedo[gold] = (0.65, 0.5, 0.2)
    return {"albedo": clamp_albedo(albedo), "height": 0.48 + veins * 0.1, "roughness": np.full((size, size), 0.3), "metallic": np.where(gold, 1.0, 0.0)}


marble_black_gold.tile_meters = 1.0


def granite_grey(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 5, seed + variant)
    speck = tileable_noise(size, 128, seed + 2) > 0.6
    base = 0.45 + n * 0.1
    albedo = np.stack([base, base, base * 1.02], axis=-1)
    albedo[speck] *= 1.08
    return {"albedo": clamp_albedo(albedo), "height": 0.5 + n * 0.12, "roughness": np.full((size, size), 0.55), "metallic": np.zeros((size, size))}


granite_grey.tile_meters = 1.0


def carpet_grey(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 64, 6, seed + variant)
    albedo = solid(size, (0.42, 0.42, 0.44)) * (0.92 + 0.12 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.42 + n * 0.18, "roughness": np.full((size, size), 0.95), "metallic": np.zeros((size, size))}


carpet_grey.tile_meters = 1.0


def cardboard(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 16, 3, seed + variant)
    albedo = solid(size, (0.62, 0.48, 0.32)) * (0.95 + 0.08 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.45 + n * 0.1, "roughness": np.full((size, size), 0.85), "metallic": np.zeros((size, size))}


cardboard.tile_meters = 1.0


def paper_rough(size: int, seed: int, variant: int = 0) -> dict:
    n = tileable_noise(size, 64, seed + variant)
    albedo = solid(size, (0.88, 0.86, 0.82)) * (0.98 + 0.04 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.48 + n * 0.06, "roughness": np.full((size, size), 0.8), "metallic": np.zeros((size, size))}


paper_rough.tile_meters = 1.0


def plaster_cracked(size: int, seed: int, variant: int = 0) -> dict:
    crack = fbm(size, 8, 3, seed + variant) > 0.62
    albedo = solid(size, (0.88, 0.86, 0.82))
    albedo[crack] *= 0.75
    h = 0.48 * np.ones((size, size))
    h[crack] = 0.3
    return {"albedo": clamp_albedo(albedo), "height": h, "roughness": np.full((size, size), 0.75), "metallic": np.zeros((size, size))}


plaster_cracked.tile_meters = 1.0


def lava_cracked(size: int, seed: int, variant: int = 0) -> dict:
    crack = fbm(size, 8, 4, seed + variant) > 0.55
    albedo = solid(size, (0.18, 0.08, 0.06))
    em = np.zeros((size, size, 3))
    em[crack] = (1.0, 0.35, 0.05)
    albedo[crack] = (0.35, 0.12, 0.05)
    h = 0.42 + fbm(size, 16, 3, seed) * 0.2
    return {"albedo": clamp_albedo(albedo), "height": h, "roughness": np.full((size, size), 0.7), "metallic": np.zeros((size, size)), "emissive": em}


lava_cracked.tile_meters = 1.0


def ice(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 4, seed + variant) * 0.06
    albedo = solid(size, (0.75, 0.85, 0.92)) + n[..., None]
    return {"albedo": clamp_albedo(albedo), "height": 0.5 + n, "roughness": np.full((size, size), 0.15), "metallic": np.zeros((size, size))}


ice.tile_meters = 1.0


def bark_birch(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    stripe = (np.sin(2 * np.pi * y / size * 40) > 0.85).astype(float)
    albedo = solid(size, (0.82, 0.78, 0.72))
    albedo[stripe > 0] = (0.2, 0.18, 0.16)
    return {"albedo": clamp_albedo(albedo), "height": 0.45 + stripe * 0.12, "roughness": np.full((size, size), 0.85), "metallic": np.zeros((size, size))}


bark_birch.tile_meters = 1.0


def moss(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 5, seed + variant)
    albedo = solid(size, (0.25, 0.42, 0.2)) * (0.9 + 0.15 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.4 + n * 0.2, "roughness": np.full((size, size), 0.9), "metallic": np.zeros((size, size))}


moss.tile_meters = 1.0


def ivy_leaves(size: int, seed: int, variant: int = 0) -> dict:
    leaf = tileable_noise(size, 32, seed + variant) > 0.6
    base = solid(size, (0.22, 0.35, 0.15))
    base[leaf] = (0.32, 0.52, 0.22)
    n = fbm(size, 16, 3, seed)
    return {"albedo": clamp_albedo(base), "height": 0.42 + n * 0.15, "roughness": np.full((size, size), 0.88), "metallic": np.zeros((size, size))}


ivy_leaves.tile_meters = 1.0


def register(reg):
    for fn in (
        tile_floor_checker,
        tile_floor_terrazzo,
        marble_white,
        marble_black_gold,
        granite_grey,
        carpet_grey,
        cardboard,
        paper_rough,
        plaster_cracked,
        lava_cracked,
        ice,
        bark_birch,
        moss,
        ivy_leaves,
    ):
        reg("misc", fn.__name__, fn)
