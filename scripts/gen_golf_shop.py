"""Golf shop (Roblox-ready low poly, flat colours + sign texture). Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_golf_shop.py"""
import numpy as np, trimesh as tm, pathlib
from trimesh.transformations import rotation_matrix as RM
from PIL import Image, ImageDraw, ImageFont
P = []
def col(m, hexc):
    h = hexc.lstrip('#'); m.visual.face_colors = [int(h[i:i+2], 16) for i in (0, 2, 4)] + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def cyl(x, y, z0, z1, r, c, n=16):
    m = tm.creation.cylinder(radius=r, height=z1-z0, sections=n); m.apply_translation([x, y, (z0+z1)/2]); return col(m, c)
def ball(x, y, z, r, c):
    m = tm.creation.icosphere(subdivisions=2, radius=r); m.apply_translation([x, y, z]); return col(m, c)

WALL, TRIM, GREEN, DGREEN, GLASS, WOOD, GREY = "#f3efe2", "#ffffff", "#2e8b3d", "#1f5f2b", "#9fd8ee", "#9a6b3f", "#555a60"
HX, HY, H = 6.0, 4.5, 3.8                      # shop 12 x 9 m, walls 3.8 m, front = -Y
box(-HX-.3, -HY-.3, 0, HX+.3, HY+.3, .2, GREY)                                   # floor slab
box(-HX, -HY, .2, HX, HY, .22, "#b98a5a")                                        # wood floor
# walls: back/sides solid, front = glass shopfront with door gap
box(-HX, HY-.25, .2, HX, HY, H, WALL)
box(-HX, -HY, .2, -HX+.25, HY, H, WALL); box(HX-.25, -HY, .2, HX, HY, H, WALL)
box(-HX, -HY, .2, HX, -HY+.25, .9, WALL)                                         # front knee wall
box(-HX, -HY, 2.9, HX, -HY+.25, H, WALL)                                         # front header
box(-HX, -HY-.05, .9, -HX+.4, -HY+.3, 2.9, WALL); box(HX-.4, -HY-.05, .9, HX, -HY+.3, 2.9, WALL)
box(-HX+.4, -HY+.08, .9, HX-.4, -HY+.14, 2.9, GLASS)                             # shopfront glass
for x in np.linspace(-HX+.4, HX-.4, 7):                                          # mullions
    box(x-.05, -HY-.02, .9, x+.05, -HY+.3, 2.9, TRIM)
box(-HX+.4, -HY-.02, 1.9, HX-.4, -HY+.3, 1.97, TRIM)                             # transom
box(-.7, -HY-.04, .2, .7, -HY+.3, 2.9, GLASS); box(-.75, -HY-.06, .2, -.65, -HY+.32, 2.9, TRIM); box(.65, -HY-.06, .2, .75, -HY+.32, 2.9, TRIM)  # glass door
box(-.75, -HY-.06, 2.85, .75, -HY+.32, 2.95, TRIM); box(-.04, -HY-.08, .2, .04, -HY+.34, 2.9, TRIM)
# flat roof with green parapet and white trim
box(-HX-.2, -HY-.2, H, HX+.2, HY+.2, H+.25, DGREEN)
box(-HX-.2, -HY-.2, H+.25, HX+.2, -HY-.1, H+.7, GREEN); box(-HX-.2, HY+.1, H+.25, HX+.2, HY+.2, H+.7, GREEN)
box(-HX-.2, -HY-.2, H+.25, -HX-.1, HY+.2, H+.7, GREEN); box(HX+.1, -HY-.2, H+.25, HX+.2, HY+.2, H+.7, GREEN)
box(-HX-.25, -HY-.25, H+.7, HX+.25, HY+.25, H+.78, TRIM)
box(-HX-.25, -HY-.25, 3.0, HX+.25, -HY-.15, H, GREEN)                            # front fascia band
# sign board over the entrance (textured separately), pole-style golf ball on a tee on the roof
box(-3.0, -HY-.3, H+.8, 3.0, -HY-.1, H+2.0, DGREEN)
cyl(4.8, 0, H+.78, H+1.3, .05, TRIM, 8); ball(4.8, 0, H+1.55, .35, "#ffffff"); cyl(4.8, 0, H+1.2, H+1.3, .09, "#ffcc33", 8)
# awning over the windows (green/white stripes)
for k in range(10):
    x0 = -HX + k*1.2
    if x0+1.2 > -.9 and x0 < .9: continue
    hull = tm.convex.convex_hull(np.array([(x0, -HY, 3.0), (x0+1.2, -HY, 3.0), (x0, -HY-1.1, 2.55), (x0+1.2, -HY-1.1, 2.55),
                                           (x0, -HY, 2.95), (x0+1.2, -HY, 2.95), (x0, -HY-1.1, 2.5), (x0+1.2, -HY-1.1, 2.5)], float))
    col(hull, GREEN if k % 2 == 0 else TRIM)
# porch + steps
box(-HX, -HY-1.4, 0, HX, -HY, .12, "#c9c4b8"); box(-1.2, -HY-2.0, 0, 1.2, -HY-1.4, .06, "#c9c4b8")
# putting green in front with flag
box(-HX, -HY-6.5, 0, HX, -HY-1.4, .1, "#3aa14a"); box(-HX, -HY-6.5, .1, HX, -HY-6.4, .14, "#cfcfcf")
cyl(2.5, -HY-4.2, .1, .14, .22, "#1a1a1a", 20); cyl(2.5, -HY-4.2, .1, 2.3, .025, "#eeeeee", 8)
box(2.5, -HY-4.2, 1.8, 3.2, -HY-4.18, 2.3, "#e03030")
ball(1.3, -HY-3.2, .2, .08, "#ffffff"); ball(-2.0, -HY-5.0, .2, .08, "#ffffff")
# bunker
bk = tm.creation.cylinder(radius=1.3, height=.04, sections=24); bk.apply_translation([-3.2, -HY-3.8, .13]); col(bk, "#e8d9a0")
# golf bag stands by the door
for bx in (-2.2, -1.6):
    cyl(bx, -HY-1.0, .12, 1.0, .18, "#c0392b" if bx < -2 else "#2c5fa8", 12); cyl(bx, -HY-1.0, 1.0, 1.05, .2, "#222222", 12)
    for k in range(3): cyl(bx-.07+k*.07, -HY-1.0, 1.05, 1.5+k*.08, .018, "#cccccc", 6); ball(bx-.07+k*.07, -HY-1.0, 1.52+k*.08, .04, "#222222")
# interior: counter, club wall rack, shelves, ball display, mat
box(-3.5, 1.5, .22, 0.5, 2.5, 1.15, WOOD); box(-3.6, 1.4, 1.15, .6, 2.6, 1.22, "#3b3b3b")
box(-3.2, 1.7, 1.22, -2.6, 2.1, 1.5, "#222222")                                  # till
for i in range(7):                                                              # clubs on back wall
    x = -5 + i*1.1
    box(x-.04, HY-.35, 1.2, x+.04, HY-.25, 2.8, "#d8d8d8"); box(x-.12, HY-.4, 2.8, x+.12, HY-.25, 3.05, "#444444")
box(-5.5, HY-.45, 1.0, 5.5, HY-.25, 1.1, WOOD)
for sx in (-1, 1):                                                              # shelves with balls on side walls
    for z in (.8, 1.5, 2.2):
        box(sx*(HX-.25)-(.4 if sx > 0 else 0) + (0 if sx > 0 else .0), -2.0, z, sx*(HX-.25)+(0 if sx > 0 else .4), 2.0, z+.06, WOOD)
        for k in range(8):
            xx = sx*(HX-.5); ball(xx, -1.7+k*.5, z+.14, .07, ["#ffffff", "#ffe14d", "#ff7a2f"][k % 3])
box(2.0, 0.5, .22, 5.0, 2.5, .26, "#2f9e44")                                      # indoor putting mat
cyl(3.5, 1.5, .22, .27, .12, "#111111", 14)
# --- merge, Y-up
scene = tm.util.concatenate(P)
scene.apply_transform(RM(-np.pi/2, [1, 0, 0]))
fc = scene.visual.face_colors[:, :3]
sc = tm.Scene()
def sign_img():
    im = Image.new("RGB", (1200, 200), "#1f5f2b"); d = ImageDraw.Draw(im)
    d.rectangle([8, 8, 1191, 191], outline="white", width=6)
    try: f = ImageFont.truetype("arialbd.ttf", 120)
    except Exception: f = ImageFont.load_default()
    d.text((600, 100), "GOLF SHOP", font=f, fill="white", anchor="mm"); return im
for cc in np.unique(fc, axis=0):
    sel = np.where((fc == cc).all(1))[0]; m = scene.submesh([sel], append=True)
    hx = "#%02x%02x%02x" % tuple(cc)
    mat = tm.visual.material.PBRMaterial(baseColorFactor=[*cc, 255], metallicFactor=0.0, roughnessFactor=0.8)
    if hx == GLASS: mat.baseColorFactor = [*cc, 140]; mat.alphaMode = "BLEND"
    m.visual = tm.visual.TextureVisuals(uv=np.zeros((len(m.vertices), 2)), material=mat)
    sc.add_geometry(m, geom_name="col" + hx[1:])
# sign: dedicated textured quad on the sign board front face (Y-up: front = +Z)
q = tm.Trimesh(vertices=[[-2.9, H+.85, HY+.0], [2.9, H+.85, HY+.0], [2.9, H+1.95, HY+.0], [-2.9, H+1.95, HY+.0]], faces=[[0, 1, 2], [0, 2, 3]])
q.vertices = np.array([[-2.9, H+.85, HY+.31], [2.9, H+.85, HY+.31], [2.9, H+1.95, HY+.31], [-2.9, H+1.95, HY+.31]])
q.visual = tm.visual.TextureVisuals(uv=[[0, 0], [1, 0], [1, 1], [0, 1]], material=tm.visual.material.PBRMaterial(baseColorTexture=sign_img(), metallicFactor=0, roughnessFactor=.8))
sc.add_geometry(q, geom_name="sign")
out = pathlib.Path("projects/golf_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"golf_shop.glb"); sc.export(out/"golf_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
