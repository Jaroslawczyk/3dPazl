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
    rep["surfaces"] = check_surfaces(V, F, result)
    for k in ("zfight", "decal_zfight", "decal_too_close"):
        if rep["surfaces"].get(k):
            rep["errors"].append({"error": f"{k}: {rep['surfaces'][k]} spots (flickering surfaces)",
                                  "elements": rep["surfaces"].get(k + "_elements", []), "at": rep["surfaces"].get(k + "_at", [])})
    if rep["surfaces"].get("degenerate"):
        rep["warnings"].append(f"degenerate triangles: {rep['surfaces']['degenerate']}")
    if final.num_tri() > 1_500_000:
        rep["warnings"].append("very heavy model, use optimize/lowpoly")
    rep["ok"] = not rep["errors"]
    return rep


def _in_tri(p, a, b, c, eps=1e-4):
    v0, v1, v2 = c - a, b - a, p - a
    d00, d01, d02, d11, d12 = v0 @ v0, v0 @ v1, v0 @ v2, v1 @ v1, v1 @ v2
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return False
    u = (d11 * d02 - d01 * d12) / den
    v = (d00 * d12 - d01 * d02) / den
    return u > eps and v > eps and u + v < 1 - eps


def check_surfaces(V, F, result=None, gap=0.002, max_tris=400_000) -> dict:
    """Find surfaces that would flicker (z-fighting): two different triangles facing the same way, < 2 mm apart and
    overlapping. Also degenerate triangles and overlay decals that overlap each other at the same depth."""
    from scipy.spatial import cKDTree
    out = {"zfight": 0, "degenerate": 0}
    if len(F) == 0 or len(F) > max_tris:
        return out
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(B - A, C - A)
    area = np.linalg.norm(nrm, axis=1) / 2
    out["degenerate"] = int(np.sum(area < 1e-9))
    ok = area > 1e-9
    n = np.zeros_like(nrm)
    n[ok] = nrm[ok] / (2 * area[ok])[:, None]
    cen = (A + B + C) / 3
    tree = cKDTree(cen)
    spots = []
    for i, j in tree.query_pairs(r=0.25):
        if not (ok[i] and ok[j]) or n[i] @ n[j] < 0.999:
            continue
        dist = abs((cen[j] - A[i]) @ n[i])
        if 1e-7 < dist < gap or (dist <= 1e-7 and set(F[i]).isdisjoint(F[j])):
            pj = cen[j] - n[i] * ((cen[j] - A[i]) @ n[i])
            if _in_tri(pj, A[i], B[i], C[i]):
                spots.append(cen[i])
    out["zfight"] = len(spots)
    out["zfight_at"] = [[round(float(x), 2) for x in p] for p in spots[:10]]
    if result is not None:  # overlay quads: same plane & overlapping -> flicker; too close to the wall -> flicker
        qs = [(eid, d) for eid, d in result.overlay() if d["kind"] == "decal"]
        bad, bad_el = 0, set()
        planes = [(np.asarray(d["pts"]), np.asarray(d.get("n", [0, 0, 1]))) for _, d in qs]
        for a_ in range(len(qs)):
            Pa, na = planes[a_]
            for b_ in range(a_ + 1, min(len(qs), a_ + 400)):
                Pb, nb = planes[b_]
                if na @ nb < 0.999 or abs((Pb[0] - Pa[0]) @ na) > 0.0005:
                    continue
                lo_a, hi_a, lo_b, hi_b = Pa.min(0), Pa.max(0), Pb.min(0), Pb.max(0)
                if np.all(lo_a <= hi_b + 1e-6) and np.all(lo_b <= hi_a + 1e-6):
                    bad += 1
                    bad_el.update([qs[a_][0], qs[b_][0]])
        out["decal_zfight"] = bad
        out["decal_zfight_elements"] = sorted(bad_el)[:20]
    return out


def optimize(m, tolerance=0.004):
    """Lossless-ish: merges coplanar/colinear triangles while staying manifold."""
    try:
        return m.simplify(tolerance)
    except Exception:
        return m


_IMG_CACHE: dict = {}


def _img(path, mode="RGB"):
    from PIL import Image
    key = (str(path), mode)
    if key not in _IMG_CACHE:
        _IMG_CACHE[key] = Image.open(path).convert(mode)
    return _IMG_CACHE[key]


def _orm(tex: dict):
    """glTF packs occlusion (R), roughness (G), metalness (B) into one texture."""
    from PIL import Image
    key = ("orm",) + tuple(str(tex.get(k)) for k in ("ao", "roughness", "metal"))
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    base = _img(tex.get("roughness") or tex.get("ao"), "L")
    size = base.size
    ao = _img(tex["ao"], "L").resize(size) if "ao" in tex else Image.new("L", size, 255)
    ro = _img(tex["roughness"], "L").resize(size) if "roughness" in tex else Image.new("L", size, 200)
    me = _img(tex["metal"], "L").resize(size) if "metal" in tex else Image.new("L", size, 0)
    _IMG_CACHE[key] = Image.merge("RGB", (ao, ro, me))
    return _IMG_CACHE[key]


def material_for(name: str, tex_dir: Path | None, textured: bool):
    """PBR material: realistic = texture maps (albedo, normal, AO+roughness+metal) tinted by paint;
    low-poly = flat colour only."""
    from .decals import ensure_all, file_for
    info = MATS.get(name)
    col = [c / 255 for c in info.get("color", [200, 200, 200])] + [float(info.get("alpha", 1.0))]
    kw = dict(name=name, baseColorFactor=col, metallicFactor=float(info.get("metal", 0.0)),
              roughnessFactor=float(info.get("rough", 0.8)), doubleSided=False)
    if info.get("alpha"):
        kw["alphaMode"] = "BLEND"
    ov = file_for(name)
    if ov is not None:  # decals / fake interiors always carry their picture
        ensure_all()
        kw["baseColorTexture"] = _img(ov, "RGBA" if name.startswith("decal_") else "RGB")
        kw["baseColorFactor"] = [1, 1, 1, 1]
        kw["roughnessFactor"] = 0.9
        kw["alphaMode"] = "BLEND" if name.startswith("decal_") else "OPAQUE"
        return trimesh.visual.material.PBRMaterial(**kw)
    tex = MATS.texture_files(name, tex_dir or Path(".")) if textured else {}
    if "albedo" in tex:
        kw["baseColorTexture"] = _img(tex["albedo"])
        kw["baseColorFactor"] = (col[:3] if info.get("tint") else [1, 1, 1]) + [col[3]]
    if "normal" in tex:
        kw["normalTexture"] = _img(tex["normal"])
    if "roughness" in tex or "ao" in tex:
        orm = _orm(tex)
        kw["metallicRoughnessTexture"] = orm
        kw["roughnessFactor"] = 1.0
        if "ao" in tex:
            kw["occlusionTexture"] = orm
    return trimesh.visual.material.PBRMaterial(**kw)


def overlay_meshes(result, kinds=None, y_up=True):
    """Decal / fake-interior quads as separate (non-welded) meshes grouped by material: [(name, Trimesh)]."""
    groups: dict[str, list] = {}
    for eid, d in result.overlay(kinds):
        groups.setdefault(d["mat"], []).append(d)
    out = []
    R = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    for mat, ds in groups.items():
        V, F, UV = [], [], []
        for d in ds:
            P = np.asarray(d["pts"], float)
            k = len(V) * 4
            tri = [[0, 1, 2], [0, 2, 3]]
            nrm = np.cross(P[1] - P[0], P[2] - P[0])
            if np.dot(nrm, d.get("n", nrm)) < 0:  # face the side the decal looks at
                tri = [[0, 2, 1], [0, 3, 2]]
            V.append(P)
            F += [[k + a, k + b, k + c] for a, b, c in tri]
            UV.append([[0, 0], [1, 0], [1, 1], [0, 1]])
        tm = trimesh.Trimesh(np.vstack(V), np.asarray(F), process=False)
        tm.visual = trimesh.visual.TextureVisuals(uv=np.vstack(UV))
        if y_up:
            tm.apply_transform(R)
        out.append((mat, tm))
    return out


def overlay_kinds(recipe: dict):
    kinds = set()
    if recipe.get("interiors", True):
        kinds.add("interior")
    if recipe.get("decals", True):
        kinds.add("decal")
    return kinds


def to_scene(final, tex_dir: Path | None = None, flat=False, y_up=True, textured=True, result=None) -> trimesh.Scene:
    V, F, oid = manifold_to_arrays(final)
    mats, _ = tri_materials(oid)
    scene = trimesh.Scene()
    for name, tm in split_by_material(V, F, mats).items():
        info = MATS.get(name)
        tm2 = box_uv(tm, info.get("tile") or 1.0)
        tm2.visual.material = material_for(name, tex_dir, textured)
        if y_up:
            tm2.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
        scene.add_geometry(tm2, node_name=name, geom_name=name)
    if result is not None:  # overlay layer: separate meshes, never welded into the shell
        for name, tm in overlay_meshes(result, overlay_kinds(result.recipe), y_up):
            tm.visual.material = material_for(name, tex_dir, textured)
            scene.add_geometry(tm, node_name=f"overlay|{name}", geom_name=f"overlay|{name}")
    return scene


def preview_scene(result, textured=False) -> trimesh.Scene:
    """Per-element, per-material meshes for the interactive viewport. Node name = 'elementId|material'.
    Geometry carries box-projected UVs; the viewer loads texture maps itself (by material name)."""
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
            tm = box_uv(tm, MATS.get(name).get("tile") or 1.0)
            tm.visual.material = material_for(name, None, False)
            tm.apply_transform(R)
            nm = f"{eid}|{name}".replace("/", "~")  # three.js strips "/" from node names
            scene.add_geometry(tm, node_name=nm, geom_name=nm)
    for name, tm in overlay_meshes(result, overlay_kinds(result.recipe)):
        tm.visual.material = trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=[1, 1, 1, 1])
        nm = f"overlay|{name}"
        scene.add_geometry(tm, node_name=nm, geom_name=nm)
    return scene


def export(final, path: Path, fmt="glb", tex_dir=None, decimate_to=None, textured=True, result=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    m = final
    if decimate_to and m.num_tri() > decimate_to:
        m = decimate(m, decimate_to)
    if fmt in ("glb", "gltf", "obj"):
        sc = to_scene(m, tex_dir, y_up=fmt != "obj", textured=textured, result=result)
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
