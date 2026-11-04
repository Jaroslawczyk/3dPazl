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
        g.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=6)  # UV / shading seams and float32 noise (<1 micron) are not holes
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
    if not (cnt == 1).any():
        return False  # closed, however small (a hair lock, a spike): solid
    return (cnt == 1).mean() > .15 or len(piece.faces) < 12


def _closed(g):
    return [x for x in g.split(only_watertight=False, repair=False) if x.is_watertight and x.volume > 0 and len(x.faces) >= 12]


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
    for piece in g.split(only_watertight=False, repair=False):
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
            whole = PV[np.unique(open_e)].mean(0)  # a rim broken into arcs by touching strands: judge the whole border too
            through = [n for n, m in solids if n != name and any(np.all((q > m.bounds[0]) & (q < m.bounds[1])) and m.contains([q])[0] for q in (c, whole))]
            res.append({"kind": "opening" if through else "hole", "part": name, "edges": sub.number_of_edges(), "perimeter": round(L, 4),
                        "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi),
                        **({"around": through[0]} if through else {"fix": "close the hole (fill / weld the border) or cover it"})})
    return res


def _orientation(name, g, lo, hi):
    res = []
    for p in g.split(only_watertight=False, repair=False):
        if len(p.faces) < 8:
            continue
        if not p.is_winding_consistent:
            res.append({"kind": "mixed_winding", "part": name, "faces": int(len(p.faces)), "at": np.round(p.centroid, 3).tolist(),
                        "where": _place(p.centroid, lo, hi), "fix": "trimesh fix_normals / flip the odd faces"})
        elif p.is_watertight and p.volume < 0:
            res.append({"kind": "inside_out", "part": name, "faces": int(len(p.faces)), "at": np.round(p.centroid, 3).tolist(),
                        "where": _place(p.centroid, lo, hi), "fix": "invert the piece"})
    return res


def lock_faces(m, max_faces=60):
    """Faces of small closed pieces (hair locks, spikes, claws): long and thin by design, never cut as slivers."""
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    out = np.zeros(len(m.faces), bool)
    for k in np.unique(lab):
        f = lab == k
        if f.sum() < max_faces and trimesh.Trimesh(m.vertices, m.faces[f]).is_watertight:
            out |= f
    return out


def bad_faces(m, scale):
    """(degenerate, sliver) masks with the same rules the report uses; scale = the whole model's diagonal."""
    T = m.triangles
    longest = np.max([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)], 0)
    deg = m.area_faces < (scale * 1e-4) ** 2
    return deg, ~deg & (2 * m.area_faces / np.maximum(longest, 1e-12) < longest * .02)


def _triangles(name, g, lo, hi, scale):
    g = g.copy()
    lab = trimesh.graph.connected_component_labels(g.face_adjacency, len(g.faces))
    keep = np.ones(len(g.faces), bool)
    for k in np.unique(lab):  # small closed pieces (hair locks, spikes) are long and thin by design: not slivers
        f = lab == k
        if f.sum() < 60 and trimesh.Trimesh(g.vertices, g.faces[f]).is_watertight:
            keep[f] = False
    g.update_faces(keep)
    if not len(g.faces):
        return []
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
        solid = [x for x in A.split(only_watertight=False, repair=False) if not _sheetlike(x) and len(x.faces) >= 60]  # locks: roots buried on purpose
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


def _loose(parts, lo, hi, scale):
    """floating: a piece of an accessory/garment that touches nothing (hair strand in the air);
    flat_sheet: one-sided paper pieces (hair cards) that look flat from the side - game hair should be solid locks."""
    from scipy.spatial import cKDTree
    res = []
    if len(parts) < 2:
        return res
    for name, g in parts:
        pieces = g.split(only_watertight=False, repair=False)
        if len(pieces) < 2 and len(parts) < 2:
            continue
        others_v = [h.vertices for n2, h in parts if n2 != name]
        seam = cKDTree(np.vstack(others_v)) if others_v else None
        # open pieces that are not patches stitched to another part (clothes painted on a block body are)
        flat = [x for x in pieces if _sheetlike(x) and len(x.faces) >= 2
                and not (seam is not None and (seam.query(x.vertices)[0] < 1e-5).mean() > .2)]
        if flat and name.lower() not in ("body",):
            c = np.vstack([x.centroid for x in flat]).mean(0)
            res.append({"kind": "flat_sheet", "part": name, "pieces": len(flat), "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi),
                        "fix": "make them solid locks (retopo.lock) or thicken them"})
        if name.lower() == "body":
            continue
        rest = [h for n2, h in parts if n2 != name]
        for i, x in enumerate(pieces):
            if len(x.faces) > 400:
                continue
            near = trimesh.util.concatenate([y for j, y in enumerate(pieces) if j != i] + rest)
            d = float(trimesh.proximity.closest_point(near, x.vertices)[1].min())  # to the surface, not to sparse vertices
            if d > scale * .01:
                c = x.centroid
                res.append({"kind": "floating", "part": name, "faces": int(len(x.faces)), "gap": round(float(d), 4),
                            "at": np.round(c, 3).tolist(), "where": _place(c, lo, hi), "fix": "move it onto the surface it should grow from"})
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
    probs += _between(parts, lo, hi, scale, samples) + _loose(parts, lo, hi, scale)
    if not openings:  # sleeves, collars, hems: expected; ask for them with openings=True
        probs = [p for p in probs if p["kind"] != "opening"]
    w = {"floating": 0, "poke_through": 0, "hole": 1, "flat_sheet": 8, "inside_out": 2, "mixed_winding": 3, "z_fighting": 4, "non_manifold": 5, "sliver": 6, "degenerate": 7}
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


def push_out_faces(m: trimesh.Trimesh, inner: trimesh.Trimesh, rounds=8):
    """push_out for vertices, then again for faces whose centres still sink (long triangles over a rounded body):
    their corners move out by how deep the centre is."""
    m = m.copy()
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    solid_f = np.zeros(len(m.faces), bool)
    for k in np.unique(lab):  # hair cards / strands / small locks keep their buried roots; only big solid pieces are pushed
        f = lab == k
        piece = trimesh.Trimesh(m.vertices, m.faces[f], process=False)
        solid_f[f] = not _sheetlike(piece) and f.sum() >= 60
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


def clean(m: trimesh.Trimesh, max_hole=12, scale=None):
    """Drop zero-area faces, drop slivers from open pieces (closing nothing), fill small holes (up to max_hole border
    edges) with a fan. Nothing is welded, so winding and UV seams stay intact."""
    m = m.copy()
    T = m.triangles
    L = np.max([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)], 0)
    zero = m.area_faces <= float(np.linalg.norm(m.extents)) ** 2 * 1e-9
    sliver = 2 * m.area_faces / np.maximum(L, 1e-12) < L * .02
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    e, cnt = np.unique(m.edges_sorted, axis=0, return_counts=True)
    open_v = np.zeros(len(m.vertices), bool)
    open_v[e[cnt == 1].ravel()] = True
    open_piece = {k for k in np.unique(lab) if open_v[m.faces[lab == k]].any()}
    on_border = open_v[m.faces].any(1)  # only slivers on an open border go: a closed lock glued to the hat keeps its faces
    m.update_faces(~zero & ~(sliver & on_border))
    m.remove_unreferenced_vertices()
    # slivers left in closed pieces have one very short edge: collapse it (both ends meet), drop what became flat
    T = m.triangles
    E = np.stack([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)], 1)
    labc = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    locks = np.zeros(len(m.faces), bool)  # small closed pieces (hair locks): collapsing their short fold edges tears them
    for k in np.unique(labc):
        f = labc == k
        if f.sum() < 60 and trimesh.Trimesh(m.vertices, m.faces[f]).is_watertight:
            locks |= f
    short = (E.min(1) < E.max(1) * .05) & ~locks
    if short.any():
        V = np.array(m.vertices)
        remap = np.arange(len(V))
        for f, j in zip(m.faces[short], E[short].argmin(1)):
            a, b = remap[f[j]], remap[f[(j + 1) % 3]]
            if a != b:
                V[a] = (V[a] + V[b]) / 2
                remap[remap == b] = a
        F = remap[m.faces]
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        m = trimesh.Trimesh(V, F, process=False)
        m.remove_unreferenced_vertices()
    if scale:  # whatever the report would still call degenerate / sliver (needles with no short edge): out, then refill
        deg, sl = bad_faces(m, scale)
        lab2 = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
        small_closed = np.zeros(len(m.faces), bool)  # thin closed locks of hair: their long faces are fine, cutting them opens holes
        for k in np.unique(lab2):
            f = lab2 == k
            if f.sum() < 60 and trimesh.Trimesh(m.vertices, m.faces[f]).is_watertight:
                small_closed |= f
        e2, c2 = np.unique(m.edges_sorted, axis=0, return_counts=True)
        ov = np.zeros(len(m.vertices), bool)
        ov[e2[c2 == 1].ravel()] = True
        drop = deg | (sl & ~small_closed & ov[m.faces].any(1))  # needles only where the surface is already open
        if drop.any():
            m.update_faces(~drop)
            m.remove_unreferenced_vertices()
    return fill_small_holes(m, max_hole)


def _tri_quality(a, b, c):
    """Height over the longest side: 0 for a needle, 0.87 for an equilateral triangle."""
    L = max(np.linalg.norm(a - b), np.linalg.norm(b - c), np.linalg.norm(c - a), 1e-12)
    return np.linalg.norm(np.cross(b - a, c - a)) / L / L


def fill_small_holes(m: trimesh.Trimesh, max_edges=12):
    """Close border loops of up to max_edges edges with a fan from their centre (the gaps left in a hair shell)."""
    e, cnt = np.unique(m.edges_sorted, axis=0, return_counts=True)
    open_e = e[cnt == 1]
    if not len(open_e):
        return m
    # directed border edges as they run in their faces, so the fan gets the same winding
    fe = np.vstack([m.faces[:, [0, 1]], m.faces[:, [1, 2]], m.faces[:, [2, 0]]])
    key = {tuple(sorted(x)) for x in open_e.tolist()}
    nxt = {int(a): int(b) for a, b in fe.tolist() if (min(a, b), max(a, b)) in key}
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(m.faces))
    sheet_v = np.zeros(len(m.vertices), bool)  # strands / cards stay open: closing them makes them "solid" for push_out
    for k in np.unique(lab):
        if _sheetlike(trimesh.Trimesh(m.vertices, m.faces[lab == k], process=False)):
            sheet_v[m.faces[lab == k].ravel()] = True
    V, F, seen = list(m.vertices), [list(f) for f in m.faces], set()
    for start in list(nxt):
        if start in seen:
            continue
        loop, v = [], start
        while v in nxt and v not in seen and len(loop) <= max_edges + 1:
            seen.add(v)
            loop.append(v)
            v = nxt[v]
        if v != start or len(loop) < 3 or len(loop) > max_edges or sheet_v[loop].any():
            continue
        P = m.vertices[loop]
        if len(loop) == 3:
            F.append([loop[2], loop[1], loop[0]])
            continue
        # fan from the loop vertex that sees the others best (no needle triangles from a near-collinear centre)
        best = max(range(len(loop)), key=lambda k: min(_tri_quality(P[k], P[(k + i) % len(loop)], P[(k + i + 1) % len(loop)])
                                                          for i in range(1, len(loop) - 1)))
        for i in range(1, len(loop) - 1):
            a, b = loop[(best + i) % len(loop)], loop[(best + i + 1) % len(loop)]
            F.append([b, a, loop[best]])
    out = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    out.fix_normals(multibody=True)
    return out
