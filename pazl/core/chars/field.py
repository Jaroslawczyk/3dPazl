"""Implicit surfaces: a signed field on a regular grid (negative = inside) meshed with naive surface nets (own code).
Characters are one continuous skin grown from such a field, not a pile of primitives."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

BIG = 1.0


class Grid:
    def __init__(self, lo, hi, cell):
        self.lo = np.asarray(lo, float)
        self.cell = float(cell)
        self.n = np.ceil((np.asarray(hi, float) - self.lo) / cell).astype(int) + 1
        self.ax = [self.lo[i] + np.arange(self.n[i]) * cell for i in range(3)]

    def empty(self):
        return np.full(self.n, BIG, np.float32)

    def window(self, lo, hi):
        """Index slices of the grid inside the box, and the coordinates there (broadcastable)."""
        sl = []
        for i in range(3):
            a = int(np.clip(np.floor((lo[i] - self.lo[i]) / self.cell), 0, self.n[i] - 1))
            b = int(np.clip(np.ceil((hi[i] - self.lo[i]) / self.cell) + 1, a + 1, self.n[i]))
            sl.append(slice(a, b))
        x, y, z = (self.ax[i][sl[i]].astype(np.float32) for i in range(3))
        return tuple(sl), x[:, None, None], y[None, :, None], z[None, None, :]


def smin(a, b, k):
    """Polynomial smooth minimum: blends two surfaces over a fillet of size k."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(.5 + .5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ellipsoid(g, f, c, r, k=0.0, cut=False):
    """Blend an ellipsoid (centre c, radii r) into field f; cut=True carves it out."""
    c, r = np.asarray(c, float), np.asarray(r, float)
    m = r.max() + k + 2 * g.cell
    sl, x, y, z = g.window(c - m, c + m)
    q = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2)
    d = (q - 1) * r.min()
    f[sl] = smax(f[sl], -d, k) if cut else smin(f[sl], d, k)


def loft(g, f, a, b, prof, k=0.0, side=(1, 0, 0)):
    """Blend a body swept from a to b. prof: [(t, r_side, r_front, offset_front)], t in 0..1 along the axis; the
    cross-section is an ellipse whose radii follow a smooth (monotone cubic) curve. side = direction of r_side."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    u = (b - a) / L
    s = np.asarray(side, float)
    s = s - u * (s @ u)
    if np.linalg.norm(s) < 1e-6:
        s = np.array([0, 0, 1.0]) - u * u[2]
    s /= np.linalg.norm(s)
    w = np.cross(s, u)
    if w[2] < 0 or (abs(w[2]) < 1e-6 and w[1] < 0):
        w = -w
    P = np.array(prof, float)
    fs = [PchipInterpolator(P[:, 0], P[:, i]) for i in (1, 2, 3)]
    m = P[:, 1:3].max() + abs(P[:, 3]).max() + k + 2 * g.cell
    sl, x, y, z = g.window(np.minimum(a, b) - m, np.maximum(a, b) + m)
    dx, dy, dz = x - a[0], y - a[1], z - a[2]
    h = dx * u[0] + dy * u[1] + dz * u[2]
    t = np.clip(h / L, P[0, 0], P[-1, 0])
    tt = np.linspace(P[0, 0], P[-1, 0], 256)
    rs, rf, of = (np.interp(t, tt, fn(tt)).astype(np.float32) for fn in fs)
    px = dx * s[0] + dy * s[1] + dz * s[2]
    pz = dx * w[0] + dy * w[1] + dz * w[2] - of
    rad = np.sqrt((px / rs) ** 2 + (pz / rf) ** 2)
    d = (rad - 1) * np.minimum(rs, rf)
    over = np.maximum(P[0, 0] * L - h, h - P[-1, 0] * L)  # past the ends: round off instead of a flat cut
    d = np.where(over > 0, np.sqrt(np.maximum(d, 0) ** 2 + over ** 2), d)
    f[sl] = smin(f[sl], d, k)


def box(g, f, c, half, r=0.0):
    """Hard union of a box with rounded edges (centre c, half sizes, edge radius r)."""
    c, half = np.asarray(c, float), np.asarray(half, float)
    sl, x, y, z = g.window(c - half - 2 * g.cell, c + half + 2 * g.cell)
    qx, qy, qz = np.abs(x - c[0]) - half[0] + r, np.abs(y - c[1]) - half[1] + r, np.abs(z - c[2]) - half[2] + r
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    f[sl] = np.minimum(f[sl], out + np.minimum(np.maximum(np.maximum(qx, qy), qz), 0) - r)


def decimate(V, F, target):
    """Fewer triangles, same shape: this is what the quality levels use."""
    if not target or len(F) <= target:
        return V, F
    import fast_simplification
    v, f = fast_simplification.simplify(np.asarray(V, np.float32), np.asarray(F, np.int32), target_reduction=1 - target / len(F))
    return np.asarray(v, float), np.asarray(f)


def cone(g, f, a, b, ra, rb, k=0.0):
    """Round tapered limb between two points."""
    loft(g, f, a, b, [(0, ra, ra, 0), (1, rb, rb, 0)], k)


def surface_nets(f, lo, cell):
    """(V, F) of the zero level of the 3D array f; winding is fixed by the caller if needed (see orient)."""
    f = np.asarray(f, np.float32)
    ins = f < 0
    c = np.zeros(np.array(f.shape) - 1, np.uint8)
    for dx, dy, dz in np.ndindex(2, 2, 2):
        c += ins[dx:f.shape[0] - 1 + dx, dy:f.shape[1] - 1 + dy, dz:f.shape[2] - 1 + dz]
    cells = np.argwhere((c > 0) & (c < 8))
    if not len(cells):
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    idx = np.full(c.shape, -1, np.int64)
    idx[tuple(cells.T)] = np.arange(len(cells))
    acc, cnt = np.zeros((len(cells), 3)), np.zeros(len(cells))
    for ax in range(3):  # average the crossing points on the 12 cell edges
        e = np.eye(3, dtype=int)[ax]
        for o in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            off = np.zeros(3, int)
            off[[i for i in range(3) if i != ax]] = o
            p = cells + off
            a, b = f[tuple(p.T)], f[tuple((p + e).T)]
            m = (a < 0) != (b < 0)
            t = a[m] / (a[m] - b[m])
            acc[m] += p[m] + t[:, None] * e
            cnt[m] += 1
    V = np.asarray(lo) + acc / cnt[:, None] * cell
    quads = []
    for ax in range(3):  # every grid edge crossing the surface gives a quad of the 4 cells around it
        u, v = [i for i in range(3) if i != ax]
        e = np.eye(3, dtype=int)[ax]
        sa = [slice(1, -1)] * 3
        sa[ax] = slice(0, f.shape[ax] - 1)
        sb = list(sa)
        sb[ax] = slice(1, f.shape[ax])
        a, b = f[tuple(sa)], f[tuple(sb)]
        p = np.argwhere((a < 0) != (b < 0))
        if not len(p):
            continue
        flip = a[tuple(p.T)] >= 0
        eu, ev = np.eye(3, dtype=int)[u], np.eye(3, dtype=int)[v]
        p = p + eu + ev  # back to absolute indices (the axis itself started at 0)
        q = np.stack([idx[tuple((p - eu - ev).T)], idx[tuple((p - ev).T)], idx[tuple(p.T)], idx[tuple((p - eu).T)]], 1)
        if ax == 1:
            flip = ~flip  # (u, v, ax) is a left-handed order for the Y axis
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    q = np.vstack(quads)
    q = q[(q >= 0).all(1)]
    return V, np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
