"""Textured low-poly medieval stone cottage: stone walls with timber posts, half-timbered gables with X braces,
steep thatch roof with timber trim, arched plank door on the gable end, shuttered side window.
Sizes from the reference (medieval_house.glb, units): walls 5.85 x 4.57 x 2.55, ridge 6.3, roof overhang to +-3.5.
Tiles come from textures/library/ref_medieval_house (tile_stone, tile_roof, tile_door).

    .venv/Scripts/python.exe scripts/textured_medieval_house.py [out.glb]
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageEnhance

sys.path.insert(0, str(Path(__file__).parent))
from textured_panel import Builder  # noqa: E402

LIB = Path("textures/library/ref_medieval_house")
PX = 110
HX, HZ, WALL_H, RIDGE, EAVE_Y, OVER = 2.925, 2.285, 2.55, 6.3, 2.35, 3.5
TIMBER = (104, 74, 52)


def tile(name, box=None, size=256):
    im = Image.open(LIB / name).convert("RGB")
    if box:
        w, h = im.size
        im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    return im.resize((size, size), Image.LANCZOS)


STONE = tile("tile_stone.png", (0.0, 0.0, 0.42, 1.0))
ROOF = tile("tile_roof.png", (0.05, 0.05, 0.95, 0.95), 384)
PLANK = tile("tile_door.png", (0.33, 0.45, 0.95, 0.95), 256)


def tiled(base, w, h, scale=1.3):
    """Repeat a tile; scale = world units per tile."""
    tw = max(16, round(scale * PX))
    t = base.resize((tw, tw), Image.LANCZOS)
    img = Image.new("RGB", (round(w * PX), round(h * PX)))
    k = 0
    for x in range(0, img.size[0], tw):
        for y in range(0, img.size[1], tw):
            k += 1
            v = t.transpose(Image.FLIP_LEFT_RIGHT) if k % 2 else t          # flip alternate tiles to hide the repeat
            img.paste(v.transpose(Image.FLIP_TOP_BOTTOM) if k % 3 == 0 else v, (x, y))
    return img


def stone_wall(w, h, door=False, window=None):
    img = tiled(STONE, w, h, 0.9)
    W, H = img.size
    d = ImageDraw.Draw(img)
    band = Image.new("RGB", (W, round(0.45 * PX)), (0, 0, 0))               # darker plinth stones
    low = ImageEnhance.Brightness(img.crop((0, H - band.size[1], W, H))).enhance(0.55)
    img.paste(low, (0, H - band.size[1]))
    if door:
        cx, dw, dh = W // 2, round(1.3 * PX), round(1.45 * PX)
        d.pieslice([cx - dw // 2 - 12, H - dh - dw // 2 - 12, cx + dw // 2 + 12, H - dh + dw // 2 + 12 + dw // 2], 180, 360, fill=(70, 62, 56))
        d.rectangle([cx - dw // 2 - 12, H - dh, cx + dw // 2 + 12, H], fill=(70, 62, 56))
        pl = PLANK.resize((dw, dh + dw // 2))
        mask = Image.new("L", pl.size, 0)
        ImageDraw.Draw(mask).pieslice([0, 0, dw, dw], 180, 360, fill=255)
        ImageDraw.Draw(mask).rectangle([0, dw // 2, dw, dh + dw // 2], fill=255)
        img.paste(pl, (cx - dw // 2, H - dh - dw // 2), mask)
        for k in (0.25, 0.75):
            d.line([cx - dw // 2, H - dh * k, cx + dw // 2, H - dh * k], fill=(30, 22, 18), width=3)
    if window:                                    # shutters + small blue-grey glass
        cx, v0 = window
        ww, wh = round(0.55 * PX), round(0.6 * PX)
        x0, y1 = round(cx * PX) - ww // 2, H - round(v0 * PX)
        d.rectangle([x0 - 6, y1 - wh - 6, x0 + ww + 6, y1 + 6], fill=TIMBER)
        d.rectangle([x0, y1 - wh, x0 + ww, y1], fill=(120, 140, 160))
        d.line([x0 + ww // 2, y1 - wh, x0 + ww // 2, y1], fill=TIMBER, width=3)
        d.rectangle([x0 - 22, y1 - wh - 4, x0 - 4, y1 + 4], fill=(130, 84, 52))
        d.rectangle([x0 + ww + 4, y1 - wh - 4, x0 + ww + 22, y1 + 4], fill=(130, 84, 52))
    return img


def gable_tex(w, h):
    """Half-timbered triangle: light stone infill, dark frame, X braces, small window."""
    img = ImageEnhance.Brightness(tiled(STONE, w, h, 1.0)).enhance(1.25)
    W, H = img.size
    d = ImageDraw.Draw(img)
    t = round(0.12 * PX)
    for y in (0.04, 0.5, 0.95):                    # horizontal rails
        yy = round(H * y)
        d.rectangle([0, yy - t // 2, W, yy + t // 2], fill=TIMBER)
    d.rectangle([W // 2 - t // 2, 0, W // 2 + t // 2, H], fill=TIMBER)
    for sx in (-1, 1):                             # X braces in the lower band
        x0, x1 = (0.08, 0.46) if sx < 0 else (0.54, 0.92)
        d.line([W * x0, H * 0.95, W * x1, H * 0.52], fill=TIMBER, width=t)
        d.line([W * x1, H * 0.95, W * x0, H * 0.52], fill=TIMBER, width=t)
    wx, wy, ww, wh = W // 2 - round(0.35 * PX), round(H * 0.58), round(0.7 * PX), round(0.45 * PX)
    d.rectangle([wx - 6, wy - 6, wx + ww + 6, wy + wh + 6], fill=TIMBER)
    d.rectangle([wx, wy, wx + ww, wy + wh], fill=(150, 175, 205))
    d.line([wx + ww // 2, wy, wx + ww // 2, wy + wh], fill=TIMBER, width=3)
    return img


def poly(B, key, pts, uvs):
    vs, fs, uv = B.parts.setdefault(key, ([], [], []))
    n = len(vs)
    vs += [np.asarray(p, float) for p in pts]
    uv += list(uvs)
    for i in range(1, len(pts) - 1):
        fs += [(n, n + i, n + i + 1), (n, n + i + 1, n + i)]


def build():
    B = Builder()
    timber = B.mat("timber", color=TIMBER)
    st = {k: B.mat(f"stone_{k}", stone_wall(w, WALL_H, door=(k == "front"), window=(1.45, 0.95) if k in ("left", "right") else None))
          for k, w in (("front", 2 * HX), ("back", 2 * HX), ("left", 2 * HZ), ("right", 2 * HZ))}
    B.box(-HX, HX, 0, WALL_H, -HZ, HZ, {"front": st["front"], "back": st["back"], "left": st["left"], "right": st["right"]})
    # vertical timber posts at the corners and beside the window
    for x in (-HX, HX):
        for z in (-HZ, HZ):
            B.box(x - 0.13, x + 0.13, 0, WALL_H, z - 0.13, z + 0.13, {s: timber for s in ("front", "back", "left", "right", "top")})
    for z in (-0.35, 1.0, -1.7):
        for x in (-HX, HX):
            B.box(x - 0.05, x + 0.05, 0, WALL_H, z - 0.09, z + 0.09, {s: timber for s in ("front", "back", "left", "right", "top")})
    B.box(-HX - 0.1, HX + 0.1, WALL_H - 0.05, WALL_H + 0.2, -HZ - 0.1, HZ + 0.1, {s: timber for s in ("front", "back", "left", "right", "top")})
    # gable triangles
    gw, gh = 2 * HX, RIDGE - WALL_H
    g = B.mat("gable", gable_tex(gw, gh))
    for z, sgn in ((HZ, 1), (-HZ, -1)):
        poly(B, "gable", [(-HX, WALL_H + 0.2, z), (HX, WALL_H + 0.2, z), (0, RIDGE - 0.05, z)], [(0, 0), (1, 0), (0.5, 1)])
    # roof planes with overhang (ridge along Z)
    rl = float(np.hypot(OVER, RIDGE - EAVE_Y))
    zz = HZ + 0.27
    roof = B.mat("roof", tiled(ROOF, rl, 2 * zz, 1.6))
    B.quad(roof, (-OVER, EAVE_Y, zz), (0, 0, -2 * zz), (OVER, RIDGE - EAVE_Y, 0))
    B.quad(roof, (OVER, EAVE_Y, -zz), (0, 0, 2 * zz), (-OVER, RIDGE - EAVE_Y, 0))
    # timber trim: rake boards on both gables, eave beams, ridge beam
    tubes = []
    for z in (zz, -zz):
        for sx in (-1, 1):
            tubes.append(trimesh.creation.cylinder(radius=0.09, segment=[[sx * OVER, EAVE_Y, z], [0, RIDGE, z]], sections=4))
    for sx in (-1, 1):
        tubes.append(trimesh.creation.cylinder(radius=0.1, segment=[[sx * OVER, EAVE_Y, -zz], [sx * OVER, EAVE_Y, zz]], sections=4))
    tubes.append(trimesh.creation.cylinder(radius=0.12, segment=[[0, RIDGE, -zz], [0, RIDGE, zz]], sections=4))
    m = trimesh.util.concatenate(tubes)
    m.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(m.vertices), 2)), material=trimesh.visual.material.PBRMaterial(
        name="trim", baseColorFactor=[*((v / 255) ** 2.2 for v in (96, 66, 46)), 1.0], metallicFactor=0, roughnessFactor=0.9))
    sc = B.scene()
    sc.add_geometry(m, node_name="trim", geom_name="trim")
    for gm in sc.geometry.values():
        mt = getattr(gm.visual, "material", None)
        if mt is not None:
            mt.doubleSided = True
    return sc


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/medieval_house_v2/export/medieval_house_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    print(out, "triangles:", sum(len(g.faces) for g in sc.geometry.values()), "size:", np.round(sc.extents, 2))
