"""Choreography: long animations from key poses, with smooth transitions, whole-body flips/spins, automatic ground
contact, and a motion QA that understands block (R15-like) bodies.

A timeline is a list of keys:
    {"t": seconds, "pose": {bone: Rot}, "ease": "smooth"|"linear",
     "spin": deg/s about the vertical through the anchor (from this key on), "flip": deg about X (whole body, e.g. 180
     for a headstand), "anchor": "feet"|"head"|"hands" (which point stays planted on the ground, xz fixed)}
Bones missing in a key keep the base pose. Between keys every bone is slerped with an ease curve; spin is integrated
per frame, so any number of turns is smooth. Root height puts the lowest point of the body (incl. hats, hair, pets)
on the ground every frame; the anchor keeps the contact point still on the floor (no sliding while spinning).

    clip = make_clip(points, bones, timeline, fps=30)      # points = body_points(char)
    report = qa(points, bones, clip)                      # gaps at joints, ground, pass-through, jerks
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

from . import anim
from .skeleton import order

q = anim.q
IDENT = Rot.identity()


def smooth(t):
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- body sampled per bone
def body_points(char_name, per_bone=400):
    """{'P': (n,3) bind-pose points, 'b': (n,) bone index, 'names': [...]} of a character: body (labels / block labels /
    weights) + its props (hat, hair, pet follow their bone). Used for ground contact and the QA."""
    import trimesh
    from .. import chars, rig
    from ..chars import cloth
    c = chars.load(char_name)
    r = rig.load(chars._rn(char_name))
    names, *_ = order(r["bones"])
    V, F, N, C = rig.load_mesh(r["src"])
    if c.get("labels"):
        from ...paths import PROJECTS
        z = np.load(PROJECTS / c["labels"])
        b = np.array([names.index(str(x)) for x in z["bone"][cKDTree(z["P"]).query(V)[1]]])
    elif c.get("blocks"):
        b = cloth.block_label(V, r["bones"], names)
    else:
        J, W, _ = rig.weights(chars._rn(char_name))
        b = J[np.arange(len(V)), np.argmax(W, 1)].astype(int)
    Ps, bs = [V], [b]
    for g in c.get("outfit", []):
        o = cloth.kinds_for(c["template"])[g["kind"]][2]
        if o.get("pet"):
            ms, bone = chars.prop_mesh(c, r, V, F, N, g)
            for m, _ in ms:
                Ps.append(np.asarray(m.vertices)), bs.append(np.full(len(m.vertices), bone))
    P, b = np.vstack(Ps), np.concatenate(bs)
    keep = []  # thin it out per bone, but always keep each bone's extremes (they touch the ground)
    rng = np.random.default_rng(0)
    for i in np.unique(b):
        idx = np.flatnonzero(b == i)
        ext = [idx[np.argmin(P[idx, a])] for a in range(3)] + [idx[np.argmax(P[idx, a])] for a in range(3)]
        keep += ext + (rng.choice(idx, per_bone, replace=False).tolist() if len(idx) > per_bone else idx.tolist())
    keep = np.unique(keep)
    return {"P": P[keep], "b": b[keep], "names": names}


def pose_points(points, bones, rots, root):
    names, par, heads, tails = order(bones)
    R, Pj = anim.fk(par, heads, rots, root)
    b = points["b"]
    return Pj[b] + np.einsum("nij,nj->ni", R[b], points["P"] - heads[b])


ANCHORS = {"feet": ("foot", "shin"), "head": ("head",), "hands": ("hand", "forearm")}


def _contact(Pj, Tj, names, mode):
    """xz of the contact from JOINTS (continuous): ankles for feet, wrists for hands, the top of the head. The lowest
    surface point jumps heel->toe and foot->foot and shakes the whole body."""
    for pref in ANCHORS.get(mode, ("foot",)):
        ids = [i for i, n in enumerate(names) if n.split(".")[0] == pref]
        if ids:
            pts = Tj[ids] if pref == "head" else Pj[ids]
            return pts.mean(0)[[0, 2]]
    return Pj[0][[0, 2]]


# ---------------------------------------------------------------- clip from a timeline
def make_clip(points, bones, timeline, fps=30, base=None, name="choreo", loop=False):
    names, par, heads, tails = order(bones)
    base = base or {}
    keys = sorted(timeline, key=lambda k: k["t"])
    T = keys[-1]["t"]
    frames = int(round(T * fps))
    full = []
    for k in keys:  # every key carries every bone (missing ones = base pose)
        pose = {n: base.get(n, IDENT) for n in names}
        pose.update(k.get("pose", {}))
        full.append(pose)
    out_keys = {n: [] for n in names}
    root = []
    spin_angle, hold, target = 0.0, np.zeros(2), np.zeros(2)
    prev_anchor = None
    for f in range(frames + 1):
        t = f / fps
        i = max(0, int(np.searchsorted([k["t"] for k in keys], t, side="right")) - 1)
        j = min(i + 1, len(keys) - 1)
        span = max(keys[j]["t"] - keys[i]["t"], 1e-9)
        u = 0.0 if i == j else (t - keys[i]["t"]) / span
        w = smooth(u) if keys[j].get("ease", "smooth") == "smooth" else u
        rots = np.zeros((len(names), 4))
        for bi, n in enumerate(names):
            a, b2 = full[i][n].as_quat(), full[j][n].as_quat()
            rots[bi] = anim.slerp(a, b2, w)
        # whole-body flip and spin are applied to the root bone (hips)
        flip = keys[i].get("flip", 0) * (1 - w) + keys[j].get("flip", 0) * w
        if f:
            spin_angle += (keys[i].get("spin", 0) * (1 - w) + keys[j].get("spin", 0) * w) / fps
        ri = names.index(names[[k for k in range(len(names)) if par[k] < 0][0]])
        rots[ri] = (q("y", spin_angle) * q("x", flip) * Rot.from_quat(rots[ri])).as_quat()
        # ground: lowest point of the posed body on y = 0; anchor point keeps its xz on the floor
        R0, Pj = anim.fk(par, heads, rots, np.zeros(3))
        Tj = anim.tails_world(R0, Pj, heads, tails)
        X = pose_points(points, bones, rots, np.zeros(3))
        dy = -X[:, 1].min()
        mode = keys[i].get("anchor", "feet") if u < .5 else keys[j].get("anchor", "feet")
        cxz = _contact(Pj, Tj, names, mode)
        if mode != prev_anchor:  # a new contact: it stays where it touches now
            target = cxz + hold
            prev_anchor = mode
        if mode != "free":
            hold = target - cxz  # the contact point does not slide (spins turn about it)
        rt = np.array([hold[0], dy, hold[1]])
        root.append([f, *map(lambda v: round(float(v), 5), rt)])
        for bi, n in enumerate(names):
            out_keys[n].append([f, *map(lambda v: round(float(v), 5), rots[bi])])
    return {"preset": name, "fps": fps, "frames": frames, "loop": loop, "keys": out_keys, "root": root}


# ---------------------------------------------------------------- QA for block bodies
def qa(points, bones, clip, step=1):
    """Problems a viewer would see, per frame: gap (two neighbouring blocks part at a joint), ground (body below the
    floor), pass (a block inside a non-neighbouring block), jerk (a point jumps between frames). Returns text + data."""
    names, par, heads, tails = order(bones)
    P0, b = points["P"], points["b"]
    H = float(np.ptp(P0[:, 1]))
    blocks = sorted(set(b.tolist()))

    def owner_parent(i):  # nearest ancestor that owns a block (neck, shoulder own none)
        p = par[i]
        while p >= 0 and p not in blocks:
            p = par[p]
        return p
    # neighbours: blocks joined through bones that own no block (neck, shoulder, hips, spine) count as touching
    adj = {i: set() for i in range(len(names))}
    for i in range(len(names)):
        if par[i] >= 0:
            adj[i].add(par[i]), adj[par[i]].add(i)
    near = set()
    for s0 in blocks:
        seen, stack = {s0}, [s0]
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if w in seen:
                    continue
                seen.add(w)
                if w in blocks:
                    near |= {(s0, w), (w, s0)}
                else:
                    stack.append(w)
    pairs = []
    for i in blocks:
        p = owner_parent(i)
        if p < 0:
            continue
        ci = np.flatnonzero((b == i) & (np.linalg.norm(P0 - heads[i], axis=1) < .06 * H))
        pi = np.flatnonzero((b == p) & (np.linalg.norm(P0 - heads[i], axis=1) < .06 * H))
        if len(ci) and len(pi):
            d0 = cKDTree(P0[pi]).query(P0[ci])[0].min()
            pairs.append((i, p, ci, pi, d0))
    hulls = {}
    from scipy.spatial import Delaunay
    for i in blocks:
        pts = P0[b == i]
        if len(pts) > 8 and np.ptp(pts, 0).min() > 1e-3:
            try:
                hulls[i] = Delaunay(pts)
            except Exception:
                pass
    frames = range(0, clip["frames"] + 1, step)
    gaps, ground, passes, jerks = {}, [], {}, []
    prev = None
    for f in frames:
        rots, rt = anim.sample(clip, names, f)
        R, Pj = anim.fk(par, heads, rots, rt)
        X = Pj[b] + np.einsum("nij,nj->ni", R[b], P0 - heads[b])
        if X[:, 1].min() < -.01 * H:
            ground.append((f, float(X[:, 1].min())))
        for i, p, ci, pi, d0 in pairs:
            d = cKDTree(X[pi]).query(X[ci])[0].min() - d0
            if d > .015 * H:
                gaps.setdefault((names[i], names[p]), []).append((f, float(d)))
        # pass-through: points of block a inside block c's rest hull, moved into c's frame
        for c, hull in hulls.items():
            sel = (b != c) & ~np.isin(b, [k for k in blocks if (k, c) in near or k == c])
            if not sel.any():
                continue
            loc = np.einsum("nji,nj->ni", np.broadcast_to(R[c], (sel.sum(), 3, 3)), X[sel] - Pj[c]) + heads[c]
            inside = hull.find_simplex(loc) >= 0
            if inside.sum() > 15:
                who = np.bincount(b[sel][inside]).argmax()
                passes.setdefault((names[who], names[c]), []).append((f, int(inside.sum())))
        if prev is not None:
            v = np.linalg.norm(X - prev, axis=1).max() / step
            if v > .12 * H:
                jerks.append((f, float(v)))
        prev = X
    rng = lambda fs: f"{fs[0][0]}-{fs[-1][0]}" if fs else ""
    lines = [
        f"gaps {'OK' if not gaps else 'BAD ' + '; '.join(f'{a}|{p} {max(d for _, d in fs) * 100:.1f}cm f{rng(fs)}' for (a, p), fs in list(gaps.items())[:6])}",
        f"ground {'OK' if not ground else f'BAD min {min(y for _, y in ground) * 100:.1f}cm f{rng(ground)}'}",
        f"pass-through {'OK' if not passes else 'BAD ' + '; '.join(f'{a} in {c} f{rng(fs)}' for (a, c), fs in list(passes.items())[:6])}",
        f"jerks {'OK' if not jerks else f'BAD max {max(v for _, v in jerks) * 100:.0f}cm/frame f{rng(jerks)}'}",
    ]
    bad = sum(" BAD" in l for l in lines)
    return {"text": f"{clip.get('preset')} {clip['frames']}f · {bad} problem(s)\n" + "\n".join(lines), "ok": bad == 0,
            "gaps": {f"{a}|{p}": fs for (a, p), fs in gaps.items()}, "passes": {f"{a} in {c}": fs for (a, c), fs in passes.items()},
            "ground": ground, "jerks": jerks}
