"""Textured low-poly stone castle (Age of Empires scan reference): 6 fat battered round towers with corbelled
crowns + merlons, curtain walls with merlons, gatehouse with painted pointed arch, stone ramp, rocky base, courtyard.
Layout (metres) comes from the TOP view of the reference; stone is a procedural block texture (the scan atlas is a grey bake).

    .venv/Scripts/python.exe scripts/textured_castle.py [out.glb]
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter

rnd = random.Random(5)
STONE = (158, 154, 146)
# (name, x, z(front = +z), r_body, height)   z = -y of the top view
TOWERS = [("rl", -5.1, -15.2, 3.6, 25), ("rr", 5.4, -15.5, 3.6, 26), ("ml", -11.5, -7.4, 5.2, 29),
          ("mr", 11.5, -7.1, 5.2, 31), ("fl", -8.8, 7.8, 4.3, 21), ("fr", 7.4, 7.1, 4.3, 22)]
WALL_H, WALL_T = 16.0, 2.2


def stone_tex(size=512, course=0.5, seed=1, arch=False, slit=False):
    r = random.Random(seed)
    img = Image.new("RGB", (size, size), STONE)
    d = ImageDraw.Draw(img)
    rows = int(1 / course * 2)
    ch = size // rows
    for j in range(rows):
        x, y = -r.randint(0, 80), j * ch
        while x < size:
            w = r.randint(70, 150)
            k = r.uniform(0.86, 1.1)
            d.rectangle([x, y, x + w, y + ch], fill=tuple(int(c * k) for c in STONE))
            d.rectangle([x, y, x + w, y + ch], outline=(96, 92, 86), width=2)
            x += w
    a = np.asarray(img, float) + np.random.default_rng(seed).normal(0, 6, (size, size, 1))
    img = Image.fromarray(np.clip(a, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))
    return img


def gate_tex():
    img = stone_tex(512, seed=9)
    d = ImageDraw.Draw(img)
    d.rectangle([150, 160, 362, 512], fill=(26, 22, 20))
    d.pieslice([150, 60, 362, 260], 180, 360, fill=(26, 22, 20))
    for x in range(170, 362, 28):                       # portcullis bars
        d.line([x, 120, x, 512], fill=(70, 62, 54), width=4)
    for y in range(180, 512, 40):
        d.line([150, y, 362, y], fill=(70, 62, 54), width=3)
    d.arc([140, 50, 372, 270], 180, 360, fill=(200, 196, 188), width=10)
    return img


class Scene:
    def __init__(self):
        self.mats, self.parts = {}, {}

    def mat(self, key, img=None, color=None):
        if key not in self.mats:
            kw = dict(name=key, metallicFactor=0.0, roughnessFactor=0.95)
            if img is not None:
                kw["baseColorTexture"] = img
            else:
                kw["baseColorFactor"] = [*((c / 255) ** 2.2 for c in color), 1.0]
            self.mats[key] = trimesh.visual.material.PBRMaterial(doubleSided=True, **kw)
        return key

    def add(self, key, verts, faces, uvs):
        vs, fs, us = self.parts.setdefault(key, ([], [], []))
        n = len(vs)
        vs.extend(verts)
        us.extend(uvs)
        fs.extend((a + n, b + n, c + n) for a, b, c in faces)

    def mesh_planar(self, key, m, tile=4.0):
        """Add a trimesh with triplanar-ish UV (stone courses stay horizontal)."""
        v = np.asarray(m.vertices)
        nrm = np.asarray(m.vertex_normals)
        u = np.where(np.abs(nrm[:, [0]]) > np.abs(nrm[:, [2]]), v[:, [2]], v[:, [0]])[:, 0] / tile
        self.add(key, list(v), [tuple(f) for f in m.faces], list(zip(u, v[:, 1] / tile)))

    def frustum(self, key, x, z, y0, r0, r1, h, seg=24, tile=4.0, cap=False):
        vs, fs, us = [], [], []
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            u = i / seg * (2 * math.pi * max(r0, r1)) / tile
            vs += [(x + r0 * math.cos(a), y0, z + r0 * math.sin(a)), (x + r1 * math.cos(a), y0 + h, z + r1 * math.sin(a))]
            us += [(u, 0), (u, h / tile)]
        for i in range(seg):
            a = 2 * i
            fs += [(a, a + 2, a + 1), (a + 1, a + 2, a + 3)]
        if cap:
            c = len(vs)
            vs.append((x, y0 + h, z)); us.append((0, 0))
            for i in range(seg):
                fs.append((c, 2 * i + 1, 2 * i + 3))
        self.add(key, vs, fs, us)

    def box(self, key, c, size, rot=0.0, tile=4.0):
        m = trimesh.creation.box(size)
        m.apply_transform(trimesh.transformations.rotation_matrix(rot, [0, 1, 0]))
        m.apply_translation(c)
        self.mesh_planar(key, m, tile)

    def scene(self):
        sc = trimesh.Scene()
        for k, (vs, fs, us) in self.parts.items():
            m = trimesh.Trimesh(np.array(vs, float), np.array(fs), process=False,
                                visual=trimesh.visual.TextureVisuals(uv=np.array(us, float), material=self.mats[k]))
            sc.add_geometry(m, node_name=k, geom_name=k)
        return sc


def build():
    S = Scene()
    stone = S.mat("stone", stone_tex(seed=1))
    dark = S.mat("dark", stone_tex(seed=2))
    top = S.mat("top", color=(120, 116, 108))
    rock = S.mat("rock", color=(92, 88, 80))
    gate = S.mat("gate", gate_tex())
    slit = S.mat("slit", color=(24, 22, 22))
    P = {t[0]: t for t in TOWERS}
    # rocky base: irregular lumpy disc under the whole castle
    base = trimesh.creation.cylinder(radius=1, height=2.2, sections=40)
    v = base.vertices.copy()
    ang = np.arctan2(v[:, 1], v[:, 0])
    rad = 1 + 0.07 * np.sin(5 * ang) + 0.05 * np.sin(11 * ang + 1)
    v[:, 0] *= 19.5 * rad
    v[:, 1] *= 22.0 * rad
    base.vertices = np.column_stack([v[:, 0], v[:, 2], v[:, 1]])  # z-up -> y-up
    base.apply_translation([0, 0.9, -3.2])
    S.mesh_planar("rock", base, 6.0)
    # courtyard floor
    S.box("dark", (0, 2.0, -3.6), (23, 1.0, 24), tile=4)
    # towers
    for name, x, z, r, h in TOWERS:
        S.frustum("stone", x, z, 1.8, r + 1.7, r, 6.0, 28)                    # battered base
        S.frustum("stone", x, z, 7.8, r, r, h - 10.0, 28)                     # body
        S.frustum("stone", x, z, h - 2.2, r, r + 1.1, 2.2, 28)                # corbelled crown
        S.frustum("top", x, z, h, r + 1.1, r + 1.1, 0.25, 28, cap=True)       # walkway
        n = 14
        for i in range(n):                                                       # merlons
            a = 2 * math.pi * (i + 0.5) / n
            S.box("stone", (x + (r + 0.8) * math.cos(a), h + 0.25 + 0.7, z + (r + 0.8) * math.sin(a)), (1.1, 1.4, 0.7), rot=-a + math.pi / 2)
        for lvl in (0.35, 0.7):                                            # arrow slits at 3 azimuths
            for a in (math.pi / 2 + 0.35, math.pi / 2 - 0.35, math.pi * 1.5):
                S.box("slit", (x + (r + 0.06) * math.cos(a), 7.0 + lvl * (h - 12), z + (r + 0.06) * math.sin(a)), (0.32, 1.5, 0.12), rot=-a + math.pi / 2)
    # curtain walls between towers (rear, both sides, front sections beside the gatehouse)
    links = [("fl", "ml"), ("ml", "rl"), ("rl", "rr"), ("rr", "mr"), ("mr", "fr")]
    for a, b in links:
        _, x0, z0, *_ = P[a]
        _, x1, z1, *_ = P[b]
        L = math.hypot(x1 - x0, z1 - z0)
        ang = -math.atan2(z1 - z0, x1 - x0)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        S.box("stone", (cx, 1.8 + WALL_H / 2, cz), (L, WALL_H, WALL_T), rot=ang)
        nm = int(L / 2.2)
        for i in range(nm):                                                      # merlons on the outer edge
            t = (i + 0.5) / nm - 0.5
            S.box("stone", (cx + t * L * math.cos(-ang), 1.8 + WALL_H + 0.6, cz - t * L * math.sin(-ang)), (1.2, 1.2, 0.9), rot=ang)
    # gatehouse between the front towers + painted gate quad + ramp
    gx0, gx1, gz = -4.2, 3.0, 8.3
    S.box("stone", ((gx0 + gx1) / 2, 1.8 + 9.0, gz - 2.0), (gx1 - gx0, 18.0, 6.0))
    for i in range(7):
        S.box("stone", (gx0 + 0.6 + i * 1.15, 1.8 + 18.0 + 0.6, gz + 0.8), (0.8, 1.2, 0.9))
    S.add("gate", [(-3.0, 1.9, gz + 1.02), (2.0, 1.9, gz + 1.02), (2.0, 11.0, gz + 1.02), (-3.0, 11.0, gz + 1.02)],
          [(0, 1, 2), (0, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in range(6):
        S.box("rock", (-0.6, 0.9 - k * 0.12 + 0.6, gz + 3.0 + k * 1.5), (7.2, 1.2 + (5 - k) * 0.25, 1.5), tile=3)
    # courtyard details seen from the top: low inner walls and a hall
    S.box("stone", (-5.0, 6.0, -4.0), (10, 8.0, 1.4))
    S.box("stone", (-1.5, 5.0, -2.0), (1.4, 6.0, 10))
    S.box("stone", (6.5, 7.0, -3.5), (5, 7.0, 7))
    return S.scene()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "projects/aoe_castle_v4/export/castle_textured.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = build()
    sc.export(out)
    print(out, "triangles:", sum(len(g.faces) for g in sc.geometry.values()), "size:", np.round(sc.extents, 1))
