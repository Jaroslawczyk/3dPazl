"""Animation clips on a skeleton: forward kinematics, key sampling (slerp), procedural presets, key editing.
Clip = {fps, frames, loop, keys: {bone: [[f, qx, qy, qz, qw], ...]}, root: [[f, x, y, z], ...]}.
Keys are local rotations relative to the (identity) rest rotation; root = offset added to the root bone head.
Presets plant the feet: root height keeps the lowest contact point on the ground, root forward motion follows
the stance foot, so walk/run do not slide."""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from .skeleton import order

PRESETS = {"idle": "Стойка (дыхание)", "walk": "Шаг", "run": "Бег", "wave": "Привет рукой", "jump": "Прыжок"}


def q(axis: str, deg: float) -> Rot:
    return Rot.from_euler(axis, deg, degrees=True)


def slerp(a, b, t):
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + t * (b - a)
    else:
        th = math.acos(d)
        r = (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)
    return r / np.linalg.norm(r)


def _interp(keys, f, dim):
    if not keys:
        return None
    k = np.asarray(keys, float)
    if f <= k[0, 0]:
        return k[0, 1:]
    if f >= k[-1, 0]:
        return k[-1, 1:]
    i = int(np.searchsorted(k[:, 0], f, side="right")) - 1
    f0, f1 = k[i, 0], k[i + 1, 0]
    t = (f - f0) / max(f1 - f0, 1e-9)
    return slerp(k[i, 1:], k[i + 1, 1:], t) if dim == 4 else k[i, 1:] * (1 - t) + k[i + 1, 1:] * t


def sample(clip, names, f):
    rots = np.tile([0, 0, 0, 1.0], (len(names), 1))
    for i, n in enumerate(names):
        v = _interp(clip["keys"].get(n), f, 4)
        if v is not None:
            rots[i] = v
    rt = _interp(clip.get("root"), f, 3)
    return rots, (np.zeros(3) if rt is None else rt)


def fk(par, heads, rots, root_t):
    """World rotation matrices (m,3,3) and joint positions (m,3)."""
    m = len(par)
    R = np.zeros((m, 3, 3)); P = np.zeros((m, 3))
    L = Rot.from_quat(rots).as_matrix()
    for i in range(m):
        p = par[i]
        if p < 0:
            R[i] = L[i]; P[i] = heads[i] + root_t
        else:
            R[i] = R[p] @ L[i]; P[i] = P[p] + R[p] @ (heads[i] - heads[p])
    return R, P


def tails_world(R, P, heads, tails):
    return P + np.einsum("mij,mj->mi", R, tails - heads)


def contacts(bones):
    """Bones whose tails touch the ground in rest (feet, leg tips)."""
    _, par, h, t = order(bones)
    lo, H = min(h[:, 1].min(), t[:, 1].min()), np.ptp(np.vstack([h, t])[:, 1])
    leaf = [i for i in range(len(bones)) if i not in set(par.tolist())]
    return [i for i in leaf if t[i, 1] - lo < 0.06 * H]


# ---------------------------------------------------------------- presets
def _humanoid_pose(name, p, H):
    """Local rotations {bone: Rot} at phase p in [0,1)."""
    s, c = math.sin(2 * math.pi * p), math.cos(2 * math.pi * p)
    r = {}
    down = {"upper_arm.L": q("z", -60), "upper_arm.R": q("z", 60)}   # + 15° in the shoulder: smoother armpit
    r["shoulder.L"], r["shoulder.R"] = q("z", -15), q("z", 15)
    if name == "idle":
        r["chest"] = q("x", 2 * s)
        r["spine"] = q("z", 1.5 * math.sin(2 * math.pi * p))
        r["head"] = q("y", 6 * math.sin(2 * math.pi * p)) * q("x", 2 * c)
        for sd, k in ((".L", 1), (".R", -1)):
            r["upper_arm" + sd] = q("x", 2 * s) * down["upper_arm" + sd]
            r["forearm" + sd] = q("y", -k * 10)
    elif name in ("walk", "run"):
        run = name == "run"
        A, K, E = (40, 100, 85) if run else (25, 65, 18)
        for sd, ph in ((".L", 0.0), (".R", 0.5)):
            a = 2 * math.pi * (p + ph)
            th = -A * math.sin(a)
            aw = (a + math.pi) % (2 * math.pi) - math.pi   # thigh moves forward for aw in (-pi/2, pi/2): swing
            kn = 5 + K * math.sin(math.pi * (aw + 2.3) / 3.9) ** 1.0 if -2.3 < aw < 1.6 else 5.0  # flex starts at push-off
            th -= 10 if run else 0
            r["thigh" + sd] = q("x", th)
            r["shin" + sd] = q("x", kn)
            r["foot" + sd] = q("x", min(35.0, max(-40.0, -(th + kn) - 8 * max(0.0, math.cos(a)))))
            k = 1 if sd == ".L" else -1
            r["upper_arm" + sd] = q("x", 0.8 * A * math.sin(a)) * down["upper_arm" + sd]
            r["forearm" + sd] = q("y", -k * (E + 10 * max(0, -math.sin(a))))
        r["spine"] = q("x", 12 if run else 3)
        r["chest"] = q("y", (8 if run else 5) * s)
        r["hips"] = q("y", -(6 if run else 4) * s)
    elif name == "wave":
        r["upper_arm.L"] = down["upper_arm.L"]
        r["forearm.L"] = q("y", -10)
        r["shoulder.R"] = q("z", -10)
        r["upper_arm.R"] = q("z", -20) * q("x", -90)
        r["forearm.R"] = q("y", 85 + 15 * math.sin(4 * math.pi * p))
        r["hand.R"] = q("z", -10 * math.sin(4 * math.pi * p))
        r["head"] = q("y", -10) * q("z", 4 * s)
        r["chest"] = q("z", 3)
    elif name == "jump":
        # 0-.3 crouch, .3-.4 push, .4-.75 air, .75-1 land
        if p < .3:
            k = 50 * math.sin(p / .3 * math.pi / 2)
        elif p < .4:
            k = 50 * (1 - (p - .3) / .1)
        elif p < .75:
            k = 10 * math.sin((p - .4) / .35 * math.pi)
        else:
            k = 45 * math.sin((p - .75) / .25 * math.pi)
        arm = (30 * k / 50) if p < .3 else (-150 if p < .75 else -150 + (p - .75) / .25 * 150)
        for sd in (".L", ".R"):
            r["thigh" + sd] = q("x", -k)
            r["shin" + sd] = q("x", 2 * k)
            r["foot" + sd] = q("x", -k)
            r["upper_arm" + sd] = q("x", arm) * down["upper_arm" + sd]
            r["forearm" + sd] = q("y", (-15 if sd == ".L" else 15))
        r["spine"] = q("x", k * 0.6)
    return r


def _generic_pose(bones, name, p):
    """Quadruped / chain fallback: legs swing, tail wags, chain sways."""
    s = math.sin(2 * math.pi * p)
    amp = {"idle": 4, "walk": 22, "run": 35, "wave": 30, "jump": 15}[name]
    r = {}
    for b in bones:
        n = b["name"]
        if n.startswith(("fleg_up", "bleg_up")):
            ph = (0 if n.endswith(".L") else .5) + (0 if n.startswith("f") else .5)
            if name in ("walk", "run"):
                r[n] = q("x", -amp * math.sin(2 * math.pi * (p + ph)))
        elif n.startswith(("fleg_lo", "bleg_lo")) and name in ("walk", "run"):
            ph = (0 if n.endswith(".L") else .5) + (0 if n.startswith("f") else .5)
            v = 30 * max(0.0, math.cos(2 * math.pi * (p + ph) + .4)) ** 2
            r[n] = q("x", -v if n.startswith("f") else v)
        elif n == "tail":
            r[n] = q("y", amp * 1.2 * s)
        elif n in ("head", "neck"):
            r[n] = q("x", amp * 0.2 * s)
        elif n.startswith("bone") and b["parent"]:
            r[n] = q("z", amp * 0.5 * s)
    return r


def _leg_ik(dy, dz, l1, l2):
    """Sagittal 2-bone IK: hip->ankle offset (dy<0 down, dz forward) -> (thigh x, knee flex) degrees.
    Thigh +x swings the leg back, knee +x bends the shin back (knee points forward)."""
    d = min(math.hypot(dy, dz), (l1 + l2) * 0.9995)
    tgt = math.atan2(-dz, -dy)
    alpha = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    inner = math.acos(max(-1, min(1, (l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2))))
    return math.degrees(tgt - alpha), math.degrees(math.pi - inner)


def _gait(names, heads, preset, p, pose):
    """Feet planted by construction: stance foot fixed in world while the root moves at constant speed,
    swing foot travels forward on an arc; legs solved with IK. Returns root offset."""
    run = preset == "run"
    i = {n: names.index(n) for n in names}
    hip, knee, ank = heads[i["thigh.L"]], heads[i["shin.L"]], heads[i["foot.L"]]
    l1, l2 = float(np.linalg.norm(knee - hip)), float(np.linalg.norm(ank - knee))
    Lm = l1 + l2
    beta = 0.38 if run else 0.62                        # share of the cycle a foot is on the ground
    travel = (2.6 if run else 1.5) * Lm                   # root travel per cycle (two steps)
    S = travel * beta                                     # foot excursion relative to the hip during stance
    drop = (0.10 if run else 0.05) * Lm
    bob = (0.05 if run else 0.012) * Lm * math.cos(4 * math.pi * p)
    root_y = -drop + bob
    for sd, ph in ((".L", 0.0), (".R", 0.5)):
        u = (p + ph) % 1.0
        if u < beta:
            s = u / beta; z = S / 2 - S * s; lift = 0.0; toe = 0.0
        else:
            s = (u - beta) / (1 - beta)
            z = -S / 2 + S * (0.5 - 0.5 * math.cos(math.pi * s))
            lift = (0.22 if run else 0.10) * Lm * math.sin(math.pi * s); toe = -12 * math.sin(math.pi * s)
        dy = (ank[1] + lift) - (hip[1] + root_y)
        th, kn = _leg_ik(dy, z, l1, l2)
        pose["thigh" + sd] = q("x", th)
        pose["shin" + sd] = q("x", kn)
        pose["foot" + sd] = q("x", max(-45.0, min(40.0, -(th + kn) + toe)))  # heel rises instead of breaking the ankle
    pose.pop("hips", None)
    return [0.0, root_y, travel * p]


def make(bones, preset="walk", frames=None, fps=30):
    names, par, heads, tails = order(bones)
    H = float(np.ptp(np.vstack([heads, tails])[:, 1])) or 1.0
    human = {"thigh.L", "shin.L", "upper_arm.R"} <= set(names)
    frames = int(frames or {"idle": 60, "walk": 32, "run": 20, "wave": 40, "jump": 36}.get(preset, 30))
    loop = preset != "jump"
    rest_rot = np.tile([0, 0, 0, 1.0], (len(names), 1))
    con = contacts(bones)
    _, P0 = fk(par, heads, rest_rot, np.zeros(3))
    ground0 = tails_world(np.tile(np.eye(3), (len(names), 1, 1)), P0, heads, tails)[con, 1].min() if con else None
    keys = {n: [] for n in names}
    root, prev = [], None
    z = 0.0
    for f in range(frames + 1):
        p = f / frames
        pose = _humanoid_pose(preset, p, H) if human else _generic_pose(bones, preset, p)
        gait = _gait(names, heads, preset, p, pose) if human and preset in ("walk", "run") else None
        rots = rest_rot.copy()
        for n, r in pose.items():
            if n in names:
                rots[names.index(n)] = r.as_quat()
        for i, n in enumerate(names):
            if n in pose:
                keys[n].append([f, *map(lambda v: round(float(v), 5), rots[i])])
        R, P = fk(par, heads, rots, np.zeros(3))
        T = tails_world(R, P, heads, tails)
        dy, dx = 0.0, 0.0
        if con:
            pts = np.vstack([T[con], P[con]])
            dy = ground0 - pts[:, 1].min()
            if preset == "jump" and .4 <= p < .75:
                dy += 0.25 * H * math.sin((p - .4) / .35 * math.pi)
            if preset == "run":
                dy += 0.03 * H * max(0.0, math.sin(4 * math.pi * p))
            if preset == "idle":
                dx = 0.008 * H * math.sin(2 * math.pi * p)
            if preset in ("walk", "run"):  # forward motion follows the planted (lowest) contact
                if prev is not None:  # the contact that is down in both frames (no jump when stance switches)
                    st = con[int(np.argmin(np.maximum(T[con, 1], prev[con, 1])))]
                    z -= min(0.0, T[st, 2] - prev[st, 2])  # never drift backwards
                prev = T
        if gait:
            dx, dy, z = gait
        root.append([f, round(dx, 5), round(dy, 5), round(z, 5)])
    keys = {n: k for n, k in keys.items() if k}
    return {"preset": preset, "fps": fps, "frames": frames, "loop": loop, "keys": keys, "root": root}


def set_key(clip, bone, frame, euler, span=4):
    """Set the local rotation (xyz degrees) of a bone at a frame; neighbours within ±span blend towards it."""
    new = q("xyz", euler)
    ks = {int(k[0]): np.asarray(k[1:]) for k in clip["keys"].get(bone, [])}
    names = [bone]
    base = {}
    for f in range(max(0, frame - span), min(clip["frames"], frame + span) + 1):
        cur = _interp(clip["keys"].get(bone), f, 4)
        base[f] = np.array([0, 0, 0, 1.0]) if cur is None else cur
    for f, cur in base.items():
        w = 1.0 if f == frame else max(0.0, 1 - abs(f - frame) / (span + 1))
        if w <= 0:
            continue
        ks[f] = slerp(cur, new.as_quat(), w)
    clip["keys"][bone] = [[f, *map(lambda v: round(float(v), 5), ks[f])] for f in sorted(ks)]
    clip["edited"] = True
    return clip
