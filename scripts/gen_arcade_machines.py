"""Boomland arcade machines (Roblox-ready, flat colours, low-poly, ~1-2k tris each), Y-up metres, front = +Z:
  claw_machine.glb   - pink cabinet, glass box with plush toys, gantry + 3-prong claw, lit header, joystick + button, prize chute
  arcade_cabinet.glb - upright game cabinet: shaped side panels, lit marquee, screen, joystick + buttons, coin door
Every colour is its own mesh with a 4x4 texture of that colour (Roblox ignores baseColorFactor).
Run: .venv/Scripts/python.exe scripts/gen_arcade_machines.py"""
import math, pathlib
import numpy as np, trimesh as tm
from PIL import Image

P = []
def col(m, hexc):
    h = hexc.lstrip('#'); m.visual.face_colors = [int(h[i:i+2], 16) for i in (0, 2, 4)] + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def cyl(x, y0, y1, z, r, c, n=12, axis='y'):
    m = tm.creation.cylinder(radius=r, height=y1-y0, sections=n)
    if axis == 'y': m.apply_transform(tm.transformations.rotation_matrix(-math.pi/2, [1, 0, 0])); m.apply_translation([x, (y0+y1)/2, z])
    elif axis == 'z': m.apply_translation([x, y0, (z+y1)/2])
    return col(m, c)
def ball(x, y, z, r, c, sub=1):
    m = tm.creation.icosphere(subdivisions=sub, radius=r); m.apply_translation([x, y, z]); return col(m, c)
def hull(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)
def beam(a, b, w, c):
    a, b = np.array(a, float), np.array(b, float); d = b - a; L = np.linalg.norm(d)
    m = tm.creation.box([w, w, L]); z = np.array([0, 0, 1.0]); u = d / L
    ax = np.cross(z, u); s = np.linalg.norm(ax)
    if s > 1e-6: m.apply_transform(tm.transformations.rotation_matrix(math.atan2(s, z @ u), ax / s))
    elif u[2] < 0: m.apply_transform(tm.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    m.apply_translation((a + b) / 2); return col(m, c)

def export(name):
    global P
    scene = tm.util.concatenate(P); P = []
    fc = scene.visual.face_colors[:, :3]; sc = tm.Scene(); n = 0
    for cc in np.unique(fc, axis=0):
        sel = np.where((fc == cc).all(1))[0]
        m = scene.submesh([sel], append=True)
        hx = "%02x%02x%02x" % tuple(cc)
        img = Image.fromarray(np.full((4, 4, 3), cc, np.uint8))
        glass = hx == GLASS[1:]
        mat = tm.visual.material.PBRMaterial(name=("glass#" if glass else "paint#") + hx, baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.8)
        if glass: mat.alphaMode = "BLEND"; mat.baseColorFactor = [255, 255, 255, 110]
        m.visual = tm.visual.TextureVisuals(uv=np.full((len(m.vertices), 2), 0.5), material=mat)
        n += len(m.faces); sc.add_geometry(m, geom_name=("Glass_" if glass else "Paint_") + hx)
    out = pathlib.Path("projects/boomland_arcade/export"); out.mkdir(parents=True, exist_ok=True)
    sc.export(out / f"{name}.glb"); print(name, n, "tris", len(sc.geometry), "materials")

PINK, PINK2, YEL, DARK, WHITE, GLASS, RED, BLUE, CYAN, PURPLE, PURP2, GREEN, ORANGE, METAL = \
    "#ff5fa2", "#d9437f", "#ffd23f", "#23232e", "#f5f5f5", "#cfefff", "#e8403a", "#3d7bff", "#3ee0e0", "#7b4dff", "#5a34c8", "#4cd964", "#ff9a3c", "#b8bcc8"

# ============================================================ CLAW MACHINE (1.3 x 2.3 x 1.3 m)
W, D = .65, .65                                   # half width / depth
box(-W, 0, -D, W, .08, D, DARK)                   # plinth
box(-W+.02, .08, -D+.02, W-.02, .95, D-.02, PINK) # cabinet
for y in (.30, .62): box(-W, y, D-.03, W, y+.05, D+.01, YEL)    # front stripes
box(-.22, .14, D-.04, .22, .40, D+.005, DARK)     # prize chute opening
box(-.24, .12, D-.03, .24, .14, D+.03, YEL); box(-.24, .40, D-.03, .24, .42, D+.03, YEL)
box(.30, .52, D-.03, .40, .60, D+.01, DARK); box(.33, .55, D, .37, .57, D+.012, YEL)  # coin slot
hull([[-W, .95, D], [W, .95, D], [-W, .95, D+.25], [W, .95, D+.25], [-W, .85, D+.25], [W, .85, D+.25], [-W, .85, D], [W, .85, D]], PINK2)  # control ledge
cyl(-.22, 1.0, 1.10, D+.13, .018, DARK, 8); ball(-.22, 1.13, D+.13, .045, RED)                        # joystick
cyl(.18, .96, 1.0, D+.13, .07, RED, 14); cyl(.18, .99, 1.01, D+.13, .075, WHITE, 14)                  # big button
box(-W+.02, .95, -D+.02, W-.02, 1.0, D-.02, YEL)  # floor of the glass box
GT = 2.02                                          # glass top
for sx in (-1, 1):
    for sz in (-1, 1):
        box(sx*W-.04 if sx > 0 else -W, .95, sz*D-.04 if sz > 0 else -D, sx*W if sx > 0 else -W+.04, GT, sz*D if sz > 0 else -D+.04, YEL)  # corner posts
box(-W+.04, 1.0, D-.02, W-.04, GT, D-.01, GLASS); box(-W+.04, 1.0, -D+.01, W-.04, GT, -D+.02, GLASS)
box(-W+.01, 1.0, -D+.04, -W+.02, GT, D-.04, GLASS); box(W-.02, 1.0, -D+.04, W-.01, GT, D-.04, GLASS)
box(.22, 1.0, .18, .50, 1.22, .50, DARK); box(.20, 1.22, .16, .52, 1.25, .52, YEL)  # prize hole corner
toys = [(-.40, -.35, PURPLE), (-.15, -.40, CYAN), (.12, -.38, ORANGE), (.40, -.30, GREEN), (-.42, -.05, BLUE), (-.18, -.10, RED),
        (.08, -.12, YEL), (.35, -.02, PINK2), (-.38, .25, ORANGE), (-.12, .22, GREEN), (.05, .32, PURPLE), (-.28, .45, CYAN)]
for x, z, c in toys:                               # plush toys: body + head + ears
    y = 1.08 + (abs(x * 7 + z * 13) % .06)
    ball(x, y, z, .085, c); ball(x, y + .11, z + .01, .06, c)
    ball(x - .04, y + .17, z, .022, c, 0); ball(x + .04, y + .17, z, .022, c, 0)
    ball(x - .02, y + .12, z + .065, .01, DARK, 0); ball(x + .02, y + .12, z + .065, .01, DARK, 0)
for sx in (-1, 1): box(sx*.52-.015, 1.90, -D+.05, sx*.52+.015, 1.93, D-.05, METAL)   # gantry rails
box(-.52, 1.88, -.03, .52, 1.92, .03, METAL)       # cross rail
box(-.10, 1.83, -.07, .02, 1.90, .05, DARK)        # carriage
cyl(-.04, 1.52, 1.83, -.01, .008, METAL, 6)        # cable
cyl(-.04, 1.46, 1.53, -.01, .045, YEL, 12)         # claw hub
for k in range(3):
    a = k * 2 * math.pi / 3; ex, ez = -.04 + math.cos(a) * .045, -.01 + math.sin(a) * .045
    tx, tz = -.04 + math.cos(a) * .10, -.01 + math.sin(a) * .10
    beam([ex, 1.47, ez], [tx, 1.38, tz], .018, METAL); beam([tx, 1.38, tz], [tx * .7 - .012, 1.30, tz * .7 - .003], .016, METAL)
box(-W, GT, -D, W, GT + .06, D, PINK2)             # roof
box(-W - .03, GT + .06, -D - .03, W + .03, GT + .40, D + .03, PINK)   # header
box(-W + .08, GT + .11, D + .03, W - .08, GT + .35, D + .045, WHITE)  # sign panel
for i in range(5): box(-.40 + i * .2 - .05, GT + .17, D + .045, -.40 + i * .2 + .05, GT + .29, D + .05, (RED, YEL, CYAN, GREEN, PURPLE)[i])  # sign blocks
for i in range(9):                                 # bulbs around the header
    x = -W + .05 + i * (2 * W - .1) / 8
    ball(x, GT + .06 + .02, D + .04, .025, (YEL, WHITE)[i % 2], 0); ball(x, GT + .38, D + .04, .025, (WHITE, YEL)[i % 2], 0)
box(-W - .05, GT + .40, -D - .05, W + .05, GT + .46, D + .05, YEL)    # cap
export("claw_machine")

# ============================================================ ARCADE CABINET (0.9 x 2.1 x 0.95 m)
W = .45
prof = [(-.45, 0), (.45, 0), (.45, .95), (.30, 1.05), (.20, 1.70), (.32, 1.80), (.32, 2.10), (-.45, 2.10)]  # side profile (z, y), front = +z
for sx in (-1, 1):
    x0, x1 = (sx * W - .04, sx * W) if sx > 0 else (-W, -W + .04)
    hull([[x, y, z] for (z, y) in prof for x in (x0, x1)], PURPLE)
    for (z0, y0), (z1, y1) in zip(prof[2:6], prof[3:7]): beam([x1 + .002 if sx > 0 else x0 - .002, y0, z0], [x1 + .002 if sx > 0 else x0 - .002, y1, z1], .03, CYAN)  # neon edge
box(-W + .04, 0, -.45, W - .04, .95, .43, PURP2)  # lower body
box(-.20, .18, .43, .20, .62, .45, DARK); box(-.08, .45, .45, .08, .50, .46, YEL); box(-.04, .30, .45, .04, .40, .46, RED)  # coin door
hull([[-W + .04, .95, .45], [W - .04, .95, .45], [-W + .04, 1.05, .30], [W - .04, 1.05, .30], [-W + .04, .90, .45], [W - .04, .90, .45], [-W + .04, .90, .20], [W - .04, .90, .20]], DARK)  # control panel
cyl(-.20, 1.0, 1.09, .37, .015, DARK, 8); ball(-.20, 1.11, .37, .04, RED)
for i, c in enumerate((YEL, CYAN, GREEN, RED)): cyl(.0 + (i % 2) * .11 + (i // 2) * .05, .985, 1.01, .40 - (i // 2) * .08, .032, c, 12)
hull([[-W + .04, 1.05, .30], [W - .04, 1.05, .30], [-W + .04, 1.70, .20], [W - .04, 1.70, .20],
      [-W + .04, 1.05, .10], [W - .04, 1.05, .10], [-W + .04, 1.70, .10], [W - .04, 1.70, .10]], DARK)  # screen bezel
hull([[-.33, 1.12, .292], [.33, 1.12, .292], [-.33, 1.64, .212], [.33, 1.64, .212], [-.33, 1.12, .27], [.33, 1.12, .27], [-.33, 1.64, .19], [.33, 1.64, .19]], BLUE)  # screen
for i in range(4): box(-.25 + i * .14, 1.30 + (i % 2) * .1, .26 - i * 0, -.17 + i * .14, 1.36 + (i % 2) * .1, .275 - .0, (YEL, GREEN, PINK, CYAN)[i])  # game sprites
box(-W + .04, 1.70, .10, W - .04, 1.80, .32, PURP2)
box(-W + .04, 1.80, -.45, W - .04, 2.10, .30, PURP2)
box(-W + .06, 1.83, .30, W - .06, 2.07, .32, YEL)  # lit marquee
for i in range(5): box(-.34 + i * .15, 1.89, .32, -.26 + i * .15, 2.01, .33, (RED, PURPLE, CYAN, GREEN, ORANGE)[i])
box(-W + .04, .95, -.45, W - .04, 1.80, -.30, PURP2)  # back
box(-W - .02, 2.10, -.47, W + .02, 2.14, .34, DARK)   # top
export("arcade_cabinet")
