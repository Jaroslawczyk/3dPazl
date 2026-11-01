"""Procedurally drawn RGBA textures: decals (graffiti, dirt, soot, moss, rust, cracks, peeling paint, posters, ...)
and fake interiors (one-point-perspective room pictures shown behind window glass, like interior mapping in
city builders). Generated once into textures/library/decals and textures/library/interiors."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .materials import TEX_LIB

DECAL_DIR = TEX_LIB / "decals"
INTERIOR_DIR = TEX_LIB / "interiors"
DECAL_KINDS = ["dirt", "soot", "moss", "rust", "water_stain", "crack", "peeling", "graffiti", "poster", "scuff"]
INTERIOR_KINDS = ["home_old", "home_soviet", "home_modern", "office", "shop", "church", "warehouse", "dark"]
VARIANTS = 4
SIZE = 512


def _noise_blobs(d: ImageDraw.ImageDraw, rng, n, color, rmin, rmax, w=SIZE, h=SIZE, ymin=0, ymax=SIZE):
    for _ in range(n):
        r = rng.uniform(rmin, rmax)
        x, y = rng.uniform(0, w), rng.uniform(ymin, ymax)
        a = int(color[3] * rng.uniform(0.3, 1.0))
        d.ellipse([x - r, y - r * rng.uniform(0.5, 1.5), x + r, y + r], fill=color[:3] + (a,))


def draw_decal(kind: str, v: int) -> Image.Image:
    rng = random.Random(f"{kind}:{v}")
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "dirt":  # grime rising from the ground: dense at the bottom, fading up
        for y in range(SIZE):
            k = (y / SIZE) ** 2.2
            d.line([(0, y), (SIZE, y)], fill=(70, 58, 42, int(200 * k)))
        _noise_blobs(d, rng, 260, (55, 45, 32, 120), 4, 30, ymin=SIZE * 0.5)
        im = im.filter(ImageFilter.GaussianBlur(6))
    elif kind == "soot":  # dark streaks running down from the top
        for _ in range(40):
            x = rng.uniform(0, SIZE)
            w = rng.uniform(6, 40)
            L = rng.uniform(SIZE * 0.3, SIZE)
            for y in range(int(L)):
                a = int(150 * (1 - y / L) ** 1.5)
                d.line([(x - w / 2, y), (x + w / 2, y)], fill=(25, 25, 25, a))
        im = im.filter(ImageFilter.GaussianBlur(5))
    elif kind == "moss":
        _noise_blobs(d, rng, 500, (70, 95, 40, 220), 3, 22, ymin=SIZE * 0.35)
        _noise_blobs(d, rng, 200, (110, 130, 55, 200), 2, 10, ymin=SIZE * 0.5)
        im = im.filter(ImageFilter.GaussianBlur(2))
    elif kind == "rust":  # rust streaks from a point near the top
        for _ in range(14):
            x = SIZE / 2 + rng.uniform(-60, 60)
            L = rng.uniform(SIZE * 0.4, SIZE * 0.95)
            w = rng.uniform(3, 18)
            for y in range(int(SIZE * 0.05), int(L)):
                a = int(170 * (1 - y / L))
                d.line([(x - w / 2, y), (x + w / 2, y)], fill=(130, 60, 25, a))
                x += rng.uniform(-0.6, 0.6)
        im = im.filter(ImageFilter.GaussianBlur(3))
    elif kind == "water_stain":
        for k in range(6):
            r = SIZE * (0.45 - k * 0.06)
            d.ellipse([SIZE / 2 - r, SIZE * 0.1, SIZE / 2 + r, SIZE * 0.1 + 2 * r * 1.3], outline=(90, 80, 60, 90), width=6)
        _noise_blobs(d, rng, 80, (100, 90, 70, 60), 10, 50)
        im = im.filter(ImageFilter.GaussianBlur(4))
    elif kind == "crack":
        for _ in range(3):
            x, y = rng.uniform(SIZE * 0.2, SIZE * 0.8), 0.0
            pts = [(x, y)]
            while y < SIZE:
                x += rng.uniform(-25, 25)
                y += rng.uniform(10, 35)
                pts.append((x, y))
                if rng.random() < 0.15:  # branch
                    bx, by = x, y
                    br = [(bx, by)]
                    for _ in range(rng.randint(2, 6)):
                        bx += rng.uniform(-30, 30)
                        by += rng.uniform(5, 25)
                        br.append((bx, by))
                    d.line(br, fill=(30, 28, 25, 230), width=2)
            d.line(pts, fill=(25, 22, 20, 255), width=rng.randint(2, 4))
    elif kind == "peeling":  # paint flaking off showing brick/plaster below
        for _ in range(26):
            cx, cy = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
            pts = [(cx + math.cos(a) * rng.uniform(10, 55), cy + math.sin(a) * rng.uniform(10, 45))
                   for a in [i * 2 * math.pi / 9 for i in range(9)]]
            d.polygon(pts, fill=(150, 120, 95, 235), outline=(235, 230, 220, 255))
    elif kind == "graffiti":
        cols = [(230, 40, 60), (40, 160, 230), (250, 200, 30), (60, 200, 90), (240, 240, 240), (150, 60, 200), (20, 20, 20)]
        base = rng.choice(cols)
        y0 = SIZE * 0.35
        x = SIZE * 0.08
        for _ in range(rng.randint(4, 7)):  # bubble letters
            w = rng.uniform(55, 95)
            h = rng.uniform(110, 190)
            d.rounded_rectangle([x, y0 + rng.uniform(-30, 30), x + w, y0 + h], radius=28,
                                fill=base + (240,), outline=(20, 20, 20, 255), width=7)
            d.line([(x + w * 0.3, y0 + 30), (x + w * 0.6, y0 + h - 30)], fill=rng.choice(cols) + (255,), width=10)
            x += w * 0.85
        for _ in range(12):  # drips
            dx = rng.uniform(SIZE * 0.1, x)
            d.line([(dx, y0 + 150), (dx, y0 + 150 + rng.uniform(20, 120))], fill=base + (220,), width=4)
        if rng.random() < 0.6:  # tag scribble
            pts = [(rng.uniform(50, 450), rng.uniform(40, 120)) for _ in range(9)]
            d.line(pts, fill=rng.choice(cols) + (255,), width=6, joint="curve")
    elif kind == "poster":
        bg = rng.choice([(230, 220, 190), (200, 60, 50), (40, 70, 130), (240, 200, 60)])
        d.rectangle([60, 30, 452, 482], fill=bg + (255,))
        for k in range(5):
            y = 70 + k * 80
            d.rectangle([90, y, 420 - rng.randint(0, 120), y + rng.randint(18, 45)], fill=(30, 30, 30, 230))
        d.ellipse([170, 200, 340, 370], fill=(250, 250, 250, 200))
        for _ in range(6):  # torn edges
            x, y = rng.uniform(60, 452), rng.choice([30, 482])
            d.ellipse([x - 25, y - 25, x + 25, y + 25], fill=(0, 0, 0, 0))
    elif kind == "scuff":
        for _ in range(60):
            x, y = rng.uniform(0, SIZE), rng.uniform(SIZE * 0.4, SIZE)
            d.line([(x, y), (x + rng.uniform(-60, 60), y + rng.uniform(-10, 10))], fill=(60, 55, 50, rng.randint(40, 120)),
                   width=rng.randint(2, 6))
        im = im.filter(ImageFilter.GaussianBlur(1.5))
    # soften edges so the quad border never shows
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([12, 12, SIZE - 12, SIZE - 12], radius=60, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(14))
    a = im.getchannel("A")
    im.putalpha(Image.composite(a, Image.new("L", (SIZE, SIZE), 0), mask))
    return im


ROOM = {  # wall, floor, ceiling, light, furniture palette
    "home_old": ((214, 196, 160), (120, 80, 50), (230, 225, 210), (255, 220, 160), [(110, 60, 40), (150, 120, 80), (80, 90, 60)]),
    "home_soviet": ((200, 190, 150), (150, 100, 60), (235, 235, 230), (255, 240, 200), [(120, 80, 50), (170, 60, 50), (90, 90, 100)]),
    "home_modern": ((235, 235, 232), (190, 160, 120), (245, 245, 245), (255, 250, 235), [(60, 60, 65), (200, 200, 205), (90, 120, 150)]),
    "office": ((225, 228, 230), (120, 125, 130), (240, 240, 240), (235, 245, 255), [(70, 70, 75), (180, 185, 190), (40, 40, 45)]),
    "shop": ((240, 235, 225), (200, 200, 195), (245, 245, 245), (255, 250, 240), [(200, 60, 50), (60, 120, 200), (230, 190, 60)]),
    "church": ((190, 165, 120), (110, 95, 80), (120, 100, 70), (255, 200, 120), [(170, 130, 60), (90, 60, 40), (200, 170, 90)]),
    "warehouse": ((150, 145, 135), (110, 110, 105), (90, 90, 88), (230, 230, 210), [(120, 90, 60), (90, 100, 110), (150, 120, 60)]),
    "dark": ((40, 38, 36), (30, 28, 26), (35, 34, 33), (60, 55, 50), [(25, 25, 25), (35, 30, 28), (20, 20, 22)]),
}


def draw_interior(kind: str, v: int) -> Image.Image:
    """One-point perspective room: back wall, floor, ceiling, side walls, furniture silhouettes, lamp."""
    rng = random.Random(f"room:{kind}:{v}")
    wall, floor, ceil, light, furn = ROOM[kind]
    lit = rng.random() > 0.3 and kind != "dark"
    k = 1.0 if lit else 0.45
    sc = lambda c, f=1.0: tuple(max(0, min(255, int(x * k * f))) for x in c)  # noqa: E731
    S = SIZE
    im = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(im)
    bx0, by0, bx1, by1 = S * 0.28, S * 0.26, S * 0.72, S * 0.7  # back wall rectangle
    d.polygon([(0, 0), (S, 0), (bx1, by0), (bx0, by0)], fill=sc(ceil, 0.95))
    d.polygon([(0, S), (S, S), (bx1, by1), (bx0, by1)], fill=sc(floor))
    d.polygon([(0, 0), (bx0, by0), (bx0, by1), (0, S)], fill=sc(wall, 0.82))
    d.polygon([(S, 0), (bx1, by0), (bx1, by1), (S, S)], fill=sc(wall, 0.88))
    d.rectangle([bx0, by0, bx1, by1], fill=sc(wall))
    for i in range(1, 7):  # floor boards / tiles perspective lines
        t = i / 7
        d.line([(S * t, S), (bx0 + (bx1 - bx0) * t, by1)], fill=sc(floor, 0.85), width=2)
    # picture / window / shelves on the back wall
    pw = (bx1 - bx0) * rng.uniform(0.25, 0.45)
    px = rng.uniform(bx0 + 10, bx1 - pw - 10)
    d.rectangle([px, by0 + 25, px + pw, by0 + 25 + pw * 0.7], fill=sc(rng.choice(furn), 1.1), outline=sc((40, 30, 20)), width=3)
    # furniture: sofa/table/bed/shelves (silhouettes on the floor against the back wall)
    for _ in range(rng.randint(1, 3)):
        fw = (bx1 - bx0) * rng.uniform(0.2, 0.5)
        fx = rng.uniform(bx0 - 40, bx1 - fw + 40)
        fh = rng.uniform(25, 90)
        fy = by1 + rng.uniform(5, 60)
        d.rectangle([fx, fy - fh, fx + fw, fy], fill=sc(rng.choice(furn)))
        d.rectangle([fx, fy - fh, fx + fw, fy - fh + 8], fill=sc(rng.choice(furn), 1.2))
    if kind in ("office", "shop"):
        for i in range(3):
            y = by0 + 20 + i * 45
            d.line([(bx0 + 10, y), (bx1 - 10, y)], fill=sc((90, 90, 90)), width=6)
    if lit:  # ceiling lamp + glow
        cx = S / 2 + rng.uniform(-40, 40)
        d.ellipse([cx - 22, S * 0.12, cx + 22, S * 0.12 + 18], fill=light)
        glow = Image.new("RGB", (S, S), light)
        gm = Image.new("L", (S, S), 0)
        ImageDraw.Draw(gm).ellipse([cx - 200, -80, cx + 200, S * 0.6], fill=70)
        gm = gm.filter(ImageFilter.GaussianBlur(60))
        im = Image.composite(glow, im, gm)
    if rng.random() < 0.5:  # curtains at the sides
        cc = sc(rng.choice([(150, 40, 40), (210, 200, 170), (60, 80, 120)]))
        ImageDraw.Draw(im).rectangle([0, 0, S * 0.12, S], fill=cc)
        ImageDraw.Draw(im).rectangle([S * 0.88, 0, S, S], fill=cc)
    return im.filter(ImageFilter.GaussianBlur(0.8))


def ensure_all() -> None:
    DECAL_DIR.mkdir(parents=True, exist_ok=True)
    INTERIOR_DIR.mkdir(parents=True, exist_ok=True)
    for k in DECAL_KINDS:
        for v in range(VARIANTS):
            f = DECAL_DIR / f"decal_{k}_{v}.png"
            if not f.exists():
                draw_decal(k, v).save(f)
    for k in INTERIOR_KINDS:
        for v in range(VARIANTS):
            f = INTERIOR_DIR / f"interior_{k}_{v}.png"
            if not f.exists():
                draw_interior(k, v).save(f)


def file_for(mat: str) -> Path | None:
    """decal_<kind>_<v> / interior_<kind>_<v> -> png path."""
    if mat.startswith("decal_"):
        return DECAL_DIR / f"{mat}.png"
    if mat.startswith("interior_"):
        return INTERIOR_DIR / f"{mat}.png"
    return None


def interior_kind_for(style: dict, program: str | None = None) -> str:
    if program:
        return {"residential": "home_old", "office": "office", "worship": "church", "industrial": "warehouse",
                "shop": "shop"}.get(program, "home_old")
    sid = style.get("id", "")
    y = (style.get("years") or [1800, 1900])[0]
    if any(s in sid for s in ("soviet", "stalin", "constructiv", "brutal")):
        return "home_soviet"
    if any(s in sid for s in ("modern", "art_deco")):
        return "office"
    if "industrial" in sid or "military" in sid:
        return "warehouse"
    return "home_modern" if y >= 1950 else "home_old"
