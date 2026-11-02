"""Facade & perimeter decor: cornices, battlements, buttresses, quoins, half-timbering, panel seams,
balconies, canopies, curtain walls, balustrades, fences, pediments."""
from __future__ import annotations

import math

import numpy as np

from .. import geo as g
from ..registry import P, Part, element
from .common import grid_positions, opening_shape


def edges(fp):
    n = len(fp)
    for i in range(n):
        x0, y0 = fp[i]
        x1, y1 = fp[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-6:
            continue
        d = np.array([(x1 - x0) / L, (y1 - y0) / L, 0])
        nrm = np.array([d[1], -d[0], 0])
        yield np.array([x0, y0, 0.0]), d, nrm, L


def along(p0, d, nrm, u, out, z):
    return p0 + d * u + nrm * out + np.array([0, 0, z])


def _fp(ctx):
    a = ctx.anchor
    return a.footprint if (a and a.footprint) else [(-5, -4), (5, -4), (5, 4), (-5, 4)]


@element("cornice", "decor", "Cornice / string course / eave moulding around a `top` (or floorN) anchor perimeter. "
         "Occupies z in [-h, 0] relative to the anchor (use offset z to move).",
         {"kind": P("crown", "", ["simple", "crown", "dentil", "corbel", "lombard", "machicolation", "band", "soviet"]),
          "h": P(0.5, "height"), "out": P(0.35, "projection"), "material": P("trim", ""), "spacing": P(0.6, "dentil/corbel spacing")},
         attach="top", title_ru="Карниз / пояс")
def cornice(p, ctx):
    fp = _fp(ctx)
    cs = g.poly(fp)
    h, out, kind = float(p["h"]), float(p["out"]), p["kind"]
    m = ctx.mat(p["material"])
    part = Part()
    inner = g.offset2(cs, -0.15)

    def ring(o, z0, z1):
        part.add(g.extrude(g.offset2(cs, o) - inner, z1 - z0, z0), m)

    if kind in ("simple", "band", "soviet"):
        ring(out if kind != "band" else min(out, 0.1), -h, 0)
    else:
        ring(out * 0.3, -h, -h * 0.55)
        ring(out * 0.65, -h * 0.58, -h * 0.25)
        ring(out, -h * 0.28, 0)
    sp = float(p["spacing"])
    if kind in ("dentil", "corbel", "lombard", "machicolation") and not (ctx.low and kind == "dentil"):
        for p0, d, nrm, L in edges(fp):
            n = max(1, int(L / sp))
            for i in range(n):
                u = (i + 0.5) * L / n
                c = along(p0, d, nrm, u, 0, 0)
                if kind == "dentil":
                    size = (sp * 0.4, out * 0.3, h * 0.25)
                    zc = -h * 0.55 - size[2]
                elif kind == "lombard":
                    shp = opening_shape("arch", sp * 0.8, h * 0.6, 12)
                    ring2 = g.offset2(shp, 0.06) - shp
                    R = g.mat_frame(c - d * 0.0, d, nrm, [0, 0, 1])
                    part.add(g.xf(g.prism_xz(ring2, -0.1, out * 0.25).translate([0, 0, -h * 1.6]), R), m)
                    continue
                else:
                    size = (sp * 0.35, out * (1.0 if kind == "machicolation" else 0.6), h * (1.2 if kind == "machicolation" else 0.6))
                    zc = -h - size[2] + 0.02
                R = g.mat_frame(c, d, nrm, [0, 0, 1])
                part.add(g.xf(g.box(-size[0] / 2, -0.15, zc, size[0] / 2, size[1], zc + size[2] + 0.02), R), m)
    return part


@element("battlements", "decor", "Crenellated parapet (зубцы) around a `top` anchor perimeter. Swallowtail = Kremlin-style merlons.",
         {"h": P(1.4, "parapet height incl. merlons"), "t": P(0.5, "thickness"), "merlon_w": P(0.9, ""),
          "crenel_w": P(0.6, ""), "crenel_h": P(0.6, ""), "out": P(0.0, "projection beyond the wall"),
          "style": P("square", "", ["square", "swallowtail"]), "material": P("wall", "")},
         attach="top", title_ru="Зубцы / парапет")
def battlements(p, ctx):
    fp = _fp(ctx)
    cs = g.poly(fp)
    h, t, out = float(p["h"]), float(p["t"]), float(p["out"])
    mw, cw, ch = float(p["merlon_w"]), float(p["crenel_w"]), float(p["crenel_h"])
    m = ctx.mat(p["material"])
    ringcs = g.offset2(cs, out) - g.offset2(cs, out - t)
    solid = g.tag(g.extrude(ringcs, h, -0.05), m)
    cuts = []
    for p0, d, nrm, L in edges(fp):
        n = max(1, int((L - mw) / (mw + cw)))
        step = (L - mw) / n if n else L
        for i in range(n):
            u = mw + i * step + (step - mw) / 2 if n else L / 2
            u = mw / 2 + i * step + step / 2
            R = g.mat_frame(along(p0, d, nrm, u, 0, 0), d, nrm, [0, 0, 1])
            cuts.append(g.xf(g.box(-cw / 2, -t - 1, h - ch, cw / 2, out + 1, h + 1), R))
            if p["style"] == "swallowtail":
                pass
        if p["style"] == "swallowtail":
            for i in range(n + 1):
                u = mw / 2 + i * step
                R = g.mat_frame(along(p0, d, nrm, u, 0, 0), d, nrm, [0, 0, 1])
                cuts.append(g.xf(g.prism_xz(g.poly([(-0.12, h + 0.01), (0.12, h + 0.01), (0, h - ch * 0.6)]), -t - 1, out + 1), R))
    part = Part().add(g.subtract(solid, [g.tag(c, m) for c in cuts]), m)
    return part


@element("buttresses", "decor", "Buttresses on a face (stepped, optional pinnacle). flying=true adds a flying buttress: "
         "a pier at `fly_dist` and an inclined arch reaching the wall at `fly_h`.",
         {"w": P(0.8, ""), "depth": P(1.2, ""), "h": P(None, "height (default 85% of face)"), "steps": P(2, "setbacks"),
          "cols": P("auto", ""), "us": P(None, ""), "margin": P(0.0, ""), "pinnacle": P(True, ""),
          "flying": P(False, ""), "fly_dist": P(5.0, "pier distance from the wall"), "fly_h": P(None, "where the arch meets the wall"),
          "pier_h": P(None, "pier height"), "material": P("stone", "")},
         attach="face", title_ru="Контрфорсы / аркбутаны")
def buttresses(p, ctx):
    a = ctx.anchor
    W = a.w if a else 10
    H = float(p["h"]) if p["h"] else (a.h if a else 10) * 0.85
    w, dp, ns = float(p["w"]), float(p["depth"]), max(1, int(p["steps"]))
    m = ctx.mat(p["material"])
    part = Part()
    q = {"cols": p["cols"], "us": p["us"], "margin": p["margin"], "rows": 1, "vs": [0]}
    if q["cols"] == "auto" and not q["us"]:
        n = max(2, int(W / 4.5) + 1)
        q["us"] = [w / 2 + (W - w) * i / (n - 1) for i in range(n)]
    for u, v, c, r in grid_positions(q, a, w):
        for i in range(ns):
            z0, z1 = H * i / ns, H * (i + 1) / ns
            dd = dp * (1 - i / ns * 0.5)
            part.add(g.box(u - w / 2, -0.15, z0, u + w / 2, dd, z1 + 0.01), m)
            part.add(g.hull([[u - w / 2, -0.15, z1], [u + w / 2, -0.15, z1], [u - w / 2, dd, z1], [u + w / 2, dd, z1],
                             [u - w / 2, -0.15, z1 + dd * 0.6], [u + w / 2, -0.15, z1 + dd * 0.6]]), m)
        if p["pinnacle"]:
            pw = w * 0.7
            zt = H - 0.05
            part.add(g.boxc(pw, pw, 1.2, u, dp * 0.5, zt), m)
            part.add(g.hull([[u - pw * .6, dp * .5 - pw * .6, zt + 1.15], [u + pw * .6, dp * .5 - pw * .6, zt + 1.15],
                             [u - pw * .6, dp * .5 + pw * .6, zt + 1.15], [u + pw * .6, dp * .5 + pw * .6, zt + 1.15],
                             [u, dp * .5, zt + 2.6]]), m)
        if p["flying"]:
            fd = float(p["fly_dist"])
            fh = float(p["fly_h"]) if p["fly_h"] else (a.h if a else 12) * 0.75
            ph = float(p["pier_h"]) if p["pier_h"] else fh * 0.8
            part.add(g.box(u - w / 2, fd - dp / 2, 0, u + w / 2, fd + dp / 2, ph), m)
            part.add(g.hull([[u - w * .6, fd - dp * .6, ph], [u + w * .6, fd - dp * .6, ph], [u - w * .6, fd + dp * .6, ph],
                             [u + w * .6, fd + dp * .6, ph], [u, fd, ph + 2.0]]), m)
            part.add(g.beam([u, -0.2, fh], [u, fd, ph - 0.6], w * 0.6, 0.5), m)
    return part


@element("quoins", "decor", "Corner quoins (рустованные углы): alternating stone blocks on every footprint corner. Top anchor.",
         {"block_h": P(0.35, ""), "long": P(0.7, ""), "short": P(0.4, ""), "out": P(0.04, ""), "material": P("trim", ""),
          "h": P(None, "height (default host height)")},
         attach="top", title_ru="Угловой руст")
def quoins(p, ctx):
    a = ctx.anchor
    fp = _fp(ctx)
    H = float(p["h"]) if p["h"] else (a.height if a else 6)
    bh, lo, sh, out = float(p["block_h"]), float(p["long"]), float(p["short"]), float(p["out"])
    m = ctx.mat(p["material"])
    part = Part()
    n = len(fp)
    for i in range(n):
        c = np.array([fp[i][0], fp[i][1], 0.0])
        pv, nx = np.array(fp[i - 1] + (0,)), np.array(fp[(i + 1) % n] + (0,))
        d1, d2 = (pv - c) / np.linalg.norm(pv - c), (nx - c) / np.linalg.norm(nx - c)
        k = int(H / bh)
        for j in range(k):
            l1, l2 = (lo, sh) if j % 2 == 0 else (sh, lo)
            z0 = -H + j * bh + 0.01
            for dd, ll in ((d1, l1), (d2, l2)):
                nrm = np.array([dd[1], -dd[0], 0]) * (-1 if dd is d1 else 1)
                p0 = c + nrm * out
                p1 = c + dd * ll + nrm * out
                part.add(g.beam(p0 + [0, 0, z0 + bh * 0.45], p1 + [0, 0, z0 + bh * 0.45], out * 2 + 0.1, bh * 0.9), m)
    return part


@element("timber_frame", "decor", "Half-timbering (фахверк) on a face: posts, floor beams, braces. Openings on the same face cut through it.",
         {"post_spacing": P(1.2, ""), "beam": P(0.18, "timber width"), "out": P(0.04, "projection"),
          "pattern": P("mann", "", ["cross", "diagonal", "mann", "k", "grid"]), "v0": P(0.0, "start height"),
          "floors": P(None, "number of storeys covered (default host floors)"), "material": P("timber", "")},
         attach="face", title_ru="Фахверк")
def timber_frame(p, ctx):
    a = ctx.anchor
    W = a.w if a else 8
    fh = a.floor_h if a else 3
    floors = int(p["floors"] or (a.floors if a else 2))
    v0 = float(p["v0"]) or (a.base if a else 0)
    bw, out = float(p["beam"]), float(p["out"])
    m = ctx.mat(p["material"])
    part = Part(overlay=True)
    n = max(2, int(W / float(p["post_spacing"])))
    us = [bw / 2 + (W - bw) * i / n for i in range(n + 1)]
    y0, y1 = -0.06, out
    for f in range(floors):
        zb, zt = v0 + f * fh, v0 + (f + 1) * fh
        part.add(g.box(0, y0, zb, W, y1, zb + bw), m)
        part.add(g.box(0, y0, zt - bw, W, y1, zt), m)
        for u in us:
            part.add(g.box(u - bw / 2, y0, zb, u + bw / 2, y1, zt), m)
        mid = (zb + zt) / 2
        part.add(g.box(0, y0, mid - bw * 0.4, W, y1 - 0.01, mid + bw * 0.4), m) if p["pattern"] in ("grid", "k") else None
        for k in range(n):
            ua, ub = us[k], us[k + 1]
            pat = p["pattern"]
            # braces sit 1 cm behind the posts' face: a rotated beam never lands exactly in that plane, and a
            # sub-millimetre offset would leave two flickering faces (z-fighting)
            yy, bd = (y0 + y1 - 0.01) / 2, y1 - 0.01 - y0
            if pat == "cross" or (pat == "mann" and k in (0, n - 1)):
                part.add(g.beam([ua, yy, zb + bw], [ub, yy, zt - bw], bw * 0.8, bd), m) if pat == "cross" or k == 0 else None
                part.add(g.beam([ub, yy, zb + bw], [ua, yy, zt - bw], bw * 0.8, bd), m) if pat == "cross" or k == n - 1 else None
            elif pat == "diagonal" and k % 2 == 0:
                part.add(g.beam([ua, yy, zb + bw], [ub, yy, zt - bw], bw * 0.8, bd), m)
            elif pat == "k" and k % 3 == 0:
                part.add(g.beam([ua, yy, mid], [ub, yy, zt - bw], bw * 0.8, bd), m)
    return part


@element("panel_grid", "decor", "Precast panel joints (швы панелей) cut into a face — soviet panel buildings. Uses host floors.",
         {"panel_w": P(3.2, "panel width"), "groove": P(0.04, ""), "deep": P(0.025, ""), "v0": P(None, "start (default plinth)")},
         attach="face", title_ru="Швы панелей")
def panel_grid(p, ctx):
    a = ctx.anchor
    W, H = (a.w, a.h) if a else (10, 10)
    fh, base = (a.floor_h, a.base) if a else (3, 0)
    v0 = base if p["v0"] is None else float(p["v0"])
    gw, dp = float(p["groove"]), float(p["deep"])
    part = Part()
    n = max(1, round(W / float(p["panel_w"])))
    for i in range(1, n):
        u = W * i / n
        part.cut(g.box(u - gw / 2, -dp, v0, u + gw / 2, 0.05, H - 0.01), "seam")
    z = v0
    while z < H - 0.1:
        part.cut(g.box(0.0, -dp, z - gw / 2, W, 0.05, z + gw / 2), "seam")
        z += fh
    return part


@element("balconies", "decor", "Balconies or loggias on a grid (like windows). loggia = recessed into the wall.",
         {"kind": P("balcony", "", ["balcony", "loggia", "french"]), "w": P(2.4, ""), "d": P(1.1, "depth"),
          "railing": P("bars", "", ["bars", "balusters", "solid", "glass", "wood"]), "rail_h": P(1.0, ""),
          "cols": P("auto", ""), "rows": P("auto", ""), "us": P(None, ""), "vs": P(None, ""), "margin": P(1.0, ""),
          "sill": P(None, "v of first floor slab (default plinth + floor_h)"), "row_step": P(None, ""),
          "skip": P(None, ""), "only_rows": P(None, ""), "slab_material": P("trim", ""), "railing_material": P("railing", "")},
         attach="face", title_ru="Балконы / лоджии")
def balconies(p, ctx):
    a = ctx.anchor
    q = dict(p)
    if q.get("sill") is None:
        q["sill"] = (a.base + a.floor_h) if a else 3.0
        if q.get("rows") in ("auto", None) and a:
            q["rows"] = max(1, a.floors - 1)
    w, d, rh = float(p["w"]), float(p["d"]), float(p["rail_h"])
    sm, rm = ctx.mat(p["slab_material"]), ctx.mat(p["railing_material"])
    part = Part()
    for u, v, c, r in grid_positions(q, a, w):
        kind = p["kind"]
        if kind == "loggia":
            dd = min(d, (a.depth if a else 0.5) + d)
            part.cut(g.box(u - w / 2, -d, v + 0.01, u + w / 2, 0.05, v + (a.floor_h if a else 3) - 0.3))
            y0, y1 = -0.05, 0.08
        elif kind == "french":
            y0, y1 = -0.05, 0.35
            part.add(g.box(u - w / 2, -0.05, v - 0.12, u + w / 2, y1, v), sm)
        else:
            y0, y1 = -0.1, d
            part.add(g.box(u - w / 2, y0, v - 0.15, u + w / 2, y1, v), sm)
        rail = p["railing"]
        if rail in ("solid", "glass"):
            mm = sm if rail == "solid" else ctx.mat("glass")
            part.add(g.box(u - w / 2, y1 - 0.08, v - 0.01, u + w / 2, y1, v + rh), mm)
            if kind != "loggia":
                for sx in (-1, 1):
                    part.add(g.box(u + sx * w / 2 - (0.08 if sx > 0 else 0), y0, v - 0.01, u + sx * w / 2 + (0 if sx > 0 else 0.08), y1, v + rh), mm)
        else:
            part.add(g.box(u - w / 2, y1 - 0.06, v + rh - 0.06, u + w / 2, y1, v + rh), rm)
            k = max(2, int(w / (0.12 if rail != "balusters" else 0.25)))
            for i in range(k + 1):
                x = u - w / 2 + 0.03 + (w - 0.06) * i / k
                if rail == "balusters" and not ctx.low:
                    part.add(g.revolve([(0, 0), (0.06, 0), (0.04, 0.15), (0.07, rh * 0.45), (0.03, rh * 0.8), (0.05, rh - 0.05), (0, rh - 0.05)], 8)
                             .translate([x, y1 - 0.06, v]), sm)
                else:
                    part.add(g.box(x - 0.012, y1 - 0.04, v, x + 0.012, y1 - 0.02, v + rh), rm)
            if kind == "balcony":
                for sx in (-1, 1):
                    xx = u + sx * (w / 2 - 0.03)
                    part.add(g.box(xx - 0.03, y0, v + rh - 0.06, xx + 0.03, y1, v + rh), rm)
    return part


@element("canopy", "decor", "Entrance canopy / awning / porch roof on a face at [u, v] (v = height of the canopy underside).",
         {"kind": P("slab", "", ["slab", "awning", "gable_porch", "shed_porch"]), "w": P(2.4, ""), "d": P(1.5, ""),
          "posts": P(False, "posts to the ground"), "post_h": P(2.6, "post length below the canopy"),
          "material": P("trim", ""), "roof_material": P("roof", "")},
         attach="face", title_ru="Козырёк / навес / крыльцо")
def canopy(p, ctx):
    w, d = float(p["w"]), float(p["d"])
    part = Part()
    m, rm = ctx.mat(p["material"]), ctx.mat(p["roof_material"])
    k = p["kind"]
    if k == "slab":
        part.add(g.box(-w / 2, -0.1, 0, w / 2, d, 0.15), m)
    elif k == "awning":
        part.add(g.hull([[-w / 2, -0.05, 0.6], [w / 2, -0.05, 0.6], [-w / 2, d, 0], [w / 2, d, 0],
                         [-w / 2, -0.05, 0.66], [w / 2, -0.05, 0.66], [-w / 2, d, 0.06], [w / 2, d, 0.06]]), rm)
    elif k == "shed_porch":
        part.add(g.hull([[-w / 2, -0.1, 0.8], [w / 2, -0.1, 0.8], [-w / 2, d, 0.1], [w / 2, d, 0.1],
                         [-w / 2, -0.1, 0.95], [w / 2, -0.1, 0.95], [-w / 2, d, 0.25], [w / 2, d, 0.25]]), rm)
    else:
        rh = w * 0.35
        roofv = g.hull([[-w / 2, -0.1, 0], [w / 2, -0.1, 0], [0, -0.1, rh], [-w / 2, d, 0], [w / 2, d, 0], [0, d, rh]])
        part.add(roofv - roofv.translate([0, 0, -0.15]), rm)
        part.add(g.hull([[-w / 2 + .1, d - .05, .0], [w / 2 - .1, d - .05, 0], [0, d - .05, rh - .15],
                         [-w / 2 + .1, d - .15, 0], [w / 2 - .1, d - .15, 0], [0, d - .15, rh - .15]]), ctx.mat("wood"))
    if p["posts"]:
        ph = float(p["post_h"])
        for sx in (-1, 1):
            part.add(g.box(sx * (w / 2 - 0.1) - 0.07, d - 0.2, -ph, sx * (w / 2 - 0.1) + 0.07, d - 0.06, 0.02), ctx.mat("wood"))
    return part


@element("curtain_wall", "decor", "Glass curtain wall skin over a face with a mullion grid (modern towers).",
         {"spacing": P(1.5, "vertical mullion spacing"), "row": P(None, "horizontal spacing (default floor height)"),
          "mullion": P(0.08, ""), "out": P(0.15, ""), "v0": P(None, "start height (default plinth)"),
          "glass_material": P("glass_dark", ""), "material": P("aluminium", "")},
         attach="face", title_ru="Светопрозрачный фасад")
def curtain_wall(p, ctx):
    a = ctx.anchor
    W, H = (a.w, a.h) if a else (10, 20)
    v0 = (a.base if a else 0) if p["v0"] is None else float(p["v0"])
    row = float(p["row"]) if p["row"] else (a.floor_h if a else 3.5)
    out, mw = float(p["out"]), float(p["mullion"])
    part = Part(overlay=True)
    part.add(g.box(0, -0.02, v0, W, out - 0.04, H - 0.05), ctx.mat(p["glass_material"]))
    mm = ctx.mat(p["material"])
    n = max(1, round(W / float(p["spacing"])))
    for i in range(n + 1):
        u = min(max(W * i / n, mw / 2), W - mw / 2)
        part.add(g.box(u - mw / 2, -0.02, v0, u + mw / 2, out, H - 0.05), mm)
    z = v0
    while z <= H - 0.05:
        part.add(g.box(0, -0.02, z, W, out, min(z + mw * 1.5, H - 0.05)), mm)
        z += row
    return part


@element("balustrade", "decor", "Balustrade / railing along a `top` anchor perimeter (roof terraces, classical attics).",
         {"h": P(1.0, ""), "inset": P(0.1, ""), "spacing": P(0.28, ""), "posts_every": P(3.0, ""), "material": P("trim", ""),
          "kind": P("balusters", "", ["balusters", "bars", "solid"])},
         attach="top", title_ru="Балюстрада")
def balustrade(p, ctx):
    fp = _fp(ctx)
    cs = g.poly(fp)
    h, ins = float(p["h"]), float(p["inset"])
    m = ctx.mat(p["material"] if p["kind"] != "bars" else "railing")
    part = Part()
    part.add(g.extrude(g.offset2(cs, -ins) - g.offset2(cs, -ins - 0.3), 0.15, -0.02), m)
    part.add(g.extrude(g.offset2(cs, -ins + 0.03) - g.offset2(cs, -ins - 0.33), 0.12, h - 0.12), m)
    if p["kind"] == "solid":
        part.add(g.extrude(g.offset2(cs, -ins) - g.offset2(cs, -ins - 0.25), h, -0.02), m)
        return part
    sp = float(p["spacing"])
    for p0, d, nrm, L in edges(fp):
        n = max(1, int(L / sp))
        for i in range(n):
            c = along(p0, d, nrm, (i + 0.5) * L / n, -ins - 0.15, 0.1)
            if p["kind"] == "balusters" and not ctx.low:
                part.add(g.revolve([(0, 0), (0.07, 0), (0.05, 0.12), (0.09, h * 0.4), (0.04, h * 0.75), (0.06, h - 0.2), (0, h - 0.2)], 8).translate(list(c)), m)
            else:
                part.add(g.boxc(0.05, 0.05, h - 0.2, c[0], c[1], c[2]), m)
    return part


@element("fence", "decor", "Fence / palisade / low stone wall along a polyline of [x,y] points (free placement).",
         {"points": P([[0, 0], [10, 0]], ""), "h": P(1.5, ""), "kind": P("picket", "", ["picket", "iron", "stone", "palisade", "wattle", "rail"]),
          "closed": P(False, "close the loop"), "material": P(None, "default by kind")},
         attach="free", title_ru="Забор / ограда / частокол")
def fence(p, ctx):
    pts = [np.array([x, y, 0.0]) for x, y in p["points"]]
    if p["closed"]:
        pts.append(pts[0])
    h, k = float(p["h"]), p["kind"]
    m = ctx.mat(p["material"] or {"picket": "wood", "iron": "railing", "stone": "stone_rubble", "palisade": "log",
                                  "wattle": "wood", "rail": "wood"}[k])
    part = Part()
    for a, b in zip(pts[:-1], pts[1:]):
        L = float(np.linalg.norm(b - a))
        d = (b - a) / max(L, 1e-6)
        if k == "stone":
            part.add(g.beam(a + [0, 0, h / 2], b + [0, 0, h / 2], 0.5, h), m)
            continue
        if k == "palisade":
            n = max(1, int(L / 0.25))
            for i in range(n + 1):
                c = a + d * L * i / n
                part.add(g.cyl(0.12, h, 6 if ctx.low else 10, 0, None, c[0], c[1]), m)
                part.add(g.cyl(0.12, 0.3, 6 if ctx.low else 10, h - 0.01, 0.01, c[0], c[1]), m)
            continue
        for z in ((0.3, h - 0.25) if k != "rail" else (0.4, 0.8, h - 0.1)):
            part.add(g.beam(a + [0, 0, z], b + [0, 0, z], 0.05, 0.1), m)
        n = max(1, int(L / (0.15 if k in ("picket", "iron", "wattle") else 2.0)))
        for i in range(n + 1):
            c = a + d * L * i / n
            if k == "iron":
                part.add(g.boxc(0.025, 0.025, h, c[0], c[1]), m)
            elif k == "rail":
                part.add(g.boxc(0.15, 0.15, h, c[0], c[1]), m)
            else:
                part.add(g.boxc(0.09, 0.025, h, c[0], c[1]), m)
    return part


@element("pediment", "decor", "Triangular or segmental pediment (фронтон) on a face at [u, v], with frame mouldings.",
         {"w": P(6.0, ""), "h": P(1.5, ""), "kind": P("triangle", "", ["triangle", "segmental", "broken"]), "depth": P(0.3, ""),
          "material": P("trim", ""), "tympanum": P(None, "relief/mosaic subject in the tympanum")},
         attach="face", title_ru="Фронтон")
def pediment(p, ctx):
    w, h, dp = float(p["w"]), float(p["h"]), float(p["depth"])
    m = ctx.mat(p["material"])
    k = p["kind"]
    shp = opening_shape("triangle" if k != "segmental" else "segmental", w, h, 32) if k != "segmental" else \
        opening_shape("segmental", w, h, 32)
    if k == "segmental":
        shp = opening_shape("segmental", w, h, 32)
    part = Part()
    frame = g.offset2(shp, 0.0) - g.offset2(shp, -0.22)
    if k == "broken":
        frame = frame - g.rect2(w * 0.3, h * 2, 0, h * 0.3)
    part.add(g.prism_xz(frame, -0.05, dp), m)
    part.add(g.box(-w / 2 - 0.1, -0.05, -0.18, w / 2 + 0.1, dp + 0.05, 0.02), m)
    if p["tympanum"]:
        part.add(g.prism_xz(g.offset2(shp, -0.22), -0.05, dp * 0.5), ctx.art("relief", p["tympanum"]))
    else:
        part.add(g.prism_xz(g.offset2(shp, -0.22), -0.05, dp * 0.3), m)
    return part


def _inside(x, y, fp):
    """Point in polygon (ray casting)."""
    ins = False
    for i in range(len(fp)):
        (x0, y0), (x1, y1) = fp[i], fp[(i + 1) % len(fp)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            ins = not ins
    return ins


@element("studs", "decor", "Toy-brick studs (round bumps) on a flat top: blocky toy / brick-game look. "
         "Attach to a `top` anchor (flat roof top, block top, platform).",
         {"spacing": P(0.8, "distance between studs (m)"), "r": P(0.24, "stud radius"), "h": P(0.17, "stud height"),
          "margin": P(0.3, "free border"), "material": P("roof", "")},
         attach="top", title_ru="Шипы игрушечного кирпича")
def studs(p, ctx):
    a = ctx.anchor
    fp = a.footprint if a and a.footprint else [(-2, -2), (2, -2), (2, 2), (-2, 2)]
    s, r, h, m = float(p["spacing"]), float(p["r"]), float(p["h"]), float(p["margin"])
    xs, ys = [q[0] for q in fp], [q[1] for q in fp]
    nx, ny = int((max(xs) - min(xs) - 2 * m) // s) + 1, int((max(ys) - min(ys) - 2 * m) // s) + 1
    if nx * ny > 900:  # a huge roof: wider spacing instead of thousands of studs
        s *= math.sqrt(nx * ny / 900)
        nx, ny = int((max(xs) - min(xs) - 2 * m) // s) + 1, int((max(ys) - min(ys) - 2 * m) // s) + 1
    x0 = (min(xs) + max(xs)) / 2 - (nx - 1) * s / 2
    y0 = (min(ys) + max(ys)) / 2 - (ny - 1) * s / 2
    pts = [(x0 + i * s, y0 + j * s) for i in range(nx) for j in range(ny)]
    pts = [q for q in pts if all(_inside(q[0] + dx, q[1] + dy, fp) for dx, dy in ((r + m, 0), (-r - m, 0), (0, r + m), (0, -r - m)))]
    part = Part()
    if pts:
        seg = 8 if ctx.low else 14
        part.add(g.union([g.cyl(r, h + 0.02, seg, -0.02, None, x, y) for x, y in pts]), ctx.mat(p["material"]))
    return part
