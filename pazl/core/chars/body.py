"""Character bodies: one continuous organic skin from a sculpted field. Bones and surface come from the same
proportions, so the skeleton fits exactly. Y up, faces +Z, T-pose (see core/rig/skeleton.py)."""
from __future__ import annotations

import numpy as np
import trimesh

from ..rig import skeleton
from .field import Grid, cone, ellipsoid, loft, smin, surface_nets

HUMAN = {"height": 1.75, "build": 1.0, "muscle": 0.0, "head": 1.0, "shoulders": 1.0, "chest": 1.0, "waist": 1.0, "hips": 1.0,
         "belly": 0.0, "bust": 0.0, "legs": 1.0, "arms": 1.0, "nose": 1.0, "ears": 1.0, "ear_tip": 0.0,
         "color": "#d9ab8c", "eyes": "#4a6b8a"}
BEAST = {"height": 0.6, "length": 0.9, "build": 1.0, "head": 1.0, "snout": 1.0, "ears": 1.0, "ear_tip": 1.0, "tail": 1.0,
         "color": "#9a6a3e", "belly_color": "#e6d6bd", "eyes": "#3a2a1a"}
BLOB = {"height": 1.0, "build": 1.0, "head": 1.0, "color": "#6db24f", "belly_color": "#cfe6a6", "eyes": "#d03030"}
PRESETS = {
    "man": ("Мужчина", "human", {"shoulders": 1.08, "chest": 1.05, "waist": 1.02, "hips": .94}),
    "woman": ("Женщина", "human", {"height": 1.66, "shoulders": .9, "chest": .9, "waist": .8, "hips": 1.08, "bust": 1.0, "nose": .85, "color": "#e3b89c"}),
    "athlete": ("Атлет", "human", {"height": 1.85, "shoulders": 1.2, "chest": 1.18, "waist": .92, "hips": .96, "muscle": 1.0, "build": 1.08}),
    "chubby": ("Полный", "human", {"height": 1.7, "build": 1.22, "belly": 1.0, "waist": 1.3, "hips": 1.14, "chest": 1.12, "legs": .94}),
    "elder": ("Старик", "human", {"height": 1.62, "build": .9, "shoulders": .92, "belly": .35, "nose": 1.25, "ears": 1.2, "color": "#d6b09a"}),
    "child": ("Ребёнок", "human", {"height": 1.2, "head": 1.28, "shoulders": .86, "chest": .9, "hips": .9, "legs": .88, "nose": .7}),
    "toon": ("Мультяшный", "human", {"height": 1.3, "head": 1.75, "build": 1.05, "legs": .78, "arms": .9, "nose": 1.3, "ears": 1.3}),
    "goblin": ("Гоблин", "human", {"height": 1.15, "head": 1.45, "build": .84, "belly": .5, "nose": 2.0, "ears": 2.3, "ear_tip": 1.0, "legs": .84, "arms": 1.14, "color": "#7f9c52", "eyes": "#c9a227"}),
    "dog": ("Собака", "beast", {}),
    "cat": ("Кошка", "beast", {"height": .32, "length": .5, "build": .84, "snout": .42, "color": "#7d7d85", "belly_color": "#e8e8ea", "eyes": "#6e9c2e"}),
    "horse": ("Лошадь", "beast", {"height": 1.65, "length": 1.9, "build": .86, "head": .9, "snout": 1.6, "ears": .5, "color": "#5c3a22", "belly_color": "#5c3a22"}),
    "monster": ("Монстр-капля", "blob", {}),
}
BASE = {"human": HUMAN, "beast": BEAST, "blob": BLOB}
TEMPLATE = {"human": "humanoid", "beast": "quadruped", "blob": "simple"}


def params_for(preset, over=None):
    kind = PRESETS[preset][1]
    return kind, {**BASE[kind], **PRESETS[preset][2], **(over or {})}


def rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _bone(n, p, h, t):
    return {"name": n, "parent": p, "head": [round(float(v), 4) for v in h], "tail": [round(float(v), 4) for v in t], "roll": 0.0}


# ------------------------------------------------------------------ human
def human_joints(p):
    H = float(p["height"])
    u = H / 1.75
    hh = .134 * H * p["head"] ** .85
    hy = (H - hh) * .565 * p["legs"]
    nb = H - hh - .036 * u  # neck base
    T = nb - hy
    sw = .17 * u * p["shoulders"] * p["build"]
    sy = hy + .9 * T
    al = .74 * u * p["arms"]
    e, w, ht = sw + al * .42, sw + al * .78, sw + al
    hx = .085 * u * p["hips"] * p["build"]
    J = {"u": u, "H": H, "hh": hh, "hy": hy, "nb": nb, "T": T}
    b = [_bone("hips", None, (0, hy, 0), (0, hy + .16 * T, 0)), _bone("spine", "hips", (0, hy + .16 * T, 0), (0, hy + .46 * T, 0)),
         _bone("chest", "spine", (0, hy + .46 * T, 0), (0, nb, 0)), _bone("neck", "chest", (0, nb, 0), (0, H - hh, 0)),
         _bone("head", "neck", (0, H - hh, 0), (0, H, 0))]
    for s, k in skeleton.SIDES:
        knee, ank = (hx * 1.2 * k, hy * .53, .008 * u), (hx * 1.35 * k, .075 * u, -.01 * u)
        b += [_bone("shoulder" + s, "chest", (.03 * u * k, sy, 0), (sw * k, sy, 0)),
              _bone("upper_arm" + s, "shoulder" + s, (sw * k, sy, 0), (e * k, sy, 0)),
              _bone("forearm" + s, "upper_arm" + s, (e * k, sy, 0), (w * k, sy, 0)),
              _bone("hand" + s, "forearm" + s, (w * k, sy, 0), (ht * k, sy, 0)),
              _bone("thigh" + s, "hips", (hx * k, hy - .02 * u, 0), knee), _bone("shin" + s, "thigh" + s, knee, ank),
              _bone("foot" + s, "shin" + s, ank, (hx * 1.35 * k, 0, .15 * u))]
    return J, b


def _head(g, f, p, J):
    s = J["hh"] / .2345  # head scale: 1 = a 23 cm head
    cy = J["H"] - J["hh"] + J["hh"] * .52

    def P(x, y, z):
        return (x * s, cy + y * s, z * s)

    ellipsoid(g, f, P(0, .016, -.012), (.081 * s, .094 * s, .096 * s), .02 * s)     # cranium
    ellipsoid(g, f, P(0, -.05, .018), (.058 * s, .062 * s, .062 * s), .03 * s)      # jaw
    ellipsoid(g, f, P(0, -.098, .05), (.026 * s, .018 * s, .022 * s), .022 * s)     # chin
    for k in (1, -1):
        ellipsoid(g, f, P(.04 * k, -.03, .052), (.022 * s, .02 * s, .018 * s), .02 * s)     # cheek
        ellipsoid(g, f, P(.032 * k, .022, .068), (.026 * s, .007 * s, .012 * s), .012 * s)  # brow
        ellipsoid(g, f, P(.032 * k, .003, .086), (.016 * s, .0085 * s, .012 * s), .007 * s, cut=True)  # eye socket
    n = float(p["nose"])
    loft(g, f, P(0, .012, .072), P(0, -.032, .082 + .018 * n),
         [(0, .007 * s, .008 * s, 0), (.7, .010 * s * n ** .5, .011 * s, 0), (1, .012 * s * n ** .5, .010 * s, 0)], .012 * s)
    ellipsoid(g, f, P(0, -.066, .0725), (.02 * s, .0055 * s, .007 * s), .008 * s)   # lips
    e, tip = float(p["ears"]), float(p["ear_tip"])
    for k in (1, -1):
        ellipsoid(g, f, P(.078 * k, -.002, -.008), (.009 * s, .029 * s * e ** .5, .017 * s * e ** .5), .006 * s)
        if tip:
            loft(g, f, P(.078 * k, .01, -.012), P((.08 + .075 * e * tip) * k, .05 * e, -.05 * e),
                 [(0, .016 * s, .008 * s, 0), (1, .003 * s, .003 * s, 0)], .008 * s, (0, 1, 0))
    return s, P


def _hand(g, f, bone, k, u):
    a, b = np.array(bone["head"]), np.array(bone["tail"])
    L = (b[0] - a[0]) * k

    def X(t, y, z):
        return (a[0] + k * L * t, a[1] + y * u, z * u)

    loft(g, f, X(-.1, 0, 0), X(.56, 0, 0), [(0, .026 * u, .02 * u, 0), (.5, .044 * u, .017 * u, 0), (1, .042 * u, .015 * u, 0)], .012 * u, (0, 0, 1))
    for z, ln in [(.03, .9), (.01, 1.0), (-.01, .94), (-.03, .76)]:
        cone(g, f, X(.5, -.002, z), X(.5 + .5 * ln, -.003, z * 1.1), .0105 * u, .0085 * u, .004 * u)
    cone(g, f, X(.05, -.004, .036), X(.42, -.006, .07), .014 * u, .0095 * u, .012 * u)


def human_field(p, cell=None):
    J, bones = human_joints(p)
    by = {b["name"]: b for b in bones}
    u, H, hy, T, nb = J["u"], J["H"], J["hy"], J["T"], J["nb"]
    B, M = float(p["build"]) * u, float(p["muscle"])
    cell = cell or max(.005, .0075 * u)
    span = by["hand.L"]["tail"][0] + .05
    be, bs = float(p["belly"]), float(p["bust"])
    c, w, hp, sh = float(p["chest"]), float(p["waist"]), float(p["hips"]), float(p["shoulders"])
    depth = .26 * u + .14 * be * B + .08 * J["hh"] / .224
    g = Grid((-span, -.02, -depth), (span, H + .03, depth), cell)
    t = g.empty()  # torso + head: arms and legs each blend with it, never with one another (no webbing)
    loft(g, t, (0, hy - .07 * u, 0), (0, nb + .012 * u, 0), [
        (0, .105 * hp * B, .085 * B, -.004), (.16, .168 * hp * B, .112 * B, -.012), (.34, .15 * (hp + w) / 2 * B, .102 * B, -.002 + .01 * be),
        (.5, .128 * w * B, (.092 + .045 * be) * B, .024 * be), (.75, .162 * c * B, .114 * c * B, .012),
        (.87, .172 * sh * B, .098 * c * B, .002), (.96, .118 * sh * B, .072 * B, -.006), (1, .062 * B, .055 * B, -.006)])
    cone(g, t, (0, nb - .02 * u, -.006 * u), (0, H - J["hh"] * .78, .004 * u), .056 * B * (1 + .1 * M), .05 * u, .02 * u)
    for k in (1, -1):
        ellipsoid(g, t, (.075 * hp * B * k, hy - .01 * u, -.075 * B), (.08 * hp * B, .088 * B, .068 * B), .03 * u)  # glutes
        if bs:
            ellipsoid(g, t, (.068 * B * k, hy + .72 * T, .092 * B * c), (.062 * B, .058 * B * (.8 + .2 * bs), .05 * B * (.7 + .3 * bs)), .035 * u)
        if M:
            ellipsoid(g, t, (.08 * B * k, hy + .77 * T, .085 * B), (.085 * B, .058 * B, .036 * B * M), .03 * u)  # pecs
    s, Hd = _head(g, t, p, J)
    f = t.copy()
    for side, k in skeleton.SIDES:
        l = g.empty()  # leg
        a, b, c2 = (np.array(by[n + side]["head"]) for n in ("thigh", "shin", "foot"))
        m = 1 + .22 * M
        loft(g, l, a + (0, .03 * u, 0), b, [(0, .05 * B, .06 * B, 0), (.14, .088 * B * m, .094 * B * m, 0), (.4, .084 * B * m, .09 * B * m, .006), (.8, .06 * B, .064 * B, .002), (1, .052 * B, .056 * B, .002)])
        loft(g, l, b, c2, [(0, .052 * B, .056 * B, 0), (.3, .058 * B * m, .068 * B * m, -.012 * u), (.75, .036 * B, .04 * B, -.004 * u), (1, .032 * B, .036 * B, 0)], .02 * u)
        ellipsoid(g, l, b + (0, .004 * u, .036 * B), (.03 * B, .032 * B, .022 * B), .025 * u)  # kneecap
        loft(g, l, (c2[0], .03 * u, -.075 * u), (c2[0], .022 * u, .185 * u),
             [(0, .026 * u, .03 * u, 0), (.25, .036 * u, .036 * u, .006 * u), (.65, .044 * u, .03 * u, -.002 * u), (.9, .046 * u, .021 * u, -.006 * u), (1, .034 * u, .015 * u, -.007 * u)], .03 * u)
        f = np.minimum(f, smin(t, l, .07 * u))
        r = g.empty()  # arm
        a, b, c2 = (np.array(by[n + side]["head"]) for n in ("upper_arm", "forearm", "hand"))
        m = 1 + .3 * M
        loft(g, r, a + (-.03 * u * k, 0, 0), b, [(0, .056 * B * m, .06 * B * m, 0), (.25, .058 * B * m, .056 * B * m, 0), (.6, .049 * B * m, .049 * B * m, 0), (1, .039 * B, .04 * B, 0)], 0, (0, 1, 0))
        loft(g, r, b, c2, [(0, .039 * B, .04 * B, 0), (.28, .045 * B * m, .044 * B * m, 0), (1, .026 * u, .021 * u, 0)], .012 * u, (0, 1, 0))
        ellipsoid(g, r, a + (-.012 * u * k, -.002 * u, 0), (.07 * B * m, .062 * B * m, .068 * B * m), .05 * u)  # deltoid
        _hand(g, r, by["hand" + side], k, u)
        f = np.minimum(f, smin(t, r, .035 * u))
    eyes = [(Hd(.032 * k, .003, .0625), .0125 * s, (0, 0, 1)) for k in (1, -1)]
    tone = rgb(p["color"])
    return g, f, bones, eyes, [(np.array(Hd(0, -.066, .08)), .02 * s, tuple(tone * (.86, .62, .6)))]


# ------------------------------------------------------------------ four-legged
def beast_field(p, cell=None):
    H, Ln, B = float(p["height"]), float(p["length"]), float(p["build"])
    w = H * .16 * B
    bones = skeleton.fit("quadruped", [[-w, 0, -Ln / 2], [w, H, Ln / 2]])
    by = {b["name"]: b for b in bones}
    cell = cell or max(.0045, H * .0115)
    g = Grid((-w * 2.1 - .03, -.02, -Ln * .85 - .05), (w * 2.1 + .03, H * 1.42, Ln * .75 + H * .4 * float(p["snout"]) + .05), cell)
    t = g.empty()
    r = H * .2 * B
    hz, cz = np.array(by["hips"]["head"]), np.array(by["chest"]["tail"])
    loft(g, t, hz + (0, 0, -r * .5), cz + (0, 0, r * .7),
         [(0, r * .5, r * .55, 0), (.15, r * .92, r * .98, 0), (.45, r * .8, r * .86, -r * .03), (.8, r * 1.0, r * 1.1, -r * .08), (1, r * .55, r * .7, 0)])
    n0, n1 = np.array(by["neck"]["head"]), np.array(by["neck"]["tail"])
    cone(g, t, n0 + (0, -r * .1, -r * .1), n1, r * .62, r * .36 * p["head"], r * .3)
    hr = H * .105 * p["head"] * (.6 / H) ** .25
    fwd = np.array([0, -.28, .96])
    hc = n1 + fwd * hr * .4
    ellipsoid(g, t, hc, (hr * .95, hr * .95, hr * 1.05), hr * .3)
    sn = hr * 1.6 * float(p["snout"])
    tip = hc + fwd * (hr * .7 + sn)
    loft(g, t, hc + fwd * hr * .3, tip, [(0, hr * .72, hr * .72, 0), (.6, hr * .47, hr * .44, 0), (1, hr * .38, hr * .32, 0)], hr * .3)
    tl0 = np.array(by["tail"]["head"])
    tl1 = tl0 + (np.array(by["tail"]["tail"]) - tl0) * float(p["tail"])
    loft(g, t, tl0 + (0, 0, r * .3), tl1, [(0, r * .3, r * .3, 0), (.5, r * .17, r * .17, 0), (1, r * .05, r * .05, 0)], r * .22)
    e, tp = float(p["ears"]), float(p["ear_tip"])
    for k in (1, -1):
        base = hc + (hr * .62 * k, hr * .62, -hr * .1)
        loft(g, t, base, base + (hr * .3 * k * e, hr * 1.05 * e, -hr * .12),
             [(0, hr * .42, hr * .13, 0), (.6, hr * .3, hr * .1, 0), (1, hr * .04 + hr * .2 * (1 - tp), hr * .04, 0)], hr * .1)
    f = t.copy()
    for side, _ in skeleton.SIDES:
        for up, lo, rr in (("fleg_up", "fleg_lo", .78), ("bleg_up", "bleg_lo", .95)):
            l = g.empty()
            a, b = np.array(by[up + side]["head"]), np.array(by[lo + side]["head"])
            c = np.array(by[lo + side]["tail"])
            lr = r * .5 * rr
            loft(g, l, a + (0, r * .35, 0), b, [(0, lr * 1.25, lr * 1.5, 0), (.4, lr * 1.0, lr * 1.2, 0), (1, lr * .52, lr * .6, 0)])
            loft(g, l, b, c + (0, lr * .22, 0), [(0, lr * .52, lr * .6, 0), (.5, lr * .4, lr * .44, 0), (1, lr * .42, lr * .48, 0)], lr * .2)
            ellipsoid(g, l, c + (0, lr * .28, lr * .28), (lr * .58, lr * .3, lr * .85), lr * .3)  # paw / hoof
            f = np.minimum(f, smin(t, l, r * .24))
    eyes = [(hc + (hr * .55 * k, hr * .3, hr * .72), hr * .17, tuple(fwd)) for k in (1, -1)]
    return g, f, bones, eyes, [(tip + (0, hr * .1, hr * .08), hr * .22, (.1, .08, .08))]


# ------------------------------------------------------------------ blob creature
def blob_field(p, cell=None):
    H, B = float(p["height"]), float(p["build"])
    bones = skeleton.fit("simple", [[-H * .4, 0, -H * .4], [H * .4, H, H * .4]])
    bones = [{**b, "head": [0, b["head"][1], 0], "tail": [0, b["tail"][1], 0]} for b in bones]
    cell = cell or H * .011
    g = Grid((-H * .7 * B, -.02, -H * .6 * B), (H * .7 * B, H * 1.08, H * .6 * B), cell)
    f = g.empty()
    loft(g, f, (0, 0, 0), (0, H, 0), [(0, H * .22 * B, H * .22 * B, 0), (.08, H * .42 * B, H * .4 * B, 0), (.4, H * .38 * B, H * .36 * B, .01),
                                      (.8, H * .26 * B * p["head"], H * .25 * B, 0), (1, H * .06, H * .06, 0)])
    for k in (1, -1):
        cone(g, f, (H * .3 * B * k, H * .42, 0), (H * .55 * B * k, H * .3, H * .12), H * .08, H * .05, H * .07)
        ellipsoid(g, f, (H * .18 * B * k, H * .03, H * .1), (H * .13, H * .05, H * .17), H * .05)
    ellipsoid(g, f, (0, H * .5, H * .36 * B), (H * .13, H * .022, H * .04), H * .02, cut=True)
    eyes = [(np.array((H * .11 * k, H * .68, H * .235 * B)), H * .065, (0, 0, 1)) for k in (1, -1)]
    return g, f, bones, eyes, []


FIELDS = {"human": human_field, "beast": beast_field, "blob": blob_field}


def _eye(c, r, fwd, iris):
    m = trimesh.creation.icosphere(subdivisions=3, radius=r)
    d = np.asarray(fwd, float)
    d /= np.linalg.norm(d)
    a = (m.vertices / r) @ d
    col = np.where((a > .965)[:, None], (.03, .03, .04), np.where((a > .86)[:, None], iris, (.95, .95, .93)))
    return np.asarray(m.vertices) + c, np.asarray(m.faces), col


def _paint(kind, V, p, bones, marks):
    C = np.tile(rgb(p["color"]), (len(V), 1))
    top = V[:, 1].max()
    if kind == "blob":  # lighter belly
        t = np.clip(1 - (np.abs(V[:, 0]) / (top * .2)) ** 2, 0, 1) * np.clip(V[:, 2] * 8, 0, 1) * (V[:, 1] < top * .6)
    elif kind == "beast":
        hip = next(b for b in bones if b["name"] == "hips")["head"][1]
        t = np.clip((hip * .88 - V[:, 1]) / (top * .1), 0, 1) * (np.abs(V[:, 0]) < top * .13) * (V[:, 1] > hip * .55)
    else:
        t = None
    if t is not None:
        C = C * (1 - t[:, None]) + rgb(p["belly_color"]) * t[:, None]
    for c, r, col in marks:
        t = np.clip(1.4 - np.linalg.norm(V - c, axis=1) / r * 1.4, 0, 1)[:, None] ** .7
        C = C * (1 - t) + np.asarray(col) * t
    return C


def build(kind, p, cell=None):
    """(mesh, bones): vertex-coloured trimesh in metres; eyes are added as separate little balls."""
    g, f, bones, eyes, marks = FIELDS[kind](p, cell)
    V, F = surface_nets(f, g.lo, g.cell)
    m = trimesh.Trimesh(V, F, process=False)
    parts = m.split(only_watertight=False)  # drop stray specks
    if len(parts) > 1:
        m = max(parts, key=lambda x: len(x.vertices))
    if m.volume < 0:
        m.invert()
    trimesh.smoothing.filter_taubin(m, iterations=4)
    V, F = np.array(m.vertices), np.asarray(m.faces)
    V[:, 1] = np.maximum(V[:, 1], 0)  # soles stand on the ground
    C = _paint(kind, V, p, bones, marks)
    Vs, Fs, Cs, off = [V], [F], [C], len(V)
    for c, r, fwd in eyes:
        v, fa, col = _eye(np.asarray(c, float), r, fwd, rgb(p["eyes"]))
        Vs.append(v); Fs.append(fa + off); Cs.append(col); off += len(v)
    out = trimesh.Trimesh(np.vstack(Vs), np.vstack(Fs), process=False)
    out.visual.vertex_colors = (np.clip(np.vstack(Cs), 0, 1) * 255).astype(np.uint8)
    return out, bones


def sculpt(V, N, strokes):
    """Clay strokes: [{p:[x,y,z], r, amount (m, minus dents), mirror}] push the surface along its normal with a soft falloff."""
    V = np.array(V, float)
    for s in strokes:
        cs = [np.array(s["p"], float)]
        if s.get("mirror", True) and abs(cs[0][0]) > float(s["r"]) * .2:
            cs.append(cs[0] * (-1, 1, 1))
        for c in cs:
            d2 = ((V - c) ** 2).sum(1)
            V += N * (float(s["amount"]) * np.exp(-d2 / (2 * (float(s["r"]) / 2) ** 2)))[:, None]
    return V
