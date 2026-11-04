"""Model import for characters: OBJ (with .mtl and textures), FBX, GLB/GLTF, DAE, STL, PLY -> one vertex-coloured GLB in
projects/imports/, Y up, standing on the ground, centred, facing +Z. Binary FBX is read by our own small parser (geometry,
node transforms, diffuse colours), so Blender is not needed; bones and animation inside the file are not kept."""
from __future__ import annotations

import math
import re
import shutil
import struct
import zlib
from pathlib import Path, PurePosixPath

import numpy as np
import trimesh

from ...paths import PROJECTS

IMPORTS = PROJECTS / "imports"
FORMATS = (".obj", ".fbx", ".glb", ".gltf", ".dae", ".stl", ".ply")
_ARR = {b"f": ("<f4", 4), b"d": ("<f8", 8), b"l": ("<i8", 8), b"i": ("<i4", 4), b"b": ("<u1", 1)}
_ONE = {b"Y": "<h", b"C": "<B", b"I": "<i", b"F": "<f", b"D": "<d", b"L": "<q"}


def _props(b, o, n):
    out = []
    for _ in range(n):
        t = b[o:o + 1]
        o += 1
        if t in _ONE:
            out.append(struct.unpack_from(_ONE[t], b, o)[0])
            o += struct.calcsize(_ONE[t])
        elif t in _ARR:
            ln, enc, size = struct.unpack_from("<III", b, o)
            o += 12
            raw = b[o:o + size]
            o += size
            out.append(np.frombuffer(zlib.decompress(raw) if enc else raw, _ARR[t][0], ln))
        elif t in (b"S", b"R"):
            size = struct.unpack_from("<I", b, o)[0]
            o += 4
            out.append(b[o:o + size].decode("utf8", "replace") if t == b"S" else b[o:o + size])
            o += size
        else:
            raise ValueError("повреждённый FBX")
    return out


def _nodes(b, o, end, wide):
    """[(name, props, children)] of one FBX level."""
    fmt, hs = ("<QQQ", 24) if wide else ("<III", 12)
    res = []
    while o < end:
        e, n, ln = struct.unpack_from(fmt, b, o)
        if e == 0:
            break
        k = b[o + hs]
        name = b[o + hs + 1:o + hs + 1 + k].decode("utf8", "replace")
        p = o + hs + 1 + k
        res.append((name, _props(b, p, n), _nodes(b, p + ln, e, wide) if p + ln < e else []))
        o = e
    return res


def _kid(n, name):
    return next((c for c in n[2] if c[0] == name), None)


def _p70(n):
    p = _kid(n, "Properties70")
    return {c[1][0]: c[1][4:] for c in p[2]} if p else {}


def _matrix(p):
    T = np.eye(4)
    rx, ry, rz = (math.radians(v) for v in p.get("Lcl Rotation", (0, 0, 0)))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    R = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    T[:3, :3] = R * np.array(p.get("Lcl Scaling", (1, 1, 1)), float)
    T[:3, 3] = p.get("Lcl Translation", (0, 0, 0))
    return T


def read_fbx(data: bytes):
    """(V, F, C): merged mesh in metres, Y up."""
    if data[:18] != b"Kaydara FBX Binary":
        raise ValueError("текстовый FBX не читается: сохраните его как двоичный (binary) или в OBJ")
    ver = struct.unpack_from("<I", data, 23)[0]
    top = _nodes(data, 27, len(data), ver >= 7500)
    get = lambda n: next((x for x in top if x[0] == n), None)  # noqa: E731
    objs, conn, gs = get("Objects"), get("Connections"), get("GlobalSettings")
    if not objs:
        raise ValueError("в FBX нет объектов")
    g = _p70(gs) if gs else {}
    unit = float((g.get("UnitScaleFactor") or (1,))[0]) / 100
    zup = (g.get("UpAxis") or (1,))[0] == 2
    geos = {n[1][0]: n for n in objs[2] if n[0] == "Geometry" and _kid(n, "Vertices")}
    models = {n[1][0]: n for n in objs[2] if n[0] == "Model"}
    mats = {n[1][0]: n for n in objs[2] if n[0] == "Material"}
    parent, geo_of, col_of = {}, {}, {}
    for c in (conn[2] if conn else []):
        if c[1][0] != "OO":
            continue
        a, b = c[1][1], c[1][2]
        if a in geos:
            geo_of.setdefault(b, []).append(a)
        elif a in mats:
            col_of.setdefault(b, _p70(mats[a]).get("DiffuseColor"))
        elif a in models:
            parent[a] = b

    def world(i):
        T = _matrix(_p70(models[i]))
        return world(parent[i]) @ T if parent.get(i) in models else T

    Vs, Fs, Cs, off = [], [], [], 0
    for mid, gids in geo_of.items():
        if mid not in models:
            continue
        T = world(mid)
        col = col_of.get(mid)
        col = np.array(col[:3], float) if col else np.array([.8, .8, .8])
        for gid in gids:
            n = geos[gid]
            V = np.asarray(_kid(n, "Vertices")[1][0], float).reshape(-1, 3)
            idx = _kid(n, "PolygonVertexIndex")[1][0].astype(np.int64)
            ends = np.flatnonzero(idx < 0)
            idx = np.where(idx < 0, ~idx, idx)
            tri, s = [], 0
            for e in ends:  # fan-triangulate polygons
                tri += [(idx[s], idx[i], idx[i + 1]) for i in range(s + 1, e)]
                s = e + 1
            Vs.append(V @ T[:3, :3].T + T[:3, 3])
            Fs.append(np.array(tri, np.int64).reshape(-1, 3) + off)
            Cs.append(np.tile(col, (len(V), 1)))
            off += len(V)
    if not Vs or not off:
        raise ValueError("в FBX нет геометрии")
    V = np.vstack(Vs) * unit
    if zup:
        V = V[:, [0, 2, 1]] * (1, 1, -1)
    return V, np.vstack(Fs), np.vstack(Cs)


def _bake(g):
    """Texture -> vertex colours. The mesh is subdivided first, so a face painted on a few big triangles stays readable."""
    img = getattr(g.visual.material, "baseColorTexture", None) or getattr(g.visual.material, "image", None)
    uv = getattr(g.visual, "uv", None)
    if img is None or uv is None or len(uv) != len(g.vertices):
        return None
    V, F, uv = np.asarray(g.vertices, float), np.asarray(g.faces), np.asarray(uv, float)
    a = np.asarray(img.convert("RGB"), dtype=np.uint8)
    if len(np.unique(a.reshape(-1, 3), axis=0)) <= 128:
        # Palette atlases assign one flat colour to each original face. Sample at
        # face centres and split shared vertices at colour seams instead of
        # subdividing the whole mesh just to bake a tiny swatch texture.
        h, w = a.shape[:2]
        centers = uv[F].mean(axis=1)
        colors = a[((1 - centers[:, 1] % 1) * (h - 1)).astype(int),
                   ((centers[:, 0] % 1) * (w - 1)).astype(int)]
        vertices, vertex_colors, faces, cache = [], [], np.empty_like(F), {}
        for fi, face in enumerate(F):
            color = tuple(map(int, colors[fi]))
            for ci, vi in enumerate(face):
                key = (int(vi), color)
                if key not in cache:
                    cache[key] = len(vertices)
                    vertices.append(V[vi])
                    vertex_colors.append(color)
                faces[fi, ci] = cache[key]
        return np.asarray(vertices), faces, np.asarray(vertex_colors, dtype=float) / 255
    while len(F) * 4 <= 24000:  # stays under the "high" quality limit, so block bodies are not simplified out of shape
        V, F, at = trimesh.remesh.subdivide(V, F, vertex_attributes={"uv": uv})
        uv = at["uv"]
    a = a.astype(float) / 255
    h, w = a.shape[:2]
    C = a[((1 - uv[:, 1] % 1) * (h - 1)).astype(int), ((uv[:, 0] % 1) * (w - 1)).astype(int)]
    return V, F, C


def _read_scene(path):
    sc = trimesh.load(path, force="scene")
    Vs, Fs, Cs, Ms, off, mats = [], [], [], [], 0, {}
    for g in sc.dump(concatenate=False):
        if not hasattr(g, "faces") or not len(g.faces):
            continue
        mid = mats.setdefault(id(g), len(mats))  # one mesh of the file
        try:
            b = _bake(g) if getattr(g.visual, "kind", None) == "texture" else None
        except Exception:
            b = None
        if b:
            Vs.append(b[0]); Fs.append(b[1] + off); Cs.append(b[2]); Ms.append(np.full(len(b[0]), mid))
            off += len(b[0])
            continue
        try:
            c = np.asarray(g.visual.to_color().vertex_colors, float)[:, :3] / 255
        except Exception:
            c = np.full((len(g.vertices), 3), .8)
        if len(c) != len(g.vertices):
            c = np.full((len(g.vertices), 3), .8)
        Vs.append(np.asarray(g.vertices, float)); Fs.append(np.asarray(g.faces) + off); Cs.append(c); Ms.append(np.full(len(g.vertices), mid))
        off += len(g.vertices)
    if not Vs:
        raise ValueError("в файле нет геометрии")
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs), np.concatenate(Ms)


def straighten(V, F):
    """A body of separate blocks with lowered arms: swing the arms out into the T-pose every animation expects.
    Returns (V, crotch height or None)."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from ..rig.weights import weld
    first, inv = weld(V)
    f = inv[F]
    e = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1)  # blocks that merely touch share edges of 4 faces: not a link
    fid = np.tile(np.arange(len(f)), 3)
    _, ei, cnt = np.unique(e, axis=0, return_inverse=True, return_counts=True)
    ei = ei.reshape(-1)
    keep = np.flatnonzero(cnt[ei] == 2)
    keep = keep[np.argsort(ei[keep], kind="stable")]
    a, b = fid[keep[0::2]], fid[keep[1::2]]
    n, lab = connected_components(sparse.coo_matrix((np.ones(len(a)), (a, b)), shape=(len(f), len(f))), directed=False)
    H = float(np.ptp(V[:, 1]))
    parts = []
    order = np.argsort(lab, kind="stable")
    for fs in np.split(order, np.flatnonzero(np.diff(lab[order])) + 1):
        idx = np.unique(F[fs])
        lo, hi = V[idx].min(0), V[idx].max(0)
        if (hi - lo)[1] > H * .05 and min((hi - lo)[0], (hi - lo)[2]) > H * .03:
            parts.append({"i": idx, "lo": lo, "hi": hi, "c": (lo + hi) / 2})
    if len(parts) < 6 or np.ptp(V[:, 0]) > H * .9:  # not blocks, or the arms are already spread
        return V, None, None
    y0, y1 = V[:, 1].min(), V[:, 1].max()
    if sum(p["hi"][1] > y1 - H * .05 for p in parts) == 2 and sum(p["lo"][1] < y0 + H * .05 for p in parts) != 2:
        V = V * (1, -1, -1) + (0, y0 + y1, 0)  # two legs on top, one head below: the file is upside down
        for p in parts:
            lo, hi = p["lo"], p["hi"]
            p["lo"] = np.array([lo[0], y0 + y1 - hi[1], -hi[2]])
            p["hi"] = np.array([hi[0], y0 + y1 - lo[1], -lo[2]])
            p["c"] = (p["lo"] + p["hi"]) / 2
    parts.sort(key=lambda p: -p["hi"][1])
    rest = parts[1:]  # the highest is the head
    torso = max(rest, key=lambda p: float(np.prod(p["hi"] - p["lo"])) * (abs(p["c"][0]) < H * .1))
    tw = (torso["hi"][0] - torso["lo"][0]) / 2
    V = V.copy()
    swung = 0
    for s in (1, -1):  # an arm may be several pieces (sleeve, hand): they swing together
        ps = [p for p in rest if p is not torso and p["c"][0] * s > tw and p["hi"][1] < torso["hi"][1] + H * .05 and p["lo"][1] > torso["lo"][1] - H * .2]
        if not ps:
            continue
        idx = np.concatenate([p["i"] for p in ps])
        lo, hi = V[idx].min(0), V[idx].max(0)
        aw = min((hi[0] - lo[0]) / 2, (hi[2] - lo[2]) / 2)
        if hi[1] - lo[1] < 2 * aw:
            continue
        piv = np.array([(lo[0] + hi[0]) / 2, hi[1] - aw, (lo[2] + hi[2]) / 2])
        d = V[idx] - piv
        V[idx] = piv + np.stack([-d[:, 1] * s, d[:, 0] * s, d[:, 2]], 1)
        swung += 1
    if swung != 2:  # no clean pair of block arms: treat it as an ordinary body
        return V, None, None
    return V, float(torso["lo"][1]), float(tw)


def _by_material(V, M):
    """Figures of one file are usually separate meshes: same-size meshes standing apart are separate figures.
    Small ones (a head, goggles) join the nearest figure, overlapping ones (shirt and trousers) merge."""
    ids = [i for i in np.unique(M) if i >= 0]
    box = {i: (V[M == i].min(0), V[M == i].max(0)) for i in ids}
    tall = float(np.median([np.ptp(np.array(box[i]), 0).max() for i in ids]))
    main = [i for i in ids if float(np.ptp(np.array(box[i]), 0).max()) > tall * .5]
    def linked(a, b):  # really overlapping: figures in a row only touch at the fingertips
        lo, hi = np.maximum(box[a][0], box[b][0]), np.minimum(box[a][1], box[b][1])
        return bool(((hi - lo) > .02 * np.minimum(box[a][1] - box[a][0], box[b][1] - box[b][0])).all())

    figs = []
    for i in main:
        near = [f for f in figs if any(linked(i, j) for j in f)]
        figs = [f for f in figs if not any(f is x for x in near)] + [[i, *[j for f in near for j in f]]]
    if len(figs) < 2:
        return None
    cen = [np.mean([V[M == i].mean(0) for i in f], 0) for f in figs]
    for i in ids:
        if not any(i in f for f in figs):
            figs[int(np.argmin([np.linalg.norm(V[M == i].mean(0) - c) for c in cen]))].append(i)
    return [np.flatnonzero(np.isin(M, f)) for f in figs]


def groups(V, F, M=None):
    """Several characters in one file: lists of vertex ids, one per figure. M: material id per vertex."""
    if M is not None:
        by = _by_material(V, M)
        if by:
            return by
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from ..rig.weights import weld
    first, inv = weld(V, 1e-4)
    f = inv[F]
    e = np.vstack([f[:, [0, 1]], f[:, [1, 2]]])
    n, lab = connected_components(sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(first), len(first))), directed=False)
    lab = lab[inv]
    order = np.argsort(lab, kind="stable")
    parts = [(V[i].min(0), V[i].max(0), i) for i in np.split(order, np.flatnonzero(np.diff(lab[order])) + 1)]
    size = np.ptp(V, 0)
    big = float(np.max([p[1] - p[0] for p in parts]))
    m = big * .05
    root = list(range(len(parts)))

    def find(a):
        while root[a] != a:
            root[a] = root[root[a]]
            a = root[a]
        return a
    for a in range(len(parts)):
        for b in range(a):
            if (parts[a][0] - m < parts[b][1]).all() and (parts[b][0] - m < parts[a][1]).all():
                root[find(a)] = find(b)
    res = {}
    for a, p in enumerate(parts):
        res.setdefault(find(a), []).append(p)
    res = [np.concatenate([p[2] for p in v]) for v in res.values()]
    res = [v for v in res if np.ptp(V[v], 0).max() > float(size.max()) * .05 and len(v) > len(V) * .01]
    return sorted(res, key=lambda v: V[v].mean(0)[int(size.argmax())])


def convert_all(files, name="", height=0.0, up="auto", turn=0) -> list[dict]:
    """One result per character found in the file."""
    return [convert(files, name if n == 1 else f"{name or 'model'}_{i + 1}", height, up, turn, (i, n)) for n in [_count(files)] for i in range(n)]


def _count(files):
    V, F, _, M = _load(files)
    return max(1, len(groups(V, F, M)))


def _load(files):
    safe = {}
    for key, value in files.items():
        relative = PurePosixPath(str(key).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"путь файла выходит за каталог импорта: {key}")
        safe[relative.as_posix()] = value
    main = next((k for k in safe if Path(k).suffix.lower() in FORMATS), None)
    if not main:
        raise ValueError(f"нужен файл модели: {', '.join(FORMATS)}")
    if main.lower().endswith(".fbx"):
        return (*read_fbx(safe[main]), None)
    tmp = IMPORTS / "_tmp" / re.sub(r"[^\w\-]+", "_", Path(main).stem)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        for k, v in safe.items():
            target = tmp / Path(k)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(v)
        return _read_scene(tmp / main)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def convert(files: dict[str, bytes], name="", height=0.0, up="auto", turn=0, pick=None) -> dict:
    """files: file name -> bytes (a model and its .mtl/textures). height: resize to this many metres (0 keeps the size).
    up: which axis of the file is up, turn: degrees about the vertical so that the model faces +Z."""
    main = next((k for k in files if Path(k).suffix.lower() in FORMATS), "model")
    name = re.sub(r"[^\w\-]+", "_", name or Path(main).stem).strip("_") or "model"
    V, F, C, M = _load(files)
    if pick and pick[1] > 1:  # keep only this character of the file
        keep = groups(V, F, M)[pick[0]]
        mask = np.zeros(len(V), bool)
        mask[keep] = True
        F = F[mask[F].all(1)]
        new = np.cumsum(mask) - 1
        V, C, F = V[mask], C[mask], new[F]
    size = np.ptp(V, 0)
    if up == "z" or (up == "auto" and size[1] < size[2] * .6):
        V = V[:, [0, 2, 1]] * (1, 1, -1)
    size = np.ptp(V, 0)
    if up == "auto" and not turn and size[2] > size[0] * 1.2 and size[2] > size[1] * .6:
        turn = 90  # spread arms run along Z: stand the figure square to the camera
    a = math.radians(float(turn))
    V = V @ np.array([[math.cos(a), 0, -math.sin(a)], [0, 1, 0], [math.sin(a), 0, math.cos(a)]]).T
    lo, hi = V.min(0), V.max(0)
    if not np.ptp(V, 0)[1]:
        raise ValueError("модель плоская по вертикали: проверьте, какая ось вверх")
    V = V - ((lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2)
    k = float(height) / (hi[1] - lo[1]) if height else 1.0
    V = V * k
    V, crotch, tw = straighten(V, F)
    m = trimesh.Trimesh(V, F, process=False)
    m.visual.vertex_colors = (np.clip(C, 0, 1) * 255).astype(np.uint8)
    out = IMPORTS / f"{name}.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    m.export(out)
    return {"src": out.relative_to(PROJECTS).as_posix(), "name": name, "verts": len(V), "tris": len(F),
            "size_m": [round(float(x), 3) for x in np.ptp(V, 0)], "crotch": crotch, "torso": tw}
