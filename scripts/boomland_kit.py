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


def gable(x0, x1, z0, z1, y0, h, c, over=0.25, thick=0.12, ridge="x"):
    """Two roof slabs over the box x0..x1, z0..z1. The underside runs from the wall tops (y0 at the eave walls) up to the
    ridge (y0 + h) and goes on past the walls by `over`. ridge="x": ridge along X, slopes fall to -Z / +Z (gable ends at
    x0 / x1). ridge="z": ridge along Z, slopes fall to -X / +X (gable ends at z0 / z1, the front)."""
    a0, a1, b0, b1 = (z0, z1, x0, x1) if ridge == "x" else (x0, x1, z0, z1)   # a = across the slopes, b = along the ridge
    ac = (a0 + a1) / 2; half = (a1 - a0) / 2; k = h / half; run = half + over
    ang = math.atan(k); L = math.hypot(run, run * k); bc = (b0 + b1) / 2; blen = b1 - b0 + 2 * over
    for s in (-1, 1):
        ca = ac + s * (run / 2 + thick / 2 * math.sin(ang)); cy = y0 + h - run * k / 2 + thick / 2 * math.cos(ang)
        if ridge == "x": boxc(bc, cy, ca, blen, thick, L, c, pitch=s * math.degrees(ang))
        else: boxc(ca, cy, bc, L, thick, blen, c, roll=-s * math.degrees(ang))
    cap = thick * 1.6
    if ridge == "x": box(b0 - over, y0 + h, ac - cap / 2, b1 + over, y0 + h + thick * 1.3, ac + cap / 2, c)
    else: box(ac - cap / 2, y0 + h, b0 - over, ac + cap / 2, y0 + h + thick * 1.3, b1 + over, c)


def gable_end(a0, a1, y0, h, c, at, t=0.18, ridge="x"):
    """Triangular gable wall under gable(): base a0..a1 at y0, peak y0 + h in the middle. ridge="x": the wall stands
    across Z at x = at..at+t; ridge="z": across X at z = at..at+t."""
    am = (a0 + a1) / 2; tri = [(a0, y0), (a1, y0), (am, y0 + h - .02)]
    if ridge == "x": return hull([[x, y, a] for x in (at, at + t) for a, y in tri], c)
    return hull([[a, y, z] for z in (at, at + t) for a, y in tri], c)


LIB = pathlib.Path(__file__).resolve().parents[1] / "textures" / "library"
# flat colour -> (CC0 texture from textures/library, metres per texture repeat); the texture is tinted to the colour
TEX = {"9a6a40": ("wood_boards", 1.6), "6e4a2e": ("wood_dark", 1.6), "b98552": ("wood_floor", 1.6),
       "9a948c": ("stone_rubble", 2.0), "6f6a64": ("granite", 1.5), "c9c2b5": ("sandstone", 2.0),
       "c94a3a": ("clay_tile", 1.5), "3a6fb0": ("clay_tile", 1.5), "b5523b": ("brick_red", 1.5),
       "5a606c": ("steel", 1.5), "2b2f3a": ("iron", 1.5), "f2efe6": ("plaster_white", 2.0), "7fb4d6": ("wood_painted_white", 1.6),
       "ffd23f": ("wood_boards", 1.2), "ffc83c": ("steel", 1.0), "3a3d44": ("bitumen", 2.0)}
_cache = {}


def texture(hx, cc):
    """Tinted tileable texture (256 px) for a flat colour, or a 4x4 flat image when there is no texture for it."""
    if hx not in TEX: return Image.fromarray(np.full((4, 4, 3), cc, np.uint8)), None
    if hx not in _cache:
        t = np.asarray(Image.open(LIB / f"{TEX[hx][0]}_albedo.jpg").convert("RGB").resize((256, 256), Image.LANCZOS), float)
        lum = t.mean(2, keepdims=True); lum = 0.55 + 0.45 * lum / lum.mean()          # keep the pattern, soften it
        _cache[hx] = Image.fromarray(np.clip(lum * np.array(cc, float), 0, 255).astype(np.uint8))
    return _cache[hx], TEX[hx][1]


def box_uv(m, tile):
    """Per-face box projection in world metres: walls get (horizontal, up), floors/roofs get (x, z)."""
    m = m.copy(); m.unmerge_vertices()
    fn = m.face_normals; ax = np.abs(fn).argmax(1); uv = np.zeros((len(m.vertices), 2))
    for f, a in enumerate(ax):
        v = m.faces[f]; p = m.vertices[v]
        uv[v] = p[:, [2, 1]] if a == 0 else p[:, [0, 2]] if a == 1 else p[:, [0, 1]]
    return m, uv / tile


def export(name, out="projects/boomland_world/export"):
    global P
    scene = tm.util.concatenate(P); P = []
    fc = scene.visual.face_colors[:, :3]; sc = tm.Scene(); n = 0
    for cc in np.unique(fc, axis=0):
        sel = np.where((fc == cc).all(1))[0]
        m = scene.submesh([sel], append=True)
        hx = "%02x%02x%02x" % tuple(cc)
        kind = "Glass" if hx in GLASS else "Glow" if hx in GLOW else "Paint"
        img, tile = texture(hx, cc) if kind == "Paint" else (Image.fromarray(np.full((4, 4, 3), cc, np.uint8)), None)
        if tile: m, uv = box_uv(m, tile)
        else: uv = np.full((len(m.vertices), 2), 0.5)
        mat = tm.visual.material.PBRMaterial(name=f"{kind.lower()}#{hx}", baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.8)
        if kind == "Glass": mat.alphaMode = "BLEND"; mat.baseColorFactor = [255, 255, 255, 110]
        m.visual = tm.visual.TextureVisuals(uv=uv, material=mat)
        n += len(m.faces); sc.add_geometry(m, geom_name=f"{kind}_{hx}")
    o = pathlib.Path(out); o.mkdir(parents=True, exist_ok=True)
    sc.export(o / f"{name}.glb"); print(f"{name}: {n} tris, {len(sc.geometry)} materials")
