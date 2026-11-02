"""Процедурные бесшовные PBR-текстуры магазина (low-poly).

Запуск из этой папки:  python make_textures.py

Карты не рисуются нейросетью. Рельеф строится периодическим шумом,
швы и блики — целым числом периодов на тайл. Размытие только
scipy.ndimage с mode='wrap', производные только через np.roll,
поэтому левый край продолжает правый, верхний — нижний.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent
SIZE = 512

# Допуск автопроверки шва, в уровнях 8-битного канала.
# Квантование float→uint8 даёт ±1 на плавных переходах.
SEAM_TOL = 2.0


# ---------------------------------------------------------------------------
# Шум и фильтры. Всё периодично с периодом = размер картинки.
# ---------------------------------------------------------------------------

def _smooth(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def _lattice(cells_y: int, cells_x: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((cells_y, cells_x)).astype(np.float32)


def _sample(grid: np.ndarray, y: np.ndarray, x: np.ndarray) -> np.ndarray:
    cells_y, cells_x = grid.shape
    y = np.mod(y, cells_y)
    x = np.mod(x, cells_x)
    y0 = np.floor(y).astype(np.int32) % cells_y
    x0 = np.floor(x).astype(np.int32) % cells_x
    ty = (y - np.floor(y)).astype(np.float32)
    tx = (x - np.floor(x)).astype(np.float32)
    sy = _smooth(ty)
    sx = _smooth(tx)
    y1 = (y0 + 1) % cells_y
    x1 = (x0 + 1) % cells_x
    v00 = grid[y0, x0]
    v10 = grid[y0, x1]
    v01 = grid[y1, x0]
    v11 = grid[y1, x1]
    return (v00 * (1.0 - sx) + v10 * sx) * (1.0 - sy) + (v01 * (1.0 - sx) + v11 * sx) * sy


def noise(h: int, w: int, cells_y: int, cells_x: int, seed: int,
          warp: np.ndarray | None = None, warp_amp: float = 0.0) -> np.ndarray:
    """Value-noise с целым числом ячеек на текстуру: края совпадают."""
    grid = _lattice(max(1, cells_y), max(1, cells_x), seed)
    ys = np.linspace(0.0, grid.shape[0], h, endpoint=False, dtype=np.float32)
    xs = np.linspace(0.0, grid.shape[1], w, endpoint=False, dtype=np.float32)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    if warp is not None and warp_amp != 0.0:
        yy = yy + (warp - 0.5) * np.float32(warp_amp)
    return _sample(grid, yy, xx)


def fbm(h: int, w: int, cells_y: int, cells_x: int, octaves: int, seed: int,
        persistence: float = 0.55) -> np.ndarray:
    acc = np.zeros((h, w), np.float32)
    amp = 1.0
    total = 0.0
    cy, cx = max(1, cells_y), max(1, cells_x)
    for o in range(octaves):
        acc += np.float32(amp) * noise(h, w, cy, cx, seed + o * 17)
        total += amp
        amp *= persistence
        cy = max(1, cy * 2)
        cx = max(1, cx * 2)
    return acc / np.float32(total)


def blur(img: np.ndarray, sigma) -> np.ndarray:
    """Гауссово размытие по кругу (mode='wrap')."""
    if np.isscalar(sigma):
        sig = (float(sigma), float(sigma))
    else:
        sig = (float(sigma[0]), float(sigma[1]))
    if sig[0] <= 0.01 and sig[1] <= 0.01:
        return img.astype(np.float32, copy=False)
    return gaussian_filter(img.astype(np.float32), sigma=sig, mode="wrap").astype(np.float32)


def hex_rgb(color: str) -> np.ndarray:
    c = color.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def shade(base: np.ndarray, height: np.ndarray, grain: np.ndarray | None = None,
          relief: float = 0.08, grain_amp: float = 0.0) -> np.ndarray:
    """Цвет из базового оттенка: рельеф чуть светлее на выступах, плюс слабый шум."""
    hn = height - np.mean(height)
    scale = np.percentile(np.abs(hn), 98) + 1e-6
    t = np.clip(hn / scale, -1.0, 1.0)
    factor = 1.0 + np.float32(relief) * t
    if grain is not None and grain_amp:
        factor = factor + np.float32(grain_amp) * (grain - 0.5) * 2.0
    rgb = base.reshape(1, 1, 3) * factor[..., None]
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def normal_map(h: np.ndarray, k: float) -> np.ndarray:
    """OpenGL / glTF: +Y вверх (к верху картинки), нейтраль (0.5, 0.5, 1).

    dx/dy — центральные разности через np.roll, без краевых срезов.
    На верхней стороне выпуклости зелёный канал > 0.5, на правой — красный > 0.5.
    Знак dy относительно «наивного» (-dx, -dy) перевёрнут: в координатах
    картинки ось Y смотрит вниз, а в glTF зелёный канал смотрит вверх.
    """
    h = h.astype(np.float32)
    dx = np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)
    dy = np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)
    nx = -dx * np.float32(k)
    ny = dy * np.float32(k)
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.empty(h.shape + (3,), np.float32)
    rgb[..., 0] = nx * inv * 0.5 + 0.5
    rgb[..., 1] = ny * inv * 0.5 + 0.5
    rgb[..., 2] = nz * inv * 0.5 + 0.5
    return np.clip(rgb, 0.0, 1.0)


def ao_map(h: np.ndarray, sigma: float, strength: float, floor: float = 0.55) -> np.ndarray:
    """Впадины (ниже циклически размытого рельефа) темнее. Не темнее floor."""
    if strength <= 0.0:
        return np.ones_like(h, dtype=np.float32)
    smooth = blur(h, sigma)
    cavity = np.clip(smooth - h, 0.0, None)
    denom = float(np.percentile(cavity, 99.0)) + 1e-6
    c = np.clip(cavity / denom, 0.0, 1.0)
    c = np.sqrt(c).astype(np.float32)
    ao = 1.0 - c * np.float32((1.0 - floor) * strength)
    return np.clip(ao, floor, 1.0).astype(np.float32)


def as_map(value, shape) -> np.ndarray:
    if np.isscalar(value):
        return np.full(shape, np.float32(value), np.float32)
    arr = np.asarray(value, np.float32)
    if arr.shape != shape:
        arr = np.broadcast_to(arr, shape).astype(np.float32, copy=True)
    return arr


def groove_from_dist(dist_px: np.ndarray, width: float, depth: float) -> np.ndarray:
    """Гладкая канавка. dist_px = 0 на оси шва. Профиль симметричен, период целый."""
    t = np.clip(dist_px / np.float32(width), 0.0, 1.0)
    s = _smooth(t)
    return (np.float32(depth) * (1.0 - s)).astype(np.float32)


def dist_to_period_lines(coord_px: np.ndarray, period_px: float) -> np.ndarray:
    """Расстояние до ближайшей линии сетки с шагом period_px, с учётом склейки краёв."""
    p = np.float32(period_px)
    r = np.mod(coord_px.astype(np.float32), p)
    return np.minimum(r, p - r)


def to_u8(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr)
    if a.dtype == np.uint8 and a.ndim == 3 and a.shape[-1] == 3:
        return np.ascontiguousarray(a)
    a = a.astype(np.float32)
    if a.ndim == 2:
        g = np.clip(np.rint(a * 255.0), 0, 255).astype(np.uint8)
        return np.stack([g, g, g], axis=-1)
    return np.clip(np.rint(a * 255.0), 0, 255).astype(np.uint8)


def save_rgb(path: Path, arr: np.ndarray) -> np.ndarray:
    u8 = to_u8(arr)
    Image.fromarray(u8, "RGB").save(path, format="PNG")
    return u8


# ---------------------------------------------------------------------------
# Проверка шва
# ---------------------------------------------------------------------------

def seam_metrics(u8: np.ndarray) -> tuple[bool, dict]:
    """Левый/правый и верх/низ не расходятся сильнее, чем соседние пиксели внутри."""
    a = u8.astype(np.float32)
    if a.ndim == 2:
        a = a[..., None]

    def chmax(d):
        return np.max(np.abs(d), axis=-1)

    seam_x = chmax(a[:, :1, :] - a[:, -1:, :])
    int_x = chmax(a[:, 1:, :] - a[:, :-1, :])
    seam_y = chmax(a[:1, :, :] - a[-1:, :, :])
    int_y = chmax(a[1:, :, :] - a[:-1, :, :])

    def ok(seam, internal) -> bool:
        # Кромка не круче самого крутого соседства внутри.
        # Шов панели может лежать на границе тайла: тогда шаг «последний|первый»
        # такой же, как шаг по склону канавки на пару пикселей глубже, и максимум
        # внутри его покрывает. Ступенька градиента — нет: внутри шаги мелкие.
        return float(np.max(seam)) <= float(np.max(internal)) + SEAM_TOL

    info = {
        "sx": float(seam_x.max()),
        "ix": float(int_x.max()),
        "sy": float(seam_y.max()),
        "iy": float(int_y.max()),
        "mx": float(seam_x.mean()),
        "my": float(seam_y.mean()),
    }
    return ok(seam_x, int_x) and ok(seam_y, int_y), info


def float_height_seamless(h: np.ndarray, name: str) -> bool:
    a = h.astype(np.float32)
    good = True
    for axis, label in ((1, "x"), (0, "y")):
        if axis == 1:
            seam = np.abs(a[:, 0] - a[:, -1])
            internal = np.abs(np.diff(a, axis=1))
        else:
            seam = np.abs(a[0, :] - a[-1, :])
            internal = np.abs(np.diff(a, axis=0))
        limit = float(internal.max()) + 1e-4
        if float(seam.max()) > limit:
            print(
                f"  рельеф {name} {label}: шов {float(seam.max()):.5f} > "
                f"внутри {float(internal.max()):.5f}"
            )
            good = False
    return good


# ---------------------------------------------------------------------------
# Материалы
# ---------------------------------------------------------------------------

def make_wall_plaster():
    """2×2 м, швы панелей каждые 1 м — две панели по каждой оси."""
    base = hex_rgb("#e8e4da")
    n = SIZE
    px = np.arange(n, dtype=np.float32)
    # 2 м на 512 px → 1 м = 256 px. Шов по центру пиксельной сетки и на краю тайла.
    dist_x = dist_to_period_lines(px, 256.0)
    dist_y = dist_to_period_lines(px, 256.0)
    dx = dist_x[None, :]
    dy = dist_y[:, None]
    seams = np.maximum(groove_from_dist(dx, 3.2, 0.045), groove_from_dist(dy, 3.2, 0.045))
    grain = fbm(n, n, 48, 48, 3, seed=11, persistence=0.5)
    grain = blur(grain, 0.45)
    broad = fbm(n, n, 4, 4, 2, seed=12)
    height = 0.50 + (grain - 0.5) * 0.035 + (broad - 0.5) * 0.012 - seams
    color = shade(base, height, grain, relief=0.04, grain_amp=0.01)
    mask = np.clip(seams / 0.045, 0.0, 1.0)
    color *= (1.0 - 0.06 * mask)[..., None]
    rough = np.clip(0.90 + (grain - 0.5) * 0.04, 0.0, 1.0)
    ao = ao_map(height, sigma=3.0, strength=0.40)
    return height, np.clip(color, 0, 1), 1.5, rough, 0.0, ao


def make_glass():
    """3×3 м. Мягкие диагональные блики, целое число периодов."""
    base = hex_rgb("#78b9e1")
    n = SIZE
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    # Целое число периодов по диагонали — на противоположных краях фаза совпадает.
    s1 = 0.5 + 0.5 * np.cos(2.0 * np.pi * (x + y) / n)
    s2 = 0.5 + 0.5 * np.cos(2.0 * np.pi * (x - y) / n + 1.1)
    sheen = np.clip(np.power(s1, 1.5) + 0.40 * np.power(s2, 2.0), 0.0, 1.0).astype(np.float32)
    grain = fbm(n, n, 6, 6, 2, seed=21)
    height = 0.50 + (sheen - float(sheen.mean())) * 0.05 + (grain - 0.5) * 0.01
    # Мягкий блик к светлому голубому, без резкой полосы.
    highlight = np.array([0.85, 0.94, 0.99], np.float32)
    strength = (0.18 * sheen)[..., None]
    rgb = base.reshape(1, 1, 3) * (0.97 + 0.015 * (grain - 0.5) * 2.0)[..., None]
    color = rgb * (1.0 - strength) + highlight.reshape(1, 1, 3) * strength
    rough = np.clip(0.08 - (sheen - float(sheen.mean())) * 0.015, 0.04, 0.14)
    ao = ao_map(height, sigma=1.0, strength=0.0)
    return height, np.clip(color, 0, 1), 0.2, rough, 0.0, ao


def make_roof_tiles():
    """1.6×1.6 м, 8 рядов, сдвиг ряда на полплитки. 4 плитки в ряду (128×64 px)."""
    base = hex_rgb("#a8472f")
    n = SIZE
    rows, cols = 8, 4
    rh, cw = n // rows, n // cols
    yy, xx = np.mgrid[0:n, 0:n]
    row = yy // rh
    shift = (row % 2) * (cw // 2)
    local_x = np.mod(xx - shift, cw).astype(np.float32)
    local_y = np.mod(yy, rh).astype(np.float32)
    col = np.mod(np.floor_divide(xx - shift, cw), cols).astype(np.int32)
    dist_x = np.minimum(local_x, cw - local_x)
    dist_y = np.minimum(local_y, rh - local_y)
    g_x = groove_from_dist(dist_x, 3.4, 0.16)
    g_y = groove_from_dist(dist_y, 4.6, 0.30)
    face = np.clip(dist_x / 5.0, 0.0, 1.0) * np.clip(dist_y / 6.0, 0.0, 1.0)
    face = _smooth(face).astype(np.float32)
    # Носик черепицы ближе к нижнему краю, но гаснет в шве.
    nose = np.exp(-0.5 * ((local_y - rh * 0.70) / 5.5) ** 2).astype(np.float32)
    grain = fbm(n, n, 28, 28, 3, seed=31, persistence=0.5)
    rng = np.random.default_rng(32)
    jit = rng.uniform(-0.028, 0.028, size=(rows, cols)).astype(np.float32)
    offset = jit[row, col]
    height = 0.52 - g_x - g_y + (nose * 0.07 + offset) * face + (grain - 0.5) * 0.03

    color_jit = rng.uniform(0.93, 1.06, size=(rows, cols)).astype(np.float32)
    warm = rng.uniform(-0.035, 0.035, size=(rows, cols)).astype(np.float32)
    mul = 1.0 + (color_jit[row, col] - 1.0) * face
    color = base.reshape(1, 1, 3) * mul[..., None]
    color = color + np.stack([
        warm[row, col] * face,
        warm[row, col] * face * 0.25,
        -warm[row, col] * face * 0.45,
    ], axis=-1)
    color *= (1.0 + (grain - 0.5) * 0.05)[..., None]
    # Тёмные швы и тень под нижним краем плитки.
    mask_x = np.clip(g_x / 0.16, 0.0, 1.0)
    mask_y = np.clip(g_y / 0.30, 0.0, 1.0)
    color *= (1.0 - 0.28 * mask_x - 0.42 * mask_y)[..., None]
    shadow_t = np.clip((local_y - rh * 0.48) / (rh * 0.38), 0.0, 1.0)
    shadow = (shadow_t * shadow_t) * face
    color *= (1.0 - 0.20 * shadow)[..., None]
    rough = np.clip(0.80 + (grain - 0.5) * 0.05 + offset * 0.4, 0.62, 0.92)
    ao = ao_map(height, sigma=5.5, strength=0.82)
    return height, np.clip(color, 0, 1), 4.0, rough, 0.0, ao


def make_floor_tiles():
    """1×1 м, одна плитка на текстуру. Шов по центру кромки, чтобы стык не удваивался."""
    base = hex_rgb("#b9a98d")
    grout_c = hex_rgb("#8a7b66")
    n = SIZE
    px = np.arange(n, dtype=np.float32)
    # Расстояние до границы тайла. На левом и правом краю оно зеркально.
    dist = dist_to_period_lines(px, float(n))
    dist_x = dist[None, :]
    dist_y = dist[:, None]
    dist_e = np.minimum(dist_x, dist_y)
    groove = groove_from_dist(dist_e, 6.5, 0.30)
    grain = fbm(n, n, 22, 22, 3, seed=41)
    grain = blur(grain, 0.5)
    # Лёгкая подушка: центр чуть выше, к шву сходит в ноль вместе с канавкой.
    inner = _smooth(np.clip(dist_e / 48.0, 0.0, 1.0))
    height = 0.48 + inner * 0.06 + (grain - 0.5) * 0.035 - groove
    face = _smooth(np.clip((dist_e - 2.0) / 8.0, 0.0, 1.0))
    tile = shade(base, height, grain, relief=0.06, grain_amp=0.02)
    tile *= (0.97 + 0.03 * inner)[..., None]
    mask = np.clip(groove / 0.30, 0.0, 1.0)[..., None]
    color = tile * (1.0 - mask) + grout_c.reshape(1, 1, 3) * mask
    # В самой канавке зерно не должно развести левый и правый край.
    # mask==1 на оси шва с обеих сторон, цвет там чистый grout.
    rough = np.clip(0.45 + (grain - 0.5) * 0.06 + mask[..., 0] * 0.08, 0.3, 0.7)
    ao = ao_map(height, sigma=4.0, strength=0.70)
    return height, np.clip(color, 0, 1), 2.0, rough, 0.0, ao


def make_metal_dark():
    """1.5×1.5 м. Вертикальная шлифовка: рисунок почти постоянен вдоль Y."""
    base = hex_rgb("#2b2f3a")
    n = SIZE
    brush = fbm(n, n, 2, 48, 3, seed=51, persistence=0.6)
    fine = fbm(n, n, 1, 96, 2, seed=52, persistence=0.5)
    broad = fbm(n, n, 2, 6, 2, seed=53)
    # Растянуть остаточную рябь вдоль вертикали.
    brush = blur(brush, (8.0, 0.4))
    fine = blur(fine, (6.0, 0.3))
    height = 0.50 + (brush - 0.5) * 0.09 + (fine - 0.5) * 0.045 + (broad - 0.5) * 0.02
    color = shade(base, height, fine, relief=0.05, grain_amp=0.018)
    rough = np.clip(0.40 + (fine - 0.5) * 0.06, 0.28, 0.55)
    metal = np.clip(0.70 + (broad - 0.5) * 0.06, 0.55, 0.85)
    ao = ao_map(height, sigma=1.0, strength=0.0)
    return height, np.clip(color, 0, 1), 1.0, rough, metal, ao


def make_sign_blue():
    """2×2 м. Глянцевый пластик, мягкая вертикальная волна (светлее к верху тайла).

    Монотонный градиент сверху вниз не склеивается. Один период косинуса
    светлый на верхней и нижней кромке (производная там ноль) и темнее
    к середине: повтор даёт плавную волну, без светлой полоски на шве.
    Верх тайла светлее середины.
    """
    base = hex_rgb("#1b4f9c")
    n = SIZE
    t = (np.arange(n, dtype=np.float32) + 0.5) / n
    wave = np.cos(2.0 * np.pi * t).astype(np.float32)  # +1 на кромках, −1 в середине
    column = np.broadcast_to(wave[:, None], (n, n))
    grain = fbm(n, n, 2, 3, 2, seed=61)
    height = 0.50 + column * 0.025 + (grain - 0.5) * 0.008
    mult = 1.0 + 0.08 * column + 0.01 * (grain - 0.5) * 2.0
    color = base.reshape(1, 1, 3) * mult[..., None]
    rough = np.clip(0.20 - column * 0.015, 0.12, 0.28).astype(np.float32)
    ao = ao_map(height, sigma=1.0, strength=0.0)
    return height, np.clip(color, 0, 1), 0.3, rough, 0.0, ao


def _weave(n: int = SIZE, pitch: int = 8) -> np.ndarray:
    """Корзина. pitch делит n, число ячеек чётное — переплетение продолжается за край."""
    y, x = np.mgrid[0:n, 0:n]
    arch_y = 0.5 - 0.5 * np.cos(2.0 * np.pi * y / pitch)
    arch_x = 0.5 - 0.5 * np.cos(2.0 * np.pi * x / pitch)
    top_horiz = (((x // pitch) + (y // pitch)) & 1) == 0
    h = np.where(top_horiz, arch_y, arch_x).astype(np.float32)
    return blur(h, 0.45)


def make_awning(base_hex: str, seed: int):
    """1×1 м. Мелкое плетение без полос."""
    base = hex_rgb(base_hex)
    n = SIZE
    threads = _weave(n, 8)
    slow = fbm(n, n, 3, 3, 2, seed=seed)
    height = 0.46 + (threads - 0.35) * 0.20 + (slow - 0.5) * 0.025
    # Средний цвет остаётся у заданного hex: вверх — только пока не упираемся в 1,
    # вниз — чуть сильнее, чтобы плетение читалось и на белой ткани.
    t = threads - float(np.mean(threads))
    peak = float(np.max(base))
    headroom = max(0.02, (1.0 / peak) - 1.0)
    hi = np.clip(t, 0.0, None)
    lo = np.clip(t, None, 0.0)
    mult = 1.0 + hi * (headroom / 0.42) + lo * 0.16 + (slow - 0.5) * 0.012
    color = base.reshape(1, 1, 3) * mult[..., None]
    rough = np.clip(0.95 - (threads - 0.4) * 0.04, 0.86, 0.99)
    ao = ao_map(height, sigma=2.2, strength=0.38)
    return height, np.clip(color, 0, 1), 2.0, rough, 0.0, ao


def make_wood():
    """1×1 м. Волокна вдоль горизонтали, редкие поры."""
    base = hex_rgb("#8a6a4a")
    n = SIZE
    warp = fbm(n, n, 3, 2, 2, seed=81)
    # Мало ячеек по X — линия почти не меняется вдоль волокна, часто меняется поперёк.
    fiber = noise(n, n, 8, 2, seed=82, warp=warp, warp_amp=2.2)
    fine = noise(n, n, 22, 4, seed=83, warp=warp, warp_amp=1.4)
    fiber = (0.62 * fiber + 0.38 * fine).astype(np.float32)
    fiber = blur(fiber, (0.4, 5.0))
    pores_n = fbm(n, n, 40, 40, 2, seed=84)
    pores = np.clip((pores_n - 0.83) / 0.09, 0.0, 1.0)
    pores = blur(pores, 1.25)
    pores = np.clip(pores, 0.0, 1.0) ** 2
    height = 0.50 + (fiber - 0.5) * 0.20 - pores * 0.04
    hn = (height - np.mean(height))
    scale = np.percentile(np.abs(hn), 98) + 1e-6
    t = np.clip(hn / scale, -1.0, 1.0)
    color = base.reshape(1, 1, 3) * (1.0 + 0.10 * t)[..., None]
    # Тёплый сдвиг по волокну, поры чуть темнее и холоднее.
    color = color + np.array([0.035, 0.012, -0.02], np.float32) * t[..., None]
    color *= (1.0 - 0.10 * np.clip(pores, 0, 1))[..., None]
    rough = np.clip(0.70 + (fiber - 0.5) * 0.06 + pores * 0.08, 0.55, 0.86)
    ao = ao_map(height, sigma=2.4, strength=0.34)
    return height, np.clip(color, 0, 1), 2.5, rough, 0.0, ao


# ---------------------------------------------------------------------------
# Вывеска — не тайл
# ---------------------------------------------------------------------------

# Силуэты в долях прямоугольника иконки: x вправо, y вниз.
# Кузов с неглубокими арками: круги колёс заходят в арку и читаются как часть машины.
CAR_BODY = [
    (0.00, 0.60), (0.00, 0.48), (0.07, 0.44), (0.18, 0.42),
    (0.28, 0.40), (0.36, 0.24), (0.42, 0.13), (0.66, 0.11),
    (0.74, 0.20), (0.84, 0.36), (0.96, 0.42), (1.00, 0.50),
    (1.00, 0.60), (0.93, 0.66), (0.84, 0.64), (0.78, 0.56),
    (0.66, 0.56), (0.60, 0.66), (0.30, 0.66), (0.24, 0.56),
    (0.12, 0.56), (0.06, 0.64),
]
CAR_WHEELS = ((0.18, 0.68), (0.78, 0.68))
CAR_WHEEL_R = 0.195

# Корма слева плоская, нос справа острый, рубка отдельным горбом.
BOAT_HULL = [
    (0.00, 0.40), (0.00, 0.62), (0.10, 0.76), (0.38, 0.88),
    (0.70, 0.76), (0.88, 0.58), (1.00, 0.40), (0.84, 0.32),
    (0.66, 0.30), (0.60, 0.16), (0.38, 0.12), (0.32, 0.28),
    (0.14, 0.36),
]

# Вертолёт носом вправо: винт отдельно сверху, балка горизонтально назад, киль не достаёт до винта.
HELI_PARTS = [
    [(0.05, 0.09), (0.96, 0.07), (0.96, 0.145), (0.05, 0.165)],
    [(0.44, 0.145), (0.51, 0.145), (0.51, 0.34), (0.44, 0.34)],
    [(0.03, 0.30), (0.03, 0.50), (0.11, 0.50), (0.13, 0.34), (0.08, 0.26)],
    [(0.00, 0.32), (0.05, 0.29), (0.055, 0.44), (0.00, 0.47)],
    [(0.10, 0.38), (0.38, 0.42), (0.38, 0.50), (0.10, 0.46)],
    [(0.34, 0.34), (0.32, 0.46), (0.36, 0.60), (0.54, 0.66),
     (0.70, 0.58), (0.80, 0.46), (0.74, 0.36), (0.58, 0.30), (0.44, 0.31)],
    [(0.40, 0.74), (0.74, 0.74), (0.76, 0.81), (0.38, 0.81)],
    [(0.46, 0.62), (0.50, 0.62), (0.48, 0.76), (0.44, 0.76)],
    [(0.62, 0.58), (0.66, 0.58), (0.68, 0.76), (0.64, 0.76)],
]


def _mirror(pts):
    return [(1.0 - x, y) for x, y in pts]


def _draw_sign_plate() -> np.ndarray:
    """2048×182, белая панель, рамка 6 px, силуэты полигонами. Центр пустой."""
    w, h = 2048, 182
    scale = 4
    bg = (0xF6, 0xF6, 0xF6)
    blue = (0x1B, 0x4F, 0x9C)
    border = (0xC9, 0xCE, 0xD6)
    im = Image.new("RGB", (w * scale, h * scale), bg)
    dr = ImageDraw.Draw(im)

    def poly(rect, pts):
        x, y, rw, rh = rect
        x *= scale
        y *= scale
        rw *= scale
        rh *= scale
        dr.polygon([(x + px * rw, y + py * rh) for px, py in pts], fill=blue)

    def circle(rect, cx, cy, r_frac, n=28):
        x, y, rw, rh = rect
        pcx = (x + cx * rw) * scale
        pcy = (y + cy * rh) * scale
        pr = r_frac * rh * scale
        ang = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
        dr.polygon(list(zip(pcx + pr * np.cos(ang), pcy + pr * np.sin(ang))), fill=blue)

    def car(rect, face=1):
        body = CAR_BODY if face > 0 else _mirror(CAR_BODY)
        poly(rect, body)
        wheels = CAR_WHEELS if face > 0 else tuple((1.0 - cx, cy) for cx, cy in CAR_WHEELS)
        for cx, cy in wheels:
            circle(rect, cx, cy, CAR_WHEEL_R)

    def boat(rect, face=1):
        poly(rect, BOAT_HULL if face > 0 else _mirror(BOAT_HULL))

    def heli(rect, face=1):
        for part in HELI_PARTS:
            poly(rect, part if face > 0 else _mirror(part))

    # Слева ~600 px: машина и лодка, носами к центру. Справа ~600 px: вертолёт и машина.
    # Центральные 800 px (x=624..1424) не занимать.
    car((26, 30, 256, 122), face=1)
    boat((318, 38, 276, 108), face=1)
    heli((1456, 16, 340, 150), face=-1)
    car((1816, 32, 206, 118), face=-1)

    small = im.resize((w, h), Image.Resampling.LANCZOS)
    d2 = ImageDraw.Draw(small)
    b = 6
    d2.rectangle([0, 0, w - 1, b - 1], fill=border)
    d2.rectangle([0, h - b, w - 1, h - 1], fill=border)
    d2.rectangle([0, 0, b - 1, h - 1], fill=border)
    d2.rectangle([w - b, 0, w - 1, h - 1], fill=border)
    arr = np.asarray(small)
    if arr.dtype != np.uint8 or arr.shape != (h, w, 3):
        raise RuntimeError(f"sign_plate: неожиданный растр {arr.shape} {arr.dtype}")
    # Центр внутри рамки — чистый белый, без текста и иконок.
    center = arr[b:h - b, 624:1424]
    white = np.array(bg, np.uint8)
    if not np.all(center == white):
        raise RuntimeError("sign_plate: центр 800 px не пустой")
    return arr


def sign_plate_height() -> np.ndarray:
    """Рамка чуть приподнята, внутри плоско. k применяется снаружи."""
    h, w = 182, 2048
    yy, xx = np.indices((h, w))
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)).astype(np.float32)
    t = np.clip((dist - 3.0) / 6.0, 0.0, 1.0)
    s = _smooth(t)
    return (0.40 + 0.14 * (1.0 - s)).astype(np.float32)


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------

def export_tile(name: str, height, color, k, rough, metal, ao) -> list[tuple[str, str, str]]:
    h = np.clip(np.asarray(height, np.float32), 0.0, 1.0)
    if not float_height_seamless(h, name):
        raise RuntimeError(f"{name}: рельеф не склеивается")
    color = np.clip(np.asarray(color, np.float32), 0.0, 1.0)
    if color.shape != (h.shape[0], h.shape[1], 3):
        raise RuntimeError(f"{name}: цвет {color.shape}")
    rough_m = np.clip(as_map(rough, h.shape), 0.0, 1.0)
    metal_m = np.clip(as_map(metal, h.shape), 0.0, 1.0)
    ao_m = np.clip(as_map(ao, h.shape), 0.55, 1.0)
    if float(ao_m.min()) < 0.55 - 1e-5:
        raise RuntimeError(f"{name}: AO темнее 0.55")
    normal = normal_map(h, k)
    orm = np.stack([ao_m, rough_m, metal_m], axis=-1)
    maps = {
        f"{name}.png": color,
        f"{name}_normal.png": normal,
        f"{name}_rough.png": rough_m,
        f"{name}_metal.png": metal_m,
        f"{name}_ao.png": ao_m,
        f"{name}_orm.png": orm,
    }
    rows = []
    color_u8 = None
    for fname, arr in maps.items():
        u8 = save_rgb(OUT / fname, arr)
        if fname == f"{name}.png":
            color_u8 = u8
        rows.append((fname, u8))
    preview = np.tile(color_u8, (2, 2, 1))
    prev_name = f"preview_{name}.png"
    save_rgb(OUT / prev_name, preview)
    rows.append((prev_name, preview))
    return [(fname, f"{u8.shape[1]}x{u8.shape[0]}", _seam_label(u8)) for fname, u8 in rows]


def export_sign() -> list[tuple[str, str, str]]:
    color_u8 = _draw_sign_plate()
    height = sign_plate_height()
    normal = normal_map(height, k=1.0)
    ao = np.ones(height.shape, np.float32)
    rough = np.full(height.shape, 0.5, np.float32)
    metal = np.zeros(height.shape, np.float32)
    orm = np.stack([ao, rough, metal], axis=-1)
    save_rgb(OUT / "sign_plate.png", color_u8)
    n_u8 = save_rgb(OUT / "sign_plate_normal.png", normal)
    o_u8 = save_rgb(OUT / "sign_plate_orm.png", orm)
    preview = np.tile(color_u8, (2, 2, 1))
    save_rgb(OUT / "preview_sign_plate.png", preview)
    # Плоский центр нормали — ровно нейтраль OpenGL.
    cy, cx = 90, 1024
    if list(n_u8[cy, cx]) != [128, 128, 255]:
        raise RuntimeError(f"sign_plate_normal центр {tuple(n_u8[cy, cx])}")
    if list(o_u8[cy, cx]) != [255, 128, 0]:
        raise RuntimeError(f"sign_plate_orm центр {tuple(o_u8[cy, cx])}")
    files = [
        ("sign_plate.png", color_u8),
        ("sign_plate_normal.png", n_u8),
        ("sign_plate_orm.png", o_u8),
        ("preview_sign_plate.png", preview),
    ]
    return [(fname, f"{u8.shape[1]}x{u8.shape[0]}", _seam_label(u8)) for fname, u8 in files]


def _seam_label(u8: np.ndarray) -> str:
    ok, info = seam_metrics(u8)
    if ok:
        return "OK"
    return (
        f"ошибка L/R {info['sx']:.1f}>{info['ix']:.1f}"
        f" T/B {info['sy']:.1f}>{info['iy']:.1f}"
    )


def _self_test() -> None:
    # Периодический синус склеивается, линейный градиент — нет.
    x = np.arange(64, dtype=np.float32)
    wave = np.sin(2.0 * np.pi * x / 64.0)
    img = np.broadcast_to(wave, (64, 64)).copy()
    u8 = np.stack([np.clip(np.rint((img * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)] * 3, axis=-1)
    ok, _ = seam_metrics(u8)
    if not ok:
        raise RuntimeError("самопроверка: периодический сигнал помечен как шов")
    grad = np.linspace(0, 255, 64, dtype=np.float32)
    g = np.broadcast_to(grad, (64, 64)).copy()
    gu = np.stack([np.clip(np.rint(g), 0, 255).astype(np.uint8)] * 3, axis=-1)
    bad, _ = seam_metrics(gu)
    if bad:
        raise RuntimeError("самопроверка: градиент со швом пропущен")

    # Выпуклость: верх зелёный, низ пурпурный, правый край красный — OpenGL.
    bump = np.zeros((48, 48), np.float32)
    bump[24, 24] = 1.0
    bump = gaussian_filter(bump, 2.2, mode="wrap")
    nmap = normal_map(bump, k=6.0)
    py, px = np.unravel_index(int(np.argmax(bump)), bump.shape)
    above = float(nmap[py - 3, px, 1])
    below = float(nmap[py + 3, px, 1])
    right = float(nmap[py, px + 3, 0])
    left = float(nmap[py, px - 3, 0])
    if not (above > 0.5 > below and right > 0.5 > left):
        raise RuntimeError(
            f"нормали не OpenGL: up {above:.3f} down {below:.3f} right {right:.3f} left {left:.3f}"
        )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    _self_test()
    tiles = [
        ("wall_plaster", make_wall_plaster),
        ("glass", make_glass),
        ("roof_tiles", make_roof_tiles),
        ("floor_tiles", make_floor_tiles),
        ("metal_dark", make_metal_dark),
        ("sign_blue", make_sign_blue),
        ("awning_fabric", lambda: make_awning("#f5f5f5", 71)),
        ("awning_red", lambda: make_awning("#d8262c", 71)),
        ("wood", make_wood),
    ]
    report: list[tuple[str, str, str]] = []
    for name, fn in tiles:
        height, color, k, rough, metal, ao = fn()
        report.extend(export_tile(name, height, color, k, rough, metal, ao))
    report.extend(export_sign())

    # Повторное чтение с диска: в таблице то, что реально лежит в файле.
    print()
    header = ("файл", "размер", "шов")
    disk_rows = []
    failed = 0
    for fname, _, _ in report:
        im = Image.open(OUT / fname)
        if im.mode != "RGB":
            raise RuntimeError(f"{fname}: режим {im.mode}, нужен RGB без альфы")
        u8 = np.asarray(im)
        ok, _ = seam_metrics(u8)
        label = "OK" if ok else "ошибка"
        if not ok:
            failed += 1
        disk_rows.append((fname, f"{im.size[0]}x{im.size[1]}", label))
    name_w = max(len(header[0]), max(len(r[0]) for r in disk_rows))
    size_w = max(len(header[1]), max(len(r[1]) for r in disk_rows))
    print(f"{header[0]:<{name_w}}  {header[1]:<{size_w}}  {header[2]}")
    print(f"{'-' * name_w}  {'-' * size_w}  {'-' * 8}")
    for fname, size, label in disk_rows:
        print(f"{fname:<{name_w}}  {size:<{size_w}}  {label}")
    print()
    print(f"файлов: {len(disk_rows)}, ошибок шва: {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
