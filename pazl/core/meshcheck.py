"""Find mesh defects by code, without looking at pictures: holes / torn edges, non-manifold edges, flipped or inside-out
parts, degenerate and sliver triangles, one part poking through another (body through clothes), coincident surfaces
that flicker (z-fighting). Every finding has a world position and a plain place ("front left, 62% height") so it can
be fixed or shown in the app. Works on any GLB under projects/ (skinned models are checked in their bind pose).

    from pazl.core import meshcheck; meshcheck.check("chars/hero.glb")
    .venv/Scripts/python.exe scripts/mesh_check.py chars/hero.glb"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from ..paths import PROJECTS


def _load(path):
    p = Path(path)
    p = p if p.is_absolute() else PROJECTS / p
    sc = trimesh.load(p, force="scene")
    out = []
    for node in sc.graph.nodes_geometry:
        T, key = sc.graph[node]
        g = sc.geometry[key]
        if not hasattr(g, "faces") or not len(g.faces):
            continue
        g = g.copy()
        g.apply_transform(T)
        g.merge_vertices(merge_tex=True, merge_norm=True)  # UV / shading seams are not holes
        out.append((node, g))
    return out


def _place(p, lo, hi):
    """Plain words for a point inside the model's box. Models face +Z, the figure's left is +X."""
    r = (np.asarray(p) - lo) / np.maximum(hi - lo, 1e-9)
    fb = "спереди" if r[2] > .6 else "сзади" if r[2] < .4 else "сбоку"
    lr = "слева" if r[0] > .6 else "справа" if r[0] < .4 else "по центру"
    return f"{fb} {lr}, {int(round(r[1] * 100))}% высоты"


def _sheetlike(piece):
    """Hair cards, ribbons, flat locks: open by design (many border edges for their size)."""
    e = piece.edges_sorted
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return (cnt == 1).mean() > .15 or len(piece.faces) < 12


def _closed(g):
    return [x for x in g.split(only_watertight=False) if x.is_watertight and x.volume > 0 and len(x.faces) >= 12]


def _inside(pieces, Q):
    ins = np.zeros(len(Q), bool)
    for x in pieces:
        box = np.all((Q > x.bounds[0]) & (Q < x.bounds[1]), axis=1)
        if box.any():
            ins[box] |= x.contains(Q[box])
    return ins


def _holes(name, g, lo, hi, min_len, solids, seams=None):
    """Open boundary loops. A loop that another part passes through (a sleeve around an arm, a hem around the legs)
    is an expected opening; one with nothing inside it is a tear you can see through. Open sheets are skipped."""
    res = []
    V = g.vertices
    for piece in g.split(only_watertight=False):
        if _sheetlike(piece):
            continue
        uniq, cnt = np.unique(piece.edges_sorted, axis=0, return_counts=True)
        open_e = uniq[cnt == 1]
        bad = uniq[cnt > 2]
        if len(bad):
            c = piece.vertices[bad].mean((0, 1))
            res.append({"kind": "non_manifold", "part": name, "edges": int(len(bad)), "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi)})
        if not len(open_e):
            continue
        graph = trimesh.graph.nx.Graph()
        graph.add_edges_from(open_e.tolist())
        PV = piece.vertices
        for comp in trimesh.graph.nx.connected_components(graph):
            sub = graph.subgraph(comp)
            L = float(sum(np.linalg.norm(PV[a] - PV[b]) for a, b in sub.edges))
            if L < min_len:
                continue
            c = PV[list(comp)].mean(0)
            if seams is not None and len(seams.data) and (seams.query(PV[list(comp)])[0] < 1e-4).mean() > .8:
                continue  # the border is shared with another part (clothes painted on the body): a seam, not a hole
            through = [n for n, m in solids if n != name and np.all((c > m.bounds[0]) & (c < m.bounds[1])) and m.contains([c])[0]]
            res.append({"kind": "opening" if through else "hole", "part": name, "edges": sub.number_of_edges(), "perimeter": round(L, 4),
                        "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi),
                        **({"around": through[0]} if through else {"fix": "close the hole (fill / weld the border) or cover it"})})
    return res


def _orientation(name, g, lo, hi):
    res = []
    for p in g.split(only_watertight=False):
        if len(p.faces) < 8:
            continue
        if not p.is_winding_consistent:
            res.append({"kind": "mixed_winding", "part": name, "faces": int(len(p.faces)), "at": np.round(p.centroid, 3).tolist(),
                        "where": _place(p.centroid, lo, hi), "fix": "trimesh fix_normals / flip the odd faces"})
        elif p.is_watertight and p.volume < 0:
            res.append({"kind": "inside_out", "part": name, "faces": int(len(p.faces)), "at": np.round(p.centroid, 3).tolist(),
                        "where": _place(p.centroid, lo, hi), "fix": "invert the piece"})
    return res


def _triangles(name, g, lo, hi, scale):
    T = g.triangles
    a, b, c = (np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3))
    area = g.area_faces
    longest = np.maximum(np.maximum(a, b), c)
    deg = area < (scale * 1e-4) ** 2
    sliver = ~deg & (2 * area / np.maximum(longest, 1e-12) < longest * .02)  # height < 2% of the long side
    res = []
    for kind, m in (("degenerate", deg), ("sliver", sliver)):
        if m.sum():
            cc = T[m].mean((0, 1))
            res.append({"kind": kind, "part": name, "faces": int(m.sum()), "at": np.round(cc, 3).tolist(), "where": _place(cc, lo, hi)})
    return res


def _between(parts, lo, hi, scale, samples):
    """Poke-through: the surface of an outer part (clothes, hair cap) dips inside a closed inner part (body), so the
    body shows through it - the torn look. Only shallow dips count (deep ones are buried roots, never seen).
    Z-fighting: two parts' surfaces on top of each other facing the same way - they flicker."""
    res = []
    for i, (na, A) in enumerate(parts):
        solid = [x for x in A.split(only_watertight=False) if not _sheetlike(x)]
        if not solid:
            continue
        A = trimesh.util.concatenate(solid)  # hair cards / strand roots are buried in the scalp on purpose
        P, fi = trimesh.sample.sample_surface(A, samples, seed=1)
        Na = A.face_normals[fi]
        for j, (nb, B) in enumerate(parts):
            if i == j:
                continue
            near = np.all((P > B.bounds[0] - scale * .01) & (P < B.bounds[1] + scale * .01), axis=1)
            if not near.any():
                continue
            Q = P[near]
            cp, dist, tri = trimesh.proximity.closest_point(B, Q)
            same = (np.einsum("ij,ij->i", B.face_normals[tri], Na[near]) > .9) & (dist < scale * 2e-4)
            if same.sum() > max(10, .02 * len(Q)) and i < j:
                c = Q[same].mean(0)
                res.append({"kind": "z_fighting", "part": f"{na} + {nb}", "points": int(same.sum()), "at": np.round(c, 3).tolist(),
                            "where": _place(c, lo, hi), "fix": "move one surface out a little or delete the copy"})
            closed = _closed(B)
            if closed:
                ins = _inside(closed, Q)
                if ins.sum() > .6 * len(P):
                    continue  # A lies inside B on purpose (an inner part), not a poke-through
                dip = ins & (dist > scale * .003) & (dist < scale * .015)  # deeper = buried, never seen
                if dip.sum() > max(8, .01 * len(Q)):
                    c = Q[dip].mean(0)
                    res.append({"kind": "poke_through", "part": f"{nb} through {na}", "points": int(dip.sum()),
                                "depth": round(float(dist[dip].max()), 4), "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi),
                                "fix": f"push {na} out (more ease) or {nb} in here"})
    return res


def check(path, hole_min=None, samples=2500, openings=False):
    """{'model', 'size', 'tris', 'problems': [...], 'summary': {kind: count}} - biggest first."""
    parts = _load(path)
    allv = np.vstack([g.vertices for _, g in parts])
    lo, hi = allv.min(0), allv.max(0)
    scale = float(np.linalg.norm(hi - lo))
    hole_min = scale * .02 if hole_min is None else hole_min
    probs = []
    solids = [(n, x) for n, g in parts for x in _closed(g)]  # per closed piece: touching blocks make the whole part non-manifold
    from scipy.spatial import cKDTree
    for name, g in parts:
        others = [x.vertices for n, x in parts if n != name]
        seams = cKDTree(np.vstack(others)) if others else None
        probs += _holes(name, g, lo, hi, hole_min, solids, seams) + _orientation(name, g, lo, hi) + _triangles(name, g, lo, hi, scale)
    probs += _between(parts, lo, hi, scale, samples)
    if not openings:  # sleeves, collars, hems: expected; ask for them with openings=True
        probs = [p for p in probs if p["kind"] != "opening"]
    w = {"poke_through": 0, "hole": 1, "inside_out": 2, "mixed_winding": 3, "z_fighting": 4, "non_manifold": 5, "sliver": 6, "degenerate": 7}
    probs.sort(key=lambda p: (w.get(p["kind"], 9), -p.get("perimeter", p.get("points", p.get("faces", 0)))))
    summ = {}
    for p in probs:
        summ[p["kind"]] = summ.get(p["kind"], 0) + 1
    return {"model": str(path), "size": np.round(hi - lo, 3).tolist(), "tris": int(sum(len(g.faces) for _, g in parts)),
            "parts": [n for n, _ in parts], "summary": summ, "problems": probs}


# ---------------------------------------------------------------- fixes
def push_out(V, inner: trimesh.Trimesh, gap=None):
    """Vertices of an outer part (hat, hair, clothes) that sit inside a closed inner part (body) or closer than `gap` to
    it are moved just outside its surface along its normal. Fixes poke_through without touching the rest."""
    V = np.array(V, float)
    inner = inner.copy()
    inner.merge_vertices(merge_tex=True, merge_norm=True)  # UV seams would make the body look open
    pieces = _closed(inner)
    if not pieces:
        return V
    gap = float(np.linalg.norm(inner.extents)) * .002 if gap is None else gap
    ins = _inside(pieces, V)
    cp, dist, tri = trimesh.proximity.closest_point(inner, V)
    move = ins | (dist < gap)
    V[move] = cp[move] + inner.face_normals[tri[move]] * gap
    return V


def push_out_faces(m: trimesh.Trimesh, inner: trimesh.Trimesh, rounds=3):
    """push_out for vertices, then again for faces whose centres still sink (long triangles over a rounded body):
    their corners move out by how deep the centre is."""
    m = m.copy()
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    solid_f = np.zeros(len(m.faces), bool)
    for k in np.unique(lab):  # hair cards / strands keep their buried roots; only solid pieces are pushed
        f = lab == k
        piece = trimesh.Trimesh(m.vertices, m.faces[f], process=False)
        solid_f[f] = not _sheetlike(piece)
    if not solid_f.any():
        return m
    vmask = np.zeros(len(m.vertices), bool)
    vmask[m.faces[solid_f].ravel()] = True
    V = np.array(m.vertices)
    V[vmask] = push_out(V[vmask], inner)
    m.vertices = V
    inner = inner.copy()
    inner.merge_vertices(merge_tex=True, merge_norm=True)
    pieces = _closed(inner)
    for _ in range(rounds):
        c = m.triangles_center
        ins = (_inside(pieces, c) if pieces else np.zeros(len(c), bool)) & solid_f
        if not ins.any():
            break
        cp, dist, tri = trimesh.proximity.closest_point(inner, c[ins])
        V = np.array(m.vertices)
        lift = inner.face_normals[tri] * (dist + float(np.linalg.norm(inner.extents)) * .002)[:, None]
        for f, d in zip(m.faces[ins], lift):
            V[f] += d / 1.0
        m.vertices = V
    return m


def clean(m: trimesh.Trimesh):
    """Drop zero-area faces (collapsed shrinkwrap points). Nothing is welded, so winding and UV seams stay intact."""
    m = m.copy()
    m.update_faces(m.area_faces > float(np.linalg.norm(m.extents)) ** 2 * 1e-9)
    m.remove_unreferenced_vertices()
    return m
