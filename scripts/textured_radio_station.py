"""Textured low-poly copy of the orange radio station (tall + low block, lattice mast, ladders, fans, dish).
Sizes come from the reference GLB (metres, Y up, front = +Z). Wall texture is cut from the saved reference atlas.

    .venv/Scripts/python.exe scripts/textured_radio_station.py [out.glb]
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from textured_panel import Builder, all_sides  # noqa: E402

ATLAS = Path("textures/library/ref_radio_station/building_atlas_albedo.png")
PX = 50
PL, HT, HL, PAR = 1.1, 10.5, 5.5, 0.5            # plinth, tall wall top, low wall top, parapet
XT0, XT1, XL1 = -11.5, 2.5, 11.5                  # tall block x range, low block end
ZF, ZB = 5.5, -5.5
GLASS, FRAME, TRIM = (22, 24, 32), (54, 38, 30), (90, 56, 38)
PLINTH, METAL, ROOF = (62, 38, 26), (150, 146, 150), (205, 160, 125)


def orange_tile():
    """256x256 patch of the reference atlas with the most orange plaster (fallback: flat orange)."""
    try:
        a = np.asarray(Image.open(ATLAS).convert("RGB").resize((512, 512)), float)
    except OSError:
        return Image.new("RGB", (256, 256), (217, 144, 79))
    m = ((a[..., 0] > 150) & (a[..., 1] > 90) & (a[..., 1] < 190) & (a[..., 2] < 130)).astype(float)
    best, pos = -1, (0, 0)
    for y in range(0, 512 - 64, 16):
        for x in range(0, 512 - 64, 16):
            s = m[y:y + 64, x:x + 64].mean()
            if s > best:
                best, pos = s, (x, y)
    x, y = pos
    return Image.fromarray(a[y:y + 64, x:x + 64].astype("uint8")).resize((256, 256), Image.BICUBIC)


TILE = orange_tile()


def canvas(w, h):
    img = Image.new("RGB", (round(w * PX), round(h * PX)))
    for x in range(0, img.size[0], 256):
        for y in range(0, img.size[1], 256):
            img.paste(TILE, (x, y))
    mean = np.asarray(img, float).reshape(-1, 3).mean(0)
    a = 0.35 * np.asarray(img, float) + 0.65 * mean
    a += np.random.default_rng(3).normal(0, 4, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(2))


def window(img, cx, v0, w, h):
    d = ImageDraw.Draw(img)
    Hp = img.size[1]
    x0, x1 = round((cx - w / 2) * PX), round((cx + w / 2) * PX)
    y1, y0 = Hp - round(v0 * PX), Hp - round((v0 + h) * PX)
    b = round(0.12 * PX)
    d.rectangle([x0 - b, y0 - b, x1 + b, y1 + b], fill=FRAME)
    d.rectangle([x0, y0, x1, y1], fill=GLASS)
    d.line([(x0 + x1) // 2, y0, (x0 + x1) // 2, y1], fill=FRAME, width=3)
    d.rectangle([x0 - b - 3, y1 + b, x1 + b + 3, y1 + b + 5], fill=(190, 150, 110))


def band(img, v, h=0.25):
    Hp, W = img.size[1], img.size[0]
    d = ImageDraw.Draw(img)
    d.rectangle([0, Hp - round((v + h) * PX), W, Hp - round(v * PX)], fill=TRIM)


def tex_tall_front():
    img = canvas(14, HT - PL)
    for c in range(4):
        for v in (1.4, 6.0):
            window(img, (c + 0.5) * 3.5 - 0.6 * (c == 3), v, 1.3, 1.6)
    return img


def tex_low_front():
    img = canvas(9, HL - PL)
    for c in range(4):
        window(img, (c + 0.5) * 2.25, 1.5, 0.9, 1.3)
    return img


def tex_door():
    img = Image.new("RGB", (60, 110), TRIM)
    ImageDraw.Draw(img).rectangle([6, 6, 54, 110], fill=(70, 52, 44))
    return img


def tube(p0, p1, r, mat, out):
    out.setdefault(mat, []).append(trimesh.creation.cylinder(radius=r, segment=[p0, p1], sections=8))


def build():
    B = Builder()
    mat = lambda k, c: B.mat(k, color=c)  # noqa: E731
    wall, trim, plinth, roof = mat("wall", (217, 144, 79)), mat("trim", TRIM), mat("plinth", PLINTH), mat("roof", ROOF)
    tf, lf = B.mat("tall_front", tex_tall_front()), B.mat("low_front", tex_low_front())
    plain_t, plain_l = B.mat("plain_t", canvas(14, HT - PL)), B.mat("plain_l", canvas(9, HL - PL))
    side_t, side_l = B.mat("side_t", canvas(11, HT - PL)), B.mat("side_l", canvas(11, HL - PL))
    # tall block, low block, plinths
    B.box(XT0, XT1, PL, HT, ZB, ZF, {"front": tf, "back": plain_t, "left": side_t, "right": side_t, "top": roof})
    B.box(XT1 - 0.01, XL1, PL, HL, ZB, ZF, {"front": lf, "back": plain_l, "right": side_l, "top": roof})
    B.box(XT0 - 0.05, XL1 + 0.05, 0, PL, ZB - 0.05, ZF + 0.05, {**all_sides(plinth), "top": None, "bottom": None})
    # platform
    base = mat("base_top", (242, 242, 255))
    B.box(-14, 19, -1.33, 0, -11.3, 11.3, {**all_sides(mat("base", (242, 242, 255))), "top": base, "bottom": None})
    # parapets
    for x0, x1, h, ytop in ((XT0, XT1, PAR, HT), (XT1, XL1, PAR, HL)):
        t = 0.25
        for a in ((x0, x1, ZF - t, ZF), (x0, x1, ZB, ZB + t)):
            B.box(a[0], a[1], ytop, ytop + h, a[2], a[3], all_sides(trim) | {"bottom": None})
    for ax0, ax1, ytop in ((XT0, XT0 + 0.25, HT), (XT1 - 0.25, XT1, HT), (XL1 - 0.25, XL1, HL)):
        B.box(ax0, ax1, ytop, ytop + PAR, ZB, ZF, all_sides(trim) | {"bottom": None})
    B.quad(B.mat("door", tex_door()), (XT0 + 11.1 - 0.5, 0.01, ZF + 0.02), (1.0, 0, 0), (0, 2.2, 0))
    # mast base pad
    mx, mz = -4.5, 0.0
    B.box(mx - 1.5, mx + 1.5, HT, HT + 0.7, mz - 1.5, mz + 1.5, all_sides(wall) | {"bottom": None})
    sc = B.scene()

    # tube geometry by material colour
    parts, col = {}, {"metal": METAL, "dark": (45, 45, 52), "light": (214, 214, 220)}
    y0 = HT + 0.6
    legs = [(-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)]
    for sx, sz in legs:                                   # lattice legs
        tube([mx + sx, y0, mz + sz], [mx + sx * 0.45, y0 + 9.5, mz + sz * 0.45], 0.09, "metal", parts)
    for k, (ya, yb) in enumerate(((2.5, 5.5), (5.5, 8.5))):  # diagonals + rings
        s0, s1 = 1 - 0.58 * ya / 9.5, 1 - 0.58 * yb / 9.5
        for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            tube([mx + 1.1 * s0 * a[0], y0 + ya, mz + 1.1 * s0 * a[1]],
                 [mx + 1.1 * s1 * b[0], y0 + yb, mz + 1.1 * s1 * b[1]], 0.05, "metal", parts)
            tube([mx + 1.1 * s0 * a[0], y0 + ya, mz + 1.1 * s0 * a[1]],
                 [mx + 1.1 * s0 * b[0], y0 + ya, mz + 1.1 * s0 * b[1]], 0.05, "metal", parts)
    spire = trimesh.creation.cone(radius=0.3, height=23.4, sections=8)
    spire.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    spire.apply_translation([mx, HT + 0.7, mz])
    parts.setdefault("metal", []).append(spire)
    # satellite dish (front-left corner of the tall roof)
    dx, dz = XT0 + 1.2, ZF - 0.3
    tube([dx, HT, dz], [dx, HT + 2.2, dz], 0.1, "metal", parts)
    dish = trimesh.creation.cylinder(radius=1.05, height=0.3, sections=14)
    dish.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2 - 0.35, [1, 0, 0]))
    dish.apply_translation([dx, HT + 2.4, dz + 0.3])
    parts.setdefault("light", []).append(dish)
    # roof fans: 2 on tall roof (back), 4 on low roof
    for fx in (-9.6, -6.5):
        parts.setdefault("dark", []).append(trimesh.creation.box([2.0, 0.35, 1.9], transform=trimesh.transformations.translation_matrix([fx + 3.0 - 0.0, HT + 0.18, ZB + 1.6])))
        parts.setdefault("metal", []).append(trimesh.creation.cylinder(radius=0.8, height=0.2, sections=12, transform=trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]) @ np.eye(4)))
        parts["metal"][-1].apply_translation([fx + 3.0, HT + 0.45, ZB + 1.6])
    for fx in (9.46 - 0.0, 10.8):
        for fz in (0.2, -1.8):
            c = trimesh.creation.cylinder(radius=0.5, height=0.24, sections=12)
            c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
            c.apply_translation([fx - 2.4, HL + 0.12, fz])
            parts.setdefault("dark", []).append(c)
    # wall AC fans on the low block front, electrical box, duct
    for fy in (3.9, 5.0):
        c = trimesh.creation.cylinder(radius=0.55, height=0.26, sections=12)
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]) @ np.eye(4))
        c.apply_translation([XT1 + 0.7, fy - 0.0, ZF + 0.1])
        parts.setdefault("dark", []).append(c)
    parts.setdefault("metal", []).append(trimesh.creation.box([1, 0.8, 0.3], transform=trimesh.transformations.translation_matrix([XT1 + 0.3, 8.6, -4.0])))
    parts.setdefault("trim", []).append(trimesh.creation.box([0.55, 4.5, 1.0], transform=trimesh.transformations.translation_matrix([XT0 - 0.27, 7.5, -1.0])))
    # vertical / horizontal pipes
    for x in (XT0 + 6.7, XT0 + 13.2):
        tube([x, 0, ZF + 0.18], [x, HT, ZF + 0.18], 0.15, "metal", parts)
    tube([XT0, 5.25, ZF + 0.2], [XT1, 5.25, ZF + 0.2], 0.17, "metal", parts)
    for z in (-3.5, -1.5):
        tube([XT0 - 0.15, 0, z], [XT0 - 0.15, HT, z], 0.15, "metal", parts)
    for x in (XT0 + 2, XT0 + 11):
        tube([x, 0, ZB - 0.15], [x, HT, ZB - 0.15], 0.15, "metal", parts)
    # ladders: tall wall above low roof, low block end wall
    for lx, lz, y0_, hh in ((XT1 + 0.1, -3.0, HL, HT - HL), (XL1 + 0.1, -3.0, 0.0, HL)):
        for dz in (0, 0.7):
            tube([lx, y0_, lz + dz], [lx, y0_ + hh, lz + dz], 0.05, "metal", parts)
        for k in range(int(hh / 0.48)):
            tube([lx, y0_ + 0.3 + k * 0.48, lz], [lx, y0_ + 0.3 + k * 0.48, lz + 0.7], 0.035, "metal", parts)
    for key, ms in parts.items():
        c = col.get(key) or (TRIM if key == "trim" else METAL)
        m = trimesh.util.concatenate(ms)
        m.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(m.vertices), 2)), material=trimesh.visual.material.PBRMaterial(
            name="p_" + key, baseColorFactor=[*((v / 255) ** 2.2 for v in c), 1.0], metallicFactor=0.1, roughnessFactor=0.7))
        sc.add_geometry(m, node_name="p_" + key, geom_name="p_" + key)
    return sc


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/radio_station_v4/export/radio_station_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    print(out, "triangles:", sum(len(g.faces) for g in sc.geometry.values()), "size:", np.round(sc.extents, 2))
