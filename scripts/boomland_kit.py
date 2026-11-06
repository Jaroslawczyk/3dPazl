"""Shared low-poly kit for Boomland props (Y-up metres, front = +Z). Flat colours; every colour becomes its own mesh with a
4x4 texture of that colour (Roblox ignores baseColorFactor). Colours listed in GLOW / GLASS get material names the
Boomland importer turns into Neon / see-through parts."""
import math, pathlib
import numpy as np, trimesh as tm
from PIL import Image

P = []
GLOW = {"ffe28c", "7ee8ff", "ff6a3d", "9dff7a"}
GLASS = {"cfefff"}


def col(m, hexc):
    h = hexc.lstrip('#'); m.visual.face_colors = [int(h[i:i+2], 16) for i in (0, 2, 4)] + [255]; P.append(m); return m


def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([abs(x1-x0), abs(y1-y0), abs(z1-z0)]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)


def boxc(cx, cy, cz, sx, sy, sz, c, yaw=0.0, pitch=0.0, roll=0.0):
    m = tm.creation.box([sx, sy, sz])
    for ang, ax in ((roll, [0, 0, 1]), (pitch, [1, 0, 0]), (yaw, [0, 1, 0])):
        if ang: m.apply_transform(tm.transformations.rotation_matrix(math.radians(ang), ax))
    m.apply_translation([cx, cy, cz]); return col(m, c)


def cyl(x, y0, y1, z, r, c, n=10):
    m = tm.creation.cylinder(radius=r, height=y1-y0, sections=n)
    m.apply_transform(tm.transformations.rotation_matrix(-math.pi/2, [1, 0, 0])); m.apply_translation([x, (y0+y1)/2, z]); return col(m, c)


def cylx(x0, x1, y, z, r, c, n=12):
    m = tm.creation.cylinder(radius=r, height=x1-x0, sections=n)
    m.apply_transform(tm.transformations.rotation_matrix(math.pi/2, [0, 1, 0])); m.apply_translation([(x0+x1)/2, y, z]); return col(m, c)


def ball(x, y, z, r, c, sub=1):
    m = tm.creation.icosphere(subdivisions=sub, radius=r); m.apply_translation([x, y, z]); return col(m, c)


def hull(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)


def beam(a, b, w, c, h=None):
    a, b = np.array(a, float), np.array(b, float); d = b - a; L = np.linalg.norm(d)
    m = tm.creation.box([w, h or w, L]); z = np.array([0, 0, 1.0]); u = d / L
    ax = np.cross(z, u); s = np.linalg.norm(ax)
    if s > 1e-6: m.apply_transform(tm.transformations.rotation_matrix(math.atan2(s, z @ u), ax / s))
    elif u[2] < 0: m.apply_transform(tm.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    m.apply_translation((a + b) / 2); return col(m, c)


def rock(x, y, z, r, c, seed=0, squash=0.7):
    rng = np.random.default_rng(seed)
    pts = [[x + math.cos(a) * r * rng.uniform(.7, 1.1), y + h * r * squash, z + math.sin(a) * r * rng.uniform(.7, 1.1)]
           for a in np.linspace(0, 2 * math.pi, 7, endpoint=False) for h in (0, rng.uniform(.4, .9))]
    pts.append([x, y + r * squash * 1.2, z]); return hull(pts, c)


def gable(x0, x1, z0, z1, y0, h, c, over=0.25, thick=0.12):
    """Two roof slabs, ridge along X."""
    zc = (z0 + z1) / 2; half = (z1 - z0) / 2 + over
    L = math.hypot(half, h); ang = math.degrees(math.atan2(h, half))
    for s in (-1, 1):
        boxc((x0 + x1) / 2, y0 + h / 2, zc + s * half / 2, x1 - x0 + 2 * over, thick, L, c, pitch=s * ang)


def export(name, out="projects/boomland_world/export"):
    global P
    scene = tm.util.concatenate(P); P = []
    fc = scene.visual.face_colors[:, :3]; sc = tm.Scene(); n = 0
    for cc in np.unique(fc, axis=0):
        sel = np.where((fc == cc).all(1))[0]
        m = scene.submesh([sel], append=True)
        hx = "%02x%02x%02x" % tuple(cc)
        kind = "Glass" if hx in GLASS else "Glow" if hx in GLOW else "Paint"
        img = Image.fromarray(np.full((4, 4, 3), cc, np.uint8))
        mat = tm.visual.material.PBRMaterial(name=f"{kind.lower()}#{hx}", baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.8)
        if kind == "Glass": mat.alphaMode = "BLEND"; mat.baseColorFactor = [255, 255, 255, 110]
        m.visual = tm.visual.TextureVisuals(uv=np.full((len(m.vertices), 2), 0.5), material=mat)
        n += len(m.faces); sc.add_geometry(m, geom_name=f"{kind}_{hx}")
    o = pathlib.Path(out); o.mkdir(parents=True, exist_ok=True)
    sc.export(o / f"{name}.glb"); print(f"{name}: {n} tris, {len(sc.geometry)} materials")
