"""Low-poly textured Soviet 5-storey panel house (game style): simple boxes, windows / seams / doors painted
into facade textures - like the reference model (~2k triangles instead of ~30k of cut geometry).

    .venv/Scripts/python.exe scripts/textured_panel.py [out.glb]
"""
import random
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

PX = 40                      # texture pixels per metre
L, D = 64.0, 14.6            # main block length (X) and depth (Z); front faces +Z
PL, FH, FL = 0.9, 2.8, 5     # plinth, floor height, floors
H = PL + FH * FL             # wall top
PAR = 1.2                    # parapet
BAY_D = 1.5
MOD = 3.2                    # panel module
COLS = 20
BAYS = [(0, 1), (4, 2), (9, 2), (14, 2), (19, 1)]   # (first column, columns)
STAIRS = [2, 7, 12, 17]

WALL, SEAM, FRAME = (201, 203, 216), (232, 234, 220), (244, 244, 236)
GLASS, LIT, DOOR = (44, 41, 68), (240, 160, 80), (42, 69, 168)
PLINTH, ROOF, STEPS = (142, 51, 38), (59, 64, 75), (74, 79, 92)
rnd = random.Random(7)


# ---------- textures ----------
def canvas(w, h):
    return Image.new("RGB", (round(w * PX), round(h * PX)), WALL)


def seams(img, w, h, step, floors=True):
    d = ImageDraw.Draw(img)
    W, Hp = img.size
    t = max(2, round(0.08 * PX))
    x = step
    while x < w - 0.01:
        d.rectangle([round(x * PX) - t // 2, 0, round(x * PX) + t // 2, Hp], fill=SEAM)
        x += step
    if floors:
        for f in range(1, FL):
            y = Hp - round(f * FH * PX)
            d.rectangle([0, y - t // 2, W, y + t // 2], fill=SEAM)


def window(img, cx, v0, w=1.6, h=1.4, lit=None, bars=None):
    """cx = centre (m from the left), v0 = sill height above the texture bottom (m)."""
    d = ImageDraw.Draw(img)
    Hp = img.size[1]
    lit = rnd.random() < 0.27 if lit is None else lit
    bars = rnd.choice([1, 1, 2, 3]) if bars is None else bars
    x0, x1 = round((cx - w / 2) * PX), round((cx + w / 2) * PX)
    y1, y0 = Hp - round(v0 * PX), Hp - round((v0 + h) * PX)
    b = round(0.1 * PX)
    d.rectangle([x0 - b // 2, y0 - b // 2, x1 + b // 2, y1 + b // 2], fill=FRAME)
    d.rectangle([x0 + b // 2, y0 + b // 2, x1 - b // 2, y1 - b // 2], fill=LIT if lit else GLASS)
    m = max(2, b // 2)
    for i in range(1, bars + 1):          # vertical bars
        x = x0 + (x1 - x0) * i // (bars + 1)
        d.rectangle([x - m // 2, y0, x + m // 2, y1], fill=FRAME)
    if bars >= 2:                          # transom over the side sash (Soviet "форточка")
        y = y0 + (y1 - y0) // 3
        d.rectangle([x1 - (x1 - x0) // (bars + 1), y - m // 2, x1, y + m // 2], fill=FRAME)


def slit(img, cx, v0):
    for dv in (0.0, 0.6):
        window(img, cx, v0 + dv, w=1.8, h=0.28, lit=False, bars=0)


def col_u(c):
    return (c + 0.5) * MOD


def bay_cols():
    return {c + i for c, n in BAYS for i in range(n)}


def tex_main(front):
    img = canvas(L, H - PL)
    seams(img, L, H - PL, MOD)
    bc = bay_cols()
    for c in range(COLS):
        if c in bc:
            continue
        for f in range(FL):
            v = f * FH + 0.9
            if front and c in STAIRS:
                if f:
                    slit(img, col_u(c), f * FH + 0.6)
            else:
                window(img, col_u(c), v)
    return img


def tex_bay(n):
    img = canvas(n * MOD, H - PL)
    seams(img, n * MOD, H - PL, MOD)
    for i in range(n):
        for f in range(FL):
            window(img, col_u(i), f * FH + 0.9)
    return img


def tex_end():
    img = canvas(D, H - PL)
    seams(img, D, H - PL, D / 4)
    d = ImageDraw.Draw(img)
    for x in (D / 3, 2 * D / 3):           # wide light strips of the end wall
        d.rectangle([round((x - 0.15) * PX), 0, round((x + 0.15) * PX), img.size[1]], fill=SEAM)
    for f in range(FL):
        for u in (1.6, D - 1.6):
            window(img, u, f * FH + 0.9, w=1.4)
    return img


def tex_plain(w, h, step=None):
    img = canvas(w, h)
    if step:
        seams(img, w, h, step)
    return img


def tex_door(w=1.5, h=2.2, frame=True):
    img = Image.new("RGB", (round(w * PX), round(h * PX)), FRAME if frame else WALL)
    d = ImageDraw.Draw(img)
    b = round(0.08 * PX)
    W, Hp = img.size
    d.rectangle([b, b, W - b, Hp], fill=DOOR)
    d.rectangle([W // 2 - 1, b, W // 2 + 1, Hp], fill=(30, 50, 120))
    for x in (W // 4, 3 * W // 4):         # small glazing in each leaf
        d.rectangle([x - W // 10, Hp // 6, x + W // 10, Hp // 2.5], fill=GLASS)
    return img


def tex_ac():
    img = Image.new("RGB", (64, 44), (236, 236, 236))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 38, 38], fill=(120, 124, 130))
    d.ellipse([12, 12, 32, 32], fill=(70, 72, 78))
    d.line([22, 8, 22, 36], fill=(200, 200, 200), width=2)
    d.line([8, 22, 36, 22], fill=(200, 200, 200), width=2)
    for y in range(8, 38, 5):
        d.line([44, y, 58, y], fill=(150, 150, 150), width=2)
    return img


# ---------- geometry ----------
class Builder:
    def __init__(self):
        self.parts = {}                     # material key -> (verts, faces, uvs, material)
        self.mats = {}

    def mat(self, key, img=None, color=None):
        if key not in self.mats:
            if img is not None:
                self.mats[key] = trimesh.visual.material.PBRMaterial(
                    name=key, baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.9)
            else:
                self.mats[key] = trimesh.visual.material.PBRMaterial(
                    name=key, baseColorFactor=[*(((c / 255) ** 2.2) for c in color), 1.0],  # glTF factor is linear
                    metallicFactor=0.0, roughnessFactor=0.9)
        return key

    def quad(self, key, p0, u, v):
        """p0 = bottom-left corner seen from outside, u = right edge vector, v = up edge vector (normal = u x v)."""
        p0, u, v = map(np.asarray, (p0, u, v))
        vs, fs, uvs = self.parts.setdefault(key, ([], [], []))
        n = len(vs)
        vs += [p0, p0 + u, p0 + u + v, p0 + v]
        uvs += [(0, 0), (1, 0), (1, 1), (0, 1)]
        fs += [(n, n + 1, n + 2), (n, n + 2, n + 3)]

    def box(self, x0, x1, y0, y1, z0, z1, faces):
        """faces: dict side -> material key (sides missing = skipped); sides front(+Z) back(-Z) left(-X) right(+X) top bottom."""
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        q = {
            "front": ((x0, y0, z1), (dx, 0, 0), (0, dy, 0)),
            "back": ((x1, y0, z0), (-dx, 0, 0), (0, dy, 0)),
            "left": ((x0, y0, z0), (0, 0, dz), (0, dy, 0)),
            "right": ((x1, y0, z1), (0, 0, -dz), (0, dy, 0)),
            "top": ((x0, y1, z1), (dx, 0, 0), (0, 0, -dz)),
            "bottom": ((x0, y0, z0), (dx, 0, 0), (0, 0, dz)),
        }
        for side, key in faces.items():
            if key:
                self.quad(key, *q[side])

    def scene(self):
        sc = trimesh.Scene()
        for key, (vs, fs, uvs) in self.parts.items():
            m = trimesh.Trimesh(np.array(vs, float), np.array(fs), process=False,
                                visual=trimesh.visual.TextureVisuals(uv=np.array(uvs, float), material=self.mats[key]))
            sc.add_geometry(m, node_name=key, geom_name=key)
        return sc


def all_sides(key):
    return {s: key for s in ("front", "back", "left", "right", "top", "bottom")}


def build():
    B = Builder()
    wall = B.mat("wall", color=WALL)
    seam = B.mat("seam", color=SEAM)
    plinth = B.mat("plinth", color=PLINTH)
    roof = B.mat("roof", color=ROOF)
    steps = B.mat("steps", color=STEPS)
    x0, x1, zf, zb = -L / 2, L / 2, D / 2, -D / 2

    # main block walls (facade textures from the plinth up), plinth, roof
    B.box(x0, x1, PL, H, zb, zf, {"front": B.mat("main_front", tex_main(True)),
                                 "back": B.mat("main_back", tex_main(False)),
                                 "left": B.mat("end_l", tex_end()), "right": B.mat("end_r", tex_end()),
                                 "top": roof})
    B.box(x0 - 0.05, x1 + 0.05, 0, PL, zb - 0.05, zf + 0.05, {**all_sides(plinth), "top": None, "bottom": None})

    # bays front and back
    for side, z in (("front", zf), ("back", zb)):
        for c, n in BAYS:
            if side == "front":
                bx0, bx1, bz0, bz1 = x0 + c * MOD, x0 + (c + n) * MOD, z - 0.01, z + BAY_D
            else:
                bx1, bx0, bz0, bz1 = x1 - c * MOD, x1 - (c + n) * MOD, z - BAY_D, z + 0.01
            fac = B.mat(f"bay_{side}_{c}", tex_bay(n))
            sidetex = B.mat("bay_side", tex_plain(BAY_D, H - PL))
            faces = {side: fac, "top": wall, "left": sidetex, "right": sidetex}
            B.box(bx0, bx1, PL, H, bz0, bz1, faces)
            B.box(bx0 - 0.05, bx1 + 0.05, 0, PL, bz0 - (0.05 if side == "back" else 0),
                  bz1 + (0.05 if side == "front" else 0),
                  {"front": plinth if side == "front" else None, "back": plinth if side == "back" else None,
                   "left": plinth, "right": plinth})

    # parapet ring
    t = 0.25
    for a in ((x0, x1, zf - t, zf), (x0, x1, zb, zb + t), (x0, x0 + t, zb, zf), (x1 - t, x1, zb, zf)):
        B.box(a[0], a[1], H, H + PAR, a[2], a[3], all_sides(wall) | {"top": seam, "bottom": None})

    # entrances: porch walls, canopy, landing, steps, door
    door = B.mat("door", tex_door())
    for c in STAIRS:
        cx = x0 + col_u(c)
        for sx in (cx - 1.5, cx + 1.35):
            B.box(sx, sx + 0.15, 0, 3.0, zf, zf + 2.1, all_sides(wall) | {"bottom": None})
        B.box(cx - 1.65, cx + 1.65, 3.0, 3.15, zf, zf + 2.3, all_sides(seam) | {"back": None})
        B.box(cx - 1.35, cx + 1.35, 0, 0.45, zf, zf + 1.5, all_sides(steps) | {"bottom": None, "back": None})
        for i in range(3):
            B.box(cx - 1.35, cx + 1.35, 0, 0.45 - 0.15 * (i + 1), zf + 1.5, zf + 1.5 + 0.3 * (i + 1),
                  {"front": steps, "top": steps, "left": steps, "right": steps})
        B.quad(door, (cx - 0.75, 0.45, zf + 0.01), (1.5, 0, 0), (0, 2.2, 0))

        # roof exit with a blue double door, antenna next to it
        ex0, ex1, ez0, ez1 = cx - 1.2, cx + 1.2, zf - 5.5, zf - 2.5
        B.box(ex0, ex1, H, H + 2.6, ez0, ez1, all_sides(wall) | {"top": seam, "bottom": None})
        B.quad(B.mat("exit_door", tex_door(1.2, 1.7, frame=False)), (cx - 0.6, H + 0.05, ez1 + 0.01),
               (1.2, 0, 0), (0, 1.7, 0))
        mast = B.mat("mast", color=(130, 60, 45))
        ax, az = cx + 2.2, ez0 - 0.5
        B.box(ax - 0.04, ax + 0.04, H, H + 3.2, az - 0.04, az + 0.04, all_sides(mast) | {"bottom": None})
        for k, y in enumerate((H + 2.4, H + 3.0)):
            w = 0.9 - 0.3 * k
            B.box(ax - w, ax + w, y, y + 0.05, az - 0.03, az + 0.03, all_sides(mast) | {"bottom": None})
            for e in (-w, w):
                B.box(ax + e - 0.03, ax + e + 0.03, y - 0.2, y + 0.25, az - 0.03, az + 0.03,
                      all_sides(mast) | {"bottom": None})

    # AC units (front, back, ends)
    ac, white = B.mat("ac", tex_ac()), B.mat("ac_body", color=(236, 236, 236))
    spots = [("front", 5, 2), ("front", 8, 3), ("front", 13, 1), ("front", 16, 4), ("back", 3, 2),
             ("back", 11, 3), ("back", 17, 1), ("left", 0, 4), ("right", 1, 1), ("right", 0, 3)]
    for side, c, f in spots:
        y = PL + f * FH + 0.4
        if side in ("front", "back"):
            sgn = 1 if side == "front" else -1
            cx = (x0 + c * MOD + 0.35) * sgn
            zz = zf * sgn if c not in bay_cols() else (zf + BAY_D) * sgn
            z0, z1 = (zz, zz + 0.3) if sgn > 0 else (zz - 0.3, zz)
            B.box(cx - 0.5, cx + 0.5, y, y + 0.7, z0, z1, all_sides(white) | {side: ac})
        else:
            sx = x0 if side == "left" else x1
            zc = -D / 2 + 3.2 + c * 7.0
            a, b = (sx - 0.3, sx) if side == "left" else (sx, sx + 0.3)
            B.box(a, b, y, y + 0.7, zc - 0.5, zc + 0.5, all_sides(white) | {side: ac})
    return B.scene()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/panel_5fl_4sec/export/panel_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    tris = sum(len(g.faces) for g in sc.geometry.values())
    print(out, "triangles:", tris, "size:", np.round(sc.extents, 2))
