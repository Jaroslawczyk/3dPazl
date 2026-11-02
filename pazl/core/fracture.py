"""Destructible buildings: the welded model pre-split into chunks a game can break apart.

Modes:
- voronoi: natural cracks - Voronoi cells around seed points sampled on the surface (so pieces follow walls,
  not empty rooms); every cell intersected with the shell; break faces get the `rubble` material;
- elements: one piece per element (walls, roof, windows, ...) - "falls apart into parts";
- bricks (brick builder): bricks grouped into Voronoi chunks; with level "bricks" every brick is a piece.
Each chunk: geometry + centre of mass + volume (for game physics: mass, impulses).
"""
from __future__ import annotations

import numpy as np

from . import geo as g

LEVELS = {"light": 12, "medium": 40, "heavy": 100, "extreme": 250}
INNER = "rubble"


def settings(recipe: dict) -> dict | None:
    f = (recipe or {}).get("fracture") or {}
    if not f.get("on"):
        return None
    n = int(f.get("pieces") or LEVELS.get(f.get("level", "medium"), 40))
    return {"pieces": max(2, min(n, 1500)), "mode": f.get("mode", "voronoi"), "seed": int(f.get("seed", 1)),
            "level": f.get("level", "medium")}


def _seeds(V, F, n, rng):
    """Area-weighted surface samples pushed a little inward: cells concentrate where the material is."""
    a = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    tri = rng.choice(len(F), size=n, p=a / a.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    p = (V[F[tri, 0]] * (1 - s)[:, None] + V[F[tri, 1]] * (s * (1 - r2))[:, None] + V[F[tri, 2]] * (s * r2)[:, None])
    nrm = np.cross(V[F[tri, 1]] - V[F[tri, 0]], V[F[tri, 2]] - V[F[tri, 0]])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-12
    return p - nrm * rng.uniform(0.05, 0.3, n)[:, None]


def _cells(pts, lo, hi):
    """Convex Voronoi cells (Manifold) clipped to the box lo..hi: box trimmed by the bisector planes of each
    point's Delaunay neighbours."""
    from scipy.spatial import Delaunay
    nb = [set() for _ in pts]
    if len(pts) >= 5:
        for simp in Delaunay(pts).simplices:
            for i in simp:
                nb[i].update(int(j) for j in simp if j != i)
    else:
        nb = [set(range(len(pts))) - {i} for i in range(len(pts))]
    box = g.box(*lo, *hi)
    cells = []
    for i, p in enumerate(pts):
        c = box
        for j in nb[i]:
            d = pts[j] - p
            L = np.linalg.norm(d)
            if L < 1e-9:
                continue
            n = d / L
            c = c.trim_by_plane((-n).tolist(), float(-n @ ((p + pts[j]) / 2)))  # keep the side of p
            if c.is_empty():
                break
        cells.append(c)
    return cells


def fracture_solid(final, n, seed=1):
    """Voronoi chunks of a Manifold -> [(Manifold chunk, centroid, volume)]; break faces are `rubble`."""
    from .mesh import manifold_to_arrays
    V, F, _ = manifold_to_arrays(final)
    rng = np.random.default_rng(seed)
    pts = _seeds(V, F, n, rng)
    lo, hi = V.min(0) - 0.5, V.max(0) + 0.5
    out = []
    g.set_current_element("fracture")
    for cell in _cells(pts, lo, hi):
        ch = final ^ g.tag(cell, INNER)
        for piece in ch.decompose():  # a cell may cut two separate walls: each its own chunk
            vol = piece.volume()
            if vol > 1e-6:
                out.append((piece, _centroid(piece), vol))
    return out


def _centroid(m):
    from .mesh import manifold_to_arrays
    V, F, _ = manifold_to_arrays(m)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, c))  # signed tetra volumes from the origin
    tot = vol6.sum()
    if abs(tot) < 1e-12:
        return V.mean(0)
    return ((a + b + c) * vol6[:, None]).sum(0) / (4 * tot)


def fracture_elements(result):
    """One chunk per element (its solids welded)."""
    out = []
    for eid in result.order:
        sol = [m for m, _ in result.elements[eid].solids]
        if not sol:
            continue
        m = g.union(sol)
        if not m.is_empty() and m.volume() > 1e-6:
            out.append((eid, m, _centroid(m), m.volume()))
    return out


def brick_labels(vox, n, seed=1, level=None):
    """Group bricks into n chunks (nearest of n seed bricks); level 'bricks' = every brick its own piece."""
    ijk = vox["ijk"]
    if level == "bricks" or n >= len(ijk):
        return np.arange(len(ijk))
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    seeds = ijk[rng.choice(len(ijk), size=n, replace=False)]
    return cKDTree(seeds).query(ijk)[1]
