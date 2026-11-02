"""Sapper shop (Roblox): mines, metal detectors, drones, wire cutters. Writes a native 3dPazl recipe.
Run: python scripts/gen_sapper_shop_recipe.py ; then load_project('sapper_shop') in the app. Front = -Y, block y 0..8."""
import json, pathlib
E = []
OL, KH, SAND, YEL, BLK, RED, STL = "#5b6a3c", "#8d8a5a", "#b3a070", "#e8b923", "#1d1f22", "#c0392b", "#aab0b8"
WOODC, DKG, CRATE = "#6a5236", "#3b3f35", "#4c5a30"
def pl(c): return "plaster_white#" + c.lstrip('#')
def B(i, x, y, z, w, d, h, c, rot=0):
    e = {"id": i, "type": "box", "params": {"w": w, "d": d, "h": h, "material": pl(c)}, "offset": [x, y, z]}
    if rot: e["rot"] = rot
    E.append(e)
def C(i, x, y, z, r, h, c, rt=None, axis="z"):
    p = {"r": r, "h": h, "material": pl(c), "axis": axis}
    if rt is not None: p["r_top"] = rt
    E.append({"id": i, "type": "cylinder", "params": p, "offset": [x, y, z]})
def BM(i, p0, p1, c, w=.05, h=None, rnd=True):
    E.append({"id": i, "type": "beam", "params": {"p0": p0, "p1": p1, "w": w, "h": h or w, "round": rnd, "material": pl(c)}})

# ---- shell
B("found", 0, 4, 0, 12.4, 8.4, .2, "#6b6a5a")
B("porch", 0, -1.3, 0, 12.4, 2.6, .2, "#7a5a3a")
E.append({"id": "shop", "type": "block", "params": {"w": 12, "d": 8, "floors": 1, "floor_h": 3.8, "hollow": True, "material": pl(KH), "plinth_material": "granite#8a8472", "plinth_h": .5, "slab_t": .2, "plinth_out": 0}, "offset": [0, 4, 0]})
E.append({"id": "roof", "type": "roof", "params": {"type": "gable", "pitch": 28, "overhang": .6, "ridge": "x", "material": "corrugated_metal#7f8a68", "gable_material": pl(KH)}, "on": "shop:top"})
E.append({"id": "door", "type": "door", "params": {"w": 2.2, "h": 2.6, "open": True, "trim": "none", "steps": 0, "canopy": "none", "trim_w": .15, "trim_material": pl(OL)}, "on": "shop:front", "at": ["50%", 0]})
for n, u in (("win_l", 2.4), ("win_r", 9.6)):
    E.append({"id": n, "type": "window", "params": {"w": 2.4, "h": 1.5, "mullions": [1, 1], "shutters": False, "trim_w": .15, "sill_ledge": False, "trim": "none", "frame_material": "frame#2f3a22", "trim_material": pl(OL)}, "on": "shop:front", "at": [u, 1.7]})
# ---- awning + sign
B("awn", 0, -1.25, 3.1, 12.6, 2.7, .2, OL)
B("awn_f", 0, -2.62, 3.1, 12.6, .05, .2, YEL)
for k in range(10): B(f"awn_s{k}", -5.9 + k * 1.3, -2.66, 3.1, .62, .05, .2, BLK)
for s in (-1, 1): BM(f"post{s}", [s * 5.9, -2.3, .2], [s * 5.9, -2.3, 3.15], DKG, .18, rnd=False)
B("sign", 0, -1.0, 3.3, 8.6, .25, 1.5, "#2c3320")
B("sg_t", 0, -1.15, 4.7, 8.6, .06, .1, YEL); B("sg_b", 0, -1.15, 3.3, 8.6, .06, .1, YEL)
B("sg_l", -4.25, -1.15, 3.4, .1, .06, 1.3, YEL); B("sg_r", 4.25, -1.15, 3.4, .1, .06, 1.3, YEL)
SY, SZ = -1.14, 4.05
for k, x in enumerate((-3.0, -1.0, 1.0, 3.0)): B(f"ic{k}", x, SY, SZ - .6, 1.2, .08, 1.2, YEL)
# ---- mines table (left)
TT = 1.06
B("t1", -4.5, -1.6, .2, 2.4, 1.0, .8, WOODC); B("t1c", -4.5, -1.6, 1.0, 2.5, 1.1, .06, OL)
def mine(i, x, y, z):
    C(i + "a", x, y, z - .01, .28, .11, OL); C(i + "b", x, y, z + .1, .2, .02, YEL); C(i + "c", x, y, z + .11, .13, .05, BLK)
def bmine(i, x, y, z):
    C(i + "a", x, y, z - .01, .12, .3, "#6d5a36"); C(i + "b", x, y, z + .29, .12, .1, STL, rt=.03)
    for k, (dx, dy) in enumerate(((.1, 0), (-.1, 0), (0, .1))): BM(f"{i}p{k}", [x, y, z + .38], [x + dx, y + dy, z + .46], BLK, .02)
for k, (x, y) in enumerate(((-5.2, -1.9), (-4.5, -1.9), (-3.8, -1.9), (-5.2, -1.3), (-4.5, -1.3))): mine(f"m{k}", x, y, TT - .01)
bmine("bm0", -3.8, -1.3, TT - .01)
# ---- detector rack
B("rack", -2.2, -.45, .2, 1.5, .6, .1, DKG)
BM("rail", [-3.0, .0, 1.1], [-1.4, .0, 1.1], DKG, .05)
for k, x in enumerate((-2.7, -2.2, -1.7)):
    C(f"dd{k}d", x, -.55, .29, .2, .04, "#222426"); C(f"dd{k}c", x, -.55, .33, .06, .08, STL)
    BM(f"dd{k}r", [x, -.55, .35], [x, -.12, 1.55], STL, .04)
    B(f"dd{k}h", x, -.12, 1.45, .1, .3, .08, BLK); BM(f"dd{k}g", [x, -.12, 1.5], [x, -.12, 1.15], RED, .05)
# ---- cutters pegboard (right) and drones table
B("peg", 3.6, -.05, 1.55, 4.2, .1, 1.2, WOODC)
B("t2", 4.5, -1.6, .2, 2.4, 1.0, .8, WOODC); B("t2c", 4.5, -1.6, 1.0, 2.5, 1.1, .06, "#3d4a2a")
def drone(i, x, y, z, big=1):
    s = big
    B(i + "b", x, y, z + .02 * s, .5 * s, .5 * s, .14 * s, "#25282b"); C(i + "cam", x, y, z - .02 * s, .07 * s, .07 * s, "#111111")
    for k, sg in enumerate((1, -1)): BM(f"{i}sk{k}", [x - .3 * s, y + sg * .18 * s, z + .01], [x + .3 * s, y + sg * .18 * s, z + .01], BLK, .03 * s)
    for k, sg in enumerate((1, -1)): BM(f"{i}ar{k}", [x - .4 * s, y - sg * .4 * s, z + .1 * s], [x + .4 * s, y + sg * .4 * s, z + .1 * s], STL, .06 * s, .04 * s, rnd=False)
    for k, (dx, dy) in enumerate(((-1, -1), (1, 1), (-1, 1), (1, -1))):
        C(f"{i}m{k}", x + dx * .4 * s, y + dy * .4 * s, z + .1 * s, .05 * s, .1 * s, BLK); C(f"{i}p{k}", x + dx * .4 * s, y + dy * .4 * s, z + .2 * s, .2 * s, .015 * s, "#555a60")
drone("d1", 3.8, -1.6, TT - .01); drone("d2", 5.2, -1.6, TT - .01)
BM("hang1", [-.2, -1.6, 3.15], [-.2, -1.6, 2.75], BLK, .03); BM("hang2", [.2, -1.6, 3.15], [.2, -1.6, 2.75], BLK, .03)
drone("dh", 0, -1.6, 2.65)
r = {"name": "sapper_shop", "style": "generic", "detail": "realistic", "interiors": False, "elements": E}
p = pathlib.Path("projects/sapper_shop"); p.mkdir(parents=True, exist_ok=True)
(p / "recipe.json").write_text(json.dumps(r, indent=1), encoding="utf-8"); print(len(E), "elements")
