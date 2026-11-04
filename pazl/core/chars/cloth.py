"""Clothes that fit any body. A garment is a recipe (kind + colour/skin + ease), not a fixed mesh: the surface is the body's
own offset surface, cut to a region defined by bones, plus optional flares (skirts, brims). Because it is computed from the
body, the same recipe fits a child, a goblin, an imported mesh; `wrap` needs no bones at all, so any object can get a cover.
Skin weights are copied from the nearest body vertices, so clothes follow every animation of the character."""
from __future__ import annotations

import copy

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from ..rig import skeleton
from ..rig.weights import seg_dist
from .field import decimate, surface_nets

ARM = ("shoulder", "upper_arm", "forearm")


def _both(d):
    return {f"{k}{s}": v for k, v in d.items() for s in (".L", ".R")}


TOP = {"spine": (0, 1), "chest": (0, 1)}
TOPL = {"hips": (.35, 1), **TOP}
LEG = {"hips": (-.3, .75)}
# cover: bone -> (from, to) along the bone; cut: bones whose tubes are removed; opts per kind
KINDS = {
    "humanoid": {
        "tshirt": ("Футболка", "Верх", {"cover": {**TOPL, **_both({"shoulder": (-.4, 1), "upper_arm": (0, .5)})}, "color": "#d8d8d8", "ease": .019}),
        "longsleeve": ("Свитер", "Верх", {"cover": {**TOPL, **_both({"shoulder": (-.4, 1), "upper_arm": (0, 1), "forearm": (0, .94)})}, "color": "#7a2f35", "ease": .022, "skin": "knit_red"}),
        "tank": ("Майка", "Верх", {"cover": TOPL, "cut": _both({"upper_arm": (-.25, 1)}), "color": "#f0f0f0", "ease": .017}),
        "jacket": ("Куртка", "Верх", {"cover": {"hips": (0, 1), **TOP, **_both({"shoulder": (-.4, 1), "upper_arm": (0, 1), "forearm": (0, .98)})}, "color": "#3a3f4a", "ease": .03, "skin": "leather"}),
        "pants": ("Брюки", "Низ", {"cover": {**LEG, **_both({"thigh": (-.2, 1), "shin": (0, .92)})}, "color": "#333a4d", "ease": .01, "skin": "denim"}),
        "shorts": ("Шорты", "Низ", {"cover": {**LEG, **_both({"thigh": (-.2, .6)})}, "color": "#6d6a52", "ease": .011}),
        "skirt": ("Юбка", "Низ", {"band": ("spine", .1, "thigh.L", .75), "flare": .17, "color": "#8c3a5c"}),
        "dress": ("Платье", "Целиком", {"cover": {**TOP, **_both({"shoulder": (0, .7)})}, "cut": _both({"upper_arm": (-.25, 1)}), "band": ("spine", .3, "shin.L", .2), "flare": .14, "color": "#2f6d8c", "ease": .01}),
        "cloak": ("Плащ", "Целиком", {"cloak": True, "color": "#5a1f2a", "ease": .016}),
        "boots": ("Сапоги", "Обувь", {"cover": _both({"foot": (-.3, 1.3), "shin": (.45, 1)}), "color": "#3a2618", "ease": .024, "ground": True, "skin": "leather"}),
        "shoes": ("Ботинки", "Обувь", {"cover": _both({"foot": (-.3, 1.3), "shin": (.86, 1)}), "color": "#2a2a2e", "ease": .02, "ground": True}),
        "gloves": ("Перчатки", "Аксессуары", {"cover": _both({"hand": (-.1, 1.2), "forearm": (.88, 1)}), "color": "#2d2d30", "ease": .006}),
        "scarf": ("Шарф", "Аксессуары", {"cover": {"neck": (-.15, .8)}, "color": "#a8322e", "ease": .026, "skin": "tartan"}),
        "belt": ("Ремень", "Аксессуары", {"cover": {"hips": (.45, .95)}, "color": "#3b2415", "ease": .022, "skin": "leather"}),
        "beanie": ("Шапка", "Голова", {"cover": {"head": (.6, 1.2)}, "color": "#2f5a6d", "ease": .012, "skin": "knit_red"}),
        "hat": ("Шляпа", "Голова", {"cover": {"head": (.66, 1.2)}, "brim": .075, "color": "#4a3a2a", "ease": .012}),
        "hair_short": ("Короткие волосы", "Волосы", {"hair": .45, "color": "#3b2a1c", "ease": .011, "wrinkle": 2.2}),
        "hair_long": ("Длинные волосы", "Волосы", {"hair": .1, "mane": True, "color": "#5b3a1e", "ease": .012, "wrinkle": 2.2}),
        "beard": ("Борода", "Волосы", {"beard": True, "color": "#3b2a1c", "ease": .012, "wrinkle": 2.5}),
    },
    "quadruped": {
        "coat": ("Попона", "Верх", {"cover": {"hips": (.25, 1), "spine": (0, 1), "chest": (0, .8)}, "color": "#8c2f2f", "ease": .012, "skin": "tartan"}),
        "collar": ("Ошейник", "Аксессуары", {"cover": {"neck": (.35, .6)}, "color": "#b03030", "ease": .012}),
        "paws": ("Носочки", "Обувь", {"cover": _both({"fleg_lo": (.6, 1.3), "bleg_lo": (.6, 1.3)}), "color": "#e8e0d0", "ease": .008, "ground": True}),
    },
    "any": {
        "wrap": ("Чехол (любой объект)", "Универсальное", {"wrap": True, "color": "#7a6a4a", "ease": .008}),
    },
}


def kinds_for(template):
    return {**KINDS.get(template, {}), **KINDS["any"]}


def catalog():
    return {t: [{"id": k, "title": v[0], "group": v[1], "color": v[2]["color"]} for k, v in kinds_for(t).items()] for t in ("humanoid", "quadruped", "simple")}


def _tube(P, a, b, t0, t1, R):
    """Field of a flat-ended tube around part of a bone."""
    ab = b - a
    L = float(np.linalg.norm(ab)) or 1e-6
    u = ab / L
    d = P - a
    h = d @ u
    rad = np.linalg.norm(d - h[:, None] * u, axis=1)
    return np.maximum(rad - R, np.maximum(t0 * L - h, h - t1 * L))


def block_label(P, bones, names):
    """Which block of a toy-like body a point is in: index of the one bone that block follows."""
    by = {b["name"]: b for b in bones}
    tw, neck, crotch = by["shoulder.L"]["head"][0], by["neck"]["head"][1], by["hips"]["head"][1]
    ix = {k: i for i, k in enumerate(names)}
    x, y = P[:, 0], P[:, 1]
    lab = np.full(len(P), ix["chest"])
    lab[y > neck * .999] = ix["head"]
    low = y < crotch
    lab[low & (x > 0)], lab[low & (x <= 0)] = ix["thigh.L"], ix["thigh.R"]
    sh = by["shoulder.L"]
    top = sh["head"][1] + (sh["tail"][0] - sh["head"][0]) * 1.1  # the arm is as thick as its joint is far from the torso edge
    arm = (np.abs(x) > tw) & ~low & (y <= top)  # torso corners above it stay with the torso
    lab[arm & (x > 0)], lab[arm & (x <= 0)] = ix["upper_arm.L"], ix["upper_arm.R"]
    return lab


class Fit:
    """Measurements of one body, shared by its garments. names: bone order of a block body."""

    def __init__(self, V, F, N, bones, names=None):
        self.skin_tree = cKDTree(V)  # real vertices: skin weights come from them
        self.names, self.bones_raw = names, bones
        if names or len(V) < 20000:  # low-poly body: measure on points spread over its faces, or the cloth would be lumpy
            m = trimesh.Trimesh(V, F, process=False)
            V, fi = trimesh.sample.sample_surface(m, 60000, seed=1)
            V, N = np.asarray(V, float), np.asarray(m.face_normals[fi], float)
        self.V, self.N = V, N
        self.tree = cKDTree(V)
        self.bones = {b["name"]: (np.array(b["head"], float), np.array(b["tail"], float)) for b in bones}
        names = list(self.bones)
        A, B = np.array([self.bones[n][0] for n in names]), np.array([self.bones[n][1] for n in names])
        near = np.concatenate([seg_dist(V[i:i + 4096], A, B).argmin(1) for i in range(0, len(V), 4096)])
        self.reach = {}
        for i, n in enumerate(names):  # how far this bone's flesh extends, measured on this very body
            pts = V[near == i]
            if not len(pts):
                self.reach[n] = .05
                continue
            a, b = self.bones[n]
            q = 96 if n.startswith("shoulder") else 100  # the whole limb, box corners too: a short reach cuts hems into arches
            self.reach[n] = float(np.percentile(seg_dist(pts, a[None], b[None]), q)) * 1.15 + .03
        trunk = [n for n in ("hips", "spine", "chest") if n in self.reach]
        for n in trunk:  # one width for the whole trunk, or hems step in on boxy bodies
            self.reach[n] = max(self.reach[k] for k in trunk)
        self.lo, self.hi = V.min(0), V.max(0)
        self.H = float(self.hi[1] - self.lo[1])
        if self.names:  # stepping just inside tells apart two faces that touch: torso side and arm end
            self.lab = block_label(self.V - self.N * .004, bones, self.names)
            box = self.V[self.lab == self.names.index("chest")]
            for n in ("hips", "spine", "chest"):  # measured on the torso block itself, corners included
                self.reach[n] = float(np.linalg.norm(box[:, [0, 2]], axis=1).max()) * 1.1 + .03
            for s in (".L", ".R"):  # one sleeve width from the shoulder on, or the seam gets a step
                self.reach["shoulder" + s] = self.reach["upper_arm" + s]

    def only(self, lab):
        """The same body measured on one block: its shell closes on every side, also where it touches a neighbour."""
        f = copy.copy(self)
        m = self.lab == lab
        f.V, f.N = self.V[m], self.N[m]
        f.tree = cKDTree(f.V)
        return f

    def offset(self, P, ease):
        """Smooth signed distance to the body surface, minus ease."""
        d, i = self.tree.query(P, k=6, workers=-1)
        w = 1 / np.maximum(d, 1e-4) ** 2
        w /= w.sum(1, keepdims=True)
        sd = (((P[:, None] - self.V[i]) * self.N[i]).sum(2) * w).sum(1)
        near = d[:, 0]  # beyond a box edge the plane distance drops to 0 and would grow false sheets: outside stays outside
        return np.where(sd > -.3 * near, np.maximum(sd, .9 * near), sd) - ease

    def y_at(self, bone, t):
        a, b = self.bones[bone]
        return float(a[1] + (b[1] - a[1]) * t)


def _region(fit, o, P):
    """Field < 0 inside the area the garment covers."""
    r = np.full(len(P), 1.0)
    for n, (t0, t1) in o.get("cover", {}).items():
        if n in fit.bones:
            r = np.minimum(r, _tube(P, *fit.bones[n], t0, t1, fit.reach[n]))
    for n, (t0, t1) in o.get("cut", {}).items():
        if n in fit.bones:
            r = np.maximum(r, -_tube(P, *fit.bones[n], t0, t1, fit.reach[n]))
    if "neck" in fit.bones and "head" in fit.bones and not {"neck", "head"} & set(o.get("cover", {})):
        r = np.maximum(r, P[:, 1] - fit.y_at("neck", .15))  # body clothes never climb the neck
    if "foot.L" in o.get("cover", {}) and "shin.L" in o["cover"]:  # a flat top: the slanted foot tube must not arch above the shaft
        r = np.maximum(r, P[:, 1] - fit.y_at("shin.L", o["cover"]["shin.L"][0]))
    return r


def _head_box(fit):
    a, b = fit.bones["head"]
    return a, b, float(b[1] - a[1])


def _shape(fit, kind, o, spec, P):
    """(solid, sheet) fields: solid < 0 inside the garment; faces on sheet ~ 0 are kept, cut hems are removed."""
    ease = float(spec.get("ease") or o.get("ease", .012)) * (fit.H / 1.75) ** .5
    O = fit.offset(P, ease)
    length = float(spec.get("length", 1))
    x, y, z = P.T
    if o.get("wrap"):
        y0, y1 = fit.lo[1] + fit.H * float(spec.get("from", .25)), fit.lo[1] + fit.H * float(spec.get("to", .75))
        return np.maximum(O, np.maximum(y0 - y, y - y1)), O
    if "hair" in o or "beard" in o:
        a, b, hh = _head_box(fit)
        if o.get("beard"):
            r = np.maximum(np.maximum(y - (a[1] + hh * .44), a[1] - .03 * hh - y), .012 - z)
            r = np.maximum(r, -_lipcut(y, z, x, a, hh))
            return np.maximum(O, r), O
        low = a[1] + hh * (.34 if not o.get("mane") else .05)
        line = a[1] + hh * .77 + np.maximum(z - hh * .2, 0) * .3  # hairline over the forehead
        r = np.maximum(low - y, np.minimum(line - y, z + hh * .04))  # the cap, and everything behind the ears
        s = np.maximum(O, r)
        if o.get("mane"):  # falls down the back
            bottom = fit.y_at("chest", .25) if length >= 1 else a[1]
            yy = np.clip((a[1] + hh * .3 - y) / max(hh, 1e-3), 0, 2)
            m = np.sqrt((x / (hh * .5)) ** 2 + ((z + hh * .3 + yy * .02) / (hh * .3)) ** 2) - 1
            m = np.maximum(m * hh * .3, np.maximum(bottom - y, y - (a[1] + hh * .75)))
            s = np.minimum(s, m)
            O = np.minimum(O, m)
        return s, O
    if o.get("cloak"):
        a, b = fit.bones["chest"]
        ys = fit.y_at("chest", .98)
        yb = fit.y_at("shin.L", .35 + .65 * (1 - min(length, 1)))
        back = fit.V[fit.V[:, 1] > fit.y_at("spine", 0)][:, 2].min()
        d = np.clip(ys - y, 0, None)
        zc = back - .025 - d * .1 + .012 * np.sin(x * 34) * np.clip(d * 3, 0, 1)
        wide = fit.reach["chest"] * .92 + d * .1
        sheet = zc - z  # solid in front of the back sheet
        r = np.maximum(np.maximum(np.abs(x) - wide, np.maximum(yb - y, y - ys)), z - (back + .1))
        collar = np.maximum(O, _tube(P, *fit.bones["chest"], .86, 1.02, fit.reach["chest"]))
        collar = np.maximum(collar, -_tube(P, *fit.bones["upper_arm.L"], .25, 1.2, fit.reach["upper_arm.L"]))
        collar = np.maximum(collar, -_tube(P, *fit.bones["upper_arm.R"], .25, 1.2, fit.reach["upper_arm.R"]))
        return np.minimum(np.maximum(sheet, r), collar), -np.minimum(np.abs(sheet), np.abs(O))
    s = np.maximum(O, _region(fit, o, P)) if "cover" in o else np.full(len(P), 1.0)
    if "band" in o:  # skirts: a bell around the hips from a waist down to a hem
        b0, t0, b1, t1 = o["band"]
        top, hem = fit.y_at(b0, t0), fit.y_at(b1, t1 + (1 - length) * -.6 if b1 != "shin.L" else t1 + (1 - length) * -1.2)
        hips = fit.V[(fit.V[:, 1] > fit.y_at("hips", 0) - .05) & (fit.V[:, 1] < fit.y_at("hips", 1)) & (np.abs(fit.V[:, 0]) < fit.reach["hips"])]
        rx, rz = np.abs(hips[:, 0]).max(), np.abs(hips[:, 2]).max()
        q = np.clip((fit.y_at("hips", .3) - y), 0, None) * o["flare"] * float(spec.get("flare", 1)) * 2
        c = (np.sqrt((x / (rx + q + ease)) ** 2 + (z / (rz + q + ease)) ** 2) - 1) * min(rx, rz)
        c = np.where(y > fit.y_at("hips", .3), 1.0, c)  # above the hips the cloth follows the body
        r = np.maximum(hem - y, y - top)
        s = np.minimum(s, np.maximum(np.minimum(O, c), r))
        O = np.minimum(O, np.maximum(c, r))
    if "brim" in o:
        a, b, hh = _head_box(fit)
        yb = a[1] + hh * .68
        w = o["brim"] * hh / .22 + hh * .48
        d = np.maximum(np.sqrt(x ** 2 + (z / 1.1) ** 2) - w, np.abs(y - yb) - .007)
        s = np.minimum(s, d)
        O = np.minimum(O, d)
    return s, O


def _lipcut(y, z, x, a, hh):
    """Keeps the mouth open in a beard."""
    return np.maximum(np.abs(x) - hh * .12, np.abs(y - (a[1] + hh * .25)) - hh * .035)


def _bounds(fit, kind, o, spec):
    if o.get("wrap"):
        return fit.lo - .05, fit.hi + .05
    if "hair" in o or "beard" in o or o.get("cloak") or "band" in o:
        lo, hi = fit.lo.copy(), fit.hi.copy()
        a, b, *_ = fit.bones.get("head", (lo, hi))
        if "hair" in o or "beard" in o:
            hh = float(b[1] - a[1])
            lo = np.array([-hh, a[1] - hh * (1.2 if o.get("mane") else .3), -hh])
            hi = np.array([hh, b[1] + .05, hh])
        else:
            arm = fit.reach["chest"] + .3
            lo[0], hi[0] = -arm, arm
            lo[2], hi[2] = lo[2] - .25, hi[2] + .25
        if "cover" not in o:
            return lo, hi
    P = fit.V
    r = _region(fit, o, P)
    pts = P[r < .02]
    if not len(pts):
        raise ValueError(f"нет частей тела под {kind}")
    lo, hi = pts.min(0) - .06, pts.max(0) + .06
    if "band" in o:
        lo, hi = np.minimum(lo, fit.lo * (0, 1, 0) + (-.6, 0, -.6)), np.maximum(hi, (.6, 0, .6))
    if "brim" in o:
        lo, hi = lo - (.15, .02, .15), hi + (.15, 0, .15)
    return lo, hi


def make(fit, kind, spec, template, target=None):
    """(V, F, N) of an open garment shell; raises ValueError if it does not suit this body."""
    if kind not in kinds_for(template):
        raise ValueError(f"«{kind}» не подходит к скелету {template}; есть: {', '.join(kinds_for(template))}")
    o = kinds_for(template)[kind][2]
    lo, hi = _bounds(fit, kind, o, spec)
    cell = max(.006, fit.H * .0062)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    n = np.ceil((hi - lo) / cell).astype(int) + 1
    ax = [lo[i] + np.arange(n[i]) * cell for i in range(3)]
    P = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)
    S, O = np.empty(len(P), np.float32), np.empty(len(P), np.float32)
    for i in range(0, len(P), 400000):
        S[i:i + 400000], O[i:i + 400000] = _shape(fit, kind, o, spec, P[i:i + 400000])
    S, O = S.reshape(n), O.reshape(n)
    wr = float(spec.get("wrinkle", o.get("wrinkle", 1)))
    if wr:  # fabric is not perfectly smooth: slow folds; hair uses the same at a larger amplitude
        rng = np.random.default_rng(int(spec.get("seed", 7)))
        fold = ndimage.gaussian_filter(rng.standard_normal(n).astype(np.float32), (3.5, 2, 3.5))
        S = S + fold / max(float(fold.std()), 1e-6) * .0016 * wr
    S = ndimage.gaussian_filter(S, .7)
    V, F = surface_nets(S, lo, cell)
    if not len(F):
        raise ValueError(f"{kind}: поверхность не получилась")
    idx = np.clip(((V - lo) / cell).round().astype(int), 0, n - 1)
    on = O[tuple(idx.T)] > -(cell * 2.5 + .002 * wr)  # drop the caps that closed the hems: they lie deep inside
    F = F[on[F].all(1)]
    m = trimesh.Trimesh(V, F, process=False)
    m.remove_unreferenced_vertices()
    if not len(m.faces):
        raise ValueError(f"{kind}: поверхность не получилась")
    parts = m.split(only_watertight=False)
    big = max(len(p.faces) for p in parts)
    m = trimesh.util.concatenate([p for p in parts if len(p.faces) > big * .02])
    trimesh.smoothing.filter_taubin(m, iterations=4)
    if target and len(m.faces) > target:
        m = trimesh.Trimesh(*decimate(m.vertices, m.faces, target), process=False)
    V = np.array(m.vertices)
    d, i = fit.tree.query(V)
    if ((V - fit.V[i]) * fit.N[i]).sum(1).mean() < 0 or _inverted(m, fit):
        m.invert()
    if o.get("ground"):
        V[:, 1] = np.maximum(V[:, 1], fit.lo[1])
    return V, np.asarray(m.faces), np.asarray(m.vertex_normals, float)


def make_blocks(fit, kind, spec, template, target=None):
    """(V, F, N, bone per vertex) for a block body: one closed shell per block, so nothing stretches between blocks."""
    if kind not in kinds_for(template):
        raise ValueError(f"«{kind}» не подходит к скелету {template}; есть: {', '.join(kinds_for(template))}")
    o = kinds_for(template)[kind][2]
    spec = {"wrinkle": .3, **spec}
    if "hair" in o or "beard" in o or "brim" in o:
        whole = fit.names.index("head")
    elif o.get("cloak") or o.get("wrap") or "band" in o:
        whole = fit.names.index("chest")
    else:
        whole = None
    if whole is not None:
        V, F, N = make(fit, kind, spec, template, target)
        return V, F, N, np.full(len(V), whole)
    res, off = [], 0
    for lab in np.unique(fit.lab):
        try:
            V, F, N = make(fit.only(lab), kind, spec, template, max(1500, target // 3) if target else None)
        except ValueError:
            continue  # this garment does not reach this block
        res.append((V, F + off, N, np.full(len(V), lab)))
        off += len(V)
    if not res:
        raise ValueError(f"{kind}: поверхность не получилась")
    return tuple(np.vstack([r[i] for r in res]) for i in range(3)) + (np.concatenate([r[3] for r in res]),)


def _inverted(m, fit):
    d, i = fit.tree.query(m.vertices)
    return float((np.asarray(m.vertex_normals) * fit.N[i]).sum(1).mean()) < 0


def transfer(fit, Vg, Wd, k=4, rigid=None):
    """Skin weights for garment vertices: inverse-distance mix of the k nearest body vertices (Wd: dense n x bones)."""
    d, i = fit.skin_tree.query(Vg, k=[*range(1, k + 1)], workers=-1)
    w = 1 / np.maximum(d, 1e-3) ** 2
    w /= w.sum(1, keepdims=True)
    W = (Wd[i] * w[..., None]).sum(1)
    if rigid is not None:
        W[:] = 0
        W[:, rigid] = 1
    J = np.argsort(-W, axis=1)[:, :4]
    Wk = np.take_along_axis(W, J, 1)
    Wk[Wk < .01] = 0
    return J.astype(np.uint16), (Wk / np.maximum(Wk.sum(1, keepdims=True), 1e-9)).astype(np.float32)


def soft(kind, template):
    """Loose garments average many body points, so they do not tear between the legs."""
    o = kinds_for(template)[kind][2]
    return 48 if "band" in o or o.get("mane") else 4


def rigid_bone(kind, template, names):
    o = kinds_for(template)[kind][2]
    return names.index("chest") if o.get("cloak") and "chest" in names else None
