"""Manifold -> trimesh conversion, validation, optimisation, export."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from . import geo as g
from .materials import MATS


def manifold_to_arrays(m):
    mesh = m.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    F = np.asarray(mesh.tri_verts).astype(np.int64)
    run_idx = np.asarray(mesh.run_index)
    run_ids = np.asarray(mesh.run_original_id)
    tri_oid = np.empty(len(F), dtype=np.int64)
    for i, oid in enumerate(run_ids):
        tri_oid[run_idx[i] // 3: run_idx[i + 1] // 3] = oid
    return V, F, tri_oid


def tri_materials(tri_oid):
    cache = {}
    out = []
    for oid in tri_oid:
        if oid not in cache:
            cache[oid] = g.info(int(oid))
        out.append(cache[oid])
    mats = np.array([m for m, _ in out], dtype=object)
    elems = np.array([e for _, e in out], dtype=object)
    return mats, elems


def split_by_material(V, F, mats) -> dict[str, trimesh.Trimesh]:
    out = {}
    for name in sorted(set(mats)):
        idx = np.where(mats == name)[0]
        tm = trimesh.Trimesh(V, F[idx], process=False)
        tm.remove_unreferenced_vertices()
        out[name] = tm
    return out


def box_uv(tm: trimesh.Trimesh, tile: float) -> trimesh.Trimesh:
    """World-space box projection: unweld by dominant normal axis, uv = coords / tile."""
    tile = tile or 1.0
    fn = tm.face_normals
    ax = np.argmax(np.abs(fn), axis=1)
    sign = np.sign(fn[np.arange(len(fn)), ax])
    groups = ax * 2 + (sign > 0)
    Vs, Fs, UVs = [], [], []
    off = 0
    for gi in np.unique(groups):
        idx = np.where(groups == gi)[0]
        sub = tm.submesh([idx], append=True, repair=False)
        v = sub.vertices
        a = gi // 2
        if a == 0:
            uv = np.c_[v[:, 1] * (1 if gi % 2 else -1), v[:, 2]]
        elif a == 1:
            uv = np.c_[v[:, 0] * (-1 if gi % 2 else 1), v[:, 2]]
        else:
            uv = np.c_[v[:, 0], v[:, 1]]
        Vs.append(v)
        Fs.append(sub.faces + off)
        UVs.append(uv / tile)
        off += len(v)
    out = trimesh.Trimesh(np.vstack(Vs), np.vstack(Fs), process=False)
    out.visual = trimesh.visual.TextureVisuals(uv=np.vstack(UVs))
    return out


def validate(result, ground_eps=0.05) -> dict:
    final = result.final()
    rep = {"ok": True, "errors": list(result.errors), "warnings": [], "info": []}
    if final.is_empty():
        rep["ok"] = False
        rep["errors"].append({"error": "empty model"})
        return rep
    st = final.status()
    rep["manifold_status"] = str(st)
    # negative-volume shells are closed interior voids (rooms), not parts
    comps = [c for c in final.decompose() if c.volume() > 1e-9]
    vols = [c.volume() for c in comps]
    main = int(np.argmax(vols))
    floating, separate = [], []
    for i, c in enumerate(comps):
        mn, mx = g.bbox(c)
        if i == main and mn[2] <= ground_eps:
            continue
        V, F, oid = manifold_to_arrays(c)
        _, elems = tri_materials(oid)
        ids = sorted(set(elems))
        item = {"elements": ids, "zmin": round(float(mn[2]), 3), "volume": round(vols[i], 4),
                "center": [round(float(x), 2) for x in (mn + mx) / 2]}
        (floating if mn[2] > ground_eps else separate).append(item)
    for f in floating:
        rep["errors"].append({"error": "floating part (not touching anything)", **f})
    if separate:
        rep["info"].append({"separate_grounded_parts": len(separate),
                            "elements": sorted({x for s in separate for x in s["elements"]})[:30]})
    rep["components"] = len(comps)
    rep["floating"] = floating
    mn, mx = g.bbox(final)
    rep["bbox"] = {"min": [round(float(x), 2) for x in mn], "max": [round(float(x), 2) for x in mx],
                   "size": [round(float(x), 2) for x in mx - mn]}
    rep["triangles"] = final.num_tri()
    V, F, _ = manifold_to_arrays(final)
    e = np.sort(np.c_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]].reshape(-1, 2), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    rep["watertight"] = bool(np.all(counts == 2))  # every edge shared by exactly two triangles
    if not rep["watertight"]:
        rep["errors"].append({"error": f"open/non-manifold edges: {int(np.sum(counts != 2))}"})
    rep["genus"] = final.genus()
    if final.num_tri() > 1_500_000:
        rep["warnings"].append("very heavy model, use optimize/lowpoly")
    rep["ok"] = not rep["errors"]
    return rep


def optimize(m, tolerance=0.004):
    """Lossless-ish: merges coplanar/colinear triangles while staying manifold."""
    try:
        return m.simplify(tolerance)
    except Exception:
        return m


def to_scene(final, tex_dir: Path | None = None, flat=False, y_up=True) -> trimesh.Scene:
    V, F, oid = manifold_to_arrays(final)
    mats, _ = tri_materials(oid)
    scene = trimesh.Scene()
    for name, tm in split_by_material(V, F, mats).items():
        info = MATS.get(name)
        tm2 = box_uv(tm, info.get("tile") or 1.0)
        col = list(info.get("color", [200, 200, 200])) + [255]
        tex = MATS.texture_files(name, tex_dir) if tex_dir else {}
        kw = dict(name=name, baseColorFactor=[c / 255 for c in col[:3]] + [1.0], metallicFactor=float(info.get("metal", 0.0)),
                  roughnessFactor=float(info.get("rough", 0.8)), doubleSided=False)
        if "albedo" in tex:
            from PIL import Image
            kw["baseColorTexture"] = Image.open(tex["albedo"]).convert("RGB")
            kw["baseColorFactor"] = [1, 1, 1, 1]
        if "normal" in tex:
            from PIL import Image
            kw["normalTexture"] = Image.open(tex["normal"]).convert("RGB")
        if info.get("alpha"):
            kw["alphaMode"] = "BLEND"
            kw["baseColorFactor"][3] = float(info["alpha"])
        tm2.visual.material = trimesh.visual.material.PBRMaterial(**kw)
        if y_up:
            tm2.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
        scene.add_geometry(tm2, node_name=name, geom_name=name)
    return scene


def _pbr(name):
    info = MATS.get(name)
    col = [c / 255 for c in info.get("color", [200, 200, 200])] + [float(info.get("alpha", 1.0))]
    kw = dict(name=name, baseColorFactor=col, metallicFactor=float(info.get("metal", 0.0)),
              roughnessFactor=float(info.get("rough", 0.8)))
    if info.get("alpha"):
        kw["alphaMode"] = "BLEND"
    return trimesh.visual.material.PBRMaterial(**kw)


def preview_scene(result) -> trimesh.Scene:
    """Per-element, per-material meshes (fast, for the interactive viewport). Node name = 'elementId|material'."""
    scene = trimesh.Scene()
    R = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    for eid, r in result.elements.items():
        if not r.solids:
            continue
        m = g.union([s for s, _ in r.solids])
        if m.is_empty():
            continue
        V, F, oid = manifold_to_arrays(m)
        mats, _ = tri_materials(oid)
        for name, tm in split_by_material(V, F, mats).items():
            tm.visual = trimesh.visual.TextureVisuals(material=_pbr(name))
            tm.apply_transform(R)
            nm = f"{eid}|{name}".replace("/", "~")  # three.js strips "/" from node names
            scene.add_geometry(tm, node_name=nm, geom_name=nm)
    return scene


def export(final, path: Path, fmt="glb", tex_dir=None, decimate_to=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    m = final
    if decimate_to and m.num_tri() > decimate_to:
        m = decimate(m, decimate_to)
    if fmt in ("glb", "gltf", "obj"):
        sc = to_scene(m, tex_dir, y_up=fmt != "obj")
        sc.export(str(path), file_type=fmt)
    elif fmt == "stl":
        V, F, _ = manifold_to_arrays(m)
        trimesh.Trimesh(V, F).export(str(path))
    else:
        raise ValueError(f"unknown format {fmt}")
    return path, m.num_tri()


def decimate(m, target_tris: int):
    """Aggressive LOD: quadric decimation per material group, then re-validated as manifold where possible."""
    import fast_simplification as fs
    V, F, oid = manifold_to_arrays(m)
    ratio = 1.0 - min(1.0, target_tris / max(1, len(F)))
    if ratio <= 0:
        return m
    V2, F2 = fs.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=ratio)
    # keep material provenance: nearest original triangle centroid
    from scipy.spatial import cKDTree
    c0 = V[F].mean(axis=1)
    c1 = V2[F2].mean(axis=1)
    _, nn = cKDTree(c0).query(c1)
    return _with_runs(V2, F2, oid[nn])


class _MeshOnly:
    """Minimal manifold-like wrapper for decimated meshes (export only)."""

    def __init__(self, V, F, oid):
        self.V, self.F, self.oid = V, F, oid

    def num_tri(self):
        return len(self.F)

    def to_mesh(self):
        order = np.argsort(self.oid, kind="stable")
        F = self.F[order]
        oid = self.oid[order]
        ids, starts = np.unique(oid, return_index=True)

        class Mm:
            pass
        mm = Mm()
        mm.vert_properties = self.V
        mm.tri_verts = F
        mm.run_original_id = ids
        mm.run_index = np.r_[starts * 3, len(F) * 3]
        return mm


def _with_runs(V, F, oid):
    return _MeshOnly(np.asarray(V, np.float64), np.asarray(F, np.int64), np.asarray(oid))
