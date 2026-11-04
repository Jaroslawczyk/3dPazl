"""Skeleton templates (own design, not taken from any other tool) and fitting them to a mesh's bounding box.
Bone = {name, parent, head, tail, roll}. Coordinates: glTF (Y up, character faces +Z, its left side is +X).
Rest rotations are identity: a bone's local frame is world-aligned in the rest pose, so animation keys are
plain rotations about world-aligned axes (X = pitch forward/back, Y = twist, Z = side)."""
from __future__ import annotations

import numpy as np

SIDES = ((".L", 1), (".R", -1))


def _humanoid():
    # normalized: x * width (arm span, T-pose), y * height, z * height (around the box centre)
    b = [("hips", None, (0, .53, 0), (0, .60, 0)),
         ("spine", "hips", (0, .60, 0), (0, .70, 0)),
         ("chest", "spine", (0, .70, 0), (0, .82, 0)),
         ("neck", "chest", (0, .82, 0), (0, .87, 0)),
         ("head", "neck", (0, .87, 0), (0, 1.0, 0))]
    for s, k in SIDES:
        b += [("shoulder" + s, "chest", (.02 * k, .81, 0), (.10 * k, .81, 0)),
              ("upper_arm" + s, "shoulder" + s, (.10 * k, .81, 0), (.26 * k, .81, 0)),
              ("forearm" + s, "upper_arm" + s, (.26 * k, .81, 0), (.41 * k, .81, 0)),
              ("hand" + s, "forearm" + s, (.41 * k, .81, 0), (.5 * k, .81, 0)),
              ("thigh" + s, "hips", (.055 * k, .51, 0), (.055 * k, .28, 0)),
              ("shin" + s, "thigh" + s, (.055 * k, .28, 0), (.055 * k, .045, 0)),
              ("foot" + s, "shin" + s, (.055 * k, .045, 0), (.055 * k, 0, .075))]
    return b


def _quadruped():
    # normalized: x * width, y * height, z * length (head towards +Z)
    b = [("hips", None, (0, .62, -.30), (0, .64, -.05)),
         ("spine", "hips", (0, .64, -.05), (0, .65, .20)),
         ("chest", "spine", (0, .65, .20), (0, .66, .32)),
         ("neck", "chest", (0, .66, .32), (0, .82, .42)),
         ("head", "neck", (0, .82, .42), (0, .85, .5)),
         ("tail", "hips", (0, .64, -.32), (0, .5, -.5))]
    for s, k in SIDES:
        b += [("fleg_up" + s, "chest", (.3 * k, .6, .3), (.3 * k, .32, .32)),
              ("fleg_lo" + s, "fleg_up" + s, (.3 * k, .32, .32), (.3 * k, 0, .3)),
              ("bleg_up" + s, "hips", (.3 * k, .58, -.32), (.3 * k, .3, -.28)),
              ("bleg_lo" + s, "bleg_up" + s, (.3 * k, .3, -.28), (.3 * k, 0, -.32))]
    return b


def _simple():
    return [("bone0", None, (0, 0, 0), (0, .34, 0)), ("bone1", "bone0", (0, .34, 0), (0, .67, 0)),
            ("bone2", "bone1", (0, .67, 0), (0, 1, 0))]


TEMPLATES = {"humanoid": ("Человек (двуногий)", _humanoid), "quadruped": ("Четвероногое", _quadruped),
             "simple": ("Простая цепочка (3 кости)", _simple)}

# joint limits for local rotation, extrinsic xyz euler degrees; for .R bones y and z are mirrored
LIMITS = {
    "hips": None, "upper_arm": None,
    "spine": {"x": (-40, 60), "y": (-40, 40), "z": (-40, 40)},
    "chest": {"x": (-40, 60), "y": (-40, 40), "z": (-40, 40)},
    "neck": {"x": (-50, 60), "y": (-70, 70), "z": (-40, 40)},
    "head": {"x": (-50, 60), "y": (-70, 70), "z": (-40, 40)},
    "shoulder": {"x": (-30, 30), "y": (-30, 30), "z": (-30, 30)},
    "forearm": {"x": (-15, 15), "y": (-150, 5), "z": (-15, 15)},
    "hand": {"x": (-80, 80), "y": (-80, 80), "z": (-80, 80)},
    "thigh": {"x": (-120, 40), "y": (-40, 40), "z": (-20, 50)},
    "shin": {"x": (-5, 150), "y": (-10, 10), "z": (-10, 10)},
    "foot": {"x": (-50, 45), "y": (-30, 30), "z": (-30, 30)},
    "fleg_up": {"x": (-70, 70), "y": (-20, 20), "z": (-25, 25)},
    "bleg_up": {"x": (-70, 70), "y": (-20, 20), "z": (-25, 25)},
    "fleg_lo": {"x": (-120, 10), "y": (-10, 10), "z": (-10, 10)},
    "bleg_lo": {"x": (-10, 120), "y": (-10, 10), "z": (-10, 10)},
    "tail": {"x": (-80, 80), "y": (-80, 80), "z": (-80, 80)},
}


def limits_for(name: str):
    base, side = (name[:-2], name[-2:]) if name[-2:] in (".L", ".R") else (name, "")
    lim = LIMITS.get(base)
    if not lim:
        return None
    if side == ".R":
        lim = {"x": lim["x"], "y": (-lim["y"][1], -lim["y"][0]), "z": (-lim["z"][1], -lim["z"][0])}
    return lim


def fit(template: str, bounds) -> list[dict]:
    """Template scaled to the mesh bounding box (min, max)."""
    lo, hi = np.asarray(bounds, float)
    size, c = hi - lo, (lo + hi) / 2
    raw = TEMPLATES[template][1]()
    if template == "simple":  # along the longest axis
        ax = int(np.argmax(size))
        def P(p):
            q = c.copy(); q[ax] = lo[ax] + p[1] * size[ax]; return q
    elif template == "quadruped":
        def P(p):
            return np.array([c[0] + p[0] * size[0], lo[1] + p[1] * size[1], c[2] + p[2] * size[2]])
    else:
        def P(p):
            return np.array([c[0] + p[0] * size[0], lo[1] + p[1] * size[1], c[2] + p[2] * size[1]])
    return [{"name": n, "parent": par, "head": [round(float(v), 4) for v in P(h)],
             "tail": [round(float(v), 4) for v in P(t)], "roll": 0.0} for n, par, h, t in raw]


def order(bones: list[dict]):
    """(names, parent index array, heads (m,3), tails (m,3)); bones must be listed parents-first."""
    names = [b["name"] for b in bones]
    idx = {n: i for i, n in enumerate(names)}
    par = np.array([idx.get(b["parent"], -1) if b["parent"] else -1 for b in bones])
    if any(p >= i for i, p in enumerate(par)):
        raise ValueError("bones must be ordered parents first")
    return names, par, np.array([b["head"] for b in bones], float), np.array([b["tail"] for b in bones], float)
