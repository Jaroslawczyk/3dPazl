"""Shop (no cars/asphalt) -- was car & boat dealership (low-poly, Roblox-ready). Built Z-up in metres, exported Y-up. Run with .venv/Scripts/python.exe"""
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
box(-7.5, -4.5, 0, 7.5, 4.5, .2, "#b9a98d")                               # showroom floor
# showroom shell 15 x 9 x 4.4, front = -Y
WALL, TRIM = "#eceae4", "#2b2f3a"
box(-7.5, 4.2, .2, 7.5, 4.5, 4.4, WALL); box(-7.5, -4.5, .2, -7.2, 4.5, 4.4, WALL); box(7.2, -4.5, .2, 7.5, 4.5, 4.4, WALL)
box(-7.5, -4.5, 3.4, 7.5, -4.2, 4.4, WALL)                                # fascia
box(-7.5, -4.5, .2, -6.5, -4.2, 3.4, WALL); box(6.5, -4.5, .2, 7.5, -4.2, 3.4, WALL)
box(-6.5, -4.42, .2, -1.2, -4.3, 3.4, "#8fd3f4"); box(1.2, -4.42, .2, 6.5, -4.3, 3.4, "#8fd3f4")   # glass wall with a doorway
for i in (-3, -2, -1, 1, 2, 3): box(i*1.8-.05, -4.46, .2, i*1.8+.05, -4.28, 3.4, TRIM)
box(-1.3, -4.52, .2, -1.2, -4.2, 3.4, TRIM); box(1.2, -4.52, .2, 1.3, -4.2, 3.4, TRIM)   # door posts
# gable roof: two sloped slabs (26 deg, 0.25 thick) over the long sides, 0.6 overhang at the gable ends, vertical gable walls, ceiling
RZ, RH, OV, TH = 4.3, 2.44, 8.1, 0.25
for sy in (-1, 1):
    hullp([(-OV, sy*5.0, RZ), (OV, sy*5.0, RZ), (-OV, 0, RZ+RH), (OV, 0, RZ+RH),
           (-OV, sy*5.0, RZ-TH), (OV, sy*5.0, RZ-TH), (-OV, 0, RZ+RH-TH), (OV, 0, RZ+RH-TH)], "#a8472f")
hullp([(-OV-.05, 0, RZ+RH+.14), (OV+.05, 0, RZ+RH+.14), (-OV-.05, -.5, RZ+RH-.2), (OV+.05, -.5, RZ+RH-.2), (-OV-.05, .5, RZ+RH-.2), (OV+.05, .5, RZ+RH-.2)], "#7a4a2a")   # ridge cap
for gx in (-7.5, 7.2):
    hullp([(gx, -4.5, 4.4), (gx, 4.5, 4.4), (gx, 0, 6.55), (gx+0.3, -4.5, 4.4), (gx+0.3, 4.5, 4.4), (gx+0.3, 0, 6.55)], "#eceae4")
box(-7.5, -4.5, 4.2, 7.5, 4.5, 4.4, "#eceae4")                           # ceiling
# awning over the whole storefront: rainbow stripes + valance
RAIN = ["#ff3b3b", "#ffd23f", "#2ecc71", "#3498db", "#ff8a1f", "#a855f7"]
for k in range(14):
    x0 = -6.3 + k*0.9; cc = RAIN[k % 6]
    box(x0, -6.0, 3.2, x0+0.9, -4.3, 3.35, cc); box(x0, -6.06, 2.85, x0+0.9, -5.98, 3.35, cc)
# teal wainscot, orange band, bunting under the sign, flower planters
TEAL = "#1fb8a8"
box(-7.56, -4.56, 3.4, 7.56, -4.5, 3.6, "#ff7a1a")
for k in range(14):
    x = -6.0 + k*0.92; cc = RAIN[(k+2) % 6]
    hullp([(x-.32, -4.60, 4.4), (x+.32, -4.60, 4.4), (x, -4.60, 3.8), (x-.32, -4.46, 4.4), (x+.32, -4.46, 4.4), (x, -4.46, 3.8)], cc)
for sx in (-4.0, 4.0):
    box(sx-1.2, -5.35, .2, sx+1.2, -4.75, .75, "#e8743b"); box(sx-1.15, -5.3, .75, sx+1.15, -4.8, .9, "#2ecc71")
    for f in range(6): box(sx-1.0+f*.4, -5.2+(f % 2)*.1, .9, sx-.8+f*.4, -5.0+(f % 2)*.1, 1.25, ["#ff3b8f", "#ffd23f", "#ffffff"][f % 3] if False else ["#ff3b8f", "#ffd23f", "#ff8a1f"][f % 3])
# remove overlapping/coplanar faces (z-fighting): later parts win, earlier ones get the overlap cut out
solid, acc = [], None
for m in reversed(P):
    rgb = m.visual.face_colors[0].tolist()
    c = m if acc is None else tm.boolean.difference([m, acc], engine="manifold")
    if len(c.faces):
        c = c.copy(); c.visual.face_colors = rgb; solid.append(c)
    acc = m if acc is None else tm.boolean.union([acc, m], engine="manifold")
P[:] = solid
scene = tm.util.concatenate(P)
scene.apply_transform(RM(-np.pi/2, [1, 0, 0]))                              # Z-up -> Y-up
# ---------------- textures (procedural, tileable) ----------------
from PIL import Image, ImageDraw, ImageFont
rng = np.random.default_rng(7)
def noise(n, k=1):                                   # tileable smooth noise 0..1
    a = rng.random((n, n))
    for _ in range(k):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    a -= a.min(); return a / a.max()
def tint(base, n):                                   # base hex * (1 + noise)
    h = base.lstrip('#'); c = np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], float)
    return np.clip(c[None, None, :] * (1 + n[..., None]), 0, 255).astype(np.uint8)
N = 512
def tex_plaster(base):
    n = (noise(N, 3) - .5) * .10 + (noise(N, 1) - .5) * .04
    a = tint(base, n).astype(float)
    a[::128, :, :] *= .93                              # faint panel seams every 128 px
    a[:, ::128, :] *= .93
    return a.clip(0, 255).astype(np.uint8)
def tex_glass(base):
    y, x = np.mgrid[0:N, 0:N] / N
    d = (x + y) % 1.0
    streak = np.exp(-((d - .3) / .05) ** 2) * .5 + np.exp(-((d - .62) / .025) ** 2) * .3
    g = np.stack([np.full((N, N), v) for v in (120, 185, 225)], -1) * (0.85 + .15 * (1 - y)[..., None])
    return np.clip(g + streak[..., None] * 120, 0, 255).astype(np.uint8)
def tex_roof(base):
    n = (noise(N, 1) - .5) * .5 + (rng.random((N, N)) - .5) * .25
    return tint(base, n)
def tex_floor(base):
    a = tint(base, (noise(N, 2) - .5) * .12).astype(float)
    a[:6, :, :] *= .65; a[:, :6, :] *= .65                    # grout, 1 tile per texture
    return a.clip(0, 255).astype(np.uint8)
def tex_metal(base):
    n = (rng.random((N, N)) - .5) * .06 + (noise(N, 2) - .5) * .12
    return tint(base, np.tile(n[:, :1], (1, N)) * .6 + n * .4)
def tex_fabric(base):
    y, x = np.mgrid[0:N, 0:N]
    w = ((x // 4 + y // 4) % 2) * .06 + (rng.random((N, N)) - .5) * .05
    return tint(base, w - .03)
def tex_wood(base):
    y, x = np.mgrid[0:N, 0:N] / N
    g = np.sin((x * 14 + noise(N, 3) * 3) * 2 * np.pi) * .05 + (rng.random((N, N)) - .5) * .04
    return tint(base, g)
def tex_sign_blue(base):
    y = np.linspace(0, 1, N)[:, None] * np.ones((1, N))
    return tint(base, (0.1 - y * .25) + (noise(N, 2) - .5) * .03)
def icon_car(d, x, y, sc, c):          # (x, y) = bottom-left, sc ~ height 100*sc
    u = lambda px, py: (x + px*sc, y - py*sc)
    d.rounded_rectangle([*u(0, 40), *u(190, 10)], radius=12*sc, fill=c)
    d.polygon([u(35, 40), u(62, 78), u(130, 78), u(160, 40)], fill=c)
    d.polygon([u(48, 44), u(68, 72), u(95, 72), u(95, 44)], fill="#e9f7ff"); d.polygon([u(102, 44), u(102, 72), u(125, 72), u(146, 44)], fill="#e9f7ff")
    for cx in (45, 148):
        d.ellipse([*u(cx-20, 40), *u(cx+20, 0)], fill=c); d.ellipse([*u(cx-10, 30), *u(cx+10, 10)], fill="#e9f7ff")
def icon_boat(d, x, y, sc, c):
    u = lambda px, py: (x + px*sc, y - py*sc)
    d.polygon([u(0, 40), u(200, 40), u(170, 6), u(30, 6)], fill=c)                       # hull
    d.polygon([u(60, 40), u(80, 70), u(130, 70), u(145, 40)], fill=c)                    # cabin
    d.polygon([u(88, 44), u(96, 64), u(120, 64), u(126, 44)], fill="#e9f7ff")
    d.rectangle([*u(100, 100), *u(104, 70)], fill=c); d.polygon([u(104, 100), u(130, 90), u(104, 80)], fill=c)  # mast + flag
    d.line([u(10, -4), u(40, 2), u(80, -4), u(120, 2), u(160, -4), u(195, 2)], fill=c, width=int(5*sc))        # waves
def icon_heli(d, x, y, sc, c):
    u = lambda px, py: (x + px*sc, y - py*sc)
    d.ellipse([*u(40, 70), *u(130, 22)], fill=c)                                          # cabin
    d.polygon([u(120, 56), u(200, 62), u(200, 52), u(125, 38)], fill=c)                   # tail boom
    d.polygon([u(192, 52), u(206, 84), u(214, 80), u(204, 52)], fill=c)                   # fin
    d.polygon([u(52, 62), u(80, 62), u(80, 36), u(48, 34)], fill="#e9f7ff")               # window
    d.rectangle([*u(82, 80), *u(88, 70)], fill=c); d.rectangle([*u(0, 88), *u(190, 82)], fill=c)  # mast + rotor
    d.line([u(46, 14), u(130, 14)], fill=c, width=int(6*sc)); d.line([u(66, 24), u(64, 14)], fill=c, width=int(5*sc)); d.line([u(112, 24), u(114, 14)], fill=c, width=int(5*sc))
def tex_plate():
    W, H = 2048, 182
    im = Image.new("RGB", (W, H), "#bfe8ff"); dr = ImageDraw.Draw(im)
    for k in range(0, W, 64): dr.ellipse([k-30, 150, k+60, 215], fill="#ffffff")      # cloud line
    dr.rectangle([0, 0, W-1, H-1], outline="#ffd23f", width=10)
    sc = 1.45                                    # icons at both edges, centre left free
    icon_car(dr, 40, 150, sc, "#e53935");   icon_boat(dr, 340, 150, sc, "#ff8a1f")
    icon_heli(dr, 1440, 150, sc, "#1e9e4a"); icon_car(dr, 1760, 150, sc, "#8e44ad")
    return np.asarray(im)
def tex_tiles(base):
    a = np.zeros((N, N, 3), float); h = np.array([int(base[i:i+2], 16) for i in (1, 3, 5)], float)
    r, w = 8, N // 8                                           # 8 tile rows, 8 tiles per row, odd rows shifted
    for row in range(r):
        for k in range(8):
            x0 = (k * w + (w // 2 if row % 2 else 0)) % N
            sh = 1 + (rng.random() - .5) * .22
            for xx in range(w):
                a[row*w:(row+1)*w, (x0 + xx) % N] = h * sh * (0.78 + .22 * (np.arange(w)/w)[:, None])
    a[:, ::w // 1, :] *= .8; a[::w, :, :] *= .7
    return (a * (1 + (rng.random((N, N, 1)) - .5) * .06)).clip(0, 255).astype(np.uint8)
SPECIAL = {"#a8472f": ("tiles", tex_tiles, 1.0), "#8fd3f4": ("glass", tex_glass, 3.0), "#4a4f5c": ("roof", tex_roof, 1.5), "#b9a98d": ("floor", tex_floor, 1.0),
           "#2b2f3a": ("metal", tex_metal, 1.5), "#3a3f4b": ("metal", tex_metal, 1.5), "#1b4f9c": ("blue", tex_sign_blue, 2.0),
           "#d8262c": ("fabric", tex_fabric, 1.0), "#f5f5f5": ("fabric", tex_fabric, 1.0), "#eceae4": ("plaster", tex_plaster, 2.0),
           "#5b4636": ("wood", tex_wood, 1.0), "#8a6a4a": ("wood", tex_wood, 1.0), "#c8b79a": ("wood", tex_wood, 1.0)}
def uvs(m, scale, plate=False):
    m = m.copy(); m.unmerge_vertices()
    f, n, v = m.faces, m.face_normals, m.vertices
    uv = np.zeros((len(v), 2))
    for fi in range(len(f)):
        ax = int(np.argmax(np.abs(n[fi]))); a, b = [(2, 1), (0, 2), (0, 1)][ax]    # Y-up world: choose plane axes
        slope = n[fi][1] > .3 and abs(n[fi][2]) > .3
        for vi in f[fi]:
            if slope:
                uv[vi] = (v[vi][0] / 1.6, (v[vi][1] - 4.3) / 0.438 / 1.6); continue
            if plate:
                uv[vi] = ((v[vi][0] + 6.2) / 12.4, (v[vi][1] - 5.0) / 1.1) if ax == 2 and n[fi][2] > 0 else (0.01, 0.01)
            else:
                uv[vi] = (v[vi][a] / scale, v[vi][b] / scale)
    return m, uv
TEXDIR = pathlib.Path("textures/car_boat_shop")           # Cursor-made set: <n>.png, <n>_normal.png, <n>_orm.png
PBR = {"#8fd3f4": ("glass", "#7fe8ff"), "#a8472f": ("roof_shingles", None), "#b9a98d": ("floor_planks", None),
       "#2b2f3a": ("metal_dark", "#ff6b2c"), "#3a3f4b": ("metal_dark", "#ff6b2c"), "#1b4f9c": ("sign_blue", "#ff4f9a"),
       "#eceae4": ("wall_brick", None), "#1fb8a8": ("wall_plaster", "#1fb8a8"), "#ff7a1a": ("wall_plaster", "#ff7a1a"),
       "#5b4636": ("wood", "#c97b3a"), "#8a6a4a": ("wood", "#e0a050"), "#c8b79a": ("wood", "#f0c070"), "#e8743b": ("wood", "#e8743b")}
for _h in ["#ff3b3b", "#ffd23f", "#2ecc71", "#3498db", "#ff8a1f", "#a855f7"]: PBR[_h] = ("awning_fabric", _h)
def tint_img(img, hx):                                   # recolour a texture: keep its light/dark detail, replace the hue
    a = np.asarray(img, float) / 255.0; lum = a.mean(2); lum = lum / lum.mean() * 1.05
    c = np.array([int(hx[i:i+2], 16) for i in (1, 3, 5)], float) / 255.0
    return Image.fromarray((np.clip(lum[..., None] * c[None, None, :], 0, 1) * 255).astype(np.uint8))
def load_pbr(hx):
    n, tc = PBR.get(hx, (None, None))
    if not n or not (TEXDIR / f"{n}.png").exists(): return None
    g = lambda suf: Image.open(TEXDIR / f"{n}{suf}.png").convert("RGB")
    return (tint_img(g(""), tc) if tc else g("")), (g("_normal") if (TEXDIR / f"{n}_normal.png").exists() else None), (g("_orm") if (TEXDIR / f"{n}_orm.png").exists() else None)
def shape_mesh(m, name, img, uv, alpha=1.0, pbr=None):
    mat = tm.visual.material.PBRMaterial(baseColorTexture=Image.fromarray(img), baseColorFactor=[255, 255, 255, int(alpha * 255)],
                                          metallicFactor=0.0, roughnessFactor=0.85)
    if pbr:
        col, nrm, orm = pbr
        mat.baseColorTexture = col
        if nrm: mat.normalTexture = nrm
        if orm: mat.metallicRoughnessTexture = orm; mat.occlusionTexture = orm; mat.metallicFactor = 1.0; mat.roughnessFactor = 1.0
    if alpha < 1: mat.alphaMode = "BLEND"
    m.visual = tm.visual.TextureVisuals(uv=uv, material=mat); m.metadata["name"] = name; return m
fc = scene.visual.face_colors[:, :3]
sc = tm.Scene()
for cc in np.unique(fc, axis=0):
    hx = "#%02x%02x%02x" % tuple(cc)
    sel = np.where((fc == cc).all(1))[0]
    m = scene.submesh([sel], append=True)
    if hx == "#f6f6f6":
        m, uv = uvs(m, 1, plate=True); m = shape_mesh(m, "sign", tex_plate(), uv, pbr=load_pbr(hx))
    elif hx in SPECIAL:
        nm, fn, sz = SPECIAL[hx]; m, uv = uvs(m, sz)
        m = shape_mesh(m, nm + hx[1:], fn(hx), uv, alpha=0.55 if nm == "glass" else 1.0, pbr=load_pbr(hx))
    else:
        pb = load_pbr(hx); m, uv = uvs(m, 2.0 if PBR.get(hx, ("",))[0] == "wall_plaster" else 1.0)
        m = shape_mesh(m, "col" + hx[1:], tint(hx, (noise(N, 2) - .5) * .08), uv, pbr=pb)
    sc.add_geometry(m, geom_name=m.metadata["name"])
out = pathlib.Path("projects/car_boat_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"car_boat_shop.glb"); sc.export(out/"car_boat_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
