"""Structural volumes: blocks, walls, towers, log cabins, platforms, stairs, primitives."""
from __future__ import annotations

import math

import numpy as np

from .. import geo as g
from ..registry import Anchor, P, Part, element
from .common import FP_SHAPES, face_anchors, footprint, round_face_anchors, top_anchor

FP_PARAMS = {
    "w": P(10.0, "width along local X (m)", min=0.5),
    "d": P(8.0, "depth along local Y (m)", min=0.5),
    "shape": P("rect", "footprint shape (w x d box): round/oval towers, rounded corners, L/U/T wings, wedge "
                       "(flatiron), bow (curved front), cut_corner (corner house) ...", FP_SHAPES),
    "shape_k": P(0.4, "proportion of the shape feature: L/U/T notch, corner radius, taper, bulge (0.1-0.8)"),
    "flip": P(False, "mirror the shape left-right (asymmetric buildings)"),
    "poly": P(None, "optional footprint polygon [[x,y],...] instead of w/d/shape"),
}


@element("block", "structure", "Building volume: hollow walls, floor slabs, plinth. The base of almost every building.",
         {**FP_PARAMS,
          "floors": P(2, "number of floors", min=1, max=200),
          "floor_h": P(3.2, "floor-to-floor height (m)"),
          "wall_t": P(0.5, "wall thickness (m)"),
          "plinth_h": P(0.6, "plinth (base) height (m), 0 = none"),
          "plinth_out": P(0.06, "how far the plinth projects (m)"),
          "slab_t": P(0.25, "floor slab thickness"),
          "hollow": P(True, "hollow interior (rooms per floor)"),
          "top_slab": P(True, "close the top with a slab"),
          "material": P("wall", "wall material/role"),
          "plinth_material": P("plinth", "plinth material/role")},
         attach="any", title_ru="Объём здания",
         anchors="top, base, floor0..N (top-type), face0..N / front,right,back,left (face-type)")
def block(p, ctx):
    fp = footprint(p)
    floors, fh, t = int(p["floors"]), float(p["floor_h"]), float(p["wall_t"])
    ph = float(p["plinth_h"])
    H = ph + floors * fh
    cs = g.poly(fp)
    wall_mat, inner_mat = ctx.mat(p["material"]), ctx.mat("interior")
    solid = g.extrude(cs, H)
    cav = []
    if p["hollow"]:
        inner = g.offset2(cs, -t)
        if not inner.is_empty():
            st = float(p["slab_t"])
            for i in range(floors):
                z0 = ph + i * fh + (st if (i > 0 or ph < st) else 0.0)  # always keep a floor slab
                z1 = ph + (i + 1) * fh
                if i == floors - 1:
                    z1 = H - st if p["top_slab"] else H + 1.0
                if z1 - z0 > 0.2:
                    cav.append(g.tag(g.extrude(inner, z1 - z0, z0), inner_mat))
    solid = g.subtract(g.tag(solid, wall_mat), cav)
    part = Part().add(solid, wall_mat)
    if ph > 0:
        # a ring around the walls, never under the rooms: its top would lie in the floor plane and the union would
        # split the floor into random triangles of both materials. Always projects a little -> no flush coplanar faces.
        plinth = g.extrude(g.offset2(cs, max(float(p["plinth_out"]), 0.01)), ph)
        inner = g.offset2(cs, -t)
        if p["hollow"] and not inner.is_empty():
            plinth = g.subtract(plinth, [g.extrude(inner, ph + 1.0, -0.5)])
        part.add(plinth, ctx.mat(p["plinth_material"]))
    rnd = p.get("shape") in ("round", "oval") and not p.get("poly")
    if rnd:  # curved wall: face anchors on tangent planes, round roofs (domes/cones) fit the top
        rx, ry = (min(float(p["w"]), float(p["d"])) / 2,) * 2 if p["shape"] == "round" else (float(p["w"]) / 2, float(p["d"]) / 2)
        part.anchors.update(round_face_anchors(rx, ry, H, t, floors, fh, ph))
        part.anchors["top"] = top_anchor(fp, H, H, floors, fh, round=p["shape"] == "round", r=rx)
    else:
        part.anchors.update(face_anchors(fp, H, t, floors, fh, ph))
        part.anchors["top"] = top_anchor(fp, H, H, floors, fh)
    part.anchors["base"] = top_anchor(fp, 0.0, 0.0, floors, fh)
    for i in range(floors + 1):
        part.anchors[f"floor{i}"] = top_anchor(fp, ph + i * fh, ph + i * fh, floors, fh)
    inner_cs = g.offset2(cs, -t)
    if p["hollow"] and not inner_cs.is_empty():  # for interior generation
        ipoly = max(inner_cs.to_polygons(), key=len)
        part.anchors["inner"] = top_anchor([(float(x), float(y)) for x, y in ipoly], 0.0, H, floors, fh,
                                           plinth_h=ph, slab_t=float(p["slab_t"]), wall_t=t)
    return part


@element("wall", "structure", "Free-standing straight wall (fence wall, city wall, ruin). Origin at the left end.",
         {"length": P(10.0, "length along X"), "h": P(3.0, "height"), "t": P(0.6, "thickness"),
          "material": P("wall", ""), "battlements": P(False, "add crenellations on top"),
          "merlon_w": P(0.8, ""), "merlon_h": P(0.8, ""), "walkway": P(False, "walkway ledge on the inner side")},
         title_ru="Стена", anchors="front, back (face), top")
def wall(p, ctx):
    L, H, t = float(p["length"]), float(p["h"]), float(p["t"])
    mat = ctx.mat(p["material"])
    part = Part().add(g.box(0, -t / 2, 0, L, t / 2, H), mat)
    if p["battlements"]:
        mw, mh = float(p["merlon_w"]), float(p["merlon_h"])
        n = max(1, int(L / (mw * 2)))
        step = L / n
        for i in range(n):
            x = i * step + step / 4
            part.add(g.box(x, -t / 2, H - 0.01, x + min(mw, step / 2), t / 2, H + mh), mat)
    if p["walkway"]:
        part.add(g.box(0, t / 2 - 0.01, H - 1.2, L, t / 2 + 0.8, H - 1.0), mat)
    part.anchors["front"] = Anchor(g.mat_frame([0, -t / 2, 0], [1, 0, 0], [0, -1, 0], [0, 0, 1]), "face", w=L, h=H, depth=t)
    part.anchors["back"] = Anchor(g.mat_frame([L, t / 2, 0], [-1, 0, 0], [0, 1, 0], [0, 0, 1]), "face", w=L, h=H, depth=t)
    part.anchors["top"] = top_anchor([(0, -t / 2), (L, -t / 2), (L, t / 2), (0, t / 2)], H, H)
    return part


def ngon(n, r, rot=0.0):
    off = math.pi / n if n in (4, 8) else 0.0
    return [(r * math.cos(off + rot + 2 * math.pi * i / n), r * math.sin(off + rot + 2 * math.pi * i / n)) for i in range(n)]


@element("tower", "structure", "Tower: round / square / polygonal, hollow, optional battered (sloped) base.",
         {"shape": P("round", "", ["round", "square", "octagon", "hexagon"]),
          "r": P(3.0, "outer radius (half-width for square)"), "h": P(15.0, "height"),
          "wall_t": P(0.8, ""), "floors": P(4, ""), "batter": P(0.0, "extra radius at the base (sloped skirt)"),
          "batter_h": P(2.0, ""), "material": P("wall", ""), "faces": P(8, "anchor faces for round towers")},
         title_ru="Башня", anchors="top, face0..N")
def tower(p, ctx):
    r, H, t = float(p["r"]), float(p["h"]), float(p["wall_t"])
    shape = p["shape"]
    # round: >= 24 sides even in low-poly, so windows on the tangent faces sit on the wall (gap < 1-2 cm)
    n = {"square": 4, "octagon": 8, "hexagon": 6}.get(shape, max(24, ctx.seg(r, 10, 64)))
    fp = ngon(n, r if shape != "square" else r * math.sqrt(2))
    mat = ctx.mat(p["material"])
    cs = g.poly(fp)
    solid = g.tag(g.extrude(cs, H), mat)
    floors = int(p["floors"])
    fh = H / floors
    # cavities leave a floor slab and a closed top (domes/roofs placed on top always have something to sit on)
    cav = [g.tag(g.extrude(g.offset2(cs, -t), fh - 0.3 - (0.3 if i == floors - 1 else 0), i * fh + 0.3), ctx.mat("interior"))
           for i in range(floors)]
    part = Part().add(g.subtract(solid, cav), mat)
    if float(p["batter"]) > 0:
        b, bh = float(p["batter"]), float(p["batter_h"])
        k = (r + b) / r
        part.add(g.extrude(cs, bh, 0, (1 / k, 1 / k)).scale([k, k, 1]), mat)
    if shape == "round":
        k = int(p["faces"])
        # faces are tangent planes of the round wall (circumscribed k-gon)
        part.anchors.update(face_anchors(ngon(k, r / math.cos(math.pi / k)), H, t, floors, fh, 0, names=False))
    else:
        part.anchors.update(face_anchors(fp, H, t, floors, fh, 0, names=False))
    part.anchors["top"] = top_anchor(fp, H, H, floors, fh, round=shape == "round", r=r)
    return part


@element("log_cabin", "structure", "Log crib (сруб): stacked round logs with corner overhangs (в обло) or flush corners (в лапу).",
         {"w": P(6.0, ""), "d": P(6.0, ""), "h": P(3.0, "wall height"), "log_d": P(0.26, "log diameter"),
          "corner": P("obla", "corner joint", ["obla", "lapa"]), "overhang": P(0.3, "log ends beyond the corner"),
          "material": P("log", ""), "floors": P(1, "")},
         title_ru="Сруб", anchors="top, front/right/back/left (face)")
def log_cabin(p, ctx):
    w, d, H, D = float(p["w"]), float(p["d"]), float(p["h"]), float(p["log_d"])
    r = D / 2
    ov = float(p["overhang"]) if p["corner"] == "obla" else 0.0
    mat = ctx.mat(p["material"])
    seg = 6 if ctx.low else 14
    step = D * 0.82
    n = max(2, int(math.ceil(H / step)))
    logs = []
    for i in range(n):
        zx = r + i * step
        zy = zx + step / 2
        for sy in (-1, 1):
            if zx - r < H:
                logs.append(g.rod([-w / 2 - ov, sy * (d / 2 - r), zx], [w / 2 + ov, sy * (d / 2 - r), zx], r, seg))
        for sx in (-1, 1):
            if zy - r < H:
                logs.append(g.rod([sx * (w / 2 - r), -d / 2 - ov, zy], [sx * (w / 2 - r), d / 2 + ov, zy], r, seg))
    # inner core keeps the crib sealed and gives a clean top for the roof
    core = g.boxc(w - D * 0.9, d - D * 0.9, H, 0, 0, 0) - g.boxc(w - D * 1.6, d - D * 1.6, H + 1, 0, 0, 0.3)
    walls = g.union([g.tag(l, mat) for l in logs] + [g.tag(core, mat)])
    walls = walls.trim_by_plane([0, 0, -1], -H)  # flat top at H
    part = Part().add(walls, mat)
    part.add(g.boxc(w - D, d - D, 0.3, 0, 0, 0), ctx.mat("floor"))
    fp = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    part.anchors.update(face_anchors(fp, H, D, int(p["floors"]), H / int(p["floors"]), 0.0))
    part.anchors["top"] = top_anchor(fp, H, H)
    return part


@element("platform", "structure", "Stepped platform / stylobate / podium / foundation slab.",
         {**FP_PARAMS, "h": P(0.5, "total height"), "steps": P(1, "number of steps (all around)"),
          "step_out": P(0.4, "tread depth"), "material": P("stairs", "")},
         title_ru="Платформа / стилобат", anchors="top")
def platform(p, ctx):
    fp = footprint(p)
    n, H, so = int(p["steps"]), float(p["h"]), float(p["step_out"])
    mat = ctx.mat(p["material"])
    cs = g.poly(fp)
    part = Part()
    for i in range(n):
        out = so * (n - 1 - i)
        part.add(g.extrude(g.offset2(cs, out), H * (i + 1) / n), mat)
    part.anchors["top"] = top_anchor(fp, H, H)
    part.anchors.update(face_anchors(fp, H, 0.5, 1, H, 0))
    return part


@element("stairs", "structure", "Straight stairs. On a face: starts at the face and descends outward to the ground "
         "(set `at` v = top level). Free: rises along +Y.",
         {"w": P(2.0, "width"), "n": P(0, "steps count (0 = from height)"), "rise": P(0.16, ""), "run": P(0.3, ""),
          "h": P(0.6, "total height to climb"), "material": P("stairs", ""), "cheeks": P(False, "side walls")},
         title_ru="Лестница / ступени")
def stairs(p, ctx):
    H = float(p["h"])
    n = int(p["n"]) or max(1, round(H / float(p["rise"])))
    rise, run, w = H / n, float(p["run"]), float(p["w"])
    mat = ctx.mat(p["material"])
    part = Part()
    on_face = ctx.anchor is not None and ctx.anchor.kind == "face"
    for i in range(n):
        if on_face:  # top step touches the wall at z=0 (anchor level), steps go down and out
            y1 = run * (i + 1)
            part.add(g.box(-w / 2, -0.1, -H, w / 2, y1, -rise * i), mat)
        else:
            part.add(g.box(-w / 2, run * i, 0, w / 2, n * run, rise * (i + 1)), mat)
    if p["cheeks"]:
        L = n * run
        for sx in (-1, 1):
            x = sx * (w / 2 + 0.12)
            if on_face:
                part.add(g.hull([[x - .12, -.1, -H], [x + .12, -.1, -H], [x - .12, L, -H], [x + .12, L, -H],
                                 [x - .12, -.1, .3], [x + .12, -.1, .3], [x - .12, L, -H + .3], [x + .12, L, -H + .3]]), mat)
    return part


# ------------------------------------------------------------------ primitives (anything custom)
@element("box", "primitive", "Box. Origin at bottom centre.", {"w": P(1.0, ""), "d": P(1.0, ""), "h": P(1.0, ""),
         "material": P("wall", "")}, title_ru="Параллелепипед", anchors="top, front/right/back/left")
def prim_box(p, ctx):
    w, d, h = float(p["w"]), float(p["d"]), float(p["h"])
    part = Part().add(g.boxc(w, d, h), ctx.mat(p["material"]))
    fp = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    part.anchors.update(face_anchors(fp, h, min(w, d) / 2, 1, h, 0))
    part.anchors["top"] = top_anchor(fp, h, h)
    return part


@element("cylinder", "primitive", "Cylinder / cone frustum / prism (sides>0). Origin at bottom centre.",
         {"r": P(0.5, ""), "r_top": P(None, "top radius (cone)"), "h": P(1.0, ""), "sides": P(0, "0 = smooth"),
          "material": P("wall", ""), "axis": P("z", "", ["z", "x", "y"])}, title_ru="Цилиндр / конус", anchors="top")
def prim_cyl(p, ctx):
    r, h = float(p["r"]), float(p["h"])
    rt = r if p["r_top"] is None else float(p["r_top"])
    n = int(p["sides"]) or ctx.seg(r)
    m = g.cyl(r, h, n, 0, rt)
    if p["axis"] == "x":
        m = m.rotate([0, 90, 0])
    elif p["axis"] == "y":
        m = m.rotate([-90, 0, 0])
    part = Part().add(m, ctx.mat(p["material"]))
    part.anchors["top"] = top_anchor(g.ccw([(rt * math.cos(a), rt * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]), h, h, round=True, r=rt)
    return part


@element("sphere", "primitive", "Sphere / ellipsoid (sx,sy,sz scale). Origin at centre.",
         {"r": P(0.5, ""), "scale": P([1, 1, 1], "ellipsoid scale"), "material": P("wall", ""),
          "cut_below": P(False, "keep only the upper half")}, title_ru="Сфера")
def prim_sphere(p, ctx):
    m = g.sphere(float(p["r"]), ctx.seg(float(p["r"]))).scale(list(p["scale"]))
    if p["cut_below"]:
        m = m.trim_by_plane([0, 0, 1], 0)
    return Part().add(m, ctx.mat(p["material"]))


@element("prism", "primitive", "Extruded polygon (any outline) of height h.",
         {"points": P([[0, 0], [2, 0], [1, 2]], "outline [[x,y],...]"), "h": P(1.0, ""),
          "taper": P(1.0, "top scale (pyramid if 0.01)"), "material": P("wall", "")}, title_ru="Призма", anchors="top")
def prim_prism(p, ctx):
    fp = g.ccw(p["points"])
    t = float(p["taper"])
    part = Part().add(g.extrude(g.poly(fp), float(p["h"]), 0, (t, t)), ctx.mat(p["material"]))
    part.anchors["top"] = top_anchor(fp, float(p["h"]), float(p["h"]))
    part.anchors.update(face_anchors(fp, float(p["h"]), 0.3, 1, float(p["h"]), 0))
    return part


@element("revolve", "primitive", "Lathe/revolved profile: [[r,z],...] around the Z axis (vases, balusters, finials, domes).",
         {"profile": P([[0, 0], [0.5, 0], [0.3, 1], [0, 1.2]], "[[r,z],...]"), "sides": P(0, "0 = smooth"),
          "material": P("wall", "")}, title_ru="Тело вращения")
def prim_revolve(p, ctx):
    prof = p["profile"]
    rmax = max(abs(a) for a, _ in prof)
    pts = list(prof)
    if pts[0][0] != 0:
        pts.insert(0, [0, pts[0][1]])
    if pts[-1][0] != 0:
        pts.append([0, pts[-1][1]])
    return Part().add(g.revolve(pts, int(p["sides"]) or ctx.seg(rmax)), ctx.mat(p["material"]))


@element("hull", "primitive", "Convex hull of 3D points — quick way to make wedges, roofs of any shape, ramps.",
         {"points": P([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], "[[x,y,z],...]"), "material": P("wall", "")},
         title_ru="Выпуклая оболочка")
def prim_hull(p, ctx):
    return Part().add(g.hull(p["points"]), ctx.mat(p["material"]))


@element("beam", "primitive", "Beam/post between two points (timber, steel, log if round).",
         {"p0": P([0, 0, 0], ""), "p1": P([0, 0, 3], ""), "w": P(0.2, ""), "h": P(0.2, ""),
          "round": P(False, ""), "material": P("timber", "")}, title_ru="Балка / столб")
def prim_beam(p, ctx):
    if p["round"]:
        m = g.rod(p["p0"], p["p1"], float(p["w"]) / 2, ctx.seg(float(p["w"]), 6, 16))
    else:
        m = g.beam(p["p0"], p["p1"], float(p["w"]), float(p["h"]))
    return Part().add(m, ctx.mat(p["material"]))


@element("mound", "structure", "Earth mound / berm / embankment (half ellipsoid). Used for dugouts, burial mounds, ramparts.",
         {"w": P(8.0, ""), "d": P(8.0, ""), "h": P(1.5, ""), "material": P("ground", ""),
          "ring": P(0.0, "if >0: hollow ring berm with this inner opening fraction")},
         title_ru="Земляная насыпь")
def mound(p, ctx):
    w, d, h = float(p["w"]), float(p["d"]), float(p["h"])
    m = g.sphere(1.0, ctx.seg(max(w, d) / 2, 10, 48)).scale([w / 2, d / 2, h]).trim_by_plane([0, 0, 1], 0)
    if float(p["ring"]) > 0:
        k = float(p["ring"])
        m = m - g.boxc(w * k, d * k, h * 3, 0, 0, -h)
    return Part().add(m, ctx.mat(p["material"]))
