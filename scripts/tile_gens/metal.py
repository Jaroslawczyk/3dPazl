"""Metal surface generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import metal_base, sinus_waves, solid
from scripts.tilelib import _nearest_divisor, clamp_albedo, fbm, px_per_m, tileable_grid, tileable_noise, toroidal_dist, voronoi_wrap


def metal_brushed_steel(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = metal_base(size, seed + variant, (0.62, 0.64, 0.66), 0.7)
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


metal_brushed_steel.tile_meters = 0.5


def metal_diamond_plate(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 0.5)
    rh = _nearest_divisor(size, max(4, int(0.025 * ppm)))
    rw = _nearest_divisor(size, max(4, int(0.01 * ppm)))
    y, x = tileable_grid(size)
    cx = (x.astype(int) // rw) * rw + rw / 2
    cy = (y.astype(int) // rh) * rh + rh / 2
    d = toroidal_dist(y, x, cy, cx, size)
    bump = (d < min(rw, rh) * 0.6).astype(float)
    a, h, r, m = metal_base(size, seed + variant, (0.48, 0.5, 0.52), 0.55)
    h = h + bump * 0.25
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


metal_diamond_plate.tile_meters = 0.5


def metal_corrugated(size: int, seed: int, variant: int = 0) -> dict:
    wave = sinus_waves(size, 7.5, "x")
    rust = (wave < 0.15) | (wave > 0.85)
    a = solid(size, (0.55, 0.56, 0.58)) + (wave[..., None] - 0.5) * 0.05
    a[rust] = (0.45, 0.28, 0.15)
    h = 0.45 + wave * 0.2
    r = np.where(rust, 0.85, 0.45 + wave * 0.15)
    m = np.where(rust, 0.0, 1.0)
    return {"albedo": clamp_albedo(a), "height": h, "roughness": r, "metallic": m}


metal_corrugated.tile_meters = 1.0


def metal_rust_heavy(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 16, 5, seed + variant)
    rust = n > 0.45
    albedo = solid(size, (0.5, 0.52, 0.54))
    albedo[rust] = (0.55, 0.28, 0.12)
    m = np.where(rust, 0.0, 1.0)
    r = np.where(rust, 0.9, 0.5)
    return {"albedo": clamp_albedo(albedo), "height": 0.4 + n * 0.3, "roughness": r, "metallic": m}


metal_rust_heavy.tile_meters = 1.0


def metal_painted_chipped(size: int, seed: int, variant: int = 0) -> dict:
    chip = tileable_noise(size, 16, seed + variant) > 0.58
    a, h, r, m = metal_base(size, seed, (0.55, 0.58, 0.62), 0.45)
    paint = solid(size, (0.22, 0.35, 0.55))
    albedo = paint.copy()
    albedo[chip] = a[chip]
    m = np.where(chip, 1.0, 0.0)
    return {"albedo": clamp_albedo(albedo), "height": h, "roughness": np.where(chip, r, 0.65), "metallic": m}


metal_painted_chipped.tile_meters = 1.0


def metal_galvanized(size: int, seed: int, variant: int = 0) -> dict:
    _, dist = voronoi_wrap(size, 64, seed + variant)
    flake = np.sin(dist * 8) * 0.5 + 0.5
    a = solid(size, (0.72, 0.74, 0.76)) + (flake[..., None] - 0.5) * 0.06
    return {"albedo": clamp_albedo(a), "height": 0.5 + flake * 0.08, "roughness": np.full((size, size), 0.5), "metallic": np.ones((size, size))}


metal_galvanized.tile_meters = 1.0


def metal_copper_oxidized(size: int, seed: int, variant: int = 0) -> dict:
    pat = fbm(size, 16, 4, seed + variant) > 0.5
    albedo = solid(size, (0.62, 0.42, 0.28))
    albedo[pat] = (0.28, 0.42, 0.35)
    m = np.where(pat, 0.0, 1.0)
    return {"albedo": clamp_albedo(albedo), "height": 0.48, "roughness": np.where(pat, 0.75, 0.4), "metallic": m}


metal_copper_oxidized.tile_meters = 1.0


def metal_gold_brass(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = metal_base(size, seed + variant, (0.72, 0.58, 0.22), 0.35)
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


metal_gold_brass.tile_meters = 0.5


def metal_chrome(size: int, seed: int, variant: int = 0) -> dict:
    a, h, r, m = metal_base(size, seed + variant, (0.78, 0.78, 0.8), 0.1)
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


metal_chrome.tile_meters = 0.5


def metal_cast_iron(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 5, seed + variant)
    a, h, r, m = metal_base(size, seed, (0.32, 0.32, 0.34), 0.85)
    h = h + n * 0.2
    return {"albedo": a, "height": h, "roughness": r + n * 0.1, "metallic": m}


metal_cast_iron.tile_meters = 1.0


def metal_rivets_panel(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 1.0)
    step = int(0.1 * ppm)
    y, x = tileable_grid(size)
    yy = (y.astype(int) // step) * step + step // 2
    xx = (x.astype(int) // step) * step + step // 2
    d = toroidal_dist(y, x, yy, xx, size)
    rivet = np.clip(1 - d / (step * 0.15), 0, 1) ** 2
    a, h, r, m = metal_base(size, seed + variant, (0.48, 0.5, 0.52), 0.55)
    h = h + rivet * 0.2
    return {"albedo": a, "height": h, "roughness": r, "metallic": m}


metal_rivets_panel.tile_meters = 1.0


def metal_grate(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    bar = _nearest_divisor(size, 8)
    mask = (x.astype(int) % bar < max(1, bar // 4)) | (y.astype(int) % bar < max(1, bar // 4))
    a, h, r, m = metal_base(size, seed + variant, (0.42, 0.44, 0.46), 0.5)
    alpha = np.where(mask, 0.9, 0.05)
    rgba = np.dstack([a, alpha])
    h = h + mask.astype(float) * 0.15
    return {"albedo": rgba, "height": h, "roughness": r, "metallic": m, "albedo_rgba": True}


metal_grate.tile_meters = 1.0


def metal_perforated(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    hole = (x.astype(int) % 16 < 6) & (y.astype(int) % 16 < 6)
    cx = (x.astype(int) // 16) * 16 + 8
    cy = (y.astype(int) // 16) * 16 + 8
    d = np.hypot(x - cx, y - cy)
    hole |= d < 4
    a, h, r, m = metal_base(size, seed, (0.55, 0.57, 0.58), 0.45)
    alpha = np.where(hole, 0.05, 0.95)
    return {"albedo": np.dstack([a, alpha]), "height": h, "roughness": r, "metallic": m, "albedo_rgba": True}


metal_perforated.tile_meters = 1.0


def register(reg):
    for fn in (
        metal_brushed_steel,
        metal_diamond_plate,
        metal_corrugated,
        metal_rust_heavy,
        metal_painted_chipped,
        metal_galvanized,
        metal_copper_oxidized,
        metal_gold_brass,
        metal_chrome,
        metal_cast_iron,
        metal_rivets_panel,
        metal_grate,
        metal_perforated,
    ):
        reg("metal", fn.__name__, fn)
