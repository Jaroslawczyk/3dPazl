"""Small objects ("items" workshop): dishes, food and small stuff, generated parametrically with manifold3d.

Every item is a list of closed solids, each with a material; units are metres, Z up, origin at bottom centre.
`build(kind, params)` -> (parts, info); `export_glb(kind, params, path)` writes a Y-up GLB (one mesh per material).
Common params: size (uniform scale factor), seed (variant), color (main colour '#rrggbb'), seg (round detail).
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import trimesh

from . import geo
from .geo import M

# name -> (rgb, metallic, roughness, alpha)
MATS = {
    "ceramic": ((0.93, 0.92, 0.88), 0.0, 0.25, 1.0), "glaze": ((0.25, 0.45, 0.70), 0.0, 0.2, 1.0),
    "glass": ((0.75, 0.88, 0.92), 0.0, 0.05, 0.35), "glass_green": ((0.20, 0.45, 0.25), 0.0, 0.05, 0.6),
    "metal": ((0.72, 0.72, 0.74), 1.0, 0.3, 1.0), "dark_metal": ((0.15, 0.15, 0.16), 0.8, 0.45, 1.0),
    "wood": ((0.55, 0.36, 0.20), 0.0, 0.7, 1.0), "plastic": ((0.12, 0.12, 0.12), 0.0, 0.5, 1.0),
    "cork": ((0.70, 0.55, 0.35), 0.0, 0.9, 1.0), "clay": ((0.70, 0.38, 0.24), 0.0, 0.85, 1.0),
    "apple": ((0.75, 0.10, 0.08), 0.0, 0.35, 1.0), "leaf": ((0.25, 0.55, 0.15), 0.0, 0.6, 1.0),
    "stem": ((0.35, 0.22, 0.10), 0.0, 0.8, 1.0), "crust": ((0.72, 0.45, 0.18), 0.0, 0.85, 1.0),
    "crumb": ((0.95, 0.85, 0.62), 0.0, 0.9, 1.0), "cheese": ((0.98, 0.80, 0.30), 0.0, 0.6, 1.0),
    "sauce": ((0.72, 0.15, 0.08), 0.0, 0.5, 1.0), "salami": ((0.62, 0.12, 0.12), 0.0, 0.5, 1.0),
    "cream": ((0.98, 0.95, 0.90), 0.0, 0.5, 1.0), "sponge": ((0.85, 0.65, 0.40), 0.0, 0.9, 1.0),
    "berry": ((0.80, 0.05, 0.15), 0.0, 0.3, 1.0), "egg": ((0.92, 0.82, 0.68), 0.0, 0.5, 1.0),
    "sausage": ((0.65, 0.30, 0.22), 0.0, 0.45, 1.0), "paper": ((0.96, 0.94, 0.86), 0.0, 0.9, 1.0),
    "cover": ((0.45, 0.10, 0.12), 0.0, 0.7, 1.0), "wax": ((0.97, 0.94, 0.85), 0.0, 0.6, 1.0),
    "wick": ((0.10, 0.08, 0.06), 0.0, 0.9, 1.0), "cardboard": ((0.68, 0.52, 0.34), 0.0, 0.9, 1.0),
    "red_paint": ((0.75, 0.12, 0.10), 0.2, 0.5, 1.0), "water": ((0.55, 0.75, 0.85), 0.0, 0.05, 0.5),
}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ------------------------------------------------------------------ helpers
def vessel(outer, t, seg, bottom=None):
    """Hollow body of revolution. outer: (r, z) from the bottom edge up to the rim; wall t, base thickness `bottom`."""
    b = t if bottom is None else bottom
    inner = [(max(r - t, 0.002), z) for r, z in outer if z >= b]
    pts = [(0.0, 0.0)] + list(outer) + list(reversed(inner)) + [(0.0, b)]
    return geo.revolve(pts, seg)


def solid(outer, seg):
    """Solid body of revolution from outer (r, z) points, closed by the axis."""
    return geo.revolve([(0.0, outer[0][1])] + list(outer) + [(0.0, outer[-1][1])], seg)


def handle(x, z0, z1, reach, r, seg=8, n=6):
    """C-shaped handle in the XZ plane attached at x between heights z0..z1, bulging out by `reach`."""
    zc, hz = (z0 + z1) / 2, (z1 - z0) / 2
    pts = [(x - 0.004 + reach * math.sin(math.pi * i / n), 0.0, zc + hz * math.cos(math.pi * i / n)) for i in range(n + 1)]
    parts = [geo.rod(pts[i], pts[i + 1], r, seg) for i in range(n)] + [geo.sphere(r, seg, p) for p in pts[1:-1]]
    return geo.union(parts)


def rs(prof, s):
    return [(r * s, z * s) for r, z in prof]


# ------------------------------------------------------------------ dishes
def plate(p, R):
    r, h = 0.13 * p["width"], 0.022 * p["height"]
    return [(vessel([(r * 0.55, 0), (r * 0.6, h * 0.25), (r * 0.7, h * 0.35), (r, h)], 0.004, p["seg"]), "ceramic")]


def bowl(p, R):
    r, h = 0.075 * p["width"], 0.065 * p["height"]
    prof = [(r * 0.45, 0), (r * 0.45, h * 0.08)] + [(r * (0.45 + 0.55 * math.sin(math.pi / 2 * i / 5)), h * (0.08 + 0.92 * i / 5)) for i in range(1, 6)]
    return [(vessel(prof, 0.004, p["seg"]), "glaze")]


def cup(p, R):
    r, h = 0.042 * p["width"], 0.07 * p["height"]
    body = vessel([(r * 0.7, 0), (r * 0.85, h * 0.4), (r, h)], 0.003, p["seg"])
    saucer = vessel([(r * 1.1, 0), (r * 1.8, 0.008), (r * 1.95, 0.013)], 0.003, p["seg"])
    body = body.translate([0, 0, 0.008])
    return [(geo.union([body, handle(r * 0.9, 0.008 + h * 0.3, 0.008 + h * 0.85, r * 0.6, 0.004)]), "ceramic"), (saucer, "ceramic")]


def mug(p, R):
    r, h = 0.042 * p["width"], 0.095 * p["height"]
    body = vessel([(r, 0), (r, h)], 0.004, p["seg"], 0.008)
    return [(geo.union([body, handle(r, h * 0.2, h * 0.8, r * 0.75, 0.006)]), "glaze")]


def glass(p, R):
    r, h = 0.035 * p["width"], 0.11 * p["height"]
    if R.random() < 0.5:  # tumbler
        return [(vessel([(r * 0.8, 0), (r, h)], 0.0025, p["seg"], 0.01), "glass")]
    stem_h = h * 0.45
    prof = [(r * 0.9, 0), (r * 0.9, 0.003), (0.004, 0.006), (0.004, stem_h), (r * 0.6, stem_h + h * 0.08),
            (r, stem_h + h * 0.3), (r * 0.85, h)]
    outer = solid(prof[:5], p["seg"])
    cupb = vessel([(r * 0.6, stem_h + h * 0.08), (r, stem_h + h * 0.3), (r * 0.85, h)], 0.002, p["seg"], stem_h + h * 0.1)
    return [(geo.union([outer, cupb]), "glass")]


def bottle(p, R):
    r, h = 0.037 * p["width"], 0.30 * p["height"]
    prof = [(r, 0), (r, h * 0.62), (r * 0.35, h * 0.82), (r * 0.32, h * 0.97), (r * 0.38, h * 0.975), (r * 0.38, h)]
    body = vessel(prof, 0.003, p["seg"], 0.008)
    cork = geo.cyl(r * 0.3, h * 0.06, 10, h * 0.97)
    return [(body, "glass_green"), (cork, "cork")]


def jug(p, R):
    r, h = 0.065 * p["width"], 0.2 * p["height"]
    prof = [(r * 0.8, 0), (r, h * 0.35), (r * 0.7, h * 0.85), (r * 0.78, h)]
    body = vessel(prof, 0.004, p["seg"], 0.008)
    spout = geo.hull([(-r * 0.7, -0.012, h * 0.85), (-r * 0.7, 0.012, h * 0.85), (-r * 1.05, 0, h * 1.02), (-r * 0.75, 0, h * 1.0)])
    spout = geo.subtract(spout, [geo.cyl(r * 0.7 - 0.004, h, p["seg"], h * 0.5)])
    return [(geo.union([body, spout, handle(r * 0.8, h * 0.3, h * 0.88, r * 0.55, 0.007)]), "clay")]


def pot(p, R):
    r, h = 0.11 * p["width"], 0.14 * p["height"]
    body = vessel([(r, 0), (r, h)], 0.003, p["seg"], 0.005)
    lid = solid([(r + 0.004, h), (r * 0.7, h + 0.015), (0.0, h + 0.022)], p["seg"])
    knob = geo.cyl(0.012, 0.018, 12, h + 0.02)
    ears = [geo.boxc(0.03, 0.05, 0.008, s * (r + 0.012), 0, h * 0.85) for s in (-1, 1)]
    return [(geo.union([body] + ears), "metal"), (geo.union([lid, knob]), "metal")]


def pan(p, R):
    r, h = 0.12 * p["width"], 0.045 * p["height"]
    body = vessel([(r * 0.88, 0), (r, h)], 0.004, p["seg"], 0.005)
    L = 0.19 * p["width"]
    hnd = geo.rod((r - 0.005, 0, h * 0.7), (r + L, 0, h * 1.2), 0.011, 8)
    return [(body, "dark_metal"), (hnd, "wood")]


def kettle(p, R):
    r, h = 0.085 * p["width"], 0.17 * p["height"]
    prof = [(r * 0.9, 0), (r, h * 0.2), (r * 0.95, h * 0.6), (r * 0.5, h * 0.92), (r * 0.42, h * 0.95)]
    body = vessel(prof, 0.003, p["seg"], 0.004)
    lid = solid([(r * 0.46, h * 0.95), (r * 0.3, h), (0, h * 1.01)], p["seg"])
    knob = geo.sphere(0.012, 10, (0, 0, h * 1.01))
    spout = geo.rod((-r * 0.85, 0, h * 0.3), (-r * 1.5, 0, h * 0.75), 0.012, 10)
    pts = [(r * 0.55 * math.cos(math.pi * i / 6), 0, h * 0.95 + h * 0.35 * math.sin(math.pi * i / 6)) for i in range(7)]
    bail = geo.union([geo.rod(pts[i], pts[i + 1], 0.008, 8) for i in range(6)] + [geo.sphere(0.008, 8, q) for q in pts[1:-1]])
    return [(geo.union([body, spout]), "red_paint"), (geo.union([lid, knob]), "red_paint"), (bail, "plastic")]


def vase(p, R):
    r, h = 0.06 * p["width"], 0.25 * p["height"]
    a, b = 0.6 + 0.4 * R.random(), 0.25 + 0.25 * R.random()
    prof = [(r * 0.6, 0)] + [(r * (b + a * math.sin(math.pi * (0.15 + 0.85 * i / 8)) ** 1.5), h * i / 8) for i in range(1, 9)]
    prof[-1] = (r * (b + 0.15), h)
    return [(vessel(prof, 0.004, p["seg"], 0.01), "glaze")]


# ------------------------------------------------------------------ food
def apple(p, R):
    r = 0.04 * p["width"]
    prof = [(r * 0.25, 0.0)] + [(r * math.sin(math.pi * i / 10) * (1 + 0.08 * math.sin(math.pi * i / 10)), r * (0.05 + 0.9 * (1 - math.cos(math.pi * i / 10)))) for i in range(1, 10)] + [(r * 0.3, r * 1.82), (r * 0.15, r * 1.72)]
    body = solid([(r * 0.2, r * 0.05)] + prof[1:], p["seg"]).scale([1, 1, p["height"]])
    top = r * 1.72 * p["height"]
    stem = geo.rod((0, 0, top - 0.005), (0.004, 0, top + 0.018), 0.0025, 6)
    leaf = geo.sphere(0.012, 8, (0.012, 0, top + 0.012)).scale([1, 0.45, 0.12]).translate([0.006, 0, top * 0.88])
    return [(body, "apple"), (stem, "stem"), (leaf, "leaf")]


def bread(p, R):
    L, w, h = 0.28 * p["width"], 0.11 * p["width"], 0.08 * p["height"]
    loaf = geo.sphere(1, p["seg"]).scale([L / 2, w / 2, h])
    loaf = loaf.trim_by_plane([0, 0, 1], 0.0)
    cuts = [geo.boxc(0.006, w * 1.2, 0.03, 0, 0, h - 0.012).rotate([0, 0, 25]).translate([x, 0, 0]) for x in np.linspace(-L * 0.3, L * 0.3, 3 + R.randint(0, 2))]
    return [(geo.subtract(loaf, cuts), "crust")]


def cheese(p, R):
    r, h, ang = 0.1 * p["width"], 0.06 * p["height"], 50 + 30 * R.random()
    pts = [(0, 0)] + geo.arc_pts(0, 0, r, -math.radians(ang / 2), math.radians(ang / 2), 6)
    wedge = geo.extrude(geo.poly(pts), h)
    holes = [geo.sphere(0.006 + 0.008 * R.random(), 8, (r * (0.3 + 0.6 * R.random()), r * 0.25 * (R.random() - 0.5), h * R.random())) for _ in range(6)]
    return [(geo.subtract(wedge, holes).translate([-r / 2, 0, 0]), "cheese")]


def pizza(p, R):
    r, seg = 0.15 * p["width"], max(p["seg"], 24)
    base = geo.cyl(r, 0.008, seg)
    rim = solid([(r - 0.012, 0.008), (r, 0.012), (r - 0.004, 0.02), (r - 0.016, 0.014)], seg)
    sauce = geo.cyl(r - 0.012, 0.004, seg, 0.007)
    ch = geo.cyl(r - 0.018, 0.003, seg, 0.01)
    sal = []
    for _ in range(7):
        a, d = R.random() * 6.28, (r - 0.04) * math.sqrt(R.random())
        sal.append(geo.cyl(0.018, 0.004, 12, 0.011, cx=d * math.cos(a), cy=d * math.sin(a)))
    return [(geo.union([base, rim]), "crust"), (sauce, "sauce"), (ch, "cheese"), (geo.union(sal), "salami")]


def cake(p, R):
    r, h, seg = 0.11 * p["width"], 0.09 * p["height"], max(p["seg"], 24)
    sponge = geo.cyl(r, h, seg)
    icing = geo.cyl(r + 0.003, 0.012, seg, h - 0.004)
    n = 8
    blobs = [geo.sphere(0.01, 8, ((r - 0.012) * math.cos(6.283 * i / n), (r - 0.012) * math.sin(6.283 * i / n), h + 0.012)) for i in range(n)]
    berries = [geo.sphere(0.009, 10, ((r - 0.012) * math.cos(6.283 * (i + .5) / n), (r - 0.012) * math.sin(6.283 * (i + .5) / n), h + 0.012)) for i in range(n)]
    return [(sponge, "sponge"), (geo.union([icing] + blobs), "cream"), (geo.union(berries), "berry")]


def egg(p, R):
    r, h = 0.021 * p["width"], 0.057 * p["height"]
    prof = [(r * math.sin(math.pi * i / 12) * (1.0 - 0.15 * i / 12), h * (1 - math.cos(math.pi * i / 12)) / 2) for i in range(13)]
    return [(solid(prof[1:-1], p["seg"]), "egg")]


def sausage(p, R):
    L, r = 0.15 * p["width"], 0.013 * p["height"]
    n, bend = 5, 0.02 * R.random() + 0.01
    pts = [((i / n - 0.5) * L, bend * math.sin(math.pi * i / n), r) for i in range(n + 1)]
    parts = [geo.rod(pts[i], pts[i + 1], r, 10) for i in range(n)] + [geo.sphere(r, 10, q) for q in pts]
    return [(geo.union(parts), "sausage")]


# ------------------------------------------------------------------ small stuff
def book(p, R):
    w, d, t = 0.15 * p["width"], 0.22 * p["width"], (0.02 + 0.03 * R.random()) * p["height"]
    c = 0.002
    cover = geo.union([geo.boxc(w, d, c), geo.boxc(w, d, c, z0=t - c), geo.boxc(c * 2, d, t, cx=-w / 2 + c)])
    pages = geo.boxc(w - 0.006, d - 0.006, t - 2 * c, cx=0.001, z0=c)
    return [(cover, "cover"), (pages, "paper")]


def candle(p, R):
    r, h = 0.02 * p["width"], 0.12 * p["height"]
    body = geo.cyl(r, h, p["seg"])
    wick = geo.cyl(0.0012, 0.012, 6, h)
    holder = solid([(r * 2.2, 0), (r * 2.2, 0.004), (r * 1.25, 0.006), (r * 1.25, 0.02)], p["seg"])
    return [(body.translate([0, 0, 0.006]), "wax"), (wick.translate([0, 0, 0.006]), "wick"), (holder, "metal")]


def crate(p, R):
    w, d, h = 0.3 * p["width"], 0.2 * p["width"], 0.15 * p["height"]
    body = geo.subtract(geo.boxc(w, d, h), [geo.boxc(w - 0.004, d - 0.004, h, z0=0.003)])
    flaps = [geo.boxc(w, 0.002, d / 2, cy=s * (d / 2 - 0.001), z0=h).rotate([s * -20, 0, 0]) for s in (-1, 1)]
    return [(geo.union([body]), "cardboard")] + ([(geo.union(flaps), "cardboard")] if R.random() < 0.5 else [])


def hammer(p, R):
    L = 0.30 * p["width"]
    hnd = geo.boxc(L, 0.022, 0.028)
    head = geo.boxc(0.03, 0.10 * p["height"], 0.028, cx=L / 2 - 0.02)
    return [(hnd.translate([-0.02, 0, 0]), "wood"), (head.translate([-0.02, 0, 0]), "dark_metal")]


def screwdriver(p, R):
    L = 0.2 * p["width"]
    grip = solid([(0.014, 0), (0.016, 0.03), (0.014, 0.09), (0.006, 0.1)], 10)
    shaft = geo.cyl(0.0035, L - 0.1, 8, 0.1)
    tip = geo.boxc(0.007, 0.0015, 0.012, z0=L - 0.002)
    tool = geo.union([shaft, tip])
    rot = lambda m: m.rotate([0, 90, 0]).translate([-L / 2, 0, 0.016])  # lying on its side
    return [(rot(grip), "red_paint"), (rot(tool), "metal")]


def wrench(p, R):
    L, t = 0.2 * p["width"], 0.005
    bar = geo.boxc(L, 0.016, t)
    jaw = geo.subtract(geo.cyl(0.02, t, 16, cx=L / 2), [geo.boxc(0.026, 0.014, t * 3, cx=L / 2 + 0.012, z0=-t)])
    ring = geo.subtract(geo.cyl(0.017, t, 16, cx=-L / 2), [geo.cyl(0.009, t * 3, 6, -t, cx=-L / 2)])
    return [(geo.union([bar, jaw, ring]), "metal")]


KINDS = {
    "dishes": {"plate": ("Тарелка", plate), "bowl": ("Миска", bowl), "cup": ("Чашка с блюдцем", cup), "mug": ("Кружка", mug),
               "glass": ("Стакан/бокал", glass), "bottle": ("Бутылка", bottle), "jug": ("Кувшин", jug), "pot": ("Кастрюля", pot),
               "pan": ("Сковорода", pan), "kettle": ("Чайник", kettle), "vase": ("Ваза", vase)},
    "food": {"apple": ("Яблоко", apple), "bread": ("Батон", bread), "cheese": ("Кусок сыра", cheese), "pizza": ("Пицца", pizza),
             "cake": ("Торт", cake), "egg": ("Яйцо", egg), "sausage": ("Сосиска", sausage)},
    "stuff": {"book": ("Книга", book), "candle": ("Свеча", candle), "box": ("Коробка", crate), "hammer": ("Молоток", hammer),
              "screwdriver": ("Отвёртка", screwdriver), "wrench": ("Гаечный ключ", wrench)},
}
GROUPS = {"dishes": "Посуда", "food": "Еда", "stuff": "Мелочи"}
FUNCS = {k: v for g in KINDS.values() for k, v in g.items()}
DEFAULTS = {"size": 1.0, "width": 1.0, "height": 1.0, "seed": 1, "seg": 24, "color": ""}


def catalog():
    return {"groups": [{"id": g, "title": GROUPS[g], "kinds": [{"id": k, "title": t} for k, (t, _) in KINDS[g].items()]} for g in KINDS],
            "params": DEFAULTS, "materials": sorted(MATS)}


def build(kind: str, params: dict | None = None):
    if kind not in FUNCS:
        raise KeyError(f"unknown item kind {kind}; known: {', '.join(FUNCS)}")
    p = {**DEFAULTS, **(params or {})}
    p["seg"] = int(min(64, max(8, p["seg"])))
    R = random.Random(int(p["seed"]))
    parts = FUNCS[kind][1](p, R)
    s = float(p["size"])
    out = []
    for m, mat in parts:
        m = m.scale([s, s, s])
        out.append((m, mat))
    lo = np.min([geo.bbox(m)[0] for m, _ in out], axis=0)
    hi = np.max([geo.bbox(m)[1] for m, _ in out], axis=0)
    c = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])  # origin at bottom centre
    out = [(m.translate(list(-c)), mat) for m, mat in out]
    return out, {"kind": kind, "size_m": [round(float(x), 3) for x in hi - lo], "params": p}


def export_glb(kind: str, params: dict | None, path: Path) -> dict:
    parts, info = build(kind, params)
    main = (params or {}).get("color") or ""
    first = parts[0][1]
    scene = trimesh.Scene()
    tris = 0
    bymat: dict[str, list] = {}
    for m, mat in parts:
        bymat.setdefault(mat, []).append(m)
    for mat, ms in bymat.items():
        mesh = geo.union(ms).to_mesh()
        V = np.asarray(mesh.vert_properties)[:, :3]
        F = np.asarray(mesh.tri_verts)
        V = V[:, [0, 2, 1]] * [1, 1, -1]  # Z-up -> Y-up
        rgb, met, rough, a = MATS.get(mat, MATS["ceramic"])
        if main and mat == first:
            rgb = _hex(main)
        pbr = trimesh.visual.material.PBRMaterial(name=mat, baseColorFactor=[*rgb, a], metallicFactor=met, roughnessFactor=rough,
                                                  alphaMode="BLEND" if a < 1 else "OPAQUE", doubleSided=False)
        tm = trimesh.Trimesh(V, F, process=False)
        tm.visual = trimesh.visual.TextureVisuals(material=pbr)
        scene.add_geometry(tm, node_name=mat, geom_name=mat)
        tris += len(F)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.export(path)
    return {**info, "tris": tris, "materials": list(bymat)}
