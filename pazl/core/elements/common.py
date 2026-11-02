"""Shared helpers for element generators."""
from __future__ import annotations

import math

import numpy as np

from .. import geo as g
from ..registry import Anchor, pct


FP_SHAPES = ["rect", "round", "oval", "rounded", "L", "U", "T", "octagon", "hexagon", "trapezoid", "wedge", "bow",
             "cut_corner", "cross"]


def _arc(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def shape_points(shape: str, w: float, d: float, k: float = 0.4) -> list[tuple[float, float]]:
    """Footprint of a named shape, CCW, starting at the front-left so face0 is the front (-Y) where there is one.
    k = proportion of the shape's feature: notch of L/U/T, corner radius, taper of trapezoid/wedge, bulge of bow."""
    X, Y = w / 2, d / 2
    k = min(max(float(k), 0.1), 0.8)
    if shape in ("round", "oval"):
        rx, ry = (min(X, Y), min(X, Y)) if shape == "round" else (X, Y)
        return _arc(0, 0, rx, ry, -math.pi / 2, 1.5 * math.pi, 48)[:-1]
    if shape == "rounded":
        r = min(X, Y) * k
        pts = []
        for cx, cy, a0 in ((X - r, -Y + r, -math.pi / 2), (X - r, Y - r, 0), (-X + r, Y - r, math.pi / 2), (-X + r, -Y + r, math.pi)):
            pts += _arc(cx, cy, r, r, a0, a0 + math.pi / 2, 6)
        return pts[-1:] + pts[:-1]  # start after the front-left corner arc -> face0 = straight front
    if shape == "L":
        return [(-X, -Y), (X, -Y), (X, -Y + d * (1 - k)), (-X + w * (1 - k), -Y + d * (1 - k)), (-X + w * (1 - k), Y), (-X, Y)]
    if shape == "U":
        a, b = w * k / 2, d * k
        return [(-X, -Y), (X, -Y), (X, Y), (a, Y), (a, Y - b), (-a, Y - b), (-a, Y), (-X, Y)]
    if shape == "T":
        a = w * (1 - k) / 2
        return [(-X, -Y), (X, -Y), (X, -Y + d * 0.45), (a, -Y + d * 0.45), (a, Y), (-a, Y), (-a, -Y + d * 0.45), (-X, -Y + d * 0.45)]
    if shape == "cross":
        a, b = w * (1 - k) / 2, d * (1 - k) / 2
        return [(-a, -Y), (a, -Y), (a, -b), (X, -b), (X, b), (a, b), (a, Y), (-a, Y), (-a, b), (-X, b), (-X, -b), (-a, -b)]
    if shape in ("octagon", "hexagon"):
        if shape == "hexagon":
            return [(-X * 0.5, -Y), (X * 0.5, -Y), (X, 0), (X * 0.5, Y), (-X * 0.5, Y), (-X, 0)]
        c = min(X, Y) * 0.6
        return [(-X + c, -Y), (X - c, -Y), (X, -Y + c), (X, Y - c), (X - c, Y), (-X + c, Y), (-X, Y - c), (-X, -Y + c)]
    if shape in ("trapezoid", "wedge"):
        b = X * (1 - k) if shape == "trapezoid" else X * 0.12
        return [(-X, -Y), (X, -Y), (b, Y), (-b, Y)]
    if shape == "bow":  # convex curved front
        yc = -Y + d * k * 0.5
        return [(-X, yc)] + _arc(0, yc, X, d * k * 0.5, math.pi, 2 * math.pi, 16)[1:-1] + [(X, yc), (X, Y), (-X, Y)]
    if shape == "cut_corner":  # one chamfered front corner (corner house on a crossroads)
        c = min(X, Y) * k
        return [(-X, -Y), (X - c, -Y), (X, -Y + c), (X, Y), (-X, Y)]
    return [(-X, -Y), (X, -Y), (X, Y), (-X, Y)]


def footprint(p) -> list[tuple[float, float]]:
    """Footprint from params: `poly` list of points, or `shape` (rect, round, L, ...) of `w` x `d` centred at origin.
    `flip` mirrors it left-right (asymmetric shapes)."""
    if p.get("poly"):
        return g.ccw(p["poly"])
    w, d = float(p["w"]), float(p["d"])
    pts = shape_points(p.get("shape") or "rect", w, d, p.get("shape_k") or 0.4)
    if p.get("flip"):
        pts = [(-x, y) for x, y in pts][::-1]
        pts = pts[-2:] + pts[:-2]  # keep the front edge first
    return pts


def is_rect(fp) -> bool:
    if len(fp) != 4:
        return False
    xs, ys = [p[0] for p in fp], [p[1] for p in fp]
    return all(min(abs(x - min(xs)), abs(x - max(xs))) < 1e-6 for x in xs) and all(min(abs(y - min(ys)), abs(y - max(ys))) < 1e-6 for y in ys)


def clip_to(part, fp, grow=0.0):
    """Clip a part's solids to the vertical prism over footprint fp (+grow): nothing hangs over empty space
    (gable roofs and room partitions on L / round / U footprints)."""
    if is_rect(fp):
        return part
    prism = g.extrude(g.offset2(g.poly(fp), grow) if grow else g.poly(fp), 400.0, -100.0)
    part.solids = [(m ^ prism, mat) for m, mat in part.solids]
    part.solids = [(m, mat) for m, mat in part.solids if not m.is_empty()]
    return part


def face_anchors(fp, height, depth, floors=1, floor_h=3.0, base=0.0, z0=0.0, names=True) -> dict:
    """One face anchor per polygon edge (CCW). Rect footprints also get front/right/back/left."""
    out = {}
    n = len(fp)
    for i in range(n):
        x0, y0 = fp[i]
        x1, y1 = fp[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        xa = np.array([dx / L, dy / L, 0.0])
        na = np.array([dy / L, -dx / L, 0.0])
        m = g.mat_frame([x0, y0, z0], xa, na, [0, 0, 1.0])
        out[f"face{i}"] = Anchor(m, "face", w=L, h=height, depth=depth, floors=floors, floor_h=floor_h, base=base)
    if names and n == 4:
        for i, nm in enumerate(("front", "right", "back", "left")):
            if f"face{i}" in out:
                out[nm] = out[f"face{i}"]
    elif names:  # any polygon: front/right/back/left = the longest edge facing that way (macros attach to them)
        for nm, dvec in (("front", (0, -1)), ("right", (1, 0)), ("back", (0, 1)), ("left", (-1, 0))):
            best = max(((a.m[0, 1] * dvec[0] + a.m[1, 1] * dvec[1]) * a.w, k) for k, a in out.items() if k.startswith("face"))
            if best[0] > 0.3:
                out[nm] = out[best[1]]
    return out


def round_face_anchors(rx, ry, height, depth, floors=1, floor_h=3.0, base=0.0, k=None) -> dict:
    """Face anchors on tangent planes of a round / oval wall (a circumscribed k-gon): windows, doors and
    facades on curved walls."""
    per = math.pi * (rx + ry)
    k = k or max(8, int(round(per / 3.2 / 2)) * 2)
    sc = 1 / math.cos(math.pi / k)
    pts = [(rx * sc * math.cos(-math.pi / 2 - math.pi / k + 2 * math.pi * i / k), ry * sc * math.sin(-math.pi / 2 - math.pi / k + 2 * math.pi * i / k))
           for i in range(k)]
    return face_anchors(pts, height, depth, floors, floor_h, base)


def top_anchor(fp, z, height, floors=1, floor_h=3.0, **extra) -> Anchor:
    return Anchor(g.mat_t(0, 0, z), "top", footprint=list(fp), height=height, floors=floors, floor_h=floor_h,
                  w=max(p[0] for p in fp) - min(p[0] for p in fp), h=max(p[1] for p in fp) - min(p[1] for p in fp),
                  extra=extra)


def grid_positions(p, anchor: Anchor, w_item: float, default_rows="floors"):
    """Positions (u_center, v_bottom, col, row) for repeating items on a face.

    params used: cols ('auto'|int), rows ('auto'|int), us (explicit u list), vs (explicit v list),
    margin, sill (v of first row), row_step, skip ([[col,row],...]), only_rows, only_cols
    """
    W = anchor.w if anchor else 10.0
    H = anchor.h if anchor else 10.0
    floors = anchor.floors if anchor else 1
    fh = anchor.floor_h if anchor else 3.0
    base = anchor.base if anchor else 0.0
    margin = pct(p.get("margin", 1.0), W)
    if p.get("us"):
        us = [pct(u, W) for u in p["us"]]
    else:
        cols = p.get("cols", "auto")
        if cols in ("auto", None, 0):
            gap = max(w_item * 0.9, 0.6)
            cols = max(1, int((W - 2 * margin + gap) // (w_item + gap)))
        cols = int(cols)
        span = W - 2 * margin
        us = [margin + span * (i + 0.5) / cols for i in range(cols)]
    sill = p.get("sill")
    sill = base + 0.9 if sill is None else pct(sill, H)
    if p.get("vs"):
        vs = [pct(v, H) for v in p["vs"]]
    else:
        rows = p.get("rows", "auto")
        if rows in ("auto", None, 0):
            rows = floors if default_rows == "floors" else 1
        step = p.get("row_step") or fh
        vs = [sill + r * float(step) for r in range(int(rows))]
    skip = {tuple(s) for s in (p.get("skip") or [])}
    avoid = p.get("_avoid") or []  # [u0,u1,v0,v1] of doors etc. on the same face (set by the builder)
    h_item = float(p.get("h") or 1.5)
    gap = 0.25
    only_rows = p.get("only_rows")
    only_cols = p.get("only_cols")
    out = []
    for r, v in enumerate(vs):
        for c, u in enumerate(us):
            if (c, r) in skip or (only_rows and r not in only_rows) or (only_cols and c not in only_cols):
                continue
            if any(u - w_item / 2 - gap < a[1] and u + w_item / 2 + gap > a[0] and v - gap < a[3] and v + h_item + gap > a[2]
                   for a in avoid):
                continue
            if anchor is not None and (u - w_item / 2 < -0.01 or u + w_item / 2 > W + 0.01 or v + h_item > H - 0.05 or v < -0.01):
                continue  # never past the edge of the wall or into the roof
            out.append((u, v, c, r))
    return out


# ------------------------------------------------------------ 2D opening shapes (x horizontal, y up)
def opening_shape(kind: str, w: float, h: float, seg: int):
    """Opening outline with bottom at y=0, centred on x=0."""
    r = w / 2
    if kind in ("rect", "door", "ribbon", "slit", "shop", "garage", "square"):
        return g.rect2(w, h)
    if kind in ("arch", "round_arch", "romanesque"):
        hs = max(0.01, h - r)
        pts = [(-r, 0), (r, 0), (r, hs)] + g.arc_pts(0, hs, r, 0, math.pi, max(4, seg // 2))[1:-1] + [(-r, hs)]
        return g.poly(pts)
    if kind == "segmental":
        rise = min(r, w * 0.18)
        R = (r * r + rise * rise) / (2 * rise)
        hs = h - rise
        a = math.asin(min(1.0, r / R))
        pts = [(-r, 0), (r, 0)] + g.arc_pts(0, hs + rise - R, R, math.pi / 2 - a, math.pi / 2 + a, max(3, seg // 4))
        return g.poly(pts)
    if kind in ("lancet", "gothic", "pointed"):
        R = w  # equilateral arch
        rise = R * math.sin(math.acos(0.5))
        hs = max(0.01, h - rise)
        n = max(3, seg // 4)
        right = [(-r + R * math.cos(t), hs + R * math.sin(t)) for t in np.linspace(0, math.pi / 3, n)]
        left = [(r - R * math.cos(t), hs + R * math.sin(t)) for t in np.linspace(math.pi / 3, 0, n)][1:]
        return g.poly([(-r, 0), (r, 0)] + right + left)
    if kind in ("round", "oculus", "rose", "clock"):
        return g.circle2(min(w, h) / 2, seg, 0, h / 2)
    if kind == "horseshoe":
        R = r * 1.15
        c = h - R
        a = math.asin(r / R)
        arc = g.arc_pts(0, c, R, -(math.pi / 2 - a), math.pi + (math.pi / 2 - a), seg)
        return g.poly([(-r, 0), (r, 0)] + arc)
    if kind == "ogee":
        hs = h - w * 0.75
        n = max(4, seg // 4)
        right = []
        for i in range(n + 1):
            t = i / n
            x = r * (1 - t)
            y = hs + w * 0.75 * (0.5 - 0.5 * math.cos(math.pi * t)) ** 0.8
            right.append((x, y))
        left = [(-x, y) for x, y in reversed(right[:-1])]
        return g.poly([(-r, 0), (r, 0)] + right + left)
    if kind == "triangle":
        return g.poly([(-r, 0), (r, 0), (0, h)])
    return g.rect2(w, h)
