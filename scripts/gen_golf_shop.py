"""Golf shop (Roblox-ready: ~2k tris, tileable textured materials, empty interior, like zina/tech shop). Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_golf_shop.py"""
import numpy as np, trimesh as tm, pathlib
from trimesh.transformations import rotation_matrix as RM, translation_matrix as TM
P = []
def col(m, hexc):
    h = hexc.lstrip('#'); rgb = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    m.visual.face_colors = rgb + [255]; P.append(m); return m
def box(x0, y0, z0, x1, y1, z1, c):
    m = tm.creation.box([x1-x0, y1-y0, z1-z0]); m.apply_translation([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]); return col(m, c)
def hullp(pts, c): return col(tm.convex.convex_hull(np.array(pts, float)), c)
def cyl(x, y, z0, z1, r, c, n=12):
    m = tm.creation.cylinder(radius=r, height=z1-z0, sections=n); m.apply_translation([x, y, (z0+z1)/2]); return col(m, c)

WALL, TRIM, GREEN, DGREEN, GLASS, WOOD, STONE, GRASS, SAND = "#f3efe2", "#fafafa", "#2e8b3d", "#1f5f2b", "#8fd3f4", "#8a6a4a", "#c9c4b8", "#3aa14a", "#e8d9a0"
HX, HY, H = 6.0, 4.5, 3.8                      # shop 12 x 9 m, walls 3.8 m, front = -Y
box(-HX-.3, -HY-.3, 0, HX+.3, HY+.3, .2, "#a8763e")                              # floor slab (wood planks)
box(-HX, HY-.25, .2, HX, HY, H, WALL)                                            # back wall
box(-HX, -HY, .2, -HX+.25, HY, H, WALL); box(HX-.25, -HY, .2, HX, HY, H, WALL)   # side walls
box(-HX, -HY, .2, HX, -HY+.25, .9, WALL); box(-HX, -HY, 2.9, HX, -HY+.25, H, WALL)   # front knee wall + header
box(-HX, -HY-.05, .9, -HX+.4, -HY+.3, 2.9, WALL); box(HX-.4, -HY-.05, .9, HX, -HY+.3, 2.9, WALL)
box(-HX+.4, -HY+.08, .9, HX-.4, -HY+.14, 2.9, GLASS)                             # shopfront glass
for x in np.linspace(-HX+.4, HX-.4, 7): box(x-.05, -HY-.02, .9, x+.05, -HY+.3, 2.9, TRIM)   # mullions
box(-HX+.4, -HY-.02, 1.9, HX-.4, -HY+.3, 1.97, TRIM)                             # transom
box(-.7, -HY-.04, .2, .7, -HY+.3, 2.9, GLASS)                                    # glass door + frame
box(-.75, -HY-.06, .2, -.65, -HY+.32, 2.9, TRIM); box(.65, -HY-.06, .2, .75, -HY+.32, 2.9, TRIM)
box(-.75, -HY-.06, 2.85, .75, -HY+.32, 2.95, TRIM); box(-.04, -HY-.08, .2, .04, -HY+.34, 2.9, TRIM)
box(-.55, -HY-.1, 1.0, -.45, -HY-.05, 1.15, "#2b2f3a")                           # door handles
box(.45, -HY-.1, 1.0, .55, -HY-.05, 1.15, "#2b2f3a")
box(-HX-.2, -HY-.2, H, HX+.2, HY+.2, H+.25, DGREEN)                              # flat roof, green parapet, white cap
box(-HX-.2, -HY-.2, H+.25, HX+.2, -HY-.1, H+.7, GREEN); box(-HX-.2, HY+.1, H+.25, HX+.2, HY+.2, H+.7, GREEN)
box(-HX-.2, -HY-.2, H+.25, -HX-.1, HY+.2, H+.7, GREEN); box(HX+.1, -HY-.2, H+.25, HX+.2, HY+.2, H+.7, GREEN)
box(-HX-.25, -HY-.25, H+.7, HX+.25, HY+.25, H+.78, TRIM)
box(-HX-.25, -HY-.25, 3.0, HX+.25, -HY-.15, H, GREEN)                            # front fascia band
box(-3.0, -HY-.3, H+.8, 3.0, -HY-.1, H+2.0, "#f6f6f6")                           # sign board ("sign" texture on the front face)
box(-3.1, -HY-.35, H+.78, 3.1, -HY-.05, H+.85, DGREEN); box(-3.1, -HY-.35, H+2.0, 3.1, -HY-.05, H+2.07, DGREEN)
box(-3.1, -HY-.35, H+.85, -3.0, -HY-.05, H+2.0, DGREEN); box(3.0, -HY-.35, H+.85, 3.1, -HY-.05, H+2.0, DGREEN)
cyl(4.8, 0, H+.78, H+1.2, .06, "#ffcc33", 8); m = tm.creation.icosphere(subdivisions=1, radius=.38); m.apply_translation([4.8, 0, H+1.55]); col(m, "#f2f2f2")   # ball on a tee
for k in range(10):                                                              # green/white striped awning, gap at the door
    x0 = -HX + k*1.2
    if x0+1.2 > -.9 and x0 < .9: continue
    hullp([(x0, -HY, 3.0), (x0+1.2, -HY, 3.0), (x0, -HY-1.1, 2.55), (x0+1.2, -HY-1.1, 2.55),
           (x0, -HY, 2.95), (x0+1.2, -HY, 2.95), (x0, -HY-1.1, 2.5), (x0+1.2, -HY-1.1, 2.5)], GREEN if k % 2 == 0 else "#f5f5f5")
box(-HX, -HY-1.4, 0, HX, -HY, .12, STONE); box(-1.2, -HY-2.0, 0, 1.2, -HY-1.4, .06, STONE)   # porch + step
box(-HX, -HY-6.5, 0, HX, -HY-1.4, .1, GRASS); box(-HX, -HY-6.5, .1, HX, -HY-6.4, .14, STONE)   # putting green + kerb
cyl(2.5, -HY-4.2, .1, .14, .22, "#1a1a1a", 16); cyl(2.5, -HY-4.2, .1, 2.3, .025, "#eeeeee", 6)   # hole + flag
box(2.5, -HY-4.2, 1.8, 3.2, -HY-4.18, 2.3, "#e03030")
cyl(-3.2, -HY-3.8, .1, .14, 1.3, SAND, 20)                                       # bunker
for bx, bc in ((-2.2, "#c0392b"), (-1.6, "#2f5fa8")):                            # golf bags by the door
    cyl(bx, -HY-1.0, .12, 1.0, .18, bc, 8); cyl(bx, -HY-1.0, 1.0, 1.05, .2, "#2b2f3a", 8)
    for k in range(3): cyl(bx-.07+k*.07, -HY-1.0, 1.05, 1.5+k*.08, .02, "#cccccc", 4)
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
    W, H = 2048, 410
    im = Image.new("RGB", (W, H), "#1f5f2b"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W-1, H-1], outline="#ffffff", width=14); dr.rectangle([30, 30, W-31, H-31], outline="#e8c34a", width=6)
    f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 230); t = "GOLF SHOP"
    bb = dr.textbbox((0, 0), t, font=f); x, y = (W-(bb[2]-bb[0]))//2 - bb[0], (H-(bb[3]-bb[1]))//2 - bb[1]
    dr.text((x+7, y+7), t, font=f, fill="#0f3a18"); dr.text((x, y), t, font=f, fill="#ffffff")
    for cx in (170, W-170): dr.ellipse([cx-60, 150, cx+60, 270], fill="#f4f4f4", outline="#bbbbbb", width=4); dr.polygon([(cx-6, 270), (cx+6, 270), (cx, 340)], fill="#e8c34a")
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
SPECIAL = {"#8fd3f4": ("glass", tex_glass, 3.0), "#a8763e": ("floor", tex_floorboards, 2.0), "#2b2f3a": ("metal", tex_metal, 1.5),
           "#f3efe2": ("plaster", tex_plaster, 2.0), "#fafafa": ("plaster", tex_plaster, 2.0), "#1f5f2b": ("plaster", tex_plaster, 2.0),
           "#2e8b3d": ("fabric", tex_fabric, 1.0), "#f5f5f5": ("fabric", tex_fabric, 1.0), "#c0392b": ("fabric", tex_fabric, 1.0), "#2f5fa8": ("fabric", tex_fabric, 1.0),
           "#8a6a4a": ("wood", tex_wood, 1.0), "#c9c4b8": ("floor", tex_floor, 1.5), "#3aa14a": ("grass", tex_grass, 1.5), "#e8d9a0": ("sand", tex_roof, 1.0)}
def uvs(m, scale, plate=False):
    m = m.copy(); m.unmerge_vertices()
    f, n, v = m.faces, m.face_normals, m.vertices
    uv = np.zeros((len(v), 2)); bn = m.bounds
    for fi in range(len(f)):
        ax = int(np.argmax(np.abs(n[fi]))); a, b = [(2, 1), (0, 2), (0, 1)][ax]    # Y-up world: choose plane axes
        slope = False
        for vi in f[fi]:
            if slope:
                uv[vi] = (v[vi][0] / 1.6, (v[vi][1] - 3.15) / 0.438 / 1.6); continue
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
