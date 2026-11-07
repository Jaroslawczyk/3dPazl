"""Tech / carbon / fabric generators."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import solid
from scripts.tilelib import clamp_albedo, fbm, tileable_grid, tileable_noise


def carbon_twill_2x2(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    weave = (np.sin((x + y) / size * np.pi * 32) * np.sin((x - y) / size * np.pi * 32) * 0.5 + 0.5)
    albedo = solid(size, (0.08, 0.08, 0.09)) + weave[..., None] * 0.06
    height = 0.45 + weave * 0.15
    rough = 0.25 + weave * 0.1
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": rough, "metallic": np.zeros((size, size))}


carbon_twill_2x2.tile_meters = 0.1


def carbon_plain_weave(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    w = (np.sin(2 * np.pi * x / size * 24) * np.sin(2 * np.pi * y / size * 24) * 0.5 + 0.5)
    albedo = solid(size, (0.1, 0.1, 0.11)) + w[..., None] * 0.05
    return {"albedo": clamp_albedo(albedo), "height": 0.45 + w * 0.12, "roughness": np.full((size, size), 0.28), "metallic": np.zeros((size, size))}


carbon_plain_weave.tile_meters = 0.1


def carbon_forged(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 16, 5, seed + variant)
    albedo = solid(size, (0.12, 0.12, 0.13)) * (0.9 + 0.15 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.42 + n * 0.25, "roughness": np.full((size, size), 0.35), "metallic": np.zeros((size, size))}


carbon_forged.tile_meters = 0.15


def kevlar_yellow(size: int, seed: int, variant: int = 0) -> dict:
    w = tileable_noise(size, 32, seed + variant)
    albedo = solid(size, (0.72, 0.62, 0.18)) * (0.94 + 0.08 * w[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.45 + w * 0.1, "roughness": np.full((size, size), 0.75), "metallic": np.zeros((size, size))}


kevlar_yellow.tile_meters = 0.25


def _fabric(name, rgb, rough=0.8):
    def gen(size: int, seed: int, variant: int = 0) -> dict:
        w = fbm(size, 32, 4, seed + variant)
        albedo = solid(size, rgb) * (0.92 + 0.1 * w[..., None])
        return {"albedo": clamp_albedo(albedo), "height": 0.45 + w * 0.1, "roughness": np.full((size, size), rough), "metallic": np.zeros((size, size))}

    gen.__name__ = name
    gen.tile_meters = 0.25
    return gen


fabric_canvas = _fabric("fabric_canvas", (0.62, 0.55, 0.42))
fabric_denim = _fabric("fabric_denim", (0.22, 0.32, 0.48))
fabric_leather = _fabric("fabric_leather", (0.35, 0.22, 0.14), 0.55)


def leather_perforated(size: int, seed: int, variant: int = 0) -> dict:
    d = fabric_leather(size, seed, variant)
    y, x = tileable_grid(size)
    holes = (x.astype(int) % 12 < 4) & (y.astype(int) % 12 < 4)
    d["height"][holes] -= 0.1
    return d


leather_perforated.tile_meters = 0.25


def rubber_tread(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    groove = (np.sin(2 * np.pi * y / size * 20) > 0.6).astype(float)
    albedo = solid(size, (0.15, 0.15, 0.16))
    height = 0.35 + groove * 0.2
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.9), "metallic": np.zeros((size, size))}


rubber_tread.tile_meters = 0.25


def rubber_floor_dots(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    dot = ((x.astype(int) % 24) < 8) & ((y.astype(int) % 24) < 8)
    albedo = solid(size, (0.18, 0.18, 0.2))
    height = 0.4 + dot.astype(float) * 0.12
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": np.full((size, size), 0.85), "metallic": np.zeros((size, size))}


rubber_floor_dots.tile_meters = 0.5


def plastic_matte_abs(size: int, seed: int, variant: int = 0) -> dict:
    n = tileable_noise(size, 64, seed + variant)
    albedo = solid(size, (0.32, 0.34, 0.36)) * (0.97 + 0.05 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.5, "roughness": np.full((size, size), 0.55), "metallic": np.zeros((size, size))}


plastic_matte_abs.tile_meters = 0.25


def plastic_grained(size: int, seed: int, variant: int = 0) -> dict:
    return plastic_matte_abs(size, seed, variant)


plastic_grained.tile_meters = 0.25


def foam_sponge(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 32, 6, seed + variant)
    albedo = solid(size, (0.78, 0.8, 0.82)) * (0.9 + 0.15 * n[..., None])
    return {"albedo": clamp_albedo(albedo), "height": 0.35 + n * 0.3, "roughness": np.full((size, size), 0.95), "metallic": np.zeros((size, size))}


foam_sponge.tile_meters = 0.25


def glass_frosted(size: int, seed: int, variant: int = 0) -> dict:
    n = fbm(size, 64, 4, seed + variant)
    albedo = solid(size, (0.85, 0.88, 0.9))
    height = 0.5 + n * 0.08
    return {"albedo": clamp_albedo(albedo), "height": height, "roughness": 0.4 + n * 0.3, "metallic": np.zeros((size, size))}


glass_frosted.tile_meters = 0.25


def glass_scratched(size: int, seed: int, variant: int = 0) -> dict:
    scratch = tileable_noise(size, 128, seed) > 0.7
    d = glass_frosted(size, seed, variant)
    d["roughness"][scratch] = 0.55
    return d


glass_scratched.tile_meters = 0.25


def register(reg):
    for fn in (
        carbon_twill_2x2,
        carbon_plain_weave,
        carbon_forged,
        kevlar_yellow,
        fabric_canvas,
        fabric_denim,
        fabric_leather,
        leather_perforated,
        rubber_tread,
        rubber_floor_dots,
        plastic_matte_abs,
        plastic_grained,
        foam_sponge,
        glass_frosted,
        glass_scratched,
    ):
        reg("tech", fn.__name__, fn)
