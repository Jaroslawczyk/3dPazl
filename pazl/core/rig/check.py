"""Motion checks an AI can read cheaply: one compact line per check plus a {frame: [issue codes]} map.
Penetration uses per-bone capsules (radius from the vertices each bone dominates); only depth beyond what the
pair already overlaps in rest counts, so neighbouring body parts touching at rest are not reported."""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from . import anim
from .skeleton import limits_for, order


def skin(V, joints, weights, heads, R, P):
    out = np.zeros_like(V)
    for k in range(joints.shape[1]):
        j = joints[:, k]
        w = weights[:, k:k + 1]
        out += w * (np.einsum("nij,nj->ni", R[j], V - heads[j]) + P[j])
    return out


def _segdist(a0, a1, b0, b1):
    """Closest distance between two segments (sampled; robust and cheap enough for ~20 bones)."""
    t = np.linspace(0, 1, 9)
    A = a0 + t[:, None] * (a1 - a0)
    B = b0 + t[:, None] * (b1 - b0)
    return float(np.linalg.norm(A[:, None] - B[None], axis=2).min())


def _ranges(fr):
    fr = sorted(set(fr))
    out, s = [], None
    for i, f in enumerate(fr):
        if s is None:
            s = f
        if i == len(fr) - 1 or fr[i + 1] != f + 1:
            out.append(f"{s}" if s == f else f"{s}-{f}")
            s = None
    return ",".join(out[:6]) + ("…" if len(out) > 6 else "")


def run(bones, V, F, joints, weights, clip, samples=24):
    names, par, heads, tails = order(bones)
    m = len(names)
    H = float(np.ptp(V[:, 1])) or 1.0
    frames = clip["frames"]
    fl = sorted(set(np.linspace(0, frames, min(samples, frames + 1)).round().astype(int).tolist()))
    issues: dict[int, list] = {}
    lines = []

    def flag(f, code):
        issues.setdefault(int(f), []).append(code)

    # unweighted
    unw = int((weights.sum(1) < 0.5).sum())
    lines.append(f"unweighted {unw}/{len(V)} " + ("OK" if unw == 0 else "BAD"))

    # capsules
    dom = joints[np.arange(len(V)), np.argmax(weights, 1)]
    from .weights import seg_dist
    rad = np.zeros(m)
    for i in range(m):
        sel = V[dom == i]
        if len(sel):
            rad[i] = np.percentile(seg_dist(sel, heads[i:i + 1], tails[i:i + 1])[:, 0], 60)
    near = set()
    for i in range(m):
        if par[i] >= 0:
            near |= {(i, par[i]), (par[i], i)}
            for k in range(m):
                if par[k] == par[i]:
                    near.add((i, k))
            if par[par[i]] >= 0:
                near |= {(i, par[par[i]]), (par[par[i]], i)}
    pairs = [(a, b) for a in range(m) for b in range(a + 1, m) if (a, b) not in near and rad[a] > 0 and rad[b] > 0]
    rest_depth = {(a, b): rad[a] + rad[b] - _segdist(heads[a], tails[a], heads[b], tails[b]) for a, b in pairs}

    E = np.unique(np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1), axis=0) if len(F) else np.zeros((0, 2), int)
    L0 = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    okE = L0 > 0.3 * np.median(L0) if len(L0) else L0 > 0  # tiny pole/seam edges give meaningless ratios
    lim_bad, pen, stretch_max, stretch_fr = {}, {}, 1.0, []
    ground_min, ground_fr = 0.0, []
    blen_max = 0.0
    con = anim.contacts(bones)
    prevT, slide_max, slide_fr = None, 0.0, []
    ground_y = float(tails[con, 1].min()) if con else 0.0
    restL = np.linalg.norm(heads - heads[np.maximum(par, 0)], axis=1)
    dt = 1.0 / clip.get("fps", 30)
    for f in fl:
        rots, rt = anim.sample(clip, names, f)
        R, P = anim.fk(par, heads, rots, rt)
        T = anim.tails_world(R, P, heads, tails)
        # joint limits
        eul = np.degrees(Rot.from_quat(rots).as_rotvec())  # per-axis angle, no euler wrap at ±90°
        for i, n in enumerate(names):
            lim = limits_for(n)
            if not lim:
                continue
            for a, ax in enumerate("xyz"):
                lo, hi = lim[ax]
                v = eul[i, a]
                if v < lo - 2 or v > hi + 2:
                    lim_bad.setdefault((n, ax, lo, hi), []).append((f, v)); flag(f, f"limit:{n}.{ax}")
        # bone lengths
        bl = np.linalg.norm(P - P[np.maximum(par, 0)], axis=1)
        blen_max = max(blen_max, float(np.abs(bl - restL)[par >= 0].max(initial=0)))
        # penetration
        for a, b in pairs:
            d = rad[a] + rad[b] - _segdist(P[a], T[a], P[b], T[b]) - max(rest_depth[(a, b)], 0)
            if d > 0.01 * H:
                key = (names[a], names[b])
                pen.setdefault(key, []).append((f, d)); flag(f, f"pen:{key[0]}~{key[1]}")
        # skinned mesh: stretch, ground
        X = skin(V, joints.astype(int), weights, heads, R, P)
        if okE.any():
            r = np.linalg.norm(X[E[okE, 0]] - X[E[okE, 1]], axis=1) / L0[okE]
            mx = float(np.percentile(np.maximum(r, 1 / np.maximum(r, 1e-6)), 99))  # robust: ignore a few seam edges
            stretch_max = max(stretch_max, mx)
            if mx > 2.5:  # linear-blend joints reach ~2x; beyond that the mesh visibly tears or collapses
                stretch_fr.append(f); flag(f, "stretch")
        g = float(X[:, 1].min() - V[:, 1].min())
        ground_min = min(ground_min, g)
        if g < -0.01 * H:
            ground_fr.append(f); flag(f, "ground")

    # foot sliding: every frame (FK only), world space, only while the contact stays planted (<0.5% H high)
    for f in range(frames + 1) if con else []:
        rots, rt = anim.sample(clip, names, f)
        R, P = anim.fk(par, heads, rots, rt)
        T = anim.tails_world(R, P, heads, tails)
        if prevT is not None:
            for c in con:
                if T[c, 1] - ground_y < 0.005 * H and prevT[c, 1] - ground_y < 0.005 * H:
                    sl = float(np.linalg.norm((T[c] - prevT[c])[[0, 2]]))
                    slide_max = max(slide_max, sl)
                    if sl > 0.005 * H:
                        slide_fr.append(f); flag(f, f"slide:{names[c]}")
        prevT = T

    cm = lambda x: f"{x * 100:.1f}cm"
    if lim_bad:
        worst = sorted(lim_bad.items(), key=lambda kv: -max(abs(v) for _, v in kv[1]))[:5]
        lines.append("limits BAD " + "; ".join(
            f"{n}.{ax} {max((v for _, v in fs), key=abs):.0f}° (lim {lo}..{hi}) f{_ranges([f for f, _ in fs])}"
            for (n, ax, lo, hi), fs in worst))
    else:
        lines.append("limits OK")
    if pen:
        worst = sorted(pen.items(), key=lambda kv: -max(d for _, d in kv[1]))[:5]
        lines.append("penetration BAD " + "; ".join(f"{a}~{b} {cm(max(d for _, d in fs))} f{_ranges([f for f, _ in fs])}" for (a, b), fs in worst))
    else:
        lines.append("penetration OK")
    lines.append(f"stretch max x{stretch_max:.2f} " + (f"BAD f{_ranges(stretch_fr)}" if stretch_fr else "OK"))
    lines.append(f"ground min {cm(ground_min)} " + (f"BAD f{_ranges(ground_fr)}" if ground_fr else "OK"))
    lines.append(f"foot_slide max {cm(slide_max)}/frame " + (f"BAD f{_ranges(slide_fr)}" if slide_fr else "OK") if con else "foot_slide n/a")
    lines.append(f"bone_len max change {cm(blen_max)} " + ("OK" if blen_max < 0.002 * H else "BAD"))
    bad = sum(1 for l in lines if " BAD" in l or l.endswith("BAD"))
    head = f"{clip.get('preset', 'clip')} {frames}f@{clip.get('fps', 30)} sampled {len(fl)} · {bad} problem(s)"
    return {"text": head + "\n" + "\n".join(lines), "ok": bad == 0, "frames": {str(k): v for k, v in sorted(issues.items())}}
