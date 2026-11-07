"""Boomland NPC guide gear (v1.129): for every guide three textured pieces that ride the shared animated R15 rig —
<id>_head (hat, hair, beard, glasses: follows Head), <id>_torso (apron, vest, belt, straps: follows UpperTorso),
<id>_prop (the tool of the trade: follows RightHand). Drawn in STUDS around the bone centre (front = +Z, y up):
Head 1.2 cube (top y=.6, face z=.6), UpperTorso 2 x 1.6 x 1 (lower torso below to y=-1.2), RightHand = grip at 0.
Smooth shapes only (ellipsoids, capsules, tubes, rounded shells that follow the torso), no bare boxes.
Scaled to metres (x0.28) on export. Writes guides.json: bottom-centre of each piece relative to its bone (studs) for
GuideRig.luau. Run: .venv/Scripts/python.exe scripts/gen_boomland_guides.py"""
import json, math, pathlib, sys
import numpy as np, trimesh as tm
from PIL import Image
sys.path.insert(0, "scripts")
import boomland_kit as K
from boomland_kit import hull, frustum

SK = pathlib.Path(__file__).resolve().parents[1] / "projects" / "skins"
FAB = {}
col = K.col


def fab(hexc, name, rep=1.2):
    FAB[hexc.lstrip('#').lower()] = (name, rep); return hexc


_kit_texture = K.texture


def texture(hx, cc):
    if hx in FAB:
        t = np.asarray(Image.open(SK / f"{FAB[hx][0]}.jpg").convert("RGB").resize((256, 256), Image.LANCZOS), float)
        lum = t.mean(2, keepdims=True); lum = 0.6 + 0.4 * lum / lum.mean()
        return Image.fromarray(np.clip(lum * np.array(cc, float), 0, 255).astype(np.uint8)), FAB[hx][1] * .28
    return _kit_texture(hx, cc)


K.texture = texture
OFFS = {}


def export(name):
    for m in K.P: m.apply_scale(.28)
    v = np.vstack([m.vertices for m in K.P]) / .28; lo, hi = v.min(0), v.max(0)
    OFFS[name] = [round(float((lo[0] + hi[0]) / 2), 3), round(float(lo[1]), 3), round(float((lo[2] + hi[2]) / 2), 3)]
    K.export(f"guide_{name}")


# ------------------------------------------------------------------ smooth primitives
def _orient(m, a, b):
    a, b = np.array(a, float), np.array(b, float); d = b - a; L = np.linalg.norm(d); u = d / L; z = np.array([0, 0, 1.0])
    ax = np.cross(z, u); s = np.linalg.norm(ax)
    if s > 1e-6: m.apply_transform(tm.transformations.rotation_matrix(math.atan2(s, z @ u), ax / s))
    elif u[2] < 0: m.apply_transform(tm.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    m.apply_translation((a + b) / 2); return m


def ell(x, y, z, rx, ry, rz, c, sub=2):
    m = tm.creation.icosphere(subdivisions=sub, radius=1.0); m.apply_scale([rx, ry, rz]); m.apply_translation([x, y, z]); return col(m, c)


def cap(a, b, r, c):
    L = np.linalg.norm(np.subtract(b, a)); m = tm.creation.capsule(height=max(L, 1e-3), radius=r, count=[10, 8]); return col(_orient(m, a, b), c)


def tube(a, b, r, c, n=16):
    L = np.linalg.norm(np.subtract(b, a)); m = tm.creation.cylinder(radius=r, height=L, sections=n); return col(_orient(m, a, b), c)


def rope(pts, r, c):
    for a, b in zip(pts, pts[1:]): cap(a, b, r, c)


def torus(x, y, z, R, r, c, axis="y", n=32, m=12):
    t = tm.creation.torus(major_radius=R, minor_radius=r, major_sections=n, minor_sections=m)
    if axis == "y": t.apply_transform(tm.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    if axis == "x": t.apply_transform(tm.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    t.apply_translation([x, y, z]); return col(t, c)


def disc(y, r, h, c, n=48, x=0, z=0):
    m = tm.creation.cylinder(radius=r, height=h, sections=n); m.apply_transform(tm.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    m.apply_translation([x, y + h / 2, z]); return col(m, c)


def dome(y0, r, h, c, n=36, rings=10, x=0, z=0, sz=1.0):
    r *= 1.13; pts = []
    for k in range(rings + 1):
        a = k / rings * math.pi / 2; rr = r * math.cos(a); yy = y0 + h * math.sin(a)
        pts += [[x + rr * math.cos(t), yy, z + rr * sz * math.sin(t)] for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    return hull(pts, c)


def outline(w, d, r, n=7):
    """rounded rectangle in XZ (CCW seen from above), w x d with corner radius r"""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    out = []
    for j, p in enumerate(pts):                      # split the straight sides so a shell can be cut anywhere
        q = pts[(j + 1) % len(pts)]; L = math.dist(p, q); k = 1 if L < .3 else 10
        out += [(p[0] + (q[0] - p[0]) * t / k, p[1] + (q[1] - p[1]) * t / k) for t in range(k)]
    return out


def shell(y0, y1, c, w=2.0, d=1.0, r=.32, gap=.04, t=.07, keep=None, taper=0.0):
    """Cloth/leather shell around the torso between y0 and y1 (rounded rectangle, thickness t). keep(x, z) -> bool picks
    the part of the loop (apron front, open vest); a cut loop gets end caps. taper narrows the top (shoulders)."""
    o = outline(w + 2 * gap + 2 * t, d + 2 * gap + 2 * t, r + gap + t); i = outline(w + 2 * gap, d + 2 * gap, r + gap)
    idx = list(range(len(o))); closed = keep is None
    if keep is not None:
        sel = [k for k in idx if keep(*o[k])]
        if not sel: return
        start = next(k for k in sel if (k - 1) % len(o) not in sel) if len(sel) < len(o) else 0
        idx = [(start + j) % len(o) for j in range(len(sel))]
    V, F = [], []
    def put(p, y, s): V.append([p[0] * s, y, p[1]]); return len(V) - 1
    ring = []
    for k in idx:
        st = 1 - taper
        ring.append((put(o[k], y0, 1), put(o[k], y1, st), put(i[k], y1, st), put(i[k], y0, 1)))
    pairs = list(zip(ring, ring[1:])) + ([(ring[-1], ring[0])] if closed else [])
    for a, b in pairs:
        for q in range(4):
            a0, a1, b0, b1 = a[q], a[(q + 1) % 4], b[q], b[(q + 1) % 4]
            F += [[a0, b0, b1], [a0, b1, a1]]
    if not closed:
        for e, flip in ((ring[0], 1), (ring[-1], 0)):
            F += [[e[0], e[2], e[1]], [e[0], e[3], e[2]]] if flip else [[e[0], e[1], e[2]], [e[0], e[2], e[3]]]
    m = tm.Trimesh(np.array(V), np.array(F)); m.fix_normals(); return col(m, c)


def over_shoulder(x0, x1, yf, yb, c, r=.08, s=None):
    """strap from the front (x0, yf) over the shoulder at x1 down the back to (x0, yb)"""
    rope([[x0, yf, .58], [x1, .75, .58], [x1, .9, .35], [x1, .93, 0], [x1, .9, -.35], [x1, .75, -.58], [x0, yb, -.58]], r, c)


def belt(c, buckle, y=-1.05, h=.26):
    shell(y - h / 2, y + h / 2, c, gap=.05, t=.06)
    torus(0, y, .64, .14, .035, buckle, axis="z", n=20, m=8); tube([0, y - .1, .65], [0, y + .1, .65], .025, buckle, 8)


def beard(c, long=0.0):
    ell(0, -.42 - long / 2, .56, .44, .28 + long / 2, .14, c); ell(0, -.22, .57, .5, .22, .1, c)
    for s in (-1, 1): ell(s * .55, -.12, .38, .1, .3, .24, c)


def moustache(c):
    for s in (-1, 1): cap([s * .05, -.17, .66], [s * .32, -.27, .6], .075, c)


def glasses(frame, lens):
    for s in (-1, 1):
        torus(s * .24, .1, .64, .15, .025, frame, axis="z", n=24, m=8); ell(s * .24, .1, .63, .14, .14, .02, lens, 2)
        tube([s * .39, .1, .63], [s * .62, .12, .05], .025, frame, 8)
    tube([-.09, .1, .65], [.09, .1, .65], .025, frame, 8)


def grouped(fn, mat):
    n = len(K.P); fn()
    for m in K.P[n:]: m.apply_transform(mat)


# palette
LEATHER = fab("#6b4428", "web_brown_leather", 1.0); LEATHER_D = fab("#4a2e1c", "web_leather037", 1.0)
GOLD, STEEL, IRON, WOODC = "#f2b632", "#7a7f8a", "#2b2f3a", "#9a6a40"
WHITE = fab("#f4f1ea", "web_cotton_jersey", 1.5); CANVAS = fab("#b8a070", "web_olive_canvas", 1.5)
front = lambda lim: (lambda x, z: z > lim)
FR = lambda w, lim=0.0: (lambda x, z: z > lim and abs(x) < w)

# ---------------------------------------------------------------- 1 Zina: shopkeeper
GREY_HAIR = fab("#c8c8cd", "web_jogging_melange", .8)
dome(.15, .67, .8, GREY_HAIR); ell(0, .82, -.28, .32, .3, .3, GREY_HAIR); torus(0, .78, -.3, .3, .06, "#ff7aa8", axis="x")
for s in (-1, 1): ell(s * .58, .1, -.05, .14, .38, .5, GREY_HAIR)
ell(0, .4, -.45, .62, .35, .3, GREY_HAIR); glasses("#c94a3a", "#cfefff"); export("Zina_head")
APRON = fab("#fbe3ee", "web_cotton_jersey", 1.0); FRILL = "#ff8fb8"
shell(-.45, .62, APRON, keep=FR(.62, .2), t=.05); shell(-1.6, -.45, APRON, keep=front(-.25), t=.05, gap=.06)
for i in range(13): ell(-1.0 + i * 1 / 6, -1.6, .6, .1, .08, .06, FRILL, 1)
ell(0, -.85, .62, .4, .22, .05, FRILL, 1); ell(0, -.8, .64, .34, .16, .04, APRON, 2)
over_shoulder(.55, .55, .6, -.5, FRILL, .05); over_shoulder(-.55, -.55, .6, -.5, FRILL, .05)
shell(-.6, -.45, FRILL, gap=.1, t=.04); torus(0, -.52, -.66, .14, .045, FRILL, axis="z"); export("Zina_torso")
WICK = fab("#c89058", "web_rough_linen", .4)
frustum(0, -.25, -1.05, -.35, .5, .65, WICK, 40)
for y in (-.95, -.75, -.55): torus(0, y, -.25, .5 + (y + 1.05) / .7 * .15 + .01, .035, "#a8703c", n=40, m=6)
torus(0, -.35, -.25, .64, .06, "#8a5a30", n=40)
rope([[-.55, -.33, -.25], [-.5, .05, -.25], [-.28, .3, -.25], [0, .38, -.25], [.28, .3, -.25], [.5, .05, -.25], [.55, -.33, -.25]], .055, "#8a5a30")
ell(-.15, -.28, -.42, .38, .16, .18, "#e0a050"); ell(.28, -.25, -.1, .17, .17, .17, "#d93a32"); ell(.1, -.25, .08, .16, .16, .16, "#d93a32")
ell(-.25, -.25, .05, .16, .16, .16, "#7ac943"); export("Zina_prop")

# ---------------------------------------------------------------- 2 Weapons: sergeant
BERET = fab("#a82828", "web_dark_jersey", .8)
hull([[.72 * math.cos(t) + .12, .55 + .05 * math.sin(t), .7 * math.sin(t)] for t in np.linspace(0, 6.28, 40)] +
     [[.5 * math.cos(t) + .25, .9 - .04 * math.cos(t), .48 * math.sin(t)] for t in np.linspace(0, 6.28, 32)] +
     [[.25 * math.cos(t) + .3, .98, .25 * math.sin(t)] for t in np.linspace(0, 6.28, 16)], BERET)
torus(0, .55, 0, .66, .06, LEATHER_D); ell(-.32, .7, .62, .13, .15, .04, GOLD, 2); ell(-.32, .7, .65, .07, .08, .03, "#d93a32", 2)
moustache("#4a3224"); export("Weapons_head")
OLIVE = fab("#5a6e40", "web_olive_canvas", 1.0)
rope([[.95, -.95, .6], [.3, -.2, .62], [-.55, .65, .6], [-.8, .9, .3], [-.82, .93, -.1], [-.7, .8, -.58], [.1, -.1, -.62], [.95, -.95, -.6]], .11, LEATHER_D)
for i in range(5): t = .12 + i * .14; p = np.array([.95, -.95, .6]) + t * (np.array([-.55, .65, .6]) - np.array([.95, -.95, .6])); tube(p + [0, -.1, .05], p + [0, .14, .05], .055, GOLD, 10)
belt(LEATHER, GOLD)
for x in (-.7, .7): ell(x, -1.05, .64, .2, .22, .12, OLIVE, 2)
tube([0, .78, .52], [0, .3, .58], .015, STEEL, 6); ell(0, .2, .6, .09, .12, .02, STEEL, 2)


def rifle():
    tube([0, -1.3, 0], [0, 1.4, 0], .06, IRON, 16); tube([0, .2, 0], [0, 1.0, 0], .1, WOODC, 16)
    hull([[x, y, z] for x in (-.09, .09) for (y, z) in ((-1.35, -.05), (-1.35, .32), (-.65, .12), (-.65, -.05))], WOODC)
    tube([0, -.55, .15], [0, -.2, .15], .07, IRON, 12); tube([.0, -.5, -.18], [0, .05, -.18], .07, IRON, 16)
    ell(0, -.45, .3, .05, .16, .1, IRON, 2)


grouped(rifle, tm.transformations.compose_matrix(angles=[0, 0, math.radians(-38)], translate=[0, -.1, -.78]))
shell(-.95, .62, OLIVE, t=.08, taper=.05)
for x in (-.55, -.18, .18): ell(x, -.55, .7, .15, .2, .1, "#4a5c34", 2); ell(x, -.38, .76, .15, .05, .07, "#3e4e2c", 2)
tube([.55, .1, .7], [.55, .55, .7], .1, IRON, 12); tube([.6, .55, .7], [.6, .85, .7], .015, IRON, 6)
export("Weapons_torso")
for s in (-1, 1):
    tube([s * .17, 0, -.35], [s * .17, 0, .3], .14, IRON, 24); torus(s * .17, 0, .3, .14, .03, STEEL, axis="z", n=24, m=8)
    ell(s * .17, 0, .33, .12, .12, .02, "#5ec8ff", 2); tube([s * .17, 0, -.38], [s * .17, 0, -.25], .16, OLIVE, 24)
tube([-.17, 0, 0], [.17, 0, 0], .05, IRON, 12); tube([0, .1, -.05], [0, .1, .1], .05, STEEL, 12); export("Weapons_prop")

# ---------------------------------------------------------------- 3 Sapper: bomb suit
SUIT = fab("#55784b", "web_olive_canvas", 1.0)
dome(-.25, .8, 1.2, SUIT); ell(0, -.45, -.05, .82, .32, .78, SUIT)
ell(0, .08, .74, .5, .45, .12, "#5ec8ff"); torus(0, .08, .72, .5, .05, IRON, axis="z", n=40); ell(0, .85, .3, .5, .1, .4, IRON)
export("Sapper_head")
shell(-1.3, .85, SUIT, t=.22, r=.4, taper=.05); ell(0, .2, .82, .8, .62, .12, "#476540")
for y in (.45, .05, -.35): tube([-.7, y, .92], [.7, y, .92], .045, GOLD, 10)
ell(0, -.85, .78, .55, .3, .1, "#476540"); torus(0, .92, 0, .75, .2, SUIT, n=40)
for x in (-.55, .55): ell(x, -.5, .86, .2, .22, .1, "#476540", 2); ell(x, -.32, .92, .2, .06, .08, "#3a5434", 2)
tube([.62, .5, .85], [.62, .85, .85], .09, IRON, 12); tube([.66, .85, .85], [.66, 1.15, .85], .012, IRON, 6); ell(.62, .62, .94, .05, .05, .02, "#9dff7a", 2)
export("Sapper_torso")
ell(0, -.15, -.35, .6, .6, .6, IRON, 2); tube([0, .35, -.35], [0, .6, -.35], .2, STEEL, 20); torus(0, .58, -.35, .2, .04, STEEL)
rope([[0, .6, -.35], [.06, .8, -.38], [.15, .9, -.42]], .03, "#cfae78"); ell(.17, .95, -.43, .1, .1, .1, "#ff6a3d", 2)
export("Sapper_prop")

# ---------------------------------------------------------------- 4 Dig: explorer
SAFARI = fab("#c2a46c", "web_olive_canvas", .8)
dome(.32, .68, .6, SAFARI); hull([[1.05 * math.cos(t), .3 - .06 * abs(math.sin(t)), 1.05 * math.sin(t)] for t in np.linspace(0, 6.28, 48)] +
                                 [[.66 * math.cos(t), .38, .66 * math.sin(t)] for t in np.linspace(0, 6.28, 32)], SAFARI)
torus(0, .42, 0, .68, .06, LEATHER_D); beard("#7a5a40", .1); export("Dig_head")
over_shoulder(.9, -.75, -.95, -.95, LEATHER, .07)
ell(.98, -1.15, 0, .16, .3, .42, CANVAS, 2); ell(1.04, -.95, 0, .12, .14, .4, LEATHER, 2)
belt(LEATHER_D, GOLD)
shell(-1.0, .62, CANVAS, keep=lambda x, z: not (z > .3 and abs(x) < .22), t=.06, taper=.06)
for sx in (-1, 1): ell(sx * .55, -.55, .63, .24, .2, .06, "#a08a5a", 2); ell(sx * .55, -.4, .66, .25, .06, .05, "#a08a5a", 2); ell(sx * .55, .25, .63, .2, .16, .05, "#a08a5a", 2)
torus(-.55, .3, .7, .1, .025, GOLD, axis="z", n=20, m=6); ell(-.55, .3, .7, .09, .09, .02, WHITE, 2)
export("Dig_torso")
tube([0, -1.0, 0], [0, 2.1, 0], .08, WOODC, 12); torus(0, 2.28, 0, .2, .05, WOODC, axis="z")
V = []
for (y, w, b) in ((-1.0, .3, .02), (-1.45, .34, .06), (-1.85, .3, .08), (-2.1, .05, .05)):
    V += [[x, y, b * (1 - (x / max(w, .01)) ** 2)] for x in np.linspace(-w, w, 7)] + [[x, y, b * (1 - (x / max(w, .01)) ** 2) - .04] for x in np.linspace(-w, w, 7)]
hull(V, STEEL); tube([0, -1.1, 0], [0, -.8, 0], .1, STEEL, 12); export("Dig_prop")

# ---------------------------------------------------------------- 5 Vehicles: mechanic
CAPO = fab("#ee8a28", "web_cotton_jersey", .8)


def cap_hat(c, badge):
    dome(.28, .67, .52, c); ell(0, .8, 0, .08, .05, .08, c, 2)
    hull([[.55 * math.cos(t), .33, .55 + .62 * math.sin(t)] for t in np.linspace(0, math.pi, 24)] +
         [[.55 * math.cos(t), .38, .55 + .56 * math.sin(t)] for t in np.linspace(0, math.pi, 24)], c)
    ell(0, .6, .66, .22, .1, .06, badge, 2)


cap_hat(CAPO, "#1e3c6e"); export("Vehicles_head")
OVER = fab("#3c6eb4", "web_dark_pants", 1.0)
shell(-.75, .15, OVER, keep=FR(.62, .2), t=.06); ell(0, -.3, .62, .28, .2, .04, "#2e5aa0", 2)
for s in (-1, 1): over_shoulder(s * .5, s * .5, .1, -.6, OVER, .09); ell(s * .5, .1, .66, .07, .07, .03, GOLD, 2)
shell(-1.2, -.75, OVER, gap=.06); belt(LEATHER_D, STEEL, y=-.85)
ell(.62, -1.05, .66, .2, .22, .1, LEATHER, 2); tube([.58, -.95, .68], [.6, -.55, .7], .035, STEEL, 8); tube([.7, -.95, .7], [.72, -.62, .71], .03, "#d93a32", 8)
export("Vehicles_torso")
tube([0, -1.35, 0], [0, .55, 0], .09, STEEL, 16); torus(0, .78, 0, .22, .08, STEEL, axis="z"); torus(0, -1.58, 0, .2, .07, STEEL, axis="z")
tube([0, -.2, 0], [0, .35, 0], .12, "#d93a32", 16); export("Vehicles_prop")

# ---------------------------------------------------------------- 6 Golf
CAPG = fab("#3ca050", "web_cotton_jersey", .8)
cap_hat(CAPG, WHITE); ell(.52, .45, .46, .11, .11, .11, WHITE, 2); export("Golf_head")
VEST = fab("#e8e4d4", "web_rough_linen", .6)
shell(-1.0, .7, VEST, keep=lambda x, z: not (z > .3 and abs(x) < .18), t=.06, taper=.06)
for i in range(4):
    for s in (-1, 1): hull([[s * .55 + dx, -.75 + i * .4 + dy, .6] for dx, dy in ((-.17, 0), (.17, 0), (0, .18), (0, -.18))] + [[s * .55, -.75 + i * .4, .63]], CAPG)
for y in (.2, -.2, -.6): ell(.25, y, .62, .05, .05, .03, "#2a7a3a", 2)
torus(0, .82, 0, .55, .08, WHITE, n=40); export("Golf_torso")
tube([0, -2.45, 0], [0, .45, 0], .06, "#c8ccd4", 12); tube([0, .0, 0], [0, .6, 0], .1, "#1b1b1f", 16)
ell(0, -2.52, .22, .1, .1, .3, "#c8ccd4", 2); export("Golf_prop")

# ---------------------------------------------------------------- 7 Fish: dock captain
CAPT = fab("#f4f1ea", "web_cotton_jersey", .8); NAVY = "#1e3c6e"
hull([[.8 * math.cos(t), .8, .76 * math.sin(t)] for t in np.linspace(0, 6.28, 48)] + [[.64 * math.cos(t), .5, .64 * math.sin(t)] for t in np.linspace(0, 6.28, 48)] +
     [[.5 * math.cos(t), .86, .48 * math.sin(t)] for t in np.linspace(0, 6.28, 32)], CAPT)
disc(.4, .65, .2, NAVY)
hull([[.52 * math.cos(t), .4, .4 + .55 * math.sin(t)] for t in np.linspace(0, math.pi, 20)] + [[.52 * math.cos(t), .43, .4 + .5 * math.sin(t)] for t in np.linspace(0, math.pi, 20)], IRON)
ell(0, .58, .68, .2, .14, .05, GOLD, 2); tube([0, .48, .72], [0, .66, .72], .025, GOLD, 8); torus(0, .5, .72, .08, .02, GOLD, axis="z", n=16, m=6)
beard("#d6d2cc", .15); export("Fish_head")
ROPE = fab("#cfae78", "web_rough_linen", .3)
for y in (.35, -.05, -.45): shell(y - .09, y + .09, NAVY, gap=.03, t=.02)
over_shoulder(.6, -.75, -.6, -.6, ROPE, .07)
for k in range(4): torus(.45, -.2, .66 + k * .02, .42 - k * .04, .06, ROPE, axis="z", n=36, m=8)
belt(LEATHER_D, GOLD)
shell(-1.0, .7, NAVY, keep=lambda x, z: not (z > .3 and abs(x) < .3), t=.07, taper=.06)
for y in (.25, -.15, -.55):
    for sx in (-1, 1): ell(sx * .42, y, .64, .06, .06, .03, GOLD, 2)
for sx in (-1, 1): ell(sx * .95, .78, 0, .14, .05, .45, GOLD, 2)
export("Fish_torso")
ROD = "#5a3a20"
tube([0, -.6, 0], [0, 6.3, -2.2], .07, ROD, 12); tube([0, -.5, 0], [0, .6, -.38], .13, "#1b1b1f", 16)
tube([-.28, .25, -.1], [.05, .25, -.1], .18, STEEL, 24); torus(-.28, .25, -.1, .18, .03, IRON, axis="x")
tube([0, 6.3, -2.2], [0, 4.0, -2.2], .012, "#f4f4f4", 6); ell(0, 3.85, -2.2, .17, .22, .17, "#d93a32", 2); ell(0, 4.0, -2.2, .12, .08, .12, WHITE, 2)
export("Fish_prop")

# ---------------------------------------------------------------- 8 Pets: zoologist
HAIR = fab("#4a3020", "web_dark_jersey", .5)
dome(.12, .67, .82, HAIR); ell(0, .25, -.3, .66, .45, .45, HAIR)
for s in (-1, 1): ell(s * .58, .15, .05, .14, .35, .45, HAIR)
ell(0, .55, .45, .55, .14, .2, HAIR); torus(0, .3, -.7, .13, .05, "#7ac943", axis="z")
rope([[0, .3, -.72], [0, -.1, -.85], [0, -.5, -.82], [0, -.85, -.72]], .14, HAIR); export("Pets_head")
PV = fab("#5a8238", "web_olive_canvas", .8)
shell(-1.0, .7, PV, keep=lambda x, z: not (z > .3 and abs(x) < .2), t=.06, taper=.06)
for s in (-1, 1): ell(s * .55, -.6, .64, .24, .2, .05, "#4a6e2c", 2); ell(s * .55, -.45, .66, .25, .06, .05, "#4a6e2c", 2)
ell(.5, .3, .63, .2, .12, .03, WHITE, 2); ell(.5, .3, .65, .05, .05, .02, "#d93a32", 2); export("Pets_torso")
tube([-.5, -.05, -.2], [.5, -.05, -.2], .1, "#f2ead8", 16)
for s in (-1, 1):
    for t in (-1, 1): ell(s * .55, -.05, t * .11 - .2, .17, .17, .17, "#f2ead8", 2)
export("Pets_prop")

# ---------------------------------------------------------------- 9 Claw: toymaker
TOP = fab("#2a1e3c", "web_dark_jersey", .6)
hull([[.92 * math.cos(t), .45 + .06 * math.cos(2 * t) ** 2, .9 * math.sin(t)] for t in np.linspace(0, 6.28, 48)] + [[.92 * math.cos(t), .5, .9 * math.sin(t)] for t in np.linspace(0, 6.28, 48)], TOP)
frustum(0, 0, .5, 1.55, .58, .64, TOP, 40); disc(.55, .6, .2, "#ffd23f", 40)
ell(.55, .68, .32, .1, .12, .06, "#ff5ea2", 2); moustache("#3a2818"); ell(0, -.02, .63, .1, .09, .08, "#ff8a8a", 2); export("Claw_head")
for s in (-1, 1): ell(s * .2, .66, .6, .18, .1, .05, "#ffd23f", 2)
ell(0, .66, .63, .07, .07, .05, "#ff5ea2", 2)
VV = fab("#6a3aa8", "web_dark_jersey", .6)
shell(-1.0, .5, VV, keep=lambda x, z: not (z > .3 and abs(x) < .16), t=.06, taper=.06)
for y in (.15, -.25, -.65): ell(.24, y, .64, .06, .06, .03, "#ffd23f", 2)
torus(0, .78, 0, .55, .08, "#d0b0ff", n=40); export("Claw_torso")
BEAR = fab("#b47846", "web_jogging_melange", .3)
ell(0, -.2, -.35, .42, .48, .38, BEAR); ell(0, .45, -.35, .35, .32, .32, BEAR)
for s in (-1, 1): ell(s * .27, .74, -.35, .13, .13, .07, BEAR); ell(s * .27, .74, -.3, .07, .07, .04, "#f0d0a8", 2); ell(s * .38, -.05, -.15, .14, .24, .14, BEAR); ell(s * .2, -.62, -.18, .16, .14, .2, BEAR)
ell(0, .38, -.04, .15, .12, .1, "#f0d0a8"); ell(0, .42, .06, .05, .04, .04, IRON, 2)
for s in (-1, 1): ell(s * .13, .55, -.05, .04, .045, .03, IRON, 2); ell(s * .12, .14, .0, .13, .08, .05, "#ff5ea2", 2)
ell(0, -.15, .02, .2, .22, .04, "#f0d0a8", 2); export("Claw_prop")

# ---------------------------------------------------------------- 10 Minerals: sea trader
BAND = fab("#d63a48", "web_cotton_jersey", .5)
dome(.1, .68, .82, BAND)
for i in range(14): a = i / 14 * 2 * math.pi; ell(.52 * math.cos(a), .48, .52 * math.sin(a), .06, .04, .06, WHITE, 1)
ell(.05, .3, -.7, .15, .13, .1, BAND, 2); cap([.05, .28, -.72], [.25, -.2, -.85], .1, BAND); cap([.05, .28, -.72], [-.18, -.25, -.82], .1, BAND)
torus(.64, -.18, .05, .1, .025, GOLD, axis="x", n=20, m=6); moustache("#2a1a10"); export("Minerals_head")
SASH = fab("#3a2a5a", "web_dark_jersey", .5)
shell(-1.25, -.85, SASH, gap=.05, t=.08); cap([.6, -1.1, .62], [.75, -1.6, .55], .1, SASH); ell(.6, -1.05, .66, .14, .12, .08, SASH, 2)
over_shoulder(.9, -.75, -.9, -.9, LEATHER, .07)
ell(-.55, -1.05, .7, .22, .22, .12, LEATHER, 2); ell(-.55, -.9, .76, .22, .08, .08, LEATHER_D, 2); ell(-.55, -.95, .83, .04, .04, .03, GOLD, 2)
shell(-.85, .62, "#2a2030", keep=lambda x, z: not (z > .3 and abs(x) < .22), t=.06, taper=.06)
for k in range(16): a = math.pi * (k / 15); ell(.4 * math.cos(a), .72 - .5 * math.sin(a), .58 + .05 * math.sin(a), .05, .03, .03, GOLD, 1)
ell(0, .2, .64, .1, .12, .05, "#d93a32", 2)
export("Minerals_torso")
gem = [[.32 * math.cos(t), 0, .32 * math.sin(t) - .4] for t in np.linspace(0, 6.28, 12, endpoint=False)]
hull(gem + [[.2 * math.cos(t), .22, .2 * math.sin(t) - .4] for t in np.linspace(0, 6.28, 8, endpoint=False)] + [[0, -.45, -.4]], "#7ee8ff")
torus(0, 0, -.4, .33, .035, GOLD, n=32, m=8); export("Minerals_prop")

# ---------------------------------------------------------------- 11 Mine: miner
HARD = "#ffc83c"
dome(.3, .7, .64, HARD); hull([[.88 * math.cos(t), .27, .88 * math.sin(t)] for t in np.linspace(0, 6.28, 48)] + [[.84 * math.cos(t), .33, .84 * math.sin(t)] for t in np.linspace(0, 6.28, 48)], HARD)
hull([[x, .3 + .62 * math.sin(a), .7 * math.cos(a) + .02] for x in (-.07, .07) for a in np.linspace(0, math.pi, 14)], "#e8a820")
ell(0, .55, .72, .2, .17, .1, IRON, 2); tube([0, .55, .7], [0, .55, .86], .14, IRON, 24); ell(0, .55, .86, .12, .12, .02, "#ffe28c", 2)
beard("#9a8a7a", .2); export("Mine_head")
for s in (-1, 1): over_shoulder(s * .55, s * .55, -1.0, -1.0, "#d93a32", .08); ell(s * .55, .55, .66, .07, .09, .03, GOLD, 2)
belt(LEATHER_D, GOLD); ell(-.72, -1.1, .62, .2, .22, .1, LEATHER, 2)
tube([-.72, -.9, .6], [-.72, -.65, .6], .1, STEEL, 16); ell(-.72, -.55, .6, .08, .08, .08, "#ffe28c", 2)
shell(-.95, .55, "#ff7a1e", keep=lambda x, z: not (z > .3 and abs(x) < .16), t=.05, taper=.05)
for y in (-.55, -.2): shell(y - .06, y + .06, "#e8eef2", keep=lambda x, z: not (z > .3 and abs(x) < .16), gap=.1, t=.02)
ell(.5, .25, .65, .16, .12, .04, "#e86410", 2)
export("Mine_torso")
tube([0, -1.0, 0], [0, 1.95, 0], .09, WOODC, 12); ell(0, -1.0, 0, .1, .06, .1, WOODC, 2)
for s in (-1, 1):
    pts = []
    for k in range(9):
        t = k / 8; a = t * .7; zz = s * (.12 + .95 * math.sin(a) / math.sin(.7)); yy = 2.0 - .25 * t * t; w = .11 * (1 - .8 * t)
        pts += [[x, yy + dy, zz] for x in (-w * .8, w * .8) for dy in (-w, w)]
    hull(pts[:20], STEEL); hull(pts[16:], STEEL)
ell(0, 2.0, 0, .14, .18, .2, IRON, 2); export("Mine_prop")

out = pathlib.Path("projects/boomland_world/export/guides.json"); out.write_text(json.dumps(OFFS, indent=1))
print(json.dumps(OFFS))
