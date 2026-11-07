"""Road marking overlays (RGBA albedo)."""
from __future__ import annotations

import numpy as np

from scripts.tile_gens._helpers import asphalt_base
from scripts.tilelib import clamp_albedo, px_per_m, tileable_grid, tileable_noise


def _marking_base(size: int, seed: int, variant: int) -> tuple:
    a, h, r, m = asphalt_base(size, seed + variant + 1000)
    return a, h, r, m


def _paint_line(
    size: int,
    tile_m: float,
    color: tuple[float, float, float],
    width_m: float,
    mask: np.ndarray,
    wear_seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    wear = tileable_noise(size, 32, wear_seed)
    alpha = mask.astype(float) * (0.75 + 0.25 * (1 - wear * 0.4))
    rgb = np.zeros((size, size, 3))
    rgb[mask] = color
    albedo = np.dstack([rgb, alpha])
    rough = np.where(mask, 0.35 + wear * 0.2, 0.75)
    return albedo, rough


def mark_center_dashed_white(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 4.0)
    dash, gap = 3.0 * ppm, 9.0 * ppm
    period = dash + gap
    y, x = tileable_grid(size)
    cx = size // 2
    w = max(2, int(0.12 * ppm))
    along = x.astype(float)
    phase = along % period
    on = phase < dash
    mask = on & (np.abs(y - cx) < w / 2)
    a_asphalt, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.92, 0.92, 0.9), 0.12, mask, seed + 5)
    rgba = a_asphalt.copy()
    rgba = np.dstack([rgba, np.ones((size, size))])
    rgba[..., :3] = rgba[..., :3] * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    rgba[..., 3] = 1.0
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_center_dashed_white.tile_meters = 4.0


def mark_center_solid_yellow(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    cx = size // 2
    ppm = px_per_m(size, 4.0)
    w = max(2, int(0.12 * ppm))
    mask = np.abs(y - cx) < w / 2
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.85, 0.72, 0.12), 0.12, mask, seed + 3)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_center_solid_yellow.tile_meters = 4.0


def mark_double_solid_yellow(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    ppm = px_per_m(size, 4.0)
    w = max(2, int(0.1 * ppm))
    gap = max(3, int(0.15 * ppm))
    c1, c2 = size // 2 - gap, size // 2 + gap
    mask = (np.abs(y - c1) < w / 2) | (np.abs(y - c2) < w / 2)
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.85, 0.72, 0.12), 0.1, mask, seed + 7)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_double_solid_yellow.tile_meters = 4.0


def mark_edge_solid_white(size: int, seed: int, variant: int = 0) -> dict:
    y, x = tileable_grid(size)
    ppm = px_per_m(size, 4.0)
    w = max(2, int(0.12 * ppm))
    mask = y < w
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.92, 0.92, 0.9), 0.12, mask, seed + 9)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_edge_solid_white.tile_meters = 4.0


def mark_crosswalk_zebra(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 4.0)
    stripe = int(0.5 * ppm)
    step = int(1.0 * ppm)
    y, x = tileable_grid(size)
    mask = (x.astype(int) % step) < stripe
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.95, 0.95, 0.93), 0.5, mask, seed + 11)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_crosswalk_zebra.tile_meters = 4.0


def mark_stop_line(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 4.0)
    thick = int(0.4 * ppm)
    y, x = tileable_grid(size)
    mask = y < thick
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.95, 0.95, 0.93), 0.4, mask, seed + 13)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_stop_line.tile_meters = 4.0


def _arrow_mask(size: int, direction: str) -> np.ndarray:
    y, x = tileable_grid(size)
    cy, cx = size / 2, size / 2
    mask = np.zeros((size, size), dtype=bool)
    body = (np.abs(x - cx) < size * 0.08) & (y > cy - size * 0.2) & (y < cy + size * 0.25)
    mask |= body
    if direction == "straight":
        head = (y < cy - size * 0.05) & (np.abs(x - cx) < size * 0.2 - (cy - y) * 0.3)
        mask |= head
    elif direction == "left":
        mask |= (x < cx) & (y < cy + size * 0.1) & (y > cy - size * 0.35) & (x > cx - size * 0.35)
    else:
        mask |= (x > cx) & (y < cy + size * 0.1) & (y > cy - size * 0.35) & (x < cx + size * 0.35)
    return mask


def mark_arrow_straight(size: int, seed: int, variant: int = 0) -> dict:
    mask = _arrow_mask(size, "straight")
    return _arrow_result(size, seed, variant, mask)


def mark_arrow_left(size: int, seed: int, variant: int = 0) -> dict:
    mask = _arrow_mask(size, "left")
    return _arrow_result(size, seed, variant, mask)


def mark_arrow_right(size: int, seed: int, variant: int = 0) -> dict:
    mask = _arrow_mask(size, "right")
    return _arrow_result(size, seed, variant, mask)


def _arrow_result(size, seed, variant, mask):
    _, h, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.95, 0.95, 0.93), 0.12, mask, seed + 17)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": h, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


for _f in (mark_arrow_straight, mark_arrow_left, mark_arrow_right):
    _f.tile_meters = 4.0


def mark_parking_slot(size: int, seed: int, variant: int = 0) -> dict:
    ppm = px_per_m(size, 4.0)
    y, x = tileable_grid(size)
    w = int(2.5 * ppm)
    h = int(5.0 * ppm)
    ox = (size - w) // 2
    oy = size // 4
    border = (
        ((x >= ox) & (x < ox + w) & (np.abs(y - oy) < 3))
        | ((x >= ox) & (x < ox + w) & (np.abs(y - (oy + h)) < 3))
        | ((y >= oy) & (y < oy + h) & (np.abs(x - ox) < 3))
        | ((y >= oy) & (y < oy + h) & (np.abs(x - (ox + w)) < 3))
    )
    _, hh, _, _ = _marking_base(size, seed, variant)
    mark, rough = _paint_line(size, 4.0, (0.92, 0.92, 0.9), 0.12, border, seed + 19)
    base, _, _, _ = _marking_base(size, seed, variant)
    rgba = np.dstack([base, np.ones((size, size))])
    rgba[..., :3] = base * (1 - mark[..., 3:4]) + mark[..., :3] * mark[..., 3:4]
    return {"albedo": rgba, "height": hh, "roughness": rough, "metallic": np.zeros((size, size)), "albedo_rgba": True}


mark_parking_slot.tile_meters = 4.0


def register(reg):
    reg("road_marking", "mark_center_dashed_white", mark_center_dashed_white)
    reg("road_marking", "mark_center_solid_yellow", mark_center_solid_yellow)
    reg("road_marking", "mark_double_solid_yellow", mark_double_solid_yellow)
    reg("road_marking", "mark_edge_solid_white", mark_edge_solid_white)
    reg("road_marking", "mark_crosswalk_zebra", mark_crosswalk_zebra)
    reg("road_marking", "mark_stop_line", mark_stop_line)
    reg("road_marking", "mark_arrow_straight", mark_arrow_straight)
    reg("road_marking", "mark_arrow_left", mark_arrow_left)
    reg("road_marking", "mark_arrow_right", mark_arrow_right)
    reg("road_marking", "mark_parking_slot", mark_parking_slot)
