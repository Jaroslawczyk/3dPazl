"""Aunt Zina's village grocery shop (Roblox-ready, empty interior). Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_zina_shop.py"""
import numpy as np, trimesh as tm, pathlib
from trimesh.transformations import rotation_matrix as RM, translation_matrix as TM
P = []
def col(m, hexc):
    h = hexc.lstrip('#'); rgb = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    m.visual.face_colors = rgb + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def hullp(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)

WALL, TEAL, WOOD, PALE, RED, WHITE = "#f0cf8a", "#f4f1e8", "#8a6a4a", "#c8b79a", "#2f5fa8", "#f5f5f5"   # warm cream planks, white trim, blue-white awning
HX, HY, H = 4.0, 3.0, 3.4            # shop 8 x 6 m, walls 3.4 m, front = -Y
def wall(mk, a0, a1, ops, z0=0.2, z1=H):          # wall along one axis with openings [(a0, a1, z0, z1)]
    cuts = sorted({a0, a1, *[o[i] for o in ops for i in (0, 1)]})
    for s, e in zip(cuts, cuts[1:]):
        o = next((o for o in ops if o[0] <= s and e <= o[1]), None)
        if o is None: mk(s, e, z0, z1)
        else:
            if o[2] > z0: mk(s, e, z0, o[2])
            if o[3] < z1: mk(s, e, o[3], z1)
def frame(mk, a0, a1, z0, z1, t=0.1, d=0.14):      # teal frame round an opening (mk(a0, a1, z0, z1, depth_out))
    mk(a0-t, a0, z0-t, z1+t); mk(a1, a1+t, z0-t, z1+t); mk(a0-t, a1+t, z0-t, z0); mk(a0-t, a1+t, z1, z1+t)
box(-HX, -HY, 0, HX, HY, .2, "#a8763e")                                        # floor slab (wood planks)
DOOR, WIN, WINL = (-1.9, -0.7, 0.2, 2.2), (0.3, 3.3, 0.95, 2.2), (-3.4, -2.4, 0.95, 2.2)
wall(lambda a, b, z0, z1: box(a, -HY, z0, b, -HY+.25, z1, WALL), -HX, HX, [DOOR, WIN, WINL])      # front wall
box(-HX, HY-.25, .2, HX, HY, H, WALL)                                                              # back wall
SW = (0.3, 1.9, 0.95, 2.2)
for sx in (-1, 1):                                                                                  # side walls with a window each
    wall(lambda a, b, z0, z1, sx=sx: box(sx*HX-(.25 if sx > 0 else 0), a, z0, sx*HX+(0 if sx > 0 else .25), b, z1, WALL), -HY, HY, [SW])
    wx0, wx1 = (HX-.15, HX-.05) if sx > 0 else (-HX+.05, -HX+.15)
    box(wx0, SW[0], SW[2], wx1, SW[1], SW[3], "#8fd3f4")
    for y0, y1, z0, z1 in [(SW[0]-.1, SW[0], SW[2]-.1, SW[3]+.1), (SW[1], SW[1]+.1, SW[2]-.1, SW[3]+.1), (SW[0]-.1, SW[1]+.1, SW[2]-.1, SW[2]), (SW[0]-.1, SW[1]+.1, SW[3], SW[3]+.1)]:
        box(sx*HX-.14 if sx < 0 else HX-.25-.0, y0, z0, sx*HX+.0 if sx < 0 else HX+.14, y1, z1, TEAL)
# front windows: glass + teal frames + muntins, sill planks with flower boxes
for (a0, a1, z0, z1) in (WIN, WINL):
    box(a0, -HY+.08, z0, a1, -HY+.16, z1, "#8fd3f4")
    frame(lambda a, b, c, d: box(a, -HY-.06, c, b, -HY+.25, d, TEAL), a0, a1, z0, z1)
    box(a0-.15, -HY-.2, z0-.14, a1+.15, -HY, z0-.04, PALE)                       # sill
    box(a0, -HY-.4, z0-.5, a1, -HY-.1, z0-.14, WOOD)                             # flower box
    n = int((a1-a0)/.3)
    for k in range(n): box(a0+.05+k*.3, -HY-.35+(k % 2)*.08, z0-.14, a0+.25+k*.3, -HY-.15+(k % 2)*.08, z0+.12+(k % 3)*.04, ["#ff3b8f", "#ffd23f", "#ff8a1f", "#ffffff"][k % 4])
box(1.75, -HY+.08, WIN[2], 1.85, -HY+.16, WIN[3], TEAL)                          # muntin of the big window
box(WIN[0], -HY+.08, 1.55, WIN[1], -HY+.16, 1.62, TEAL)
frame(lambda a, b, c, d: box(a, -HY-.06, c, b, -HY+.25, d, TEAL), DOOR[0], DOOR[1], DOOR[2]+.0, DOOR[3])
box(DOOR[0]-.14, -HY-.1, 2.2, DOOR[1]+.14, -HY, 2.3, PALE)                       # door pediment
# porch: two steps + small lamp
box(-2.2, -HY-.6, 0, -.4, -HY, .1, WOOD); box(-2.1, -HY-.35, .1, -.5, -HY, .2, PALE)
# striped awning over the big window
for k in range(6):
    x0 = .1 + k*.55; cc = RED if k % 2 == 0 else WHITE
    hullp([(x0, -HY, 2.4), (x0+.55, -HY, 2.4), (x0, -HY-.95, 2.0), (x0+.55, -HY-.95, 2.0),
           (x0, -HY, 2.35), (x0+.55, -HY, 2.35), (x0, -HY-.95, 1.95), (x0+.55, -HY-.95, 1.95)], cc)
    box(x0, -HY-1.0, 1.72, x0+.55, -HY-.95, 2.0, cc)
# gable roof: slabs (eave y=+-3.7), ridge cap, vertical gable walls, ceiling, chimney
RZ, RIDGE, OV, EV, TH = 3.15, 2.0, 4.5, 3.7, .25
for sy in (-1, 1):
    hullp([(-OV, sy*EV, RZ), (OV, sy*EV, RZ), (-OV, 0, RZ+RIDGE), (OV, 0, RZ+RIDGE),
           (-OV, sy*EV, RZ-TH), (OV, sy*EV, RZ-TH), (-OV, 0, RZ+RIDGE-TH), (OV, 0, RZ+RIDGE-TH)], "#b5532f")
hullp([(-OV-.05, 0, RZ+RIDGE+.14), (OV+.05, 0, RZ+RIDGE+.14), (-OV-.05, -.5, RZ+RIDGE-.2), (OV+.05, -.5, RZ+RIDGE-.2), (-OV-.05, .5, RZ+RIDGE-.2), (OV+.05, .5, RZ+RIDGE-.2)], "#7a4a2a")
for gx in (-HX, HX-.25):
    hullp([(gx, -HY, H), (gx, HY, H), (gx, 0, RZ+RIDGE-.15), (gx+.25, -HY, H), (gx+.25, HY, H), (gx+.25, 0, RZ+RIDGE-.15)], WALL)
box(-HX, -HY, H-.2, HX, HY, H, WALL)                                              # ceiling
box(2.4, .9, H, 3.0, 1.5, 5.9, "#9c4a38"); box(2.3, .8, 5.9, 3.1, 1.6, 6.05, "#3a3f4b")  # chimney + cap
# outside: crates with apples/cabbages
for i, (cx, cy) in enumerate([(-3.5, -3.9), (-3.5, -3.15)]):
    box(cx-.4, cy-.3, 0, cx+.4, cy+.3, .45, PALE)
    for k in range(6): box(cx-.33+(k % 3)*.23, cy-.2+(k // 3)*.22, .45, cx-.13+(k % 3)*.23, cy-.0+(k // 3)*.22, .62, ["#d8262c", "#6bbf3a", "#ff8a1f"][(k+i) % 3])
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
def tex_plate():
    W, H = 2048, 190
    im = Image.new("RGB", (W, H), "#fff3d6"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W-1, H-1], outline="#b3261e", width=12); dr.rectangle([22, 22, W-23, H-23], outline="#1f7a4d", width=5)
    f = ImageFont.truetype("C:/Windows/Fonts/comicbd.ttf", 118); t = "МАГАЗИНЧИК ТЁТИ ЗИНЫ"
    bb = dr.textbbox((0, 0), t, font=f); tw, th = bb[2]-bb[0], bb[3]-bb[1]
    x, y = (W-tw)//2 - bb[0], (H-th)//2 - bb[1]
    dr.text((x+5, y+5), t, font=f, fill="#d9b98a"); dr.text((x, y), t, font=f, fill="#b3261e")
    for cx in (95, W-95):                                                              # apples at both ends
        dr.ellipse([cx-34, 85, cx+34, 153], fill="#d8262c"); dr.polygon([(cx, 88), (cx+22, 52), (cx+34, 62), (cx+6, 92)], fill="#2f8f3a")
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
def tex_boards(base):                                  # vertical painted planks with dark gaps
    y, x = np.mgrid[0:N, 0:N]; w = N // 8
    a = tint(base, (noise(N, 2) - .5) * .10 + (rng.random((N, N)) - .5) * .04 + np.sin(x * .5 + noise(N, 3) * 6) * .02).astype(float)
    a *= (0.93 + 0.07 * ((x % w) / w))[..., None]; a[:, ::w, :] *= .55
    return a.clip(0, 255).astype(np.uint8)
def tex_floorboards(base):                            # horizontal wooden planks, staggered joints, grain
    y, x = np.mgrid[0:N, 0:N]; h = N // 6
    row = y // h; sh = ((row * 97) % N)
    a = tint(base, (noise(N, 2) - .5) * .10 + np.sin(((x + sh) * .05) + noise(N, 3) * 5) * .05 + (row % 3 - 1) * .05).astype(float)
    a[::h, :, :] *= .5; a[(x + sh) % N < 3] *= .6
    return a.clip(0, 255).astype(np.uint8)
def tex_brick(base):                                  # running-bond bricks with light mortar
    y, x = np.mgrid[0:N, 0:N]; bh, bw = N // 8, N // 4
    row = y // bh; xs = (x + (row % 2) * bw // 2) % bw
    a = tint(base, (rng.random((N, N)) - .5) * .12 + (noise(N, 2) - .5) * .1).astype(float)
    m = (y % bh < 3) | (xs < 3); a[m] = [200, 190, 175]
    return a.clip(0, 255).astype(np.uint8)
def pbr_boards(base):                                  # realistic painted planks: colour + normal + ORM (1024 px, tileable)
    n = 1024; nb = 8; w = n // nb
    y, x = np.mgrid[0:n, 0:n]; bi = x // w; u = (x % w) / w
    tone = (rng.random(nb) - .5) * .14
    st = np.tile(rng.random((1, n)), (n, 1)); st = (st + np.roll(st, 1, 1) + np.roll(st, -1, 1)) / 3     # vertical grain streaks
    st = st * .6 + noise(n, 3) * .4
    h = np.clip(np.minimum(u, 1 - u) / .07, 0, 1) ** .6 * .7 + st * .25
    dark = np.zeros((n, n))
    for _ in range(9):                                                                                       # knots
        cx, cy, r = rng.integers(0, n), rng.integers(0, n), rng.integers(14, 30)
        d = np.hypot((x - cx + n/2) % n - n/2, ((y - cy + n/2) % n - n/2) * .7)
        h += np.exp(-(d / r) ** 2) * .25 * np.sin(d / 2.5); dark += np.exp(-(d / (r * .6)) ** 2) * .35
    a = tint(base, tone[bi] + (st - .5) * .22 + (noise(n, 2) - .5) * .12 - dark).astype(float)
    a *= (.35 + .65 * np.clip(np.minimum(u, 1 - u) / .05, 0, 1))[..., None]                                 # dark gaps
    wear = (noise(n, 4) > .72) * (noise(n, 1) * .5)                                                         # paint wear -> bare wood
    a = a * (1 - wear[..., None]) + wear[..., None] * np.array([170, 130, 85.])
    s_ = 7.0; hh = h * 1.0
    nx = -(np.roll(hh, -1, 1) - np.roll(hh, 1, 1)) * s_; ny = (np.roll(hh, -1, 0) - np.roll(hh, 1, 0)) * s_
    nz = np.ones_like(nx); l = np.sqrt(nx**2 + ny**2 + nz**2)
    nrm = np.stack([nx / l, ny / l, nz / l], -1) * .5 + .5
    orm = np.stack([.55 + .45 * np.clip(h, 0, 1), np.clip(.78 + wear * .2 - st * .1, 0, 1), np.zeros((n, n))], -1)
    im = lambda arr: Image.fromarray((np.clip(arr, 0, 255 if arr.max() > 1.5 else 1) * (1 if arr.max() > 1.5 else 255)).astype(np.uint8))
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)), Image.fromarray((nrm * 255).astype(np.uint8)), Image.fromarray((orm * 255).astype(np.uint8))
PROC_PBR = {"#f0cf8a": pbr_boards}
SPECIAL = {"#b5532f": ("shingles", tex_tiles, 1.0), "#8fd3f4": ("glass", tex_glass, 3.0), "#a8763e": ("floor", tex_floorboards, 2.0), "#9c4a38": ("brick", tex_brick, 1.5),
           "#2b2f3a": ("metal", tex_metal, 1.5), "#3a3f4b": ("metal", tex_metal, 1.5), "#2f5fa8": ("fabric", tex_fabric, 1.0),
           "#f5f5f5": ("fabric", tex_fabric, 1.0), "#f4f1e8": ("plaster", tex_plaster, 2.0), "#f0cf8a": ("boards", tex_boards, 2.0),
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
                uv[vi] = (v[vi][0] / 1.6, (v[vi][1] - 3.15) / 0.438 / 1.6); continue
            if plate:
                uv[vi] = ((v[vi][0] + 3.5) / 7.0, (v[vi][1] - 2.5) / 0.65) if ax == 2 and n[fi][2] > 0 else (0.01, 0.01)
            else:
                uv[vi] = (v[vi][a] / scale, v[vi][b] / scale)
    return m, uv
TEXDIR = pathlib.Path("textures/car_boat_shop")           # Cursor-made set: <n>.png, <n>_normal.png, <n>_orm.png
PBR = {}                                             # procedural textures only (own look, not the dealership set)
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
        pb = PROC_PBR[hx](hx) if hx in PROC_PBR else load_pbr(hx)
        m = shape_mesh(m, nm + hx[1:], np.asarray(pb[0]) if hx in PROC_PBR else fn(hx), uv, alpha=0.55 if nm == "glass" else 1.0, pbr=pb)
    else:
        pb = load_pbr(hx); m, uv = uvs(m, 2.0 if PBR.get(hx, ("",))[0] == "wall_plaster" else 1.0)
        m = shape_mesh(m, "col" + hx[1:], tint(hx, (noise(N, 2) - .5) * .08), uv, pbr=pb)
    sc.add_geometry(m, geom_name=m.metadata["name"])
out = pathlib.Path("projects/zina_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"zina_shop.glb"); sc.export(out/"zina_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
