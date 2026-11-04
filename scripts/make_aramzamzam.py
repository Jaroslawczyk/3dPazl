"""'Aram Zam Zam' dance clip for the Roblox outfit avatar. 8 beats at 120 BPM (4 s, 120 frames at 30 fps), loops.
Beats 0-2 hand pumps, 2-4 rolling hands, 4-6 arms up with claps, 6-8 side shimmy with arms out.
Run: PYTHONPATH=. .venv/Scripts/python.exe scripts/make_aramzamzam.py [char]"""
import math
import sys

import numpy as np

from pazl.core import chars, rig
from pazl.core.rig import anim
from pazl.core.rig.skeleton import order

q = anim.q
CHAR = sys.argv[1] if len(sys.argv) > 1 else "roblox_outfit"
BEATS, FPS, BPM = 8, 30, 120
FRAMES = int(BEATS * 60 / BPM * FPS)
DOWN = {".L": q("z", -60), ".R": q("z", 60)}


def leg(i, u, sd, side, ph):
    """One leg on its own: segment 0 alternating knee lifts, 1 heel taps, 2 side steps, 3 out-of-phase knee bends."""
    w = math.sin(math.pi * u + ph)
    lift = max(0.0, w)  # this leg is in the air during its own beat
    if i == 0:
        t, sh, fo, ab = -(10 + 48 * lift), 20 + 62 * lift, 18 * lift, 3 * lift
    elif i == 1:
        t, sh, fo, ab = -(8 + 32 * lift), 8 + 4 * lift, -28 * lift, 0
    elif i == 2:
        t, sh, fo, ab = -(10 + 20 * lift), 20 + 30 * lift, 8 * lift, 28 * lift
    else:
        b = 8 + 22 * (.5 + .5 * math.cos(2 * math.pi * u + ph))
        t, sh, fo, ab = -b, 2 * b, -b, 7 * (.5 + .5 * math.cos(2 * math.pi * u + ph))
    if i != 3:
        fo = -(t + sh) + fo  # flat foot unless the leg is lifted
    return {"thigh" + sd: q("x", t) * q("z", side * ab), "shin" + sd: q("x", sh), "foot" + sd: q("x", fo)}


def segment(i, u):
    """Local rotations of segment i at beat u (u in beats, inside the segment: 0..2)."""
    a = 2 * math.pi * u  # one bounce per beat
    r = {"shoulder.L": q("z", -15), "shoulder.R": q("z", 15)}
    for sd, side, ph in ((".L", 1, 0.0), (".R", -1, math.pi)):  # each leg has its own motion and phase
        r.update(leg(i, u, sd, side, ph))
    r["spine"] = q("x", 2 * (.5 + .5 * math.cos(a)))
    for sd, kk, ph in ((".L", 1, 0), (".R", -1, math.pi)):
        if i == 0:  # alternating pumps in front
            r["upper_arm" + sd] = q("x", -70 + 28 * math.sin(a + ph)) * q("z", kk * 8) * DOWN[sd]
            r["forearm" + sd] = q("y", -kk * (70 + 25 * math.sin(a + ph)))
            r["chest"] = q("y", 10 * math.sin(math.pi * u))
            r["head"] = q("z", 6 * math.sin(math.pi * u))
        elif i == 1:  # both hands roll round each other
            r["upper_arm" + sd] = q("x", -85 + 18 * math.cos(a + ph)) * q("z", kk * 14) * DOWN[sd]
            r["forearm" + sd] = q("y", -kk * (65 + 30 * math.sin(a + ph)))
            r["hand" + sd] = q("z", kk * 25 * math.sin(a + ph))
            r["hips"] = q("y", 12 * math.sin(math.pi * u))
            r["head"] = q("y", -8 * math.sin(math.pi * u))
        elif i == 2:  # arms overhead, clap on each beat
            clap = .5 + .5 * math.cos(a)
            r["upper_arm" + sd] = q("x", -150) * q("z", kk * (20 - 14 * clap)) * DOWN[sd]
            r["forearm" + sd] = q("y", -kk * (10 + 35 * (1 - clap)))
            r["hips"] = q("z", 6 * math.sin(math.pi * u))
            r["head"] = q("x", -8)
        else:  # side shimmy, arms out
            sh = math.sin(math.pi * u * 2)
            r["upper_arm" + sd] = q("x", -20 + 12 * sh * kk) * q("z", kk * -(-30)) * DOWN[sd]
            r["forearm" + sd] = q("y", -kk * (30 + 20 * math.sin(a + ph)))
            r["hips"] = q("y", 16 * sh)
            r["chest"] = q("y", -12 * sh)
            r["head"] = q("z", 8 * sh)
    return r


def pose(f):
    u = f / FPS * BPM / 60  # beats since start
    i, lu = int(u // 2) % 4, u % 2
    r = segment(i, lu)
    if lu > 1.6:  # ease into the next segment over the last 0.4 beat
        w = (lu - 1.6) / .4
        w = w * w * (3 - 2 * w)
        n = segment((i + 1) % 4, 0.0)
        for b in set(r) | set(n):
            x, y = r.get(b, q("x", 0)).as_quat(), n.get(b, q("x", 0)).as_quat()
            r[b] = anim.Rot.from_quat(anim.slerp(x, y, w))
    return r


rg = rig.load("char_" + CHAR)
names, par, heads, tails = order(rg["bones"])
con = anim.contacts(rg["bones"])
rest = np.tile([0, 0, 0, 1.0], (len(names), 1))
_, P0 = anim.fk(par, heads, rest, np.zeros(3))
T0 = anim.tails_world(np.tile(np.eye(3), (len(names), 1, 1)), P0, heads, tails)
ground, X0, Z0 = T0[con, 1].min(), T0[con, 0], T0[con, 2]
keys, root = {n: [] for n in names}, []
for f in range(FRAMES + 1):
    pz = pose(f % FRAMES)
    rots = rest.copy()
    for n, r in pz.items():
        if n in names:
            rots[names.index(n)] = r.as_quat()
    for i, n in enumerate(names):
        if n in pz:
            keys[n].append([f, *(round(float(v), 5) for v in rots[i])])
    R, P = anim.fk(par, heads, rots, np.zeros(3))
    T = anim.tails_world(R, P, heads, tails)
    dy = ground - np.vstack([T[con], P[con]])[:, 1].min()
    w = np.exp(-(T[con, 1] - T[con, 1].min()) / .03)  # the foot on the ground carries the body: the hips move over it
    w /= w.sum()
    root.append([f, round(float((w * (X0 - T[con, 0])).sum()), 5), round(float(dy), 5), round(float((w * (Z0 - T[con, 2])).sum()), 5)])
rg["clips"]["aramzamzam"] = {"preset": "custom", "fps": FPS, "frames": FRAMES, "loop": True, "keys": {n: k for n, k in keys.items() if k}, "root": root}
rig.save(rg)
print(chars.export(CHAR)["clips"])
