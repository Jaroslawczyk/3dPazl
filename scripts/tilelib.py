"""Core helpers for seamless tileable PBR texture generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
TILES_ROOT = ROOT / "assets" / "tiles"


def clamp_albedo(rgb: np.ndarray) -> np.ndarray:
    """Keep albedo in plausible 8-bit range (soft clamp)."""
    return np.clip(rgb, 30 / 255, 240 / 255)


def px_per_m(size: int, tile_meters: float) -> float:
    return size / tile_meters


def tileable_grid(size: int) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:size, 0:size]
    return y.astype(np.float64), x.astype(np.float64)


def tileable_noise(size: int, period: int, seed: int) -> np.ndarray:
    """Periodic value noise; period must divide size (adjusted automatically)."""
    period = max(2, int(period))
    if size % period != 0:
        period = _largest_divisor_leq(size, period)
    rng = np.random.default_rng(seed)
    grid = rng.random((period, period))
    rep = size // period
    # Smooth periodic bicubic upsample (no blocky cells, exact wrap)
    cell = ndimage.zoom(grid, rep, order=3, mode="grid-wrap", grid_mode=True)
    return np.clip(cell, 0, 1)


def _largest_divisor_leq(n: int, target: int) -> int:
    for p in range(min(target, n), 1, -1):
        if n % p == 0:
            return p
    return 1


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


def fbm(
    size: int,
    base_period: int,
    octaves: int,
    seed: int,
    lacunarity: float = 2.0,
    persistence: float = 0.5,
) -> np.ndarray:
    """Fractional Brownian motion with tileable octaves (integer periods divide size)."""
    period = _nearest_divisor(size, base_period)
    amp = 1.0
    total = np.zeros((size, size), dtype=np.float64)
    wsum = 0.0
    for i in range(octaves):
        period = _nearest_divisor(size, period)
        layer = tileable_noise(size, period, seed + i * 7919)
        total += layer * amp
        wsum += amp
        amp *= persistence
        period = _nearest_divisor(size, max(2, int(period // lacunarity)))
        if period < 2:
            break
    return total / max(wsum, 1e-9)


def fft_tileable_white_noise(size: int, seed: int) -> np.ndarray:
    """Band-limited white noise, exactly periodic on size x size."""
    rng = np.random.default_rng(seed)
    h = rng.standard_normal((size, size))
    f = np.fft.fft2(h)
    ky = np.fft.fftfreq(size) * size
    kx = ky[:, None]
    # Kill DC for zero mean; keep all harmonics (period = size)
    f[0, 0] = 0
    out = np.fft.ifft2(f).real
    out -= out.min()
    if out.max() > 0:
        out /= out.max()
    return out


def voronoi_wrap(size: int, n_points: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Toroidal Voronoi: cell id and edge distance (0 at edge, higher in cell center)."""
    rng = np.random.default_rng(seed)
    pts = rng.random((n_points, 2)) * size
    y, x = tileable_grid(size)
    best_d2 = np.full((size, size), np.inf)
    best_id = np.zeros((size, size), dtype=np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            px = pts[:, 0] + dx * size
            py = pts[:, 1] + dy * size
            for i in range(n_points):
                d2 = (x - px[i]) ** 2 + (y - py[i]) ** 2
                mask = d2 < best_d2
                best_d2 = np.where(mask, d2, best_d2)
                best_id = np.where(mask, i, best_id)
    return best_id, np.sqrt(best_d2)


def toroidal_dist(
    yy: np.ndarray, xx: np.ndarray, cy: float, cx: float, size: int
) -> np.ndarray:
    dy = (yy - cy + size / 2) % size - size / 2
    dx = (xx - cx + size / 2) % size - size / 2
    return np.hypot(dx, dy)


def periodic_blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur with wrap boundary."""
    return ndimage.gaussian_filter(arr, sigma=sigma, mode="wrap")


def height_to_normal(height: np.ndarray, strength: float = 3.0) -> np.ndarray:
    h = height.astype(np.float64)
    dx = np.zeros_like(h)
    dy = np.zeros_like(h)
    dx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5
    dy[1:-1, :] = (h[2:, :] - h[:-2, :]) * 0.5
    # Wrap edges
    dx[:, 0] = (h[:, 1] - h[:, -1]) * 0.5
    dx[:, -1] = (h[:, 0] - h[:, -2]) * 0.5
    dy[0, :] = (h[1, :] - h[-1, :]) * 0.5
    dy[-1, :] = (h[0, :] - h[-2, :]) * 0.5
    nx = -dx * strength
    ny = dy * strength
    nz = np.ones_like(h)
    n = np.stack([nx, ny, nz], axis=-1)
    ln = np.linalg.norm(n, axis=-1, keepdims=True).clip(1e-6)
    n /= ln
    return n * 0.5 + 0.5


def height_to_ao(height: np.ndarray, blur_sigma: float = 3.0) -> np.ndarray:
    h = height.astype(np.float64)
    blurred = periodic_blur(h, blur_sigma)
    ao = blurred - h
    ao = np.clip(ao, 0, None)
    mx = ao.max()
    if mx > 1e-9:
        ao = ao / mx
    return 1.0 - ao * 0.85


def tile3x3(rgb: np.ndarray) -> np.ndarray:
    return np.tile(rgb, (3, 3, 1) if rgb.ndim == 3 else (3, 3))


def _save_gray16(path: Path, arr: np.ndarray):
    a = np.clip(arr * 65535, 0, 65535).astype(np.uint16)
    Image.fromarray(a, mode="I;16").save(path)


def save_set(
    out_dir: Path,
    albedo: np.ndarray,
    height: np.ndarray,
    roughness: np.ndarray,
    metallic: np.ndarray | None = None,
    ao: np.ndarray | None = None,
    normal: np.ndarray | None = None,
    emissive: np.ndarray | None = None,
    albedo_rgba: bool = False,
):
    out_dir.mkdir(parents=True, exist_ok=True)
    sz = albedo.shape[0]

    def _2d(a: np.ndarray | float, fill: float = 0.0) -> np.ndarray:
        if a is None:
            return np.full((sz, sz), fill)
        if np.isscalar(a) or (isinstance(a, np.ndarray) and a.ndim == 0):
            return np.full((sz, sz), float(a))
        return np.asarray(a, dtype=np.float64)

    albedo = np.clip(albedo, 0, 1)
    height = np.clip(_2d(height, 0.5), 0, 1)
    roughness = np.clip(_2d(roughness, 0.5), 0, 1)
    if metallic is None:
        metallic = np.zeros_like(height)
    else:
        metallic = _2d(metallic, 0.0)
    if ao is None:
        ao = height_to_ao(height)
    if normal is None:
        normal = height_to_normal(height)

    if albedo_rgba:
        if albedo.shape[-1] == 4:
            rgba = (albedo * 255).astype(np.uint8)
        else:
            a = np.ones((*albedo.shape[:2], 1))
            rgba = np.dstack([albedo, a])
            rgba = (rgba * 255).astype(np.uint8)
        Image.fromarray(rgba, mode="RGBA").save(out_dir / "albedo.png")
    else:
        rgb = (clamp_albedo(albedo[..., :3] if albedo.shape[-1] >= 3 else albedo) * 255).astype(np.uint8)
        Image.fromarray(rgb, mode="RGB").save(out_dir / "albedo.png")

    try:
        _save_gray16(out_dir / "height.png", height)
    except Exception:
        Image.fromarray((height * 255).astype(np.uint8), mode="L").save(out_dir / "height.png")

    nrgb = (np.clip(normal, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(nrgb, mode="RGB").save(out_dir / "normal.png")
    Image.fromarray((ao * 255).astype(np.uint8), mode="L").save(out_dir / "ao.png")
    Image.fromarray((roughness * 255).astype(np.uint8), mode="L").save(out_dir / "roughness.png")
    metal_bin = (metallic > 0.5).astype(np.uint8) * 255
    Image.fromarray(metal_bin, mode="L").save(out_dir / "metallic.png")

    prev = tile3x3(albedo[..., :3] if albedo.ndim == 3 and albedo.shape[-1] >= 3 else albedo)
    if prev.ndim == 2:
        prev = np.stack([prev] * 3, axis=-1)
    Image.fromarray((np.clip(prev, 0, 1) * 255).astype(np.uint8), mode="RGB").save(out_dir / "preview.png")

    if emissive is not None:
        Image.fromarray((np.clip(emissive, 0, 1) * 255).astype(np.uint8), mode="RGB").save(
            out_dir / "emissive.png"
        )


def write_manifest(entries: list[dict[str, Any]], size: int):
    TILES_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = TILES_ROOT / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({"size": size, "textures": entries}, f, indent=2, ensure_ascii=False)
