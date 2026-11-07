"""Shared building blocks for tile generators."""
from __future__ import annotations

import numpy as np

def _nearest_divisor(size: int, target: int) -> int:
    best = size
    d = 1
    while d * d <= size:
        if size % d == 0:
            for cand in (d, size // d):
                if abs(cand - target) < abs(best - target):
                    best = cand
        d += 1
    return max(2, best)


from scripts.tilelib import (
    clamp_albedo,
    fbm,
    height_to_ao,
    periodic_blur,
    px_per_m,
    tileable_grid,
    tileable_noise,
    toroidal_dist,
    voronoi_wrap,
)


def solid(size: int, rgb: tuple[float, float, float]) -> np.ndarray:
    a = np.zeros((size, size, 3), dtype=np.float64)
    a[:] = rgb
    return a


def mortar_bricks(
    size: int,
    seed: int,
    tile_meters: float,
    brick_m: tuple[float, float],
    mortar_m: float,
    mortar_rgb: tuple[float, float, float],
    brick_rgb: tuple[float, float, float],
    offset_rows: bool = True,
    wear: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ppm = px_per_m(size, tile_meters)
    bh, bw = brick_m
    mortar_px = max(1, int(round(mortar_m * ppm)))
    brick_h_ideal = max(mortar_px * 2, int(round(bh * ppm)))
    brick_w_ideal = max(mortar_px * 2, int(round(bw * ppm)))
    brick_h = _nearest_divisor(size, brick_h_ideal)
    brick_w = _nearest_divisor(size, brick_w_ideal)
    n_rows = size // brick_h
    n_cols = size // brick_w

    y, x = tileable_grid(size)
    yy = (y % brick_h).astype(int)
    xx = (x % brick_w).astype(int)
    row = ((y // brick_h) % n_rows).astype(int)
    col = ((x // brick_w) % n_cols).astype(int)

    mortar_y = (yy < mortar_px) | (yy >= brick_h - mortar_px)
    mortar_x = (xx < mortar_px) | (xx >= brick_w - mortar_px)
    if offset_rows:
        shift = (row % 2) * (brick_w // 2)
        xx2 = ((x + shift) % brick_w).astype(int)
        col2 = (((x + shift) // brick_w) % n_cols).astype(int)
        mortar_x = (xx2 < mortar_px) | (xx2 >= brick_w - mortar_px)
        col = col2
    mortar = mortar_y | mortar_x

    rng = np.random.default_rng(seed)
    brick_id = row * n_cols + col
    tint = tileable_noise(size, max(2, n_cols), seed + 11)
    tone = 0.92 + 0.08 * tint
    spot = tileable_noise(size, max(4, brick_w), seed + 17)
    albedo = np.zeros((size, size, 3), dtype=np.float64)
    base = np.array(brick_rgb)
    for i in range(n_rows * n_cols):
        m = brick_id == i
        if not m.any():
            continue
        var = 0.9 + 0.12 * rng.random()
        c = base * var * tone[m, None] + spot[m, None] * 0.04
        albedo[m] = c

    albedo[mortar] = mortar_rgb
    if wear > 0:
        w = fbm(size, max(8, n_cols), 4, seed + 99) * wear
        albedo = albedo * (1 - w[..., None] * 0.25)
        dark = w > 0.55
        albedo[dark] *= 0.75

    height = np.where(mortar, 0.15, 0.55 + spot * 0.08).astype(np.float64)
    rough = np.clip(0.5 + height * 0.45 + (tint - 0.5) * 0.08, 0, 1)
    metal = np.zeros_like(height)
    return clamp_albedo(albedo), height, rough, metal


def plank_rows(
    size: int,
    seed: int,
    tile_meters: float,
    plank_w_m: float,
    horizontal: bool,
    base_rgb: tuple[float, float, float],
    gap_rgb: tuple[float, float, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ppm = px_per_m(size, tile_meters)
    pw_ideal = max(4, int(round(plank_w_m * ppm)))
    pw = _nearest_divisor(size, pw_ideal)
    n = size // pw
    rng = np.random.default_rng(seed)
    grain_p = max(2, pw // 2)
    y, x = tileable_grid(size)
    if horizontal:
        idx = ((y // pw) % n).astype(int)
        coord = (x % size) / size
    else:
        idx = ((x // pw) % n).astype(int)
        coord = (y % size) / size
    gap_w = max(1, pw // 32)
    if horizontal:
        yy_pl = y % pw
        in_gap = (yy_pl < gap_w) | (yy_pl >= pw - gap_w)
        grain = tileable_noise(size, grain_p, seed + idx.max() + 3)
        aniso = np.sin(coord * np.pi * 2 * max(8, pw // 4) + idx * 0.7) * 0.5 + 0.5
    else:
        xx_pl = x % pw
        in_gap = (xx_pl < gap_w) | (xx_pl >= pw - gap_w)
        grain = tileable_noise(size, grain_p, seed + 5)
        aniso = np.sin(coord * np.pi * 2 * max(8, pw // 4)) * 0.5 + 0.5

    tone = tileable_noise(size, n, seed + 31)
    albedo = np.array(base_rgb) * (0.88 + 0.14 * tone[..., None])
    albedo *= 0.95 + 0.1 * aniso[..., None]
    albedo += grain[..., None] * 0.03
    albedo[in_gap] = gap_rgb

    height = np.where(in_gap, 0.08, 0.45 + grain * 0.12)
    rough = np.where(in_gap, 0.9, 0.55 + grain * 0.2)
    return clamp_albedo(albedo), height, rough, np.zeros_like(height)


def asphalt_base(size: int, seed: int, wet: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    base = np.array([0.12, 0.12, 0.13])
    grain = fbm(size, 32, 5, seed)
    speck = tileable_noise(size, 64, seed + 3)
    albedo = base + (grain[..., None] - 0.5) * 0.06 + (speck[..., None] - 0.5) * 0.04
    if wet:
        albedo *= 0.75
    height = 0.4 + grain * 0.15 + speck * 0.05
    rough = 0.75 + grain * 0.15
    if wet:
        rough = 0.15 + grain * 0.1
    return clamp_albedo(albedo), height, rough, np.zeros_like(height)


def metal_base(size: int, seed: int, rgb: tuple[float, float, float], rough: float) -> tuple:
    y, x = tileable_grid(size)
    aniso = tileable_noise(size, max(2, size // 128), seed) * 0.03
    line = (np.sin(2 * np.pi * x / size * 512) * 0.5 + 0.5) * 0.02
    albedo = np.array(rgb) + aniso[..., None] + line[..., None]
    height = 0.5 + aniso * 0.2 + line * 0.15
    r = np.full((size, size), rough) + aniso * 0.1
    m = np.ones_like(height)
    return clamp_albedo(albedo), height, r, m


def sinus_waves(size: int, count: float, axis: str = "x") -> np.ndarray:
    y, x = tileable_grid(size)
    if axis == "x":
        phase = 2 * np.pi * x / size * count
    else:
        phase = 2 * np.pi * y / size * count
    return np.sin(phase) * 0.5 + 0.5
