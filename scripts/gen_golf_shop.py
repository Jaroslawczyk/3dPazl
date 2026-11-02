"""Golf shop v2 (Roblox-ready, textured, ~2.5k tris, empty interior, like zina/tech shop): brick-base cottage with gable roof, striped awning, sign, putting green, cart. Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_golf_shop.py"""
import numpy as np, trimesh as tm, pathlib
from trimesh.transformations import rotation_matrix as RM, translation_matrix as TM
P = []
def col(m, hexc):
    h = hexc.lstrip('#'); rgb = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    m.visual.face_colors = rgb + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def hullp(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)
def cyl(x, y, z0, z1, r, c, n=10):
    m = tm.creation.cylinder(radius=r, height=z1-z0, sections=n); m.apply_translation([x, y, (z0+z1)/2]); return col(m, c)
def ball(x, y, z, r, c, sub=1):
    m = tm.creation.icosphere(subdivisions=sub, radius=r); m.apply_translation([x, y, z]); return col(m, c)
def wall(mk, a0, a1, ops, z0=0.2, z1=3.4):          # wall along one axis with openings [(a0, a1, z0, z1)]
    cuts = sorted({a0, a1, *[o[i] for o in ops for i in (0, 1)]})
    for s, e in zip(cuts, cuts[1:]):
        o = next((o for o in ops if o[0] <= s and e <= o[1]), None)
        if o is None: mk(s, e, z0, z1)
        else:
            if o[2] > z0: mk(s, e, z0, o[2])
            if o[3] < z1: mk(s, e, o[3], z1)

WALL, BRICK, ROOF, TRIM, DOOR, WOOD, DECK, STONE, GRASS, GREEN2, SAND, GLASS, DARK = "#ffeaa0", "#c8553d", "#d8402f", "#ffffff", "#7ed321", "#8a6a4a", "#a8763e", "#c9c4b8", "#3f9142", "#5cc760", "#e8d9a0", "#8fd3f4", "#2b2f3a"
HX, HY, H = 5.0, 3.5, 3.4                      # shop 10 x 7 m, walls 3.4 m, front = -Y
box(-HX, -HY, 0, HX, HY, .2, DECK)                                                # floor
BW = 1.0                                                                          # brick plinth height
WIN = (-4.0, -0.9, 1.1, 2.6); DR = (1.0, 2.2, 0.2, 2.6); WIN2 = (3.0, 4.2, 1.1, 2.4)
def fw(a, b, z0, z1):                                                             # front wall piece: brick below BW, plaster above
    if z0 < BW: box(a, -HY, z0, b, -HY+.25, min(z1, BW), BRICK)
    if z1 > BW: box(a, -HY, max(z0, BW), b, -HY+.25, z1, WALL)
wall(fw, -HX, HX, [WIN, DR, WIN2])
box(-HX, HY-.25, .2, HX, HY, BW, BRICK); box(-HX, HY-.25, BW, HX, HY, H, WALL)    # back wall
SWN = [(-1.2, 1.2, 1.1, 2.4)]
for sx in (-1, 1):                                                                # side walls with one window each
    def sw(a, b, z0, z1, sx=sx):
        x0, x1 = (sx*HX-.25, sx*HX) if sx > 0 else (sx*HX, sx*HX+.25)
        if z0 < BW: box(x0, a, z0, x1, b, min(z1, BW), BRICK)
        if z1 > BW: box(x0, a, max(z0, BW), x1, b, z1, WALL)
    wall(sw, -HY, HY, SWN)
    gx = sx*HX - (.12 if sx > 0 else -.12)
    box(gx-.04, -1.2, 1.1, gx+.04, 1.2, 2.4, GLASS)
    for y0, y1, z0, z1 in [(-1.3, -1.2, 1.0, 2.5), (1.2, 1.3, 1.0, 2.5), (-1.3, 1.3, 1.0, 1.1), (-1.3, 1.3, 2.4, 2.5), (-.03, .03, 1.1, 2.4)]:
        box(sx*HX-(.2 if sx > 0 else 0), y0, z0, sx*HX+(0 if sx > 0 else .2), y1, z1, TRIM)
for (a0, a1, z0, z1) in (WIN, WIN2):                                              # front windows: glass, white frame, mullions, sill
    box(a0, -HY+.08, z0, a1, -HY+.16, z1, GLASS)
    for (p0, p1, q0, q1) in [(a0-.1, a0, z0-.1, z1+.1), (a1, a1+.1, z0-.1, z1+.1), (a0-.1, a1+.1, z0-.1, z0), (a0-.1, a1+.1, z1, z1+.1)]:
        box(p0, -HY-.06, q0, p1, -HY+.25, q1, TRIM)
    box(a0-.15, -HY-.2, z0-.14, a1+.15, -HY, z0-.04, TRIM)
    n = max(1, int((a1-a0)/1.0))
    for k in range(1, n): mx = a0+(a1-a0)*k/n; box(mx-.03, -HY-.02, z0, mx+.03, -HY+.2, z1, TRIM)
    hz = z0+(z1-z0)*.6; box(a0, -HY-.02, hz-.03, a1, -HY+.2, hz+.03, TRIM)
# gable roof (ridge along X): two slabs, ridge cap, gable triangles, ceiling, brick chimney
RZ, RIDGE, OV, EV, TH = 3.15, 1.9, 5.6, 4.2, .25
for sy in (-1, 1):
    hullp([(-OV, sy*EV, RZ), (OV, sy*EV, RZ), (-OV, 0, RZ+RIDGE), (OV, 0, RZ+RIDGE),
           (-OV, sy*EV, RZ-TH), (OV, sy*EV, RZ-TH), (-OV, 0, RZ+RIDGE-TH), (OV, 0, RZ+RIDGE-TH)], ROOF)
hullp([(-OV-.05, 0, RZ+RIDGE+.14), (OV+.05, 0, RZ+RIDGE+.14), (-OV-.05, -.5, RZ+RIDGE-.2), (OV+.05, -.5, RZ+RIDGE-.2), (-OV-.05, .5, RZ+RIDGE-.2), (OV+.05, .5, RZ+RIDGE-.2)], "#8f1f1a")
for gx in (-HX, HX-.25):
    hullp([(gx, -HY, H), (gx, HY, H), (gx, 0, RZ+RIDGE-.15), (gx+.25, -HY, H), (gx+.25, HY, H), (gx+.25, 0, RZ+RIDGE-.15)], WALL)
box(-HX, -HY, H-.2, HX, HY, H, WALL)
# decorations: awning, porch with posts, roof sign, flag, welcome green, tee-ball, gold band, chimney
for k in range(7):
    x0 = -4.1 + k*.5; cc = "#7ed321" if k % 2 == 0 else "#f5f5f5"
    hullp([(x0, -HY, 2.85), (x0+.5, -HY, 2.85), (x0, -HY-1.0, 2.4), (x0+.5, -HY-1.0, 2.4),
           (x0, -HY, 2.8), (x0+.5, -HY, 2.8), (x0, -HY-1.0, 2.35), (x0+.5, -HY-1.0, 2.35)], cc)
box(-4.15, -HY-1.05, 2.3, -.85, -HY-.95, 2.4, "#ffffff")                                 # awning front valance
box(-HX-.05, -HY-.05, 2.75, HX+.05, -HY+.3, 2.95, "#ffd23f"); box(-HX-.05, HY-.3, 2.75, HX+.05, HY+.05, 2.95, "#ffd23f")   # gold band under the eaves
box(-.05-HX, -HY-.05, 2.75, -HX+.3, HY+.05, 2.95, "#ffd23f"); box(HX-.3, -HY-.05, 2.75, HX+.05, HY+.05, 2.95, "#ffd23f")
box(-3.8, .8, H, -3.2, 1.4, 5.6, BRICK); box(-3.9, .7, 5.6, -3.1, 1.5, 5.75, DARK)      # chimney
box(-2.4, -.15, RZ+RIDGE-.1, -2.3, .15, RZ+RIDGE+.3, "#ffffff"); box(1.5, -.15, RZ+RIDGE-.1, 1.6, .15, RZ+RIDGE+.3, "#ffffff")   # roof sign posts
box(-2.5, -.12, RZ+RIDGE+.3, 1.7, -.02, RZ+RIDGE+1.5, "#ff8a1f")                          # plain orange roof sign
cyl(-4.4, 0, RZ+RIDGE, RZ+RIDGE+1.9, .03, "#eeeeee", 6); box(-4.4, 0, RZ+RIDGE+1.35, -3.6, .02, RZ+RIDGE+1.85, "#e03030")   # flag
cyl(3.8, 0, RZ+RIDGE+.1, RZ+RIDGE+.7, .09, "#ffcc33", 8); ball(3.8, 0, RZ+RIDGE+1.1, .55, "#ffffff", 1)   # giant golf ball on a tee
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
    W, H = 2048, 680
    im = Image.new("RGB", (W, H), "#1b3f8f"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W-1, H-1], outline="#ffffff", width=22); dr.rectangle([46, 46, W-47, H-47], outline="#ffd23f", width=8)
    f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 330); t = "GOLF"
    bb = dr.textbbox((0, 0), t, font=f); x, y = (W-(bb[2]-bb[0]))//2 - bb[0], 60 - bb[1]
    dr.text((x+8, y+8), t, font=f, fill="#0b1f55"); dr.text((x, y), t, font=f, fill="#ffffff")
    f2 = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 150); t2 = "PRO SHOP"
    bb = dr.textbbox((0, 0), t2, font=f2); x = (W-(bb[2]-bb[0]))//2 - bb[0]
    dr.text((x, 440-bb[1]), t2, font=f2, fill="#ffd23f")
    for cx in (200, W-200): dr.ellipse([cx-90, 250, cx+90, 430], fill="#f4f4f4", outline="#bbbbbb", width=5); dr.polygon([(cx-9, 430), (cx+9, 430), (cx, 530)], fill="#ffd23f")
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
    a[(y % h) < 5] *= .5; a[(x + sh) % N < 5] *= .6
    return a.clip(0, 255).astype(np.uint8)
def tex_brick(base):                                  # running-bond bricks with light mortar
    y, x = np.mgrid[0:N, 0:N]; bh, bw = N // 8, N // 4
    row = y // bh; xs = (x + (row % 2) * bw // 2) % bw
    a = tint(base, (rng.random((N, N)) - .5) * .12 + (noise(N, 2) - .5) * .1).astype(float)
    m = (y % bh < 3) | (xs < 3); a[m] = [200, 190, 175]
    return a.clip(0, 255).astype(np.uint8)
def pbr_boards(base):                                  # horizontal cut boards with staggered butt joints: colour + normal + ORM (1024 px, tileable)
    n = 1024; nr = 8; hr = n // nr
    y, x = np.mgrid[0:n, 0:n]; ri = y // hr; v = (y % hr) / hr
    d = np.zeros((n, n)); tone = np.zeros((n, n))
    for r in range(nr):
        cuts = (rng.integers(0, n) + np.array([0, rng.integers(380, 640)])) % n    # 2 long boards per row, uneven
        xs = np.arange(n)[:, None]; rel = (xs - cuts[None, :]) % n
        k = rel.argmin(1); nxt = (cuts[None, :] - xs) % n; dd = np.minimum(rel.min(1), nxt.min(1))
        tv = (rng.random(len(cuts)) - .5) * .16
        d[r*hr:(r+1)*hr, :] = dd[None, :]; tone[r*hr:(r+1)*hr, :] = tv[k][None, :]
    st = np.tile(rng.random((n, 1)), (1, n)); st = (st + np.roll(st, 1, 0) + np.roll(st, -1, 0)) / 3     # horizontal grain streaks
    st = st * .6 + noise(n, 3) * .4
    for _ in range(3): st = (st + np.roll(st, 1, 0) + np.roll(st, -1, 0) + np.roll(st, 1, 1) + np.roll(st, -1, 1)) / 5
    e = np.minimum(np.minimum(v, 1 - v) * hr, d)                                                          # px to nearest board edge
    h = np.clip(e / 9, 0, 1) ** .6 * .7 + st * .25
    dark = np.zeros((n, n))
    for _ in range(9):                                                                                       # knots
        cx, cy, r = rng.integers(0, n), rng.integers(0, n), rng.integers(14, 30)
        dk = np.hypot((x - cx + n/2) % n - n/2, ((y - cy + n/2) % n - n/2)) 
        h += np.exp(-(dk / r) ** 2) * .25 * np.sin(dk / 2.5); dark += np.exp(-(dk / (r * .6)) ** 2) * .35
    a = tint(base, tone + (st - .5) * .22 + (noise(n, 2) - .5) * .12 - dark).astype(float)
    a *= (.55 + .45 * np.clip(e / 4, 0, 1))[..., None]                                                      # dark gaps
    wear = (noise(n, 4) > .72) * (noise(n, 1) * .5)                                                         # paint wear -> bare wood
    a = a * (1 - wear[..., None]) + wear[..., None] * np.array([170, 130, 85.])
    for _ in range(3): h = (h + np.roll(h, 1, 0) + np.roll(h, -1, 0) + np.roll(h, 1, 1) + np.roll(h, -1, 1)) / 5     # soften: no sparkle when moving
    s_ = 5.0
    nx = -(np.roll(h, -1, 1) - np.roll(h, 1, 1)) * s_; ny = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * s_
    nz = np.ones_like(nx); l = np.sqrt(nx**2 + ny**2 + nz**2)
    nrm = np.stack([nx / l, ny / l, nz / l], -1) * .5 + .5
    orm = np.stack([.55 + .45 * np.clip(h, 0, 1), np.clip(.78 + wear * .2 - st * .1, 0, 1), np.zeros((n, n))], -1)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)), Image.fromarray((nrm * 255).astype(np.uint8)), Image.fromarray((orm * 255).astype(np.uint8))
PROC_PBR = {}
def tex_grass(base):
    n = (noise(N, 2) - .5) * .18 + (rng.random((N, N)) - .5) * .12
    return tint(base, n)
SPECIAL = {"#8fd3f4": ("glass", tex_glass, 3.0), "#a8763e": ("floor", tex_floorboards, 2.0), "#2b2f3a": ("metal", tex_metal, 1.5), "#c8553d": ("brick", tex_brick, 1.5),
           "#d8402f": ("shingles", tex_tiles, 1.0), "#ffeaa0": ("plaster", tex_plaster, 2.0), "#ffffff": ("plaster", tex_plaster, 2.0), "#8f1f1a": ("plaster", tex_plaster, 2.0),
           "#7ed321": ("wood", tex_wood, 1.0), "#f5f5f5": ("fabric", tex_fabric, 1.0), "#c0392b": ("fabric", tex_fabric, 1.0), "#2f5fa8": ("fabric", tex_fabric, 1.0),
           "#8a6a4a": ("wood", tex_wood, 1.0), "#c9c4b8": ("floor", tex_floor, 1.5), "#3f9142": ("grass", tex_grass, 1.5), "#5cc760": ("grass", tex_grass, 1.5),
           "#e8d9a0": ("sand", tex_roof, 1.0), "#ffd23f": ("fabric", tex_fabric, 1.0), "#5cc760": ("grass", tex_grass, 1.5), "#2e7d32": ("grass", tex_grass, 1.5)}
def uvs(m, scale, plate=False):
    m = m.copy(); m.unmerge_vertices()
    f, n, v = m.faces, m.face_normals, m.vertices
    uv = np.zeros((len(v), 2)); bn = m.bounds
    for fi in range(len(f)):
        ax = int(np.argmax(np.abs(n[fi]))); a, b = [(2, 1), (0, 2), (0, 1)][ax]    # Y-up world: choose plane axes
        slope = n[fi][1] > .3 and abs(n[fi][2]) > .3
        for vi in f[fi]:
            if slope:
                uv[vi] = (v[vi][0] / 1.6, (v[vi][1] - 3.15) * 2.2 / 1.6); continue
            if plate:
                uv[vi] = ((v[vi][0]-bn[0][0])/(bn[1][0]-bn[0][0]), (v[vi][1]-bn[0][1])/(bn[1][1]-bn[0][1])) if ax == 2 and n[fi][2] > 0 else (0.01, 0.01)
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
out = pathlib.Path("projects/golf_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"golf_shop.glb"); sc.export(out/"golf_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
