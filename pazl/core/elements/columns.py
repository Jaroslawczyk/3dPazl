"""Classical orders: columns, colonnades/porticoes, pilasters."""
from __future__ import annotations

import math

from .. import geo as g
from ..registry import P, Part, element
from .common import grid_positions

ORDERS = ["doric", "tuscan", "ionic", "corinthian", "composite", "egyptian", "plain", "square", "byzantine", "wood_post"]


def column_solid(order, h, r, ctx, fluted=True):
    """Column with base and capital, origin at bottom centre, total height h."""
    low = ctx.low
    seg = ctx.seg(r, 8, 32)
    parts = []
    if order == "wood_post":
        return [g.boxc(r * 2, r * 2, h)]
    if order == "square":
        parts.append(g.boxc(r * 2.4, r * 2.4, r * 0.4))
        parts.append(g.boxc(r * 2, r * 2, h - r * 0.8, 0, 0, r * 0.4 - 0.01))
        parts.append(g.boxc(r * 2.5, r * 2.5, r * 0.42, 0, 0, h - r * 0.42))
        return parts
    zb = 0.0
    if order not in ("doric", "egyptian"):
        parts.append(g.boxc(r * 2.6, r * 2.6, r * 0.35))
        parts.append(g.cyl(r * 1.15, r * 0.3, seg, r * 0.33))
        zb = r * 0.6
    cap_h = {"doric": r * 0.7, "tuscan": r * 0.7, "ionic": r * 0.8, "corinthian": r * 2.2, "composite": r * 2.2,
             "egyptian": r * 1.6, "plain": r * 0.5, "byzantine": r * 1.2}[order]
    sh = h - zb - cap_h
    top_r = r * 0.84
    shaft = g.cyl(r, sh + 0.02, seg, zb - 0.01, top_r)
    if fluted and not low and order in ("doric", "ionic", "corinthian", "composite"):
        n = 20 if order == "doric" else 24
        cuts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            fr = r * 0.12
            cuts.append(g.cyl(fr, sh * 0.96, 6, zb + sh * 0.02, fr * 0.84, math.cos(a) * r * 1.02, math.sin(a) * r * 1.02))
        shaft = shaft - g.union(cuts)
    parts.append(shaft)
    z = zb + sh
    if order in ("doric", "tuscan"):
        parts.append(g.cyl(top_r, cap_h * 0.5, seg, z - 0.01, r * 1.25))
        parts.append(g.boxc(r * 2.7, r * 2.7, cap_h * 0.55, 0, 0, z + cap_h * 0.45))
    elif order == "ionic":
        parts.append(g.cyl(top_r, cap_h * 0.4, seg, z - 0.01, r * 1.05))
        parts.append(g.boxc(r * 2.4, r * 1.6, cap_h * 0.25, 0, 0, z + cap_h * 0.75))
        for sx in (-1, 1):
            parts.append(g.rod([sx * r * 1.05, -r * 0.8, z + cap_h * 0.4], [sx * r * 1.05, r * 0.8, z + cap_h * 0.4], r * 0.38, ctx.seg(r * .4, 8, 16)))
    elif order in ("corinthian", "composite", "byzantine"):
        parts.append(g.cyl(top_r, cap_h * 0.82, seg, z - 0.01, r * 1.3))
        if not low:
            for ring, k in ((0.15, 8), (0.45, 8)):
                for i in range(k):
                    a = 2 * math.pi * (i + ring) / k
                    parts.append(g.sphere(r * 0.22, 8, (math.cos(a) * r * (0.95 + ring * 0.4), math.sin(a) * r * (0.95 + ring * 0.4),
                                                           z + cap_h * (0.15 + ring))).scale([1, 1, 1]))
        parts.append(g.boxc(r * 2.8, r * 2.8, cap_h * 0.24, 0, 0, z + cap_h * 0.76))
    elif order == "egyptian":
        parts.append(g.cyl(top_r, cap_h * 0.85, seg, z - 0.01, r * 1.6))
        parts.append(g.boxc(r * 2.0, r * 2.0, cap_h * 0.2, 0, 0, z + cap_h * 0.8))
    else:  # plain
        parts.append(g.boxc(r * 2.4, r * 2.4, cap_h, 0, 0, z))
    return parts


COL_PARAMS = {"order": P("doric", "", ORDERS), "h": P(6.0, "total column height incl. base & capital"),
              "r": P(0.4, "shaft radius at the base"), "fluted": P(True, ""), "material": P("column", "")}


@element("column", "columns", "Single column of a classical order (or plain/square/wooden post). Origin at bottom centre.",
         COL_PARAMS, title_ru="Колонна")
def column(p, ctx):
    part = Part()
    for s in column_solid(p["order"], float(p["h"]), float(p["r"]), ctx, p["fluted"]):
        part.add(s, ctx.mat(p["material"]))
    return part


@element("colonnade", "columns", "Row of columns with entablature. On a face with depth>0 it becomes a portico: "
         "ceiling to the wall, optional pediment (fronton) with its own little roof, steps. Free: along local X.",
         {**COL_PARAMS, "count": P(6, ""), "length": P(None, "span between first & last column centre (default face width - 2*margin)"),
          "margin": P(1.0, "start offset along the face"), "depth": P(3.0, "distance of the columns from the wall"),
          "ent_h": P(None, "entablature height (default 0.22*h)"), "pediment": P(True, ""), "pediment_pitch": P(15.0, ""),
          "steps": P(3, "steps of the stylobate"), "step_h": P(0.18, ""), "roof_material": P("roof", ""),
          "trim_material": P("trim", ""), "tympanum": P(None, "subject of a relief/mosaic in the pediment (unique texture)")},
         title_ru="Колоннада / портик")
def colonnade(p, ctx):
    a = ctx.anchor
    on_face = a is not None and a.kind == "face"
    n = max(1, int(p["count"]))
    h, r = float(p["h"]), float(p["r"])
    margin = float(p["margin"])
    L = float(p["length"]) if p["length"] else ((a.w - 2 * margin) if on_face else 10.0)
    depth = float(p["depth"]) if on_face else 0.0
    eh = float(p["ent_h"]) if p["ent_h"] else h * 0.22
    sh = float(p["step_h"])
    ns = int(p["steps"])
    zc = ns * sh
    cmat, tmat = ctx.mat(p["material"]), ctx.mat(p["trim_material"])
    part = Part()
    xs = [margin + (L * i / (n - 1) if n > 1 else L / 2) for i in range(n)] if on_face else \
         [(L * i / (n - 1) if n > 1 else 0.0) for i in range(n)]
    x0, x1 = xs[0] - r * 1.6, xs[-1] + r * 1.6
    for x in xs:
        for s in column_solid(p["order"], h, r, ctx, p["fluted"]):
            part.add(s.translate([x, depth, zc - 0.05]), cmat)
    yb0 = -0.1 if on_face else -r * 1.4
    yb1 = depth + r * 1.4
    for i in range(ns):
        out = (ns - i) * 0.35
        part.add(g.box(x0 - out, yb0, i * sh, x1 + out, yb1 + out, (i + 1) * sh), ctx.mat("stairs"))
    ze = zc + h
    # architrave + frieze + cornice
    part.add(g.box(x0, yb0, ze - 0.06, x1, yb1, ze + eh * 0.75), tmat)
    part.add(g.box(x0 - 0.15, yb0, ze + eh * 0.75, x1 + 0.15, yb1 + 0.15, ze + eh), tmat)
    if not ctx.low:  # triglyph/dentil hint line
        part.add(g.box(x0, yb1 - 0.01, ze + eh * 0.35, x1, yb1 + 0.04, ze + eh * 0.4), tmat)
    if p["pediment"]:
        span = (x1 - x0) / 2 + 0.15
        ph = span * math.tan(math.radians(float(p["pediment_pitch"])))
        cx = (x0 + x1) / 2
        zt = ze + eh
        tri = g.hull([[cx - span, yb0, zt - 0.01], [cx + span, yb0, zt - 0.01], [cx, yb0, zt + ph],
                      [cx - span, yb1 + 0.15, zt - 0.01], [cx + span, yb1 + 0.15, zt - 0.01], [cx, yb1 + 0.15, zt + ph]])
        part.add(tri, tmat)
        o = 0.25
        k = ph / span
        roofv = g.hull([[cx - span - o, yb0, zt - o * k], [cx + span + o, yb0, zt - o * k], [cx, yb0, zt + ph + 0.12],
                        [cx - span - o, yb1 + 0.3, zt - o * k], [cx + span + o, yb1 + 0.3, zt - o * k], [cx, yb1 + 0.3, zt + ph + 0.12]])
        part.add(roofv - roofv.translate([0, 0, -0.2]) - tri.translate([0, 0, -0.0]), ctx.mat(p["roof_material"]))
        if p["tympanum"]:
            art = ctx.art("relief", p["tympanum"])
            inner = g.poly([(cx - span * 0.8, zt + 0.15), (cx + span * 0.8, zt + 0.15), (cx, zt + ph * 0.8)])
            part.add(g.prism_xz(inner, yb1 + 0.1, yb1 + 0.2), art)
    return part


@element("pilasters", "columns", "Flat pilasters (lesenes) on a face: vertical strips with base and capital.",
         {"w": P(0.6, ""), "depth": P(0.12, ""), "h": P(None, "height (default face height)"), "v0": P(0.0, "start height"),
          "cols": P("auto", ""), "us": P(None, ""), "margin": P(0.3, ""), "capital": P(True, ""), "material": P("trim", "")},
         attach="face", title_ru="Пилястры / лопатки")
def pilasters(p, ctx):
    a = ctx.anchor
    w, dp = float(p["w"]), float(p["depth"])
    H = float(p["h"]) if p["h"] else (a.h if a else 6.0) - float(p["v0"])
    part = Part()
    m = ctx.mat(p["material"])
    q = {**p, "rows": 1, "vs": [p["v0"]]}
    if q.get("cols") == "auto" and not q.get("us"):
        q["cols"] = max(2, int((a.w if a else 10) / 4) + 1)
        q["margin"] = 0
        W = a.w if a else 10
        q["us"] = [w / 2 + (W - w) * i / (q["cols"] - 1) for i in range(q["cols"])]
    for u, v, c, r in grid_positions(q, a, w):
        part.add(g.box(u - w / 2, -0.05, v, u + w / 2, dp, v + H), m)
        if p["capital"]:
            part.add(g.box(u - w / 2 - 0.06, -0.05, v + H - 0.25, u + w / 2 + 0.06, dp + 0.06, v + H), m)
            part.add(g.box(u - w / 2 - 0.05, -0.05, v, u + w / 2 + 0.05, dp + 0.05, v + 0.3), m)
    return part
