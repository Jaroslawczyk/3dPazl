"""Characters workshop: a character = body (generated organic skin or any imported GLB, plus clay strokes) + skeleton from
core/rig + skin + outfit. projects/chars/<name>.char.json is the recipe; <name>.glb the assembled, animated model.
The rig lives in projects/rigs/char_<name>.*, so the rig workshop can edit its bones and clips."""
from __future__ import annotations

import hashlib
import json
import re
import shutil

import numpy as np
import trimesh

from ...paths import PROJECTS
from .. import rig, skins
from ..rig import gltf, skeleton
from . import body, cloth

CHARS = PROJECTS / "chars"


def _safe(n):
    return re.sub(r"[^\w\-]+", "_", n or "hero").strip("_") or "hero"


def _rn(name):
    return "char_" + _safe(name)


def _p(name):
    return CHARS / f"{_safe(name)}.char.json"


def names():
    return sorted(p.name[:-10] for p in CHARS.glob("*.char.json")) if CHARS.exists() else []


def load(name):
    if not _p(name).exists():
        raise FileNotFoundError(f"нет персонажа {name}")
    return json.loads(_p(name).read_text("utf-8"))


def save(c):
    CHARS.mkdir(parents=True, exist_ok=True)
    _p(c["name"]).write_text(json.dumps(c, ensure_ascii=False, indent=1), "utf-8")


def catalog():
    return {"presets": {k: {"title": v[0], "kind": v[1], "params": body.params_for(k)[1]} for k, v in body.PRESETS.items()},
            "clothes": cloth.catalog(), "skins": skins.catalog(), "chars": names()}


def _src(name):
    return rig.RIGS / "src" / f"{_rn(name)}.glb"


def _write_body(c):
    """(Re)generate the body mesh file from the recipe and clay strokes; bones stay in the rig."""
    out = _src(c["name"])
    out.parent.mkdir(parents=True, exist_ok=True)
    if c.get("import"):
        V, F, N, C = rig.load_mesh(c["import"])
        m = trimesh.Trimesh(V, F, process=False)
        m.visual.vertex_colors = (np.clip(C, 0, 1) * 255).astype(np.uint8)
        bones = None
    else:
        m, bones = body.build(c["kind"], c["params"], c.get("cell"))
    if c.get("sculpt"):
        m.vertices = body.sculpt(m.vertices, np.asarray(m.vertex_normals), c["sculpt"])
    m.export(out)
    shutil.rmtree(CHARS / "cache" / _safe(c["name"]), ignore_errors=True)
    return out.relative_to(PROJECTS).as_posix(), bones, m


def create(name, preset="man", params=None, src="", template="humanoid", cell=None):
    """New character from a preset (organic generated body) or from any GLB under projects/ (src)."""
    name = _safe(name)
    c = {"name": name, "skin": None, "outfit": [], "sculpt": [], "cell": cell}
    if src:
        c.update({"import": src, "kind": "import", "template": template, "preset": None, "params": {}})
    else:
        if preset not in body.PRESETS:
            raise KeyError(f"unknown preset {preset}; have {list(body.PRESETS)}")
        kind, p = body.params_for(preset, params)
        c.update({"kind": kind, "preset": preset, "params": p, "template": body.TEMPLATE[kind]})
    rel, bones, m = _write_body(c)
    bones = bones or skeleton.fit(template, m.bounds)
    rn = _rn(name)
    old = rig._p(rn, ".rig.json")
    clips = json.loads(old.read_text("utf-8"))["clips"] if old.exists() else {}
    rig.save({"name": rn, "src": rel, "template": c["template"], "bones": bones, "clips": clips})
    rig._p(rn, ".weights.npz").unlink(missing_ok=True)
    save(c)
    if not clips:
        for a in ("idle", "walk"):
            rig.make_anim(rn, a)
    return export(name)


def update(name, params):
    """Change body proportions: new surface and bones; clothes are refitted on export."""
    c = load(name)
    if c.get("import"):
        raise ValueError("импортированное тело меняется только лепкой")
    c["params"] = {**c["params"], **params}
    rel, bones, _ = _write_body(c)
    r = rig.load(_rn(name))
    r.update({"src": rel, "bones": bones})
    rig.save(r)
    rig._p(_rn(name), ".weights.npz").unlink(missing_ok=True)
    for k, v in list(r["clips"].items()):  # gait depends on leg length
        if k in rig.anim.PRESETS:
            rig.make_anim(_rn(name), k)
    save(c)
    return export(name)


def sculpt(name, strokes=None, undo=False):
    c = load(name)
    if undo and c["sculpt"]:
        c["sculpt"].pop()
    c["sculpt"] += strokes or []
    rel, _, _ = _write_body(c)
    rig._p(_rn(name), ".weights.npz").unlink(missing_ok=True)
    save(c)
    return {**export(name), "strokes": len(c["sculpt"])}


def set_skin(name, skin):
    c = load(name)
    c["skin"] = skins.resolve(skin) if skin else None
    save(c)
    return export(name)


def wear(name, kind, color="", skin=None, **opts):
    """Add a garment; it is fitted now, an unsuitable kind raises before the recipe changes."""
    c = load(name)
    c["outfit"] = [g for g in c["outfit"] if g["kind"] != kind]
    spec = {"kind": kind, **({"color": color} if color else {}), **({"skin": skins.resolve(skin)} if skin else {}), **opts}
    c["outfit"].append(spec)
    r = export_c(c)
    save(c)
    return r


def remove(name, kind):
    c = load(name)
    c["outfit"] = [g for g in c["outfit"] if g["kind"] != kind]
    save(c)
    return export(name)


def copy_outfit(src, dst):
    """Dress another character in the same recipes; kinds its skeleton cannot wear are reported, not fatal."""
    a, b = load(src), load(dst)
    ok = cloth.kinds_for(b["template"])
    b["outfit"] = [g for g in a["outfit"] if g["kind"] in ok]
    r = export_c(b)
    save(b)
    return {**r, "skipped": [g["kind"] for g in a["outfit"] if g["kind"] not in ok]}


def _garment(c, g, fit, stamp):
    """Cached fit of one garment (V, F, N)."""
    key = hashlib.sha1(json.dumps([{k: v for k, v in g.items() if k in ("kind", "ease", "length", "flare", "wrinkle", "from", "to", "seed")}, stamp], sort_keys=True).encode()).hexdigest()[:12]
    p = CHARS / "cache" / c["name"] / f"{g['kind']}_{key}.npz"
    if p.exists():
        z = np.load(p)
        return z["V"], z["F"], z["N"]
    V, F, N = cloth.make(fit, g["kind"], g, c["template"])
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    return V, F, N


def _textured(part, s):
    """Box-mapped copy of a part with the skin's texture."""
    s = skins.resolve(s)
    idx, F, uv = skins.box_uv(part["V"], part["F"], float(s.get("tile", .3)))
    return {**part, "V": part["V"][idx], "N": part["N"][idx], "F": F, "UV": uv, "C": None, "J": part["J"][idx], "W": part["W"][idx],
            "png": skins.png_bytes(s), "metal": float(s.get("metal", 0)), "rough": float(s.get("rough", .7))}


def export_c(c):
    rn = _rn(c["name"])
    r = rig.load(rn)
    V, F, N, C = rig.load_mesh(r["src"])
    J, W, st = rig.weights(rn)
    names_, *_ = skeleton.order(r["bones"])
    parts = [{"name": "Body", "V": V, "F": F, "N": N, "C": C, "J": J, "W": W}]
    if c.get("skin"):
        eye = _eyes(C) if not c.get("import") else None
        if eye is not None and eye.any():  # eyes keep their colours
            keep = eye[F].any(1)
            base = _textured({**parts[0], "F": F[~keep]}, c["skin"])
            parts = [base, {**parts[0], "name": "Eyes", "F": F[keep]}]
        else:
            parts = [_textured(parts[0], c["skin"])]
    fits = []
    if c["outfit"]:
        Wd = np.zeros((len(V), len(names_)), np.float32)
        np.put_along_axis(Wd, J.astype(int), W.astype(np.float32), 1)
        stamp = [r["src"], (PROJECTS / r["src"]).stat().st_mtime]
        fit = cloth.Fit(V, F, N, r["bones"])
        for g in c["outfit"]:
            Vg, Fg, Ng = _garment(c, g, fit, stamp)
            Vg, Ng = np.asarray(Vg, float), np.asarray(Ng, float)
            Jg, Wg = cloth.transfer(fit, Vg, Wd, cloth.soft(g["kind"], c["template"]), cloth.rigid_bone(g["kind"], c["template"], names_))
            o = cloth.kinds_for(c["template"])[g["kind"]][2]
            col = body.rgb(g.get("color") or o["color"])
            skin = g.get("skin") or (None if g.get("color") else o.get("skin"))
            part = {"name": g["kind"], "V": Vg, "F": Fg, "N": Ng, "C": np.tile(col, (len(Vg), 1)), "J": Jg, "W": Wg, "rough": .85}
            parts.append(_textured(part, skin) if skin else part)
            fits.append({"kind": g["kind"], "tris": len(Fg)})
    out = CHARS / f"{c['name']}.glb"
    size = gltf.write_parts(out, parts, r["bones"], r["clips"])
    return {"name": c["name"], "path": out.relative_to(PROJECTS).as_posix(), "kb": round(size / 1e3), "clips": list(r["clips"]),
            "template": c["template"], "tris": int(sum(len(p["F"]) for p in parts)), "outfit": fits, "unweighted": st["unweighted"]}


def _eyes(C):
    """Eye vertices: only the eyeballs are near-white or near-black."""
    return (C.min(1) > .9) | (C.max(1) < .05)


def export(name):
    return export_c(load(name))


def get(name):
    c = load(name)
    r = rig.load(_rn(name))
    return {**c, "rig": r["name"], "clips": {k: {"frames": v["frames"], "fps": v["fps"]} for k, v in r["clips"].items()},
            "wearable": [{"id": k, "title": v[0], "group": v[1], "color": v[2]["color"]} for k, v in cloth.kinds_for(c["template"]).items()]}


def anim(name, preset):
    rig.make_anim(_rn(name), preset)
    return export(name)
