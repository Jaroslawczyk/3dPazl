"""Gun shop (Roblox-ready, textured, ~2.5k tris, empty interior, like zina/tech shop): brick-base cottage with gable roof, striped awning, sign, putting green, cart. Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_gun_shop.py"""
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

WALL, BRICK, ROOF, TRIM, DOOR, WOOD, DECK, STONE, GLASS, DARK, SIGN = "#e0cba0", "#7a3b2e", "#3a3f47", "#e8e2d0", "#2f3640", "#8a6a4a", "#6e6a64", "#9a958c", "#8fd3f4", "#23272e", "#f6f6f6"
HX, HY, H, BW = 5.0, 3.5, 3.6, 1.0           # shop 10 x 7 m, walls 3.6 m, front = -Y
box(-HX, -HY, 0, HX, HY, .2, DECK)
WIN = (-4.0, -2.0, 1.2, 2.5); WIN2 = (2.6, 4.4, 1.2, 2.5); DR = (-.6, .6, .2, 2.6)
def fw(a, b, z0, z1):
    if z0 < BW: box(a, -HY, z0, b, -HY+.25, min(z1, BW), BRICK)
    if z1 > BW: box(a, -HY, max(z0, BW), b, -HY+.25, z1, WALL)
wall(fw, -HX, HX, [WIN, WIN2, DR], z1=H)
box(-HX, HY-.25, .2, HX, HY, BW, BRICK); box(-HX, HY-.25, BW, HX, HY, H, WALL)
for sx in (-1, 1):
    x0, x1 = (sx*HX-.25, sx*HX) if sx > 0 else (sx*HX, sx*HX+.25)
    box(x0, -HY, .2, x1, HY, BW, BRICK); box(x0, -HY, BW, x1, HY, H, WALL)
for (a0, a1, z0, z1) in (WIN, WIN2):          # barred windows: glass, steel frame, vertical bars
    box(a0, -HY+.08, z0, a1, -HY+.16, z1, GLASS)
    for (p0, p1, q0, q1) in [(a0-.1, a0, z0-.1, z1+.1), (a1, a1+.1, z0-.1, z1+.1), (a0-.1, a1+.1, z0-.1, z0), (a0-.1, a1+.1, z1, z1+.1)]:
        box(p0, -HY-.06, q0, p1, -HY+.25, q1, DARK)
    for k in range(1, int((a1-a0)/.25)): bx = a0+k*.25; box(bx-.02, -HY-.05, z0, bx+.02, -HY, z1, DARK)
    box(a0-.15, -HY-.2, z0-.14, a1+.15, -HY, z0-.04, STONE)
for (p0, p1, q0, q1) in [(DR[0]-.18, DR[0], .2, DR[3]+.18), (DR[1], DR[1]+.18, .2, DR[3]+.18), (DR[0]-.18, DR[1]+.18, DR[3], DR[3]+.18)]:
    box(p0, -HY-.08, q0, p1, -HY+.27, q1, DARK)
box(DR[0]-.5, -HY-.75, 0, DR[1]+.5, -HY, .13, STONE)
for cx in (-1, 1):                              # dark corner posts
    for cy in (-1, 1):
        xa, xb = sorted((cx*(HX-.2), cx*HX + cx*.06)); ya, yb = sorted((cy*(HY-.2), cy*HY + cy*.06))
        box(xa, ya, 0, xb, yb, H+.55, DARK)
box(-HX, -HY, H-.2, HX, HY, H, ROOF)           # roof deck + parapet
for a, b, c, d in [(-HX-.1, -HY-.1, HX+.1, -HY+.15), (-HX-.1, HY-.15, HX+.1, HY+.1), (-HX-.1, -HY-.1, -HX+.15, HY+.1), (HX-.15, -HY-.1, HX+.1, HY+.1)]:
    box(a, b, H, c, d, H+.55, ROOF)
box(-HX-.15, -HY-.15, H+.55, HX+.15, -HY+.2, H+.7, DARK)
# front sign board on the parapet + red stripe, sandbag wall, crates, target
box(-HX, -HY-.02, 2.9, HX, -HY+.28, 3.05, "#c0392b")                              # red band under the parapet
box(-HX+.8, -1.5, H, -HX+1.8, -.5, H+.9, DARK)                                       # roof AC unit
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
    im = Image.new("RGB", (W, H), "#1c1f26"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W-1, H-1], outline="#ffffff", width=22); dr.rectangle([46, 46, W-47, H-47], outline="#c0392b", width=8)
    f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 330); t = "GUNS"
    bb = dr.textbbox((0, 0), t, font=f); x, y = (W-(bb[2]-bb[0]))//2 - bb[0], 60 - bb[1]
    dr.text((x+8, y+8), t, font=f, fill="#000000"); dr.text((x, y), t, font=f, fill="#ffffff")
    f2 = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 130); t2 = "& AMMO SHOP"
    bb = dr.textbbox((0, 0), t2, font=f2); x = (W-(bb[2]-bb[0]))//2 - bb[0]
    dr.text((x, 440-bb[1]), t2, font=f2, fill="#e0b030")
    for cx in (200, W-200): dr.rounded_rectangle([cx-30, 240, cx+30, 470], 14, fill="#d9a441"); dr.polygon([(cx-30, 240), (cx+30, 240), (cx, 150)], fill="#b0452f")
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
FLAT = {"#3a3f47", "#e8e2d0", "#2f3640", "#23272e", "#c0392b", "#b9a77a", "#5a432d"}
SPECIAL = {"#8fd3f4": ("glass", tex_glass, 3.0), "#6e6a64": ("floor", tex_floor, 1.5), "#7a3b2e": ("brick", tex_brick, 1.5), "#e0cba0": ("plaster", tex_plaster, 2.0),
           "#8a6a4a": ("wood", tex_wood, 1.0), "#9a958c": ("floor", tex_floor, 1.5)}
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
    elif hx in FLAT:                                   # flat-colour paint: no texture tile edges, so no visible seams
        m, uv = uvs(m, 2.0); m = shape_mesh(m, "paint" + hx[1:], np.full((8, 8, 3), cc, np.uint8), uv)
    elif hx in SPECIAL:
        nm, fn, sz = SPECIAL[hx]; m, uv = uvs(m, sz)
        pb = PROC_PBR[hx](hx) if hx in PROC_PBR else load_pbr(hx)
        m = shape_mesh(m, nm + hx[1:], np.asarray(pb[0]) if hx in PROC_PBR else fn(hx), uv, alpha=0.55 if nm == "glass" else 1.0, pbr=pb)
    else:
        pb = load_pbr(hx); m, uv = uvs(m, 2.0 if PBR.get(hx, ("",))[0] == "wall_plaster" else 1.0)
        m = shape_mesh(m, "col" + hx[1:], tint(hx, (noise(N, 2) - .5) * .08), uv, pbr=pb)
    sc.add_geometry(m, geom_name=m.metadata["name"])
out = pathlib.Path("projects/gun_shop/export"); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"gun_shop.glb"); sc.export(out/"gun_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
