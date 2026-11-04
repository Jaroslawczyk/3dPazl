"""mesh_fix: repair a finished GLB in place until mesh_check has nothing fixable left.

Works on the file itself (float32 positions, the real index buffers), so what is checked is what was fixed, and every
vertex attribute (UV, normals, skin joints/weights, colours) is kept: faces are only removed or added between EXISTING
vertices, and vertex positions are only moved. Steps per round:
  1. degenerate and sliver triangles out (the report's own rules);
  2. small holes closed with a fan from the border vertex that gives the best triangles (no new vertices);
  3. outer solid parts (hats, hair caps, clothes, pets) pushed out of closed inner parts (the body) - strands/cards that
     are buried on purpose are left alone;
then mesh_check again; stop when clean or when a round changes nothing.

    from pazl.core import meshfix; meshfix.fix("chars/hero.glb")
    .venv/Scripts/python.exe scripts/mesh_fix.py chars/hero.glb"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import trimesh

from ..paths import PROJECTS
from . import meshcheck

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}


class Glb:
    """Minimal GLB editor: read accessors, append new data, save."""

    def __init__(self, path):
        self.path = Path(path)
        b = self.path.read_bytes()
        n = struct.unpack_from("<I", b, 12)[0]
        self.js = json.loads(b[20:20 + n])
        off = 20 + n
        ln = struct.unpack_from("<I", b, off)[0]
        self.bin = bytearray(b[off + 8:off + 8 + ln])

    def read(self, ai):
        a = self.js["accessors"][ai]
        v = self.js["bufferViews"][a["bufferView"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        dt = np.dtype(COMP[a["componentType"]])
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = v.get("byteStride", 0) or dt.itemsize * k
        raw = np.frombuffer(bytes(self.bin[start:start + stride * (a["count"] - 1) + dt.itemsize * k]), np.uint8)
        out = np.empty((a["count"], k), dt)
        for i in range(a["count"]):
            out[i] = np.frombuffer(raw[i * stride:i * stride + dt.itemsize * k].tobytes(), dt)
        return out if k > 1 else out[:, 0]

    def write(self, ai, arr, target=None):
        """Point accessor ai at new data appended to the binary chunk."""
        a = self.js["accessors"][ai]
        arr = np.ascontiguousarray(arr.astype(COMP[a["componentType"]]))
        while len(self.bin) % 4:
            self.bin.append(0)
        self.js["bufferViews"].append({"buffer": 0, "byteOffset": len(self.bin), "byteLength": arr.nbytes, **({"target": target} if target else {})})
        self.bin.extend(arr.tobytes())
        a.update({"bufferView": len(self.js["bufferViews"]) - 1, "count": int(len(arr)), "byteOffset": 0})
        if a["type"] == "VEC3" and arr.ndim == 2:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()

    def save(self):
        self.js["buffers"][0]["byteLength"] = len(self.bin)
        j = json.dumps(self.js, separators=(",", ":")).encode()
        j += b" " * (-len(j) % 4)
        while len(self.bin) % 4:
            self.bin.append(0)
        body = struct.pack("<I4s", len(j), b"JSON") + j + struct.pack("<I4s", len(self.bin), b"BIN\0") + bytes(self.bin)
        self.path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


def _world(js):
    """World matrix of every node."""
    nodes = js.get("nodes", [])
    par = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}

    def local(n):
        if "matrix" in n:
            return np.array(n["matrix"], float).reshape(4, 4).T
        T = trimesh.transformations.translation_matrix(n.get("translation", [0, 0, 0]))
        x, y, z, w = n.get("rotation", [0, 0, 0, 1])
        R = trimesh.transformations.quaternion_matrix([w, x, y, z])
        S = np.diag([*n.get("scale", [1, 1, 1]), 1])
        return T @ R @ S

    out = {}
    for i in range(len(nodes)):
        M, j = local(nodes[i]), i
        while j in par:
            j = par[j]
            M = local(nodes[j]) @ M
        out[i] = M
    return out


def _parts(g: Glb):
    """[(name, primitive dict, world matrix, positions world, faces)] for every triangle primitive.
    Skinned meshes are taken in their bind pose (the node transform is ignored, as glTF says)."""
    W = _world(g.js)
    out = []
    for ni, n in enumerate(g.js.get("nodes", [])):
        if "mesh" not in n:
            continue
        M = np.eye(4) if "skin" in n else W[ni]
        for pi, p in enumerate(g.js["meshes"][n["mesh"]]["primitives"]):
            if p.get("mode", 4) != 4 or "indices" not in p:
                continue
            P = g.read(p["attributes"]["POSITION"]).astype(float)
            F = g.read(p["indices"]).astype(np.int64).reshape(-1, 3)
            out.append((n.get("name") or f"mesh{n['mesh']}", p, M, trimesh.transform_points(P, M), F))
    return out


def _weld(P):
    """Index of the first vertex at the same position (UV / normal seams split vertices)."""
    _, first, inv = np.unique(np.round(P, 6), axis=0, return_index=True, return_inverse=True)
    return first[inv.ravel()]


def _quality(T):
    E = np.stack([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)], 1)
    L = E.max(1)
    A = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    return A, L


def _manifold(F, w, P):
    """Duplicate faces out; on an edge shared by more than two faces keep the two biggest (a collapsed fold)."""
    Fw = w[F]
    _, first = np.unique(np.sort(Fw, 1), axis=0, return_index=True)
    keep = np.zeros(len(F), bool)
    keep[first] = True
    keep &= (Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])
    A = np.linalg.norm(np.cross(P[Fw[:, 1]] - P[Fw[:, 0]], P[Fw[:, 2]] - P[Fw[:, 0]]), axis=1)
    edges = {}
    for i in np.flatnonzero(keep):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges.setdefault(tuple(sorted((Fw[i, a], Fw[i, b]))), []).append(i)
    for fs in edges.values():
        if len(fs) > 2:
            for i in sorted(fs, key=lambda i: -A[i])[2:]:
                keep[i] = False
    return F[keep], int((~keep).sum())


def _drop_bad(P, F, scale, w=None):
    T = P[F]
    A, L = _quality(T)
    bad = (A < (scale * 1e-4) ** 2) | (2 * A / np.maximum(L, 1e-12) < L * .02)
    if w is not None and bad.any():  # thin faces of closed hair locks stay (same rule as mesh_check)
        locks = meshcheck.lock_faces(trimesh.Trimesh(P, w[F], process=False))
        bad &= ~locks | (A < (scale * 1e-4) ** 2)
    return F[~bad], int(bad.sum())


def _fill(P, F, w, max_edges=12):
    """Close border loops (on welded topology) of up to max_edges edges, with existing vertices only."""
    Fw = w[F]
    e = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
    key = np.sort(e, 1)
    u, cnt = np.unique(key, axis=0, return_counts=True)
    open_keys = {tuple(x) for x in u[cnt == 1].tolist()}
    if not open_keys:
        return F, 0, []
    lab = trimesh.graph.connected_component_labels(trimesh.Trimesh(P, Fw, process=False).face_adjacency, len(F))
    sheet = set()
    for k in np.unique(lab):
        piece = trimesh.Trimesh(P, Fw[lab == k], process=False)
        if meshcheck._sheetlike(piece):
            sheet |= set(Fw[lab == k].ravel().tolist())
    directed, orig = set(), {}
    for (a, b), (oa, ob) in zip(e.tolist(), np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]).tolist()):
        if (min(a, b), max(a, b)) in open_keys:
            directed.add((a, b))
            orig.setdefault(a, oa)
            orig.setdefault(b, ob)
    # small cycles of the border graph (a border vertex can be shared with a strand: plain "next" walking breaks there)
    G = trimesh.graph.nx.Graph()
    G.add_edges_from(open_keys)
    new, added, cracks = [], 0, []
    for loop in trimesh.graph.nx.cycle_basis(G):
        if not 3 <= len(loop) <= max_edges or set(loop) <= sheet:
            continue
        if (loop[0], loop[1]) not in directed:  # walk the way the faces run along the border
            loop = loop[::-1]
        if any((loop[i], loop[(i + 1) % len(loop)]) not in directed for i in range(len(loop))):
            continue  # not a clean border loop

        Q = P[loop]
        n = len(loop)
        qual = lambda k: min(meshcheck._tri_quality(Q[k], Q[(k + i) % n], Q[(k + i + 1) % n]) for i in range(1, n - 1))  # noqa: E731
        best = max(range(n), key=qual)
        if qual(best) < .03:  # a crack (nearly straight border): any fan is a needle, zip it shut instead
            cracks.append(loop)
            continue
        for i in range(1, n - 1):
            a, b = loop[(best + i) % n], loop[(best + i + 1) % n]
            new.append([orig[b], orig[a], orig[loop[best]]])
        added += 1
    return (np.vstack([F, np.array(new)]) if new else F), added, cracks


def _zip(P, w, loop):
    """Pull the two sides of a crack together: nearest non-neighbour border vertices meet at their midpoint (exactly the
    same position, so they weld). Returns the new positions."""
    P = P.copy()
    n = len(loop)
    pairs = sorted(((np.linalg.norm(P[loop[i]] - P[loop[j]]), i, j) for i in range(n) for j in range(i + 2, n)
                    if not (i == 0 and j == n - 1)))
    used = set()
    for _, i, j in pairs:
        if i in used or j in used:
            continue
        used |= {i, j}
        mid = (P[loop[i]] + P[loop[j]]) / 2
        P[(w == loop[i]) | (w == loop[j])] = mid
    for i in set(range(n)) - used:  # odd one out joins its nearest neighbour on the border
        k = min((x for x in range(n) if x != i), key=lambda x: np.linalg.norm(P[loop[x]] - P[loop[i]]))
        P[w == loop[i]] = P[loop[k]]
    return P


def fix(path, rounds=5, max_hole=12, log=None):
    """Repair the GLB in place. Returns {'before', 'after', 'rounds': [...]} (mesh_check summaries)."""
    p = Path(path)
    p = p if p.is_absolute() else PROJECTS / p
    before = meshcheck.check(p)["summary"]
    score = lambda rep: sum(rep.values())  # noqa: E731
    best, best_score = p.read_bytes(), score(before)  # never hand back a file worse than it came in
    hist = []
    for r in range(rounds):
        g = Glb(p)
        parts = _parts(g)
        if not parts:
            break
        allP = np.vstack([x[3] for x in parts])
        scale = float(np.linalg.norm(np.ptp(allP, 0)))
        closed = {name: meshcheck._closed(_welded_mesh(P, F)) for name, _, _, P, F in parts}
        changed = {"dropped": 0, "filled": 0, "pushed": 0}
        for name, prim, M, P, F in parts:
            w = _weld(P)
            F2, nm = _manifold(F, w, P)
            F2, d = _drop_bad(P, F2, scale, w)
            d += nm
            F2, f, cracks = _fill(P, F2, w, max_hole)
            zipped = 0
            for loop in cracks:
                P = _zip(P, w, loop)
                zipped += 1
            # push solid pieces out of other parts' closed pieces (body)
            moved = 0
            inner = [x for n2, xs in closed.items() if n2 != name for x in xs]
            if inner:
                m = trimesh.Trimesh(P, w[F2], process=False)
                lab = trimesh.graph.connected_component_labels(m.face_adjacency, len(F2))
                solid_v = np.zeros(len(P), bool)
                for k in np.unique(lab):
                    piece = trimesh.Trimesh(P, w[F2][lab == k], process=False)
                    if not meshcheck._sheetlike(piece) and (lab == k).sum() >= 60:  # small locks keep buried roots
                        solid_v[F2[lab == k].ravel()] = True
                if solid_v.any():
                    body = trimesh.util.concatenate(inner)
                    ins = meshcheck._inside(inner, P[solid_v])
                    # only vertices of parts that are mostly outside the body (a hat, not a tongue inside the head)
                    if ins.any() and ins.mean() < .6:
                        idx = np.flatnonzero(solid_v)[ins]
                        cp, dist, tri = trimesh.proximity.closest_point(body, P[idx])
                        P = P.copy()
                        P[idx] = cp + body.face_normals[tri] * scale * .002
                        moved = len(idx)
            if d or f or moved or zipped:
                if moved or zipped:
                    local = trimesh.transform_points(P, np.linalg.inv(M))
                    g.write(prim["attributes"]["POSITION"], local.astype(np.float32), 34962)
                ia = prim["indices"]
                dt = np.uint32 if F2.max() > 65535 or g.js["accessors"][ia]["componentType"] == 5125 else np.uint16
                g.js["accessors"][ia]["componentType"] = 5125 if dt == np.uint32 else 5123
                g.write(ia, F2.ravel().astype(dt), 34963)
            changed["dropped"] += d
            changed["filled"] += f + zipped
            changed["pushed"] += moved
        if not any(changed.values()):
            break
        g.save()
        rep = meshcheck.check(p)["summary"]
        if hist and rep == hist[-1]["left"] and not changed["dropped"] and not changed["filled"]:
            hist.append({**changed, "left": rep})
            break  # only pushes that change nothing: stop
        hist.append({**changed, "left": rep})
        if score(rep) < best_score:
            best, best_score = p.read_bytes(), score(rep)
        if log:
            log(f"round {r + 1}: {changed} -> {rep or 'clean'}")
        if not rep:
            break
    if p.read_bytes() != best:
        p.write_bytes(best)
    return {"model": str(path), "before": before, "after": meshcheck.check(p)["summary"], "rounds": hist}


def _welded_mesh(P, F):
    w = _weld(P)
    m = trimesh.Trimesh(P, w[F], process=False)
    m.remove_unreferenced_vertices()
    return m
