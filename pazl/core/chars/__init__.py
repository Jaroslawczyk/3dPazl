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
from scipy.spatial import cKDTree

from ...paths import PROJECTS
from .. import rig, skins
from ..rig import gltf, skeleton
from . import body, cloth
from .field import decimate

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
            "clothes": cloth.catalog(), "skins": skins.catalog(), "chars": names(),
            "quality": {k: v[0] for k, v in body.QUALITY.items()}}


def _src(name):
    return rig.RIGS / "src" / f"{_rn(name)}.glb"


def _target(c):
    return body.QUALITY[c.get("quality") or "high"][1]


def _write_body(c):
    """(Re)generate the body mesh file from the recipe and clay strokes; bones stay in the rig."""
    out = _src(c["name"])
    out.parent.mkdir(parents=True, exist_ok=True)
    if c.get("import"):
        V, F, N, C = rig.load_mesh(c["import"])
        limit = _target(c) if c.get("quality") == "low" else max(_target(c) or 0, 20000)  # up to the Roblox mesh limit, keep painted faces sharp
        if _target(c) and len(F) > limit:  # colours follow the nearest original vertex
            first, inv = rig.wts.weld(V, 1e-4)  # unwelded seams make the simplifier throw whole parts away
            V2, F = decimate(V[first], inv[F], limit)
            C = C[cKDTree(V).query(V2)[1]]
            V = V2
        m = trimesh.Trimesh(V, F, process=False)
        m.visual.vertex_colors = (np.clip(C, 0, 1) * 255).astype(np.uint8)
        bones = None
    else:
        m, bones = body.build(c["kind"], c["params"], c.get("cell"), _target(c))
    if c.get("sculpt"):
        m.vertices = body.sculpt(m.vertices, np.asarray(m.vertex_normals), c["sculpt"])
    m.export(out)
    shutil.rmtree(CHARS / "cache" / _safe(c["name"]), ignore_errors=True)
    return out.relative_to(PROJECTS).as_posix(), bones, m


def create(name, preset="man", params=None, src="", template="humanoid", cell=None, quality="high", crotch=None, torso=None):
    """New character from a preset (organic generated body) or from any GLB under projects/ (src)."""
    name = _safe(name)
    if quality not in body.QUALITY:
        raise KeyError(f"unknown quality {quality}; have {list(body.QUALITY)}")
    c = {"name": name, "skin": None, "outfit": [], "sculpt": [], "cell": cell, "quality": quality, "blocks": crotch is not None}
    if src:
        c.update({"import": src, "kind": "import", "template": template, "preset": None, "params": {}})
    else:
        if preset not in body.PRESETS:
            raise KeyError(f"unknown preset {preset}; have {list(body.PRESETS)}")
        kind, p = body.params_for(preset, params)
        c.update({"kind": kind, "preset": preset, "params": p, "template": body.TEMPLATE[kind], "blocks": kind == "blocky"})
    rel, bones, m = _write_body(c)
    if not bones and template == "humanoid":
        bones = body.fit_tpose(trimesh.sample.sample_surface(m, 80000, seed=1)[0], crotch, torso)  # block bodies have too few vertices to measure
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


def update(name, params=None, quality=None):
    """Change body proportions or quality: new surface and bones; clothes are refitted on export."""
    c = load(name)
    if quality:
        if quality not in body.QUALITY:
            raise KeyError(f"unknown quality {quality}; have {list(body.QUALITY)}")
        c["quality"] = quality
    if c.get("import") and params:
        raise ValueError("импортированное тело меняется только лепкой")
    c["params"] = {**c["params"], **(params or {})}
    rel, bones, _ = _write_body(c)
    r = rig.load(_rn(name))
    r.update({"src": rel, "bones": bones or r["bones"]})
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
    t = int(_target(c) * .5) if _target(c) else None
    if c.get("blocks") and g["kind"] not in cloth.PAINT:  # hair and hats on a ~2k block avatar: a real one spends ~1.5k on both
        t = min(t or 1200, 1200)
    key = hashlib.sha1(json.dumps([{k: v for k, v in g.items() if k in ("kind", "ease", "length", "flare", "wrinkle", "from", "to", "seed")}, stamp, t], sort_keys=True).encode()).hexdigest()[:12]
    p = CHARS / "cache" / c["name"] / f"{g['kind']}_{key}.npz"
    if p.exists():
        z = np.load(p)
        return z["V"], z["F"], z["N"], z["L"]
    V, F, N, L = cloth.make_blocks(fit, g["kind"], g, c["template"], t) if c.get("blocks") else (*cloth.make(fit, g["kind"], g, c["template"], t), np.zeros(0, int))
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32), L=L)
    return V, F, N, L


def _rigid(V, N, bones, names_):
    """Block bodies move like toys: each block follows one bone. Stepping inside along the normal keeps two touching faces apart."""
    J = np.zeros((len(V), 4), np.uint16)
    J[:, 0] = cloth.block_label(V - N * .004, bones, names_)
    W = np.zeros((len(V), 4), np.float32)
    W[:, 0] = 1
    return J, W


def fit_for(c, r, V, F, N):
    names_ = skeleton.order(r["bones"])[0] if c.get("blocks") else None
    return cloth.Fit(V, F, N, r["bones"], names_)


def _textured(part, s):
    """Box-mapped copy of a part with the skin's texture."""
    s = skins.resolve(s)
    idx, F, uv = skins.box_uv(part["V"], part["F"], float(s.get("tile", .3)))
    return {**part, "V": part["V"][idx], "N": part["N"][idx], "F": F, "UV": uv, "C": None, "J": part["J"][idx], "W": part["W"][idx],
            "png": skins.png_bytes(s), "metal": float(s.get("metal", 0)), "rough": float(s.get("rough", .7))}


def _quad_part(name, x0, x1, y0, y1, z, png, bone):
    """A flat picture facing +Z (the front of the character) that follows one bone."""
    V = np.array([[x0, y1, z], [x1, y1, z], [x1, y0, z], [x0, y0, z]], float)
    W = np.zeros((4, 4), np.float32)
    W[:, 0] = 1
    J = np.zeros((4, 4), np.uint16)
    J[:, 0] = bone
    return {"name": name, "V": V, "F": np.array([[3, 2, 1], [3, 1, 0]]), "N": np.tile([0., 0, 1], (4, 1)), "C": None, "J": J, "W": W,
            "UV": np.array([[0, 0], [1, 0], [1, 1], [0, 1.]]), "png": png, "rough": .85}


def print_part(g, Vg, bones, names_):
    """Print on the chest front of a garment: g["print"] = PNG under projects/, g["print_size"] = share of the chest width."""
    ix = names_.index("chest")
    P = Vg[cloth.block_label(Vg, bones, names_) == ix]
    if not len(P):
        return None
    lo, hi = P.min(0), P.max(0)
    cx, cy = (lo[0] + hi[0]) / 2, lo[1] + (hi[1] - lo[1]) * .52
    h = min(hi[0] - lo[0], hi[1] - lo[1]) * float(g.get("print_size", .78)) / 2
    near = P[(np.abs(P[:, 0] - cx) < h) & (np.abs(P[:, 1] - cy) < h)]
    z = (near if len(near) else P)[:, 2].max() + .003
    from io import BytesIO
    from PIL import Image
    pic = Image.open(PROJECTS / g["print"]).convert("RGBA")  # the material is opaque: lay the picture on the garment colour
    bg = Image.new("RGBA", pic.size, tuple(int(v * 255) for v in body.rgb(g.get("color") or "#ffffff")) + (255,))
    buf = BytesIO()
    Image.alpha_composite(bg, pic).convert("RGB").save(buf, "PNG")
    return _quad_part("print", cx - h, cx + h, cy - h, cy + h, z, buf.getvalue(), ix)


def _blob(sub, scale, at, col):
    m = trimesh.creation.icosphere(subdivisions=sub)
    m.apply_scale(scale)
    m.apply_translation(at)
    return m, col


def pet_mesh(c, r, V, g):
    """Small pet sitting on the right shoulder: list of (trimesh, rgb). Built from primitives, faces +Z like the body."""
    names_ = skeleton.order(r["bones"])[0]
    lab = cloth.block_label(V, r["bones"], names_)
    side = "upper_arm.L" if g.get("side") == "L" else "upper_arm.R"
    P = V[lab == names_.index(side)]
    top = P[:, 1].max()
    cap = P[P[:, 1] > top - (top - P[:, 1].min()) * .1]
    base = np.array([cap[:, 0].mean(), top, cap[:, 2].mean()])
    s = float(np.max([b["tail"][1] for b in r["bones"]])) * .085 * float(g.get("size", 1))
    blue = body.rgb(g.get("color") or "#2bb5ea")
    parts = [_blob(2, [s * .95, s, s * .9], [0, s * 1.3, 0], blue),
             _blob(1, [s * .22, s * .55, s * .5], [s * .9, s * 1.15, -s * .05], blue * .8),
             _blob(1, [s * .22, s * .55, s * .5], [-s * .9, s * 1.15, -s * .05], blue * .8),
             _blob(1, [s * .2, s * .2, s * .1], [s * .38, s * 1.55, s * .82], np.ones(3)),
             _blob(1, [s * .2, s * .2, s * .1], [-s * .38, s * 1.55, s * .82], np.ones(3)),
             _blob(1, [s * .1, s * .12, s * .06], [s * .38, s * 1.55, s * .9], np.full(3, .03)),
             _blob(1, [s * .1, s * .12, s * .06], [-s * .38, s * 1.55, s * .9], np.full(3, .03))]
    beak = trimesh.creation.cone(radius=s * .22, height=s * .45, sections=8)
    beak.apply_translation([0, s * 1.25, s * .8])
    parts.append((beak, body.rgb("#f2a516")))
    tail = trimesh.creation.cone(radius=s * .3, height=s * .5, sections=6)
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    tail.apply_translation([0, s * .95, -s * .75])
    parts.append((tail, blue * .85))
    for x in (-.28, .28):
        leg = trimesh.creation.cylinder(radius=s * .045, height=s * .4, sections=6)
        leg.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        leg.apply_translation([s * x, s * .2, 0])
        foot = trimesh.creation.box([s * .18, s * .05, s * .28])
        foot.apply_translation([s * x, s * .025, s * .08])
        parts += [(leg, body.rgb("#d9a520")), (foot, body.rgb("#d9a520"))]
    for m, _ in parts:
        m.apply_translation(base)
    return parts, names_.index(side)


def pet_part(c, r, V, g):
    parts, bone = pet_mesh(c, r, V, g)
    Vs, Fs, Ns, Cs, off = [], [], [], [], 0
    for m, col in parts:
        Vs.append(m.vertices), Fs.append(m.faces + off), Ns.append(m.vertex_normals), Cs.append(np.tile(col, (len(m.vertices), 1)))
        off += len(m.vertices)
    Vb = np.vstack(Vs)
    J = np.zeros((len(Vb), 4), np.uint16)
    J[:, 0] = bone
    W = np.zeros((len(Vb), 4), np.float32)
    W[:, 0] = 1
    return {"name": g["kind"], "V": Vb, "F": np.vstack(Fs), "N": np.vstack(Ns), "C": np.vstack(Cs), "J": J, "W": W, "rough": .5}


def _paint_outfit(c, r, V, F, N, C, J, W, painted, names_):
    """Block body: every face takes the colour/skin of the last garment that covers it (later ones lie on top)."""
    fit = fit_for(c, r, V, F, N)
    eye = _eyes(C)[F].all(1)
    own = np.full(len(F), -1)
    T = V[F]
    e = np.stack([np.linalg.norm(T[:, 1] - T[:, 2], axis=1), np.linalg.norm(T[:, 2] - T[:, 0], axis=1), np.linalg.norm(T[:, 0] - T[:, 1], axis=1)], 1).argmax(1)
    k = np.arange(len(F))
    P = (T[k, (e + 1) % 3] + T[k, (e + 2) % 3]) / 2  # middle of the long edge = centre of the grid quad: both halves agree, no saw teeth
    for i, g in enumerate(painted):
        o = cloth.kinds_for(c["template"])[g["kind"]][2]
        own[(cloth._region(fit, o, P) < 0) & ~eye] = i
    out = []
    for i in range(-1, len(painted)):
        Fi = F[own == i]
        if not len(Fi):
            continue
        use, Fi = np.unique(Fi, return_inverse=True)
        Fi = Fi.reshape(-1, 3)
        part = {"name": "Body" if i < 0 else painted[i]["kind"], "V": V[use], "F": Fi, "N": N[use], "C": C[use].copy(), "J": J[use], "W": W[use], "rough": .85}
        if i < 0:
            ey = eye[own == -1]
            if c.get("skin") and (~ey).any():  # the body skin texture, eyes keep their colours
                sk = _textured({**part, "F": Fi[~ey]}, c["skin"])
                out += [sk] + ([{**part, "name": "Eyes", "F": Fi[ey]}] if ey.any() else [])
            else:
                out.append(part)
            continue
        g = painted[i]
        o = cloth.kinds_for(c["template"])[g["kind"]][2]
        part["C"][:] = body.rgb(g.get("color") or o["color"])
        skin = g.get("skin") or (None if g.get("color") else o.get("skin"))
        out.append(_textured(part, skin) if skin else part)
        if g.get("print"):
            pp = print_part(g, part["V"], r["bones"], names_)
            if pp:
                out.append(pp)
    return out


def export_c(c):
    rn = _rn(c["name"])
    r = rig.load(rn)
    V, F, N, C = rig.load_mesh(r["src"])
    J, W, st = rig.weights(rn)
    names_, *_ = skeleton.order(r["bones"])
    if c.get("blocks"):
        J, W = _rigid(V, N, r["bones"], names_)
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
    painted = [g for g in c["outfit"] if c.get("blocks") and not c.get("cloth3d") and g["kind"] in cloth.PAINT]
    if painted:
        parts = _paint_outfit(c, r, V, F, N, C, J, W, painted, names_)
        fits += [{"kind": g["kind"], "tris": 0, "painted": True} for g in painted]
    if c["outfit"]:
        Wd = np.zeros((len(V), len(names_)), np.float32)
        np.put_along_axis(Wd, J.astype(int), W.astype(np.float32), 1)
        stamp = [r["src"], (PROJECTS / r["src"]).stat().st_mtime, 6]
        fit = fit_for(c, r, V, F, N)
        for g in c["outfit"]:
            if any(g is x for x in painted):
                continue
            o = cloth.kinds_for(c["template"])[g["kind"]][2]
            if o.get("pet"):
                parts.append(pet_part(c, r, V, g))
                fits.append({"kind": g["kind"], "tris": len(parts[-1]["F"])})
                continue
            Vg, Fg, Ng, Lg = _garment(c, g, fit, stamp)
            Vg, Ng = np.asarray(Vg, float), np.asarray(Ng, float)
            if c.get("blocks"):
                Jg = np.zeros((len(Vg), 4), np.uint16)
                Jg[:, 0] = Lg
                Wg = np.zeros((len(Vg), 4), np.float32)
                Wg[:, 0] = 1
            else:
                Jg, Wg = cloth.transfer(fit, Vg, Wd, cloth.soft(g["kind"], c["template"]), cloth.rigid_bone(g["kind"], c["template"], names_))
            col = body.rgb(g.get("color") or o["color"])
            skin = g.get("skin") or (None if g.get("color") else o.get("skin"))
            part = {"name": g["kind"], "V": Vg, "F": Fg, "N": Ng, "C": np.tile(col, (len(Vg), 1)), "J": Jg, "W": Wg, "rough": .85}
            parts.append(_textured(part, skin) if skin else part)
            if g.get("print"):
                pp = print_part(g, Vg, r["bones"], names_)
                if pp:
                    parts.append(pp)
            fits.append({"kind": g["kind"], "tris": len(Fg)})
    out = CHARS / f"{c['name']}.glb"
    size = gltf.write_parts(out, parts, r["bones"], r["clips"])
    return {"name": c["name"], "path": out.relative_to(PROJECTS).as_posix(), "kb": round(size / 1e3), "clips": list(r["clips"]),
            "template": c["template"], "tris": int(sum(len(p["F"]) for p in parts)), "max_part": int(max(len(p["F"]) for p in parts)), "outfit": fits, "unweighted": st["unweighted"]}


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
