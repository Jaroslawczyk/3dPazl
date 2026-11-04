"""Rig & animation workshop, native (no Blender): skeleton templates, automatic skin weights, procedural clips
with editable keys, motion checks and skinned/animated GLB export. Reusable by other workshops (clothes):
load(name) gives the bones, weights and clips of a rig.

Files in projects/rigs/: <name>.rig.json (source mesh, bones, clips), <name>.weights.npz, <name>.glb (export)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from . import anim, check, gltf, skeleton, weights as wts

from ...paths import PROJECTS

RIGS = PROJECTS / "rigs"
_mesh_cache: dict = {}


def _safe(name):
    return re.sub(r"[^\w\-]+", "_", name or "rig").strip("_") or "rig"


def _p(name, ext):
    return RIGS / f"{_safe(name)}{ext}"


def load_mesh(src: str):
    """(V, F, N, C) of a GLB under projects/ merged into one mesh with vertex colours."""
    import trimesh
    path = PROJECTS / src
    key = (str(path), path.stat().st_mtime)
    if key in _mesh_cache:
        return _mesh_cache[key]
    sc = trimesh.load(path, force="scene")
    Vs, Fs, Cs, off = [], [], [], 0
    for g in sc.dump(concatenate=False) if hasattr(sc, "dump") else [sc]:
        if not hasattr(g, "faces") or not len(g.faces):
            continue
        try:
            vis = g.visual if getattr(g.visual, "kind", None) == "vertex" else g.visual.to_color()
            col = np.asarray(vis.vertex_colors, float)[:, :3] / 255
        except Exception:
            col = np.full((len(g.vertices), 3), .8)
        if col.shape[0] != len(g.vertices):
            col = np.full((len(g.vertices), 3), .8)
        Vs.append(np.asarray(g.vertices, float)); Fs.append(np.asarray(g.faces) + off); Cs.append(col)
        off += len(g.vertices)
    V, F = np.vstack(Vs), np.vstack(Fs)
    m = trimesh.Trimesh(V, F, process=False)
    out = (V, F, np.asarray(m.vertex_normals, float), np.vstack(Cs))
    _mesh_cache.clear(); _mesh_cache[key] = out
    return out


def mannequin(name="mannequin", height=1.8):
    """Test humanoid mesh built from capsules along the humanoid template (T-pose), saved under rigs/src/."""
    import trimesh
    bones = skeleton.fit("humanoid", [[-height * .48, 0, -.2], [height * .48, height, .2]])
    rad = {"spine": .12, "chest": .15, "neck": .05, "shoulder": .055, "upper_arm": .05, "forearm": .04,
           "hand": .04, "thigh": .075, "shin": .055, "foot": .045}
    color = {"spine": (.25, .4, .7), "chest": (.25, .4, .7), "shoulder": (.25, .4, .7), "upper_arm": (.25, .4, .7),
             "thigh": (.2, .2, .25), "shin": (.2, .2, .25), "foot": (.35, .2, .1)}
    by = {b["name"]: b for b in bones}
    parts = []

    def cap(a, b, r, c):
        a, b = np.array(a), np.array(b)
        d = b - a
        L = float(np.linalg.norm(d))
        m = trimesh.creation.capsule(height=L, radius=r, count=[14, 10])
        T = trimesh.geometry.align_vectors([0, 0, 1], d / L)
        T[:3, 3] = (a + b) / 2
        m.apply_transform(T)
        m.visual.vertex_colors = np.tile([*(int(v * 255) for v in c), 255], (len(m.vertices), 1))
        parts.append(m)

    for b in bones:
        base = b["name"].split(".")[0]
        if base in rad:
            cap(b["head"], b["tail"], rad[base] * height / 1.8, color.get(base, (.85, .67, .55)))
    cap(by["thigh.L"]["head"], by["thigh.R"]["head"], .11 * height / 1.8, (.2, .2, .25))  # pelvis
    h = by["head"]
    m = trimesh.creation.icosphere(subdivisions=3, radius=.11 * height / 1.8)
    m.apply_translation((np.array(h["head"]) + np.array(h["tail"])) / 2 + [0, -.005, 0])
    m.visual.vertex_colors = np.tile([217, 171, 140, 255], (len(m.vertices), 1))
    parts.append(m)
    mesh = trimesh.util.concatenate(parts)
    mesh.apply_translation([0, -mesh.bounds[0][1], 0])
    out = RIGS / "src" / f"{_safe(name)}.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(out)
    return {"src": out.relative_to(PROJECTS).as_posix(), "verts": len(mesh.vertices), "tris": len(mesh.faces)}


def load(name):
    p = _p(name, ".rig.json")
    if not p.exists():
        raise FileNotFoundError(f"no rig {name}")
    return json.loads(p.read_text("utf-8"))


def save(rig):
    _p(rig["name"], ".rig.json").write_text(json.dumps(rig, ensure_ascii=False, separators=(",", ":")), "utf-8")


def auto(name, src, template="humanoid"):
    V, F, _, _ = load_mesh(src)
    bones = skeleton.fit(template, [V.min(0), V.max(0)])
    rig = {"name": _safe(name), "src": src, "template": template, "bones": bones, "clips": {}}
    save(rig)
    _p(name, ".weights.npz").unlink(missing_ok=True)
    return {"name": rig["name"], "template": template, "bones": len(bones),
            "size_m": [round(float(v), 3) for v in np.ptp(V, 0)], "verts": len(V)}


def set_bones(name, changes: list[dict]):
    """changes: [{name, head?, tail?}] — moves joints; weights are recomputed on next use."""
    rig = load(name)
    by = {b["name"]: b for b in rig["bones"]}
    for c in changes:
        b = by.get(c.get("name"))
        if not b:
            raise KeyError(f"unknown bone {c.get('name')}")
        for k in ("head", "tail", "roll"):
            if k in c:
                b[k] = c[k]
    save(rig)
    _p(name, ".weights.npz").unlink(missing_ok=True)
    return {"bones": len(rig["bones"])}


def weights(name, force=False):
    rig = load(name)
    p = _p(name, ".weights.npz")
    names, _, heads, tails = skeleton.order(rig["bones"])
    if p.exists() and not force:
        z = np.load(p)
        J, W = z["joints"], z["weights"]
    else:
        V, F, _, _ = load_mesh(rig["src"])
        J, W = wts.compute(V, F, heads, tails)
        np.savez_compressed(p, joints=J, weights=W)
    return J, W, wts.stats(J, W, names)


def make_anim(name, preset="walk", clip="", frames=None, fps=30):
    rig = load(name)
    if preset not in anim.PRESETS:
        raise KeyError(f"unknown preset {preset}; have {list(anim.PRESETS)}")
    c = anim.make(rig["bones"], preset, frames, fps)
    rig["clips"][clip or preset] = c
    save(rig)
    return {"clip": clip or preset, "frames": c["frames"], "fps": fps, "bones_keyed": len(c["keys"]),
            "travel_m": round(float(c["root"][-1][3]), 3) if c["root"] else 0}


def set_key(name, clip, bone, frame, euler, span=4):
    rig = load(name)
    if clip not in rig["clips"]:
        raise KeyError(f"no clip {clip}")
    anim.set_key(rig["clips"][clip], bone, int(frame), euler, span)
    save(rig)
    return {"clip": clip, "bone": bone, "frame": frame}


def run_check(name, clip, samples=24):
    rig = load(name)
    if clip not in rig["clips"]:
        raise KeyError(f"no clip {clip}; have {list(rig['clips'])}")
    V, F, _, _ = load_mesh(rig["src"])
    J, W, _ = weights(name)
    return check.run(rig["bones"], V, F, J, W, rig["clips"][clip], samples)


def export(name):
    rig = load(name)
    V, F, N, C = load_mesh(rig["src"])
    J, W, st = weights(name)
    out = _p(name, ".glb")
    size = gltf.write(out, V, F, N, C, J, W, rig["bones"], rig["clips"])
    return {"path": out.relative_to(PROJECTS).as_posix(), "kb": round(size / 1e3), "clips": list(rig["clips"]), **st}
