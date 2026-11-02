"""Car & boat dealership (low-poly, Roblox-ready). Built Z-up in metres, exported Y-up. Run with .venv/Scripts/python.exe"""
import numpy as np, trimesh as tm, pathlib
from trimesh.transformations import rotation_matrix as RM, translation_matrix as TM
P = []
def col(m, hexc):
    h = hexc.lstrip('#'); rgb = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    m.visual.face_colors = rgb + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def hullp(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)
def wheel(x, y, z, r, w, c="#1c1e24"):        # axis along Y
    m = tm.creation.cylinder(radius=r, height=w, sections=14); m.apply_transform(RM(np.pi/2, [1, 0, 0])); m.apply_translation([x, y, z]); col(m, c)
    h = tm.creation.cylinder(radius=r*0.55, height=w*1.05, sections=10); h.apply_transform(RM(np.pi/2, [1, 0, 0])); h.apply_translation([x, y, z]); col(h, "#c9ced6")
def car(cx, cy, z0, yaw, body, L=4.4, W=1.9):
    s0 = len(P)
    hl, hw = L/2, W/2
    box(-hl, -hw, z0+0.35, hl, hw, z0+0.95, body)                                       # lower body
    hullp([(-1.2, -hw+.05, z0+.95), (1.0, -hw+.05, z0+.95), (0.45, -hw+.2, z0+1.5), (-0.8, -hw+.2, z0+1.5),
           (-1.2, hw-.05, z0+.95), (1.0, hw-.05, z0+.95), (0.45, hw-.2, z0+1.5), (-0.8, hw-.2, z0+1.5)], "#8fd3f4")  # cabin glass
    hullp([(-1.0, -hw+.1, z0+1.5), (0.35, -hw+.1, z0+1.5), (-1.0, hw-.1, z0+1.5), (0.35, hw-.1, z0+1.5),
           (-0.9, -hw+.2, z0+1.55), (0.25, -hw+.2, z0+1.55), (-0.9, hw-.2, z0+1.55), (0.25, hw-.2, z0+1.55)], body)  # roof
    for sy in (-1, 1):
        wheel(hl*0.62, sy*(hw-.05), z0+.38, .38, .3); wheel(-hl*0.62, sy*(hw-.05), z0+.38, .38, .3)
        box(hl-.1, sy*hw*.65-.2, z0+.65, hl+.03, sy*hw*.65+.2, z0+.85, "#fff2a8")        # headlights
        box(-hl-.03, sy*hw*.65-.2, z0+.65, -hl+.1, sy*hw*.65+.2, z0+.85, "#d8262c")      # tail lights
    box(-hl-.02, -.5, z0+.4, -hl+.1, .5, z0+.55, "#2b2f3a")
    for m in P[s0:]:
        m.apply_transform(TM([cx, cy, 0]) @ RM(yaw, [0, 0, 1]) if False else np.eye(4))
    grp = tm.util.concatenate(P[s0:]); del P[s0:]
    grp.apply_transform(TM([cx, cy, 0]) @ RM(yaw, [0, 0, 1]) @ TM([0, 0, 0])); P.append(grp)
def boat(cx, cy, z0, yaw, hullc, L=6.0, W=2.2):
    s0 = len(P)
    hl, hw = L/2, W/2
    hullp([(-hl, -hw, z0+.7), (hl*.35, -hw, z0+.7), (hl, 0, z0+.9), (hl*.35, hw, z0+.7), (-hl, hw, z0+.7),
           (-hl+.3, -hw*.55, z0+0.0), (hl*.3, -hw*.4, z0+0.05), (hl*.75, 0, z0+0.3), (hl*.3, hw*.4, z0+0.05), (-hl+.3, hw*.55, z0+0.0)], hullc)
    box(-hl, -hw-.02, z0+.7, hl*.6, -hw+.12, z0+1.0, "#f5f5f5"); box(-hl, hw-.12, z0+.7, hl*.6, hw+.02, z0+1.0, "#f5f5f5")  # rail stripe
    box(-hl*.55, -hw*.7, z0+.7, hl*.1, hw*.7, z0+1.3, "#f5f5f5")                                                              # console
    hullp([(-hl*.5, -hw*.65, z0+1.3), (-hl*.05, -hw*.65, z0+1.3), (-hl*.2, -hw*.55, z0+1.85), (-hl*.5, -hw*.55, z0+1.85),
           (-hl*.5, hw*.65, z0+1.3), (-hl*.05, hw*.65, z0+1.3), (-hl*.2, hw*.55, z0+1.85), (-hl*.5, hw*.55, z0+1.85)], "#8fd3f4")  # windshield
    box(-hl-.35, -.3, z0+.2, -hl+.05, .3, z0+1.2, "#2b2f3a")                                                                   # outboard
    box(-hl-.45, -.12, z0-.15, -hl-.25, .12, z0+.3, "#2b2f3a")
    box(-hl*.5, -hw*.5, z0+.7, -hl*.5+.9, hw*.5, z0+.85, "#7b5a3a")                                                            # seat
    grp = tm.util.concatenate(P[s0:]); del P[s0:]
    grp.apply_transform(TM([cx, cy, 0]) @ RM(yaw, [0, 0, 1])); P.append(grp)
def trailer(cx, cy, yaw):
    s0 = len(P)
    box(-2.6, -.8, .55, 2.6, .8, .7, "#7d8590"); box(2.6, -.08, .55, 4.0, .08, .68, "#7d8590"); box(3.9, -.15, .5, 4.1, .15, .75, "#2b2f3a")
    for sy in (-1, 1): wheel(-.4, sy*1.0, .45, .45, .25)
    grp = tm.util.concatenate(P[s0:]); del P[s0:]; grp.apply_transform(TM([cx, cy, 0]) @ RM(yaw, [0, 0, 1])); P.append(grp)

# ---- site ----
box(-13, -11, -.2, 13, 8, 0, "#6f7680")                                   # pavement
box(-13, -11, -.19, 13, -9.2, .0, "#6f7680")
for i in range(-5, 6): box(i*2.3-.08, -10.2, 0, i*2.3+.08, -9.6, .01, "#f5f5f5")     # parking stripes
box(-7.5, -4.5, 0, 7.5, 4.5, .2, "#b9a98d")                               # showroom floor
# showroom shell 15 x 9 x 4.4, front = -Y
WALL, TRIM = "#eceae4", "#2b2f3a"
box(-7.5, 4.2, .2, 7.5, 4.5, 4.4, WALL); box(-7.5, -4.5, .2, -7.2, 4.5, 4.4, WALL); box(7.2, -4.5, .2, 7.5, 4.5, 4.4, WALL)
box(-7.5, -4.5, 3.4, 7.5, -4.2, 4.4, WALL)                                # fascia
box(-7.5, -4.5, .2, -6.5, -4.2, 3.4, WALL); box(6.5, -4.5, .2, 7.5, -4.2, 3.4, WALL)
box(-6.5, -4.42, .2, 6.5, -4.3, 3.4, "#8fd3f4")                            # big glass wall
for i in range(-3, 4): box(i*1.8-.05, -4.46, .2, i*1.8+.05, -4.28, 3.4, TRIM)
box(-1.2, -4.5, .2, 1.2, -4.2, 3.0, "#8fd3f4"); box(-1.25, -4.52, .2, -1.15, -4.2, 3.05, TRIM); box(1.15, -4.52, .2, 1.25, -4.2, 3.05, TRIM)
box(-7.8, -4.8, 4.4, 7.8, 4.8, 4.7, "#3a3f4b")                            # roof slab
box(-7.8, -4.8, 4.7, 7.8, -4.6, 5.0, "#3a3f4b")
# sign: blue band with white "letters" (left = AUTO, right = BOAT)
box(-6.5, -4.9, 4.7, 6.5, -4.6, 6.4, "#1b4f9c"); box(-6.2, -4.95, 5.0, 6.2, -4.62, 6.1, "#f5f5f5")
for i in range(4): box(-5.6+i*1.1, -5.0, 5.2, -4.8+i*1.1, -4.96, 5.9, "#d8262c")
box(-0.9, -5.0, 5.3, 0.9, -4.96, 5.8, "#1b4f9c")
for i in range(4): box(1.4+i*1.1, -5.0, 5.2, 2.2+i*1.1, -4.96, 5.9, "#1b4f9c")
# awning over entrance
for k in range(6): box(-2.4+k*.8, -6.0, 3.2, -1.6+k*.8, -4.3, 3.35, "#d8262c" if k % 2 == 0 else "#f5f5f5")
# interior: 2 cars on podiums + counter
box(-5.6, -3.2, .2, -1.0, -0.8, .4, "#d8dee9"); box(1.2, -3.2, .2, 6.0, -0.8, .4, "#d8dee9")
car(-3.3, -2.0, .4, 0.35, "#d8262c"); car(3.6, -2.0, .4, -0.35, "#f2c230")
box(-6.5, 2.4, .2, -2.5, 3.4, 1.3, "#3b4252"); box(-6.6, 2.3, 1.3, -2.4, 3.5, 1.38, "#d8dee9"); box(-5.0, 2.7, 1.38, -4.3, 3.1, 1.8, "#1c1e24")
box(2.5, 3.9, .2, 7.0, 4.2, 2.6, "#5b4636")                               # wall board with keys/brochures
for i in range(6): box(2.8+i*.7, 3.85, 1.0, 3.3+i*.7, 3.9, 2.2, "#3fa7ff" if i % 2 else "#f5f5f5")
box(-1.5, 1.5, .2, 1.5, 2.5, .8, "#c8b79a")                               # lounge table
for sx in (-2.2, 2.2): box(sx-.5, 1.4, .2, sx+.5, 2.4, .7, "#1b4f9c")
# outside: car ramp display, boat on trailer, boat on water-blue podium, flags
car(9.5, -6.5, .2, 0.0, "#1b4f9c") if False else None
box(8.0, -8.2, 0, 12.0, -4.8, .35, "#d8dee9"); car(10.0, -6.5, .35, 1.2, "#1b4f9c")
trailer(-9.7, -5.5, 0.0); boat(-9.4, -5.5, .7, 0.0, "#f5f5f5")
box(-12.4, 0.6, 0, -6.6, 5.0, .3, "#2f7fc4"); boat(-9.5, 2.8, .35, 0.5, "#d8262c", 5.2, 2.0)         # boat on 'water' display
for fx in (-7.0, 7.0, 12.2):
    box(fx-.06, -8.6, 0, fx+.06, -8.5+.1, 6.0, "#c9ced6"); box(fx+.06, -8.6, 4.8, fx+1.0, -8.55, 5.9, "#d8262c" if fx > 0 else "#1b4f9c")

scene = tm.util.concatenate(P)
scene.apply_transform(RM(-np.pi/2, [1, 0, 0]))                              # Z-up -> Y-up
fc = scene.visual.face_colors[:, :3]
sc = tm.Scene()
for cc in np.unique(fc, axis=0):                                            # one material per colour (Roblox/GLB friendly)
    sel = np.where((fc == cc).all(1))[0]
    m = scene.submesh([sel], append=True)
    lin = ((cc / 255.0) ** 2.2).tolist() + [1.0]                             # glTF factors are linear
    m.visual = tm.visual.TextureVisuals(material=tm.visual.material.PBRMaterial(baseColorFactor=lin, metallicFactor=0.0, roughnessFactor=0.9))
    sc.add_geometry(m, geom_name="mat_%02x%02x%02x" % tuple(cc))
out = pathlib.Path("projects/car_boat_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"car_boat_shop.glb"); sc.export(out/"car_boat_shop.obj")
print(len(scene.faces), "tris", scene.bounds.round(1).tolist())
