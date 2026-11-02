"""Textured low-poly jungle stilt house (weathered plank walls, patchwork rusty corrugated roof, plank deck, ladder).
Layout from the reference scan (jungle_house_3d_model_free.glb, ratios W:L:H = .77:1:.67): ridge along X, porch deck on +Z.
Textures are procedural (the reference atlas is baked, not tileable).

    .venv/Scripts/python.exe scripts/textured_jungle_house.py [out.glb]
"""
import random
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from textured_panel import Builder  # noqa: E402

PX = 80
rnd = random.Random(11)
FLOOR, WALL_T, RIDGE = 1.8, 4.2, 6.4         # deck level, wall top, ridge height
X0, X1, ZB, ZF = -4.3, 4.3, -3.2, 1.4        # body
DECK_Z = 3.4


def noise(img, amp=10, seed=1):
    a = np.asarray(img, float)
    a += np.random.default_rng(seed).normal(0, amp, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def planks(w, h, horizontal=True, base=(106, 94, 82), board=0.2, openings=()):
    img = Image.new("RGB", (round(w * PX), round(h * PX)), base)
    d = ImageDraw.Draw(img)
    n = int((h if horizontal else w) / board)
    for i in range(n + 1):
        t = round(i * board * PX)
        k = rnd.uniform(0.8, 1.12)
        c = tuple(int(v * k) for v in base)
        if horizontal:
            d.rectangle([0, t, img.size[0], t + round(board * PX)], fill=c)
            d.line([0, t, img.size[0], t], fill=(55, 45, 38), width=2)
        else:
            d.rectangle([t, 0, t + round(board * PX), img.size[1]], fill=c)
            d.line([t, 0, t, img.size[1]], fill=(55, 45, 38), width=2)
    for (cx, v0, ow, oh, col) in openings:        # cx from left, v0 from bottom (m)
        x0, x1 = round((cx - ow / 2) * PX), round((cx + ow / 2) * PX)
        y1, y0 = img.size[1] - round(v0 * PX), img.size[1] - round((v0 + oh) * PX)
        d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], fill=(70, 55, 44))
        d.rectangle([x0, y0, x1, y1], fill=col)
    return noise(img.filter(ImageFilter.GaussianBlur(0.6)), 9)


def roof_tex(w, h):
    """Patchwork of corrugated sheets: vertical ribs, rust / grey / orange patches."""
    img = Image.new("RGB", (round(w * PX), round(h * PX)))
    d = ImageDraw.Draw(img)
    cols = [(128, 70, 50), (104, 108, 114), (146, 88, 54), (96, 56, 44), (122, 112, 104), (112, 72, 52), (134, 100, 76)]
    y = 0.0
    while y < h:                                   # staggered rows, random sheet widths, some torn/dark gaps
        ph = rnd.uniform(0.7, 1.3)
        x = -rnd.uniform(0, 0.8)
        while x < w:
            pw = rnd.uniform(0.6, 1.7)
            base = rnd.choice(cols)
            x0, y0, x1, y1 = round(x * PX), round(y * PX), round((x + pw) * PX), round((y + ph) * PX)
            d.rectangle([x0, y0, x1, y1], fill=base)
            for k in range(0, max(1, x1 - x0), 9):
                d.line([x0 + k, y0, x0 + k, y1], fill=tuple(int(v * 0.66) for v in base), width=2)
            d.rectangle([x0, y0, x1, y0 + 2], fill=(60, 40, 32))
            if rnd.random() < 0.06:
                d.rectangle([x0 + 6, y0 + 6, x0 + (x1 - x0) // 2, y0 + (y1 - y0) // 2], fill=(26, 20, 18))
            x += pw
        y += ph
    return noise(img, 12, 2)


def deck_tex(w, h):
    return planks(w, h, horizontal=False, base=(122, 102, 80), board=0.22)


def lad_wood():
    return noise(Image.new("RGB", (16, 16), (126, 98, 72)), 8, 3)


def poly(B, key, pts, uvs):
    """Convex polygon fan (both sides)."""
    vs, fs, uv = B.parts.setdefault(key, ([], [], []))
    n = len(vs)
    vs += [np.asarray(p, float) for p in pts]
    uv += list(uvs)
    for i in range(1, len(pts) - 1):
        fs += [(n, n + i, n + i + 1), (n, n + i + 1, n + i)]


def build():
    B = Builder()
    wood = B.mat("wood", lad_wood())
    cloth = B.mat("cloth", color=(214, 190, 150))
    # posts
    for x in (-4.4, -1.5, 1.5, 4.4):
        for z in (ZB, 0.1, 3.2):
            B.box(x - 0.11, x + 0.11, 0, FLOOR, z - 0.11, z + 0.11, {s: wood for s in ("front", "back", "left", "right")})
    # floor slab + deck planks on top
    B.box(-4.6, 4.6, FLOOR - 0.15, FLOOR, ZB - 0.2, DECK_Z, {s: wood for s in ("front", "back", "left", "right", "bottom")})
    deck = B.mat("deck", deck_tex(9.2, 6.6))
    B.quad(deck, (-4.6, FLOOR, DECK_Z), (9.2, 0, 0), (0, 0, -(DECK_Z - ZB + 0.2)))
    # roof profile: ridge over the body centre, long front slope covers the deck
    zc, RZ_B, RZ_F, YE_B, YE_F = (ZB + ZF) / 2, ZB - 0.8, DECK_Z + 0.2, WALL_T - 0.3, 3.5
    sb, sf = (RIDGE - YE_B) / (zc - RZ_B), (RIDGE - YE_F) / (RZ_F - zc)
    yr = lambda z: RIDGE - (zc - z) * sb if z < zc else RIDGE - (z - zc) * sf  # noqa: E731
    dark = (22, 18, 16)
    Hf, Hb = yr(ZF) - FLOOR, yr(ZB) - FLOOR
    front = B.mat("w_front", planks(8.6, Hf, openings=[(2.2, 0, 1.1, 2.0, dark), (5.0, 0.9, 1.0, 1.0, dark), (7.2, 0.9, 1.0, 1.0, dark)]))
    back = B.mat("w_back", planks(8.6, Hb, openings=[(2.5, 0.9, 1.0, 1.0, dark)]))
    B.quad(front, (X0, FLOOR, ZF), (8.6, 0, 0), (0, Hf, 0))
    B.quad(back, (X1, FLOOR, ZB), (-8.6, 0, 0), (0, Hb, 0))
    xr0, xr1 = X0 - 0.7, X1 + 0.7
    lf = float(np.hypot(RZ_F - zc, RIDGE - YE_F)); lb = float(np.hypot(zc - RZ_B, RIDGE - YE_B))
    B.quad(B.mat("roof_f", roof_tex(xr1 - xr0, lf)), (xr0, YE_F, RZ_F), (xr1 - xr0, 0, 0), (0, RIDGE - YE_F, zc - RZ_F))
    B.quad(B.mat("roof_b", roof_tex(xr1 - xr0, lb)), (xr1, YE_B, RZ_B), (-(xr1 - xr0), 0, 0), (0, RIDGE - YE_B, zc - RZ_B))
    gab = B.mat("gable", planks(4.6, 3.5, openings=[(2.3, 1.0, 0.9, 0.9, dark)]))
    for x in (X0, X1):
        poly(B, "gable", [(x, FLOOR, ZB), (x, FLOOR, ZF), (x, yr(ZF), ZF), (x, RIDGE - 0.05, zc), (x, yr(ZB), ZB)],
             [(0, 0), (1, 0), (1, yr(ZF) / 6.4), (zc / 10 + .5, 1), (0, yr(ZB) / 6.4)])
    for x in (-4.4, 4.4):                      # porch posts under the long front eave
        B.box(x - 0.1, x + 0.1, FLOOR, yr(DECK_Z - 0.1), DECK_Z - 0.2, DECK_Z, {s: wood for s in ("front", "back", "left", "right")})
    # ridge cap
    B.box(xr0 - 0.05, xr1 + 0.05, RIDGE - 0.02, RIDGE + 0.07, zc - 0.12, zc + 0.12, {s: B.mat("cap", color=(128, 78, 56)) for s in ("front", "back", "top", "left", "right")})
    # side porch on the -X gable: deck extension, 2 posts, low lean-to roof
    sx0 = X0 - 1.9
    B.box(sx0, X0, FLOOR - 0.15, FLOOR, ZB, ZF, {s: wood for s in ("front", "back", "left", "right", "bottom")})
    B.quad(deck, (sx0, FLOOR, ZF), (X0 - sx0, 0, 0), (0, 0, -(ZF - ZB)))
    for z in (ZB + 0.1, ZF - 0.1):
        B.box(sx0 - 0.1 + 0.1, sx0 + 0.1 + 0.1, 0, FLOOR, z - 0.11, z + 0.11, {s: wood for s in ("front", "back", "left", "right")})
        B.box(sx0 + 0.0, sx0 + 0.2, FLOOR, 3.5, z - 0.1, z + 0.1, {s: wood for s in ("front", "back", "left", "right")})
    B.quad(B.mat("roof_s", roof_tex(2.4, ZF - ZB + 0.6)), (sx0 - 0.3, 3.45, ZB - 0.3), (0, 0.85, 0), (X0 + 0.0 - sx0 + 0.3, 0, 0)) if False else None
    sl = B.mat("roof_s", roof_tex(ZF - ZB + 0.6, 2.4))
    B.quad(sl, (sx0 - 0.3, 3.45, ZF + 0.3), (0, 0, -(ZF - ZB + 0.6)), (X0 - sx0 + 0.3, 0.85, 0))
    # railings: front rail with gap for the ladder at the right end, side rails
    for z, x0, x1 in ((DECK_Z - 0.05, -4.5, 3.4),):
        B.box(x0, x1, FLOOR + 0.9, FLOOR + 1.0, z, z + 0.08, {s: wood for s in ("front", "back", "top")})
    B.box(-4.55, -4.47, FLOOR + 0.9, FLOOR + 1.0, ZF, DECK_Z, {s: wood for s in ("left", "right", "top")})
    for x in np.linspace(-4.4, 3.2, 9):
        B.box(x - 0.04, x + 0.04, FLOOR, FLOOR + 0.9, DECK_Z - 0.06, DECK_Z + 0.04, {s: wood for s in ("front", "back", "left", "right")})
    # cloth hanging on the left corner rail
    B.box(-4.3, -3.5, FLOOR + 0.2, FLOOR + 1.1, DECK_Z + 0.04, DECK_Z + 0.08, {"front": cloth, "back": cloth})
    # ladder from the right end of the deck down to the ground
    for dx in (4.0, 4.6):
        for k in range(2):
            pass
    sc = B.scene()
    t = []
    for dx in (3.55, 4.25):
        t.append(trimesh.creation.cylinder(radius=0.05, segment=[[dx, 0, 4.9], [dx, FLOOR, DECK_Z - 0.2]], sections=6))
    for k in range(1, 6):
        f = k / 6
        t.append(trimesh.creation.cylinder(radius=0.04, segment=[[3.55, f * FLOOR, 4.9 - f * (4.9 - DECK_Z + 0.2)], [4.25, f * FLOOR, 4.9 - f * (4.9 - DECK_Z + 0.2)]], sections=6))
    m = trimesh.util.concatenate(t)
    m.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(m.vertices), 2)), material=trimesh.visual.material.PBRMaterial(
        name="ladder", baseColorFactor=[*(((v / 255) ** 2.2) for v in (126, 98, 72)), 1.0], metallicFactor=0, roughnessFactor=0.9))
    sc.add_geometry(m, node_name="ladder", geom_name="ladder")
    for g in sc.geometry.values():                       # roof/gable quads may face either way
        mat = getattr(g.visual, "material", None)
        if mat is not None:
            mat.doubleSided = True
    return sc


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/jungle_house_v2/export/jungle_house_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    print(out, "triangles:", sum(len(g.faces) for g in sc.geometry.values()), "size:", np.round(sc.extents, 2))
