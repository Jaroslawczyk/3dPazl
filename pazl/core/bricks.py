"""Brick builder: the model as a grid of cubic bricks (voxel / toy-brick games).

The welded shell is voxelized on its surface (walls, roofs, floors become 1-2 bricks thick, rooms stay hollow);
each brick takes the material and element of the surface it came from. Output:
- cull=True: only brick faces that border empty space (what can be seen) - a light, clean mesh;
- cull=False: every brick a full cube (12 triangles), faces on faces - each brick can later be its own object.
"""
from __future__ import annotations

import numpy as np
import trimesh

from . import geo as g

MAX_BRICKS = 250_000

# 6 neighbours: axis, sign -> the 4 corners of that cube face (unit cube 0..1), CCW seen from outside
_FACES = {
    (0, -1): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], (0, 1): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (1, -1): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], (1, 1): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    (2, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)], (2, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
}


def _majority(group, value, n_groups):
    """Most frequent value per group id -> array (n_groups,), -1 where a group has no samples."""
    out = np.full(n_groups, -1, np.int64)
    if not len(group):
        return out
    nv = int(value.max()) + 1
    combo, counts = np.unique(group * nv + value, return_counts=True)
    g_, v_ = combo // nv, combo % nv
    order = np.lexsort((-counts, g_))  # per group: the biggest count first
    g_, v_ = g_[order], v_[order]
    first = np.r_[True, g_[1:] != g_[:-1]]
    out[g_[first]] = v_[first]
    return out


GLASSY = ("glass", "stained_glass")


def _raster(rings, xs, ys):
    """Even-odd fill of polygon rings on a grid of points -> bool (len(ys), len(xs))."""
    out = np.zeros((len(ys), len(xs)), bool)
    if not rings:
        return out
    E = np.vstack([np.c_[r, np.roll(r, -1, axis=0)] for r in (np.asarray(r_, float) for r_ in rings) if len(r) >= 3])
    x0, y0, x1, y1 = E.T
    for jy, y in enumerate(ys):
        m = (y0 <= y) != (y1 <= y)
        if not m.any():
            continue
        xi = np.sort(x0[m] + (y - y0[m]) * (x1[m] - x0[m]) / (y1[m] - y0[m]))
        out[jy] = np.searchsorted(xi, xs) % 2 == 1
    return out


def _occupancy(solid, origin, size, n, sub=3):
    """Bricks the solid really fills: the model is sliced (sub layers per brick), each slice rasterised on
    sub x sub points per brick; a brick is filled if any of its sub x sub x sub samples is inside. Openings
    wider than a brick (windows, doors) stay open; thin walls still get bricks."""
    offs = (np.arange(sub) + 0.5) / sub
    xs = origin[0] + (np.arange(n[0])[:, None] + offs[None, :]).ravel() * size
    ys = origin[1] + (np.arange(n[1])[:, None] + offs[None, :]).ravel() * size
    occ = np.zeros(tuple(n), bool)
    for k in range(n[2]):
        for o in offs:
            rings = solid.slice(float(origin[2] + (k + o) * size)).to_polygons()
            if rings:
                ins = _raster(rings, xs, ys).T  # (x, y)
                occ[:, :, k] |= ins.reshape(n[0], sub, n[1], sub).any(axis=(1, 3))
    return occ


def voxelize(solid, V, F, mats, elems, size: float):
    """-> dict(ijk (N,3), origin, size, mat (N,), elem (N,), dmat (N,6), delem (N,6), names).
    Presence: bricks the solid fills (_occupancy) + glass bricks where windows are glazed. Colours: every brick
    FACE takes the material of the surface facing that way (area majority of surface samples in that brick or
    the nearest sampled brick): outer plaster outside, interior paint inside, glass in windows."""
    from scipy.spatial import cKDTree
    size = float(size)
    empty = {"ijk": np.zeros((0, 3), int), "origin": np.zeros(3), "size": size, "mat": np.array([]), "elem": np.array([]),
             "dmat": np.zeros((0, 6), np.int64), "delem": np.zeros((0, 6), np.int64), "mat_names": np.array([]),
             "elem_names": np.array([])}
    if len(F) == 0:
        return empty
    mat_names, mat_idx = np.unique(np.asarray(mats).astype(str), return_inverse=True)
    elem_names, elem_idx = np.unique(np.asarray(elems).astype(str), return_inverse=True)
    nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    ax = np.argmax(np.abs(nrm), axis=1)
    dslot = ax * 2 + (nrm[np.arange(len(F)), ax] > 0)  # 0:-x 1:+x 2:-y 3:+y 4:-z 5:+z
    v2, f2, idx = trimesh.remesh.subdivide_to_size(V, F, max_edge=size * 0.45, max_iter=12, return_index=True)
    pts = np.vstack([v2[f2].mean(axis=1), v2[f2[:, 0]], v2[f2[:, 1]], v2[f2[:, 2]]])
    src = np.concatenate([idx] * 4)
    un = nrm / (np.linalg.norm(nrm, axis=1)[:, None] + 1e-12)
    pts = pts - un[src] * size * 0.02  # a hair into the solid: a wall exactly on a brick boundary colours its own brick
    origin = np.floor(V.min(axis=0) / size) * size  # bricks sit on the grid (ground at whole bricks)
    n = (np.ceil((V.max(axis=0) - origin) / size).astype(int) + 1)
    if int(np.prod(n)) > MAX_BRICKS * 40:
        raise ValueError(f"model too big for {size} m bricks; use a bigger brick size")
    s_ijk = np.floor((pts - origin) / size + 1e-6).astype(np.int64)
    surf, brick = np.unique(s_ijk, axis=0, return_inverse=True)
    brick = brick.ravel()
    ns = len(surf)
    sdm = _majority(brick * 6 + dslot[src], mat_idx[src], ns * 6).reshape(ns, 6)
    sde = _majority(brick * 6 + dslot[src], elem_idx[src], ns * 6).reshape(ns, 6)
    sbm, sbe = _majority(brick, mat_idx[src], ns), _majority(brick, elem_idx[src], ns)
    occ = _occupancy(solid, origin, size, n)
    glassy = np.isin(mat_names[sbm], GLASSY)
    gl = surf[glassy]
    gl = gl[(gl >= 0).all(1) & (gl < n).all(1)]
    occ[gl[:, 0], gl[:, 1], gl[:, 2]] = True  # glazed openings become glass bricks
    ijk = np.argwhere(occ)
    if len(ijk) > MAX_BRICKS:
        raise ValueError(f"{len(ijk)} bricks - too many; use a bigger brick size (now {size} m)")
    near = cKDTree(surf).query(ijk)[1]  # colours from the nearest surface-sampled brick
    return {"ijk": ijk, "origin": origin, "size": size, "mat": mat_names[sbm[near]], "elem": elem_names[sbe[near]],
            "dmat": sdm[near], "delem": sde[near], "mat_names": mat_names, "elem_names": elem_names}


def brick_mesh(vox, cull=True, labels=None):
    """-> list of (V, F, mats, elems) triangle soup per brick face. labels (N,) splits the bricks into groups
    (destruction chunks): with cull=True a face between two different groups is kept (the break surface)."""
    ijk, s, o = vox["ijk"], vox["size"], vox["origin"]
    if len(ijk) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), int), np.array([]), np.array([]), np.array([], int)
    lo = ijk.min(0) - 1
    grid_shape = tuple(ijk.max(0) - lo + 2)
    occ = np.full(grid_shape, -2, dtype=np.int64)  # -2 = empty, else group label
    lab = np.zeros(len(ijk), np.int64) if labels is None else np.asarray(labels, np.int64)
    loc = ijk - lo
    occ[loc[:, 0], loc[:, 1], loc[:, 2]] = lab
    Vs, Fs, Ms, Es, Ls = [], [], [], [], []
    base = 0
    for (ax, sg), corners in _FACES.items():
        if cull:
            nb = loc.copy()
            nb[:, ax] += sg
            other = occ[nb[:, 0], nb[:, 1], nb[:, 2]]
            keep = other != lab  # empty, or another chunk
        else:
            keep = np.ones(len(ijk), bool)
        k = np.flatnonzero(keep)
        if not len(k):
            continue
        c = np.asarray(corners, float)
        verts = (o + (ijk[k][:, None, :] + c[None, :, :]) * s).reshape(-1, 3)
        n = len(k)
        q = base + np.arange(n)[:, None] * 4
        Fs.append(np.vstack([np.hstack([q, q + 1, q + 2]), np.hstack([q, q + 2, q + 3])]))
        Vs.append(verts)
        d = ax * 2 + (sg > 0)  # the material of the surface facing this way, else the brick's own
        fm = np.where(vox["dmat"][k, d] >= 0, vox["mat_names"][np.maximum(vox["dmat"][k, d], 0)], vox["mat"][k])
        fe = np.where(vox["delem"][k, d] >= 0, vox["elem_names"][np.maximum(vox["delem"][k, d], 0)], vox["elem"][k])
        Ms.append(np.concatenate([fm, fm]))
        Es.append(np.concatenate([fe, fe]))
        Ls.append(np.concatenate([lab[k], lab[k]]))
        base += n * 4
    return np.vstack(Vs), np.vstack(Fs), np.concatenate(Ms), np.concatenate(Es), np.concatenate(Ls)


def bricks_of(result):
    """Voxel data of a BuildResult (cached on it) for recipe build_mode == 'bricks'."""
    rec = result.recipe or {}
    size = float(rec.get("brick_size") or 0.5)
    cache = getattr(result, "_bricks", None)
    if cache and cache[0] == size:
        return cache[1]
    from .mesh import manifold_to_arrays, tri_materials
    V, F, oid = manifold_to_arrays(result.final())
    mats, elems = tri_materials(oid)
    vox = voxelize(result.final(), V, F, mats, elems, size)
    result._bricks = (size, vox)
    return vox


def is_bricks(result) -> bool:
    return bool(result is not None and (result.recipe or {}).get("build_mode") == "bricks")


def brick_count(result) -> int:
    return int(len(bricks_of(result)["ijk"])) if is_bricks(result) else 0


__all__ = ["voxelize", "brick_mesh", "bricks_of", "is_bricks", "brick_count", "g"]
