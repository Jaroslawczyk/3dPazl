"""Shared helpers for element generators."""
from __future__ import annotations

import math

import numpy as np

from .. import geo as g
from ..registry import Anchor, pct


def footprint(p) -> list[tuple[float, float]]:
    """Footprint from params: `poly` list of points or rect `w` x `d` centred at origin."""
    if p.get("poly"):
        return g.ccw(p["poly"])
    w, d = float(p["w"]), float(p["d"])
    return [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]


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
    return out


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
    only_rows = p.get("only_rows")
    only_cols = p.get("only_cols")
    out = []
    for r, v in enumerate(vs):
        for c, u in enumerate(us):
            if (c, r) in skip or (only_rows and r not in only_rows) or (only_cols and c not in only_cols):
                continue
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
