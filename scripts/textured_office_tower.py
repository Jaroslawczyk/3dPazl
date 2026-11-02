"""Textured low-poly office tower (SpringSprout case): concrete piers + tiled dark-glass facade from the reference
tiles saved in textures/library/ref_office_tower, painted logo, L penthouse, skylight, stained ground disc.
Reference size (units): core 11.4 x 23.14 x 7.4, piers frame 12.07 x 24 x 8.21, disc 24.3. Scaled x S at the end.

    .venv/Scripts/python.exe scripts/textured_office_tower.py [out.glb]
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from textured_panel import Builder, all_sides  # noqa: E402

LIB = Path("textures/library/ref_office_tower")
S = 4.0
LX0, LX1, LZ = -3.7, 7.7, 3.7            # core: long axis X, narrow faces at x = LX0 / LX1 (logo on the -X face)
H, HT = 23.14, 24.0
FLOORS, TILE_F = 27, 3
D_NARROW = 7.4
CONCRETE, ROOF, CREAM = (178, 173, 165), (150, 150, 165), (220, 212, 192)


def tile_img(name, px):
    return Image.open(LIB / name).convert("RGB").resize((px, px), Image.LANCZOS)


def facade(width, with_logo=False):
    """Tile the 2-bay x 3-floor reference tile across the face (width in units, 0.95 per tile)."""
    nx, ny = max(1, round(width / 0.95)), FLOORS // TILE_F
    t = tile_img("facade_concrete_windows_albedo.png", 128)
    img = Image.new("RGB", (nx * 128, ny * 128))
    for i in range(nx):
        for j in range(ny):
            img.paste(t, (i * 128, j * 128))
    img = ImageEnhance.Brightness(img).enhance(0.6)
    if with_logo:
        W, Hh = img.size
        u_w, u_h = 6.0, 2.6                                  # logo block in units, drawn undistorted then fitted
        t = Image.new("RGBA", (600, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        d.polygon([(200, 40), (330, 0), (420, 70), (390, 140), (290, 150), (220, 100)], fill=(143, 208, 26, 255))
        try:
            f = ImageFont.truetype("arialbd.ttf", 64)
        except OSError:
            f = ImageFont.load_default()
        d.text((300, 200), "SpringSprout", fill=(20, 40, 28, 255), font=f, anchor="mm", stroke_width=4, stroke_fill=(190, 205, 180, 255))
        px_x, px_y = W / D_NARROW, Hh / (H - 1.0)
        t = t.resize((int(u_w * px_x), int(u_h * px_y)), Image.LANCZOS)
        img.paste(t, (W // 2 - t.size[0] // 2, int(Hh * 0.36)), t)
    return img


def lobby(width):
    nx = max(1, round(width / 0.95))
    t = tile_img("glass_grid_facade_albedo.png", 128)
    img = Image.new("RGB", (nx * 128, 128))
    for i in range(nx):
        img.paste(t, (i * 128, 0))
    return img


def ground_disc():
    a = Image.open(LIB / "ground_roof_props_atlas_albedo.png").convert("RGB")
    return a.crop((0, 225, 1375, 1950)).resize((1024, 1024), Image.LANCZOS)


def build():
    B = Builder()
    cx, cz = (LX0 + LX1) / 2, 0.0
    L, D = LX1 - LX0, 2 * LZ
    mat = lambda k, c: B.mat(k, color=c)  # noqa: E731
    conc, roof, cream = mat("conc", CONCRETE), mat("roof", ROOF), mat("cream", CREAM)
    ff, bf = B.mat("long_f", facade(L)), B.mat("long_b", facade(L))
    lf, rf = B.mat("narrow_l", facade(D, with_logo=True)), B.mat("narrow_r", facade(D))
    # core: ground-floor lobby band below the tiled facade
    lob = 1.0
    B.box(LX0, LX1, lob, H, -LZ, LZ, {"front": ff, "back": bf, "left": lf, "right": rf, "top": roof})
    B.box(LX0, LX1, 0, lob, -LZ, LZ, {"front": B.mat("lob_l", lobby(L)), "back": B.mat("lob_l2", lobby(L)),
                                      "left": B.mat("lob_n", lobby(D)), "right": B.mat("lob_n2", lobby(D))})
    # piers: long faces 6, narrow faces 4, frame depth 0.33
    pw, pd = 0.3, 0.3
    for z0, sgn in ((LZ, 1), (-LZ, -1)):
        for i in range(6):
            x = LX0 + 0.2 + i * (L - 0.4) / 5
            zz0, zz1 = (z0, z0 + pd) if sgn > 0 else (z0 - pd, z0)
            B.box(x - pw / 2, x + pw / 2, 0, HT, zz0, zz1, all_sides(conc) | {"bottom": None})
    for x0, sgn in ((LX0, -1), (LX1, 1)):
        for i in range(4):
            z = -LZ + 0.2 + i * (D - 0.4) / 3
            xx0, xx1 = (x0 - pd, x0) if sgn < 0 else (x0, x0 + pd)
            B.box(xx0, xx1, 0, HT, z - pw / 2, z + pw / 2, all_sides(conc) | {"bottom": None})
    # roof rim (cornice) + parapet
    B.box(LX0 - pd, LX1 + pd, H, HT, -LZ - pd, LZ + pd, all_sides(conc) | {"bottom": None})
    B.box(LX0 - pd, LX1 + pd, HT, HT + 0.12, -LZ - pd, -LZ - pd + 0.12, all_sides(conc) | {"bottom": None})
    B.box(LX0 - pd, LX1 + pd, HT, HT + 0.12, LZ + pd - 0.12, LZ + pd, all_sides(conc) | {"bottom": None})
    # L penthouse (cream) with a door, skylight
    B.box(-2.8, 3.2, HT, HT + 1.1, -3.4, -0.6, all_sides(cream) | {"bottom": None})
    B.box(0.6, 3.2, HT, HT + 1.1, -0.6, 1.6, all_sides(cream) | {"bottom": None})
    B.box(5.2, 6.5, HT, HT + 0.35, 1.0, 2.7, all_sides(mat("sky", (40, 70, 110))) | {"bottom": None})
    # ground disc
    disc = trimesh.creation.cylinder(radius=12.15, height=0.09, sections=40)
    disc.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    disc.apply_translation([1.0, -0.045, cz])   # reference disc centre x = 1.0
    uv = np.c_[(disc.vertices[:, 0] - 1.0) / 24.3 + 0.5, 1 - ((disc.vertices[:, 2] - cz) / 24.3 + 0.5)]
    disc.visual = trimesh.visual.TextureVisuals(uv=uv, material=trimesh.visual.material.PBRMaterial(
        name="ground", baseColorTexture=ground_disc(), metallicFactor=0.0, roughnessFactor=0.9))
    sc = B.scene()
    sc.add_geometry(disc, node_name="ground", geom_name="ground")
    sc.apply_scale(S)
    return sc


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/office_tower_v2/export/office_tower_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    print(out, "triangles:", sum(len(g.faces) for g in sc.geometry.values()), "size:", np.round(sc.extents, 1))
