"""Dig shop (Roblox-ready, textured): treasure-hunting shop with shovels, pickaxes, detector, chest, shelves. Z-up metres, exported Y-up. Run: .venv/Scripts/python.exe scripts/gen_dig_shop.py"""
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

WOODW, STONE, ROOF, TRIM, DARK, WOOD, GLASS, SIGN = "#b8905f", "#8b7b66", "#6b3a2a", "#e8e2d0", "#23272e", "#8a6a4a", "#8fd3f4", "#f6f6f6"
DK, METAL, GOLD, RED, SHUT, DIRT, LAMP = "#5a432d", "#b8bec6", "#d9a441", "#c0392b", "#2f5d50", "#6b4a2b", "#f0c050"
HX, HY, H = 5.0, 3.5, 3.8                      # shop 10 x 7 m, walls 3.8 m, front = -Y, gable roof along X
def bar(p0, p1, r, c):
    pts = [(p[0]+dx, p[1]+dy, p[2]) for p in (p0, p1) for dx, dy in ((r, r), (-r, r), (r, -r), (-r, -r))]
    return hullp(pts, c)
def lerp(p0, p1, t): return tuple(a+(b-a)*t for a, b in zip(p0, p1))
def shovel(p0, p1, up=False):                  # p0 = blade end, p1 = grip end; up=True flips blade to p1 end
    a, b = (p1, p0) if up else (p0, p1)
    bar(a, b, .028, WOOD)
    q0, q1 = lerp(a, b, .0), lerp(a, b, .2)
    hullp([(q0[0]-.03, q0[1]-.01, q0[2]), (q0[0]+.03, q0[1]+.01, q0[2]), (q1[0]-.14, q1[1]-.015, q1[2]), (q1[0]+.14, q1[1]+.015, q1[2]), (q1[0]-.14, q1[1]+.015, q1[2]), (q1[0]+.14, q1[1]-.015, q1[2])], METAL)
    g = lerp(a, b, 1.0); box(g[0]-.09, g[1]-.04, g[2]-.02, g[0]+.09, g[1]+.04, g[2]+.04, DK)
def pick(p0, p1):
    bar(p0, p1, .028, WOOD); x, y, z = p1
    hullp([(x-.36, y-.03, z), (x+.36, y+.03, z), (x, y-.03, z+.08), (x, y+.03, z-.08), (x, y+.03, z+.08), (x, y-.03, z-.08)], METAL)
def strip(p0, p1, w, z, h, c):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; l = (dx*dx+dy*dy)**.5; px, py = -dy/l*w, dx/l*w
    return hullp([(p[0]+s*px, p[1]+s*py, zz) for p in (p0, p1) for s in (-1, 1) for zz in (z, z+h)], c)
def mound(x, y, r, hh, c):
    pts = [(x+r*np.cos(a), y+r*np.sin(a), 0) for a in np.linspace(0, 6.283, 11)[:-1]] + [(x+.3*r*np.cos(a), y+.3*r*np.sin(a), hh) for a in np.linspace(0, 6.283, 7)[:-1]]
    return hullp(pts, c)
TONES = ["#4a3322", "#4f3724", "#45301f", "#523a27"]
fr = np.random.default_rng(11)
box(-HX+.04, -HY-1.6+.04, 0, HX-.04, HY-.04, .1, "#2e2016")      # dark joist layer (shows in the thin gaps)
y = -HY-1.6
while y < HY-.01:                                  # real boards: 0.2 m wide rows, staggered butt joints, flush ends
    x, row_w = -HX, min(.2, HY-y)
    while x < HX-.01:
        L = fr.uniform(1.8, 3.6); x1 = min(HX, x+L) if HX-(x+L) > .8 else HX
        box(x+.006, y+.006, .1, x1-.006, y+row_w-.006, .2, TONES[fr.integers(4)])
        x = x1
    y += .2
WIN = (-3.9, -2.1, 1.1, 2.3); WIN2 = (2.1, 3.9, 1.1, 2.3); DR = (-.7, .7, .2, 2.5)
def fw(a, b, z0, z1):
    if z0 < .7: box(a, -HY, z0, b, -HY+.25, min(z1, .7), STONE)
    if z1 > .7: box(a, -HY, max(z0, .7), b, -HY+.25, z1, WOODW)
wall(fw, -HX, HX, [WIN, WIN2, DR], z1=H+.12)
box(-HX, HY-.25, .2, HX, HY, .7, STONE); box(-HX, HY-.25, .7, HX, HY, H+.12, WOODW)
for sx in (-1, 1):
    x0, x1 = (sx*HX-.25, sx*HX) if sx > 0 else (sx*HX, sx*HX+.25)
    box(x0, -HY, .2, x1, HY, .7, STONE); box(x0, -HY, .7, x1, HY, H+.12, WOODW)
    hullp([(x, y, z) for x in (x0, x1) for (y, z) in ((-HY, H+.12), (HY, H+.12), (0, H+1.55))], WOODW)     # gable end
for (a0, a1, z0, z1) in (WIN, WIN2):          # windows: glass, wood frame + cross, shutters, sill
    box(a0, -HY+.08, z0, a1, -HY+.16, z1, GLASS)
    for (p0, p1, q0, q1) in [(a0-.1, a0, z0-.1, z1+.1), (a1, a1+.1, z0-.1, z1+.1), (a0-.1, a1+.1, z0-.1, z0), (a0-.1, a1+.1, z1, z1+.1)]:
        box(p0, -HY-.05, q0, p1, -HY+.25, q1, DK)
    mx = (a0+a1)/2; box(mx-.03, -HY-.03, z0, mx+.03, -HY+.2, z1, DK); box(a0, -HY-.03, (z0+z1)/2-.03, a1, -HY+.2, (z0+z1)/2+.03, DK)
    # exterior: sloped sill with drip edge + apron + brackets, head cap over the window
    sa, sb = a0-.2, a1+.2
    hullp([(sa, -HY, z0-.03), (sb, -HY, z0-.03), (sa, -HY-.2, z0-.075), (sb, -HY-.2, z0-.075), (sa, -HY, z0-.11), (sb, -HY, z0-.11), (sa, -HY-.2, z0-.13), (sb, -HY-.2, z0-.13)], WOOD)
    box(a0-.06, -HY-.05, z0-.3, a1+.06, -HY, z0-.11, DK)
    for bx_ in (a0+.02, a1-.12):
        hullp([(bx_, -HY, z0-.11), (bx_+.1, -HY, z0-.11), (bx_, -HY, z0-.34), (bx_+.1, -HY, z0-.34), (bx_, -HY-.16, z0-.11), (bx_+.1, -HY-.16, z0-.11)], DK)
    box(a0-.2, -HY-.1, z1+.1, a1+.2, -HY, z1+.17, WOOD); box(a0-.16, -HY-.14, z1+.17, a1+.16, -HY, z1+.21, DK)
    for (p0, p1, q0, q1) in [(a0+.02, a1-.02, z0+.03, z0+.08), (a0+.02, a1-.02, z1-.08, z1-.03), (a0+.02, a0+.07, z0, z1), (a1-.07, a1-.02, z0, z1)]:
        box(p0, -HY+.05, q0, p1, -HY+.13, q1, DK)                  # sash border around the glass
    # interior: casing around the opening, window stool (shelf) and apron
    fy2 = -HY+.25
    for (p0, p1, q0, q1) in [(a0-.12, a0, z0-.06, z1+.12), (a1, a1+.12, z0-.06, z1+.12), (a0-.12, a1+.12, z1, z1+.12)]:
        box(p0, fy2, q0, p1, fy2+.07, q1, DK)
    box(a0-.2, fy2, z0-.06, a1+.2, fy2+.22, z0, WOODW); box(a0-.14, fy2, z0-.2, a1+.14, fy2+.05, z0-.06, DK)
    for (p0, p1, q0, q1) in [(a0, a1, z0, z0+.05), (a0, a1, z1-.05, z1), (a0, a0+.05, z0, z1), (a1-.05, a1, z0, z1)]:
        box(p0, fy2-.05, q0, p1, fy2+.05, q1, DK)                   # inner sash frame
    for sx_ in (a0-.1-.42, a1+.1):
        box(sx_, -HY-.06, z0-.1, sx_+.42, -HY, z1+.1, SHUT)
for (p0, p1, q0, q1) in [(DR[0]-.2, DR[0], .2, DR[3]+.2), (DR[1], DR[1]+.2, .2, DR[3]+.2), (DR[0]-.2, DR[1]+.2, DR[3], DR[3]+.2)]:
    box(p0, -HY-.1, q0, p1, -HY+.27, q1, DK)
for cx in (-1, 1):                              # corner posts
    for cy in (-1, 1):
        xa, xb = sorted((cx*(HX-.2), cx*HX + cx*.06)); ya, yb = sorted((cy*(HY-.2), cy*HY + cy*.06))
        box(xa, ya, .2, xb, yb, H+.12, DK)
ox, yE, zr, t = HX+.45, HY+.6, H+1.7, .16        # gable roof
import os
for s in ((-1, 1) if not os.environ.get("NOROOF") else ()):
    hullp([(sx_*ox, s*yE, H) for sx_ in (-1, 1)] + [(sx_*ox, s*yE, H-t) for sx_ in (-1, 1)] + [(sx_*ox, 0, zr) for sx_ in (-1, 1)] + [(sx_*ox, 0, zr-t) for sx_ in (-1, 1)], ROOF)
box(-ox, -.16, zr-.02, ox, .16, zr+.1, DK)
# --- interior lining: light plaster above a dark panelled wainscot (inner faces only) ---
PLAS, WAIN, T_ = "#dccaa2", "#6a4a30", .03
WS = .95
def lin(x0, y0, x1, y1, a, b):                      # a,b = z range, split into wainscot / plaster
    if a < WS: box(x0, y0, a, x1, y1, min(b, WS), WAIN)
    if b > WS: box(x0, y0, max(a, WS), x1, y1, b, PLAS)
fy, by_, sx_ = -HY+.25, HY-.25, HX-.25
wall(lambda a, b, z0, z1: lin(a, fy, b, fy+T_, z0, z1), -sx_, sx_, [WIN, WIN2, DR], z1=H)
lin(-sx_, by_-T_, sx_, by_, .2, H)
lin(-sx_, fy, -sx_+T_, by_, .2, H); lin(sx_-T_, fy, sx_, by_, .2, H)
for sgn in (-1, 1):                                  # gable triangles inside
    xa, xb = sorted((sgn*sx_, sgn*(sx_-T_)))
    hullp([(x, y, z) for x in (xa, xb) for (y, z) in ((fy, H), (by_, H), (0, H+1.4))], PLAS)
# interior door casing: jambs + head trim + plinth blocks at the floor
for (p0, p1, q0, q1) in [(DR[0]-.14, DR[0], .2, DR[3]+.14), (DR[1], DR[1]+.14, .2, DR[3]+.14), (DR[0]-.14, DR[1]+.14, DR[3], DR[3]+.14)]:
    box(p0, fy, q0, p1, fy+.08, q1, DK)
for (p0, p1) in [(DR[0]-.18, DR[0]), (DR[1], DR[1]+.18)]:
    box(p0, fy, .2, p1, fy+.1, .35, DK)
box(DR[0]-.18, fy, DR[3]+.14, DR[1]+.18, fy+.1, DR[3]+.2, WOOD)          # head cap
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
    im = Image.new("RGB", (W, H), "#3b2a1a"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W-1, H-1], outline="#ffffff", width=22); dr.rectangle([46, 46, W-47, H-47], outline="#d9a441", width=8)
    f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 330); t = "DIG SHOP"
    bb = dr.textbbox((0, 0), t, font=f); x, y = (W-(bb[2]-bb[0]))//2 - bb[0], 60 - bb[1]
    dr.text((x+8, y+8), t, font=f, fill="#000000"); dr.text((x, y), t, font=f, fill="#ffffff")
    f2 = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 118); t2 = "SHOVELS & TREASURE"
    bb = dr.textbbox((0, 0), t2, font=f2); x = (W-(bb[2]-bb[0]))//2 - bb[0]
    dr.text((x, 440-bb[1]), t2, font=f2, fill="#e0b030")
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
def tex_dirt(base):                                   # packed sand/earth with pebbles
    n = (noise(N, 2) - .5) * .22 + (noise(N, 1) - .5) * .12 + (rng.random((N, N)) - .5) * .10
    a = tint(base, n).astype(float)
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(160):
        cx, cy, r = rng.integers(0, N), rng.integers(0, N), rng.integers(3, 9)
        d = np.hypot((xx - cx + N/2) % N - N/2, (yy - cy + N/2) % N - N/2)
        t = (rng.random() - .5) * .5 + .05
        a[d < r] = a[d < r] * (1 + t) * .9 + 12
        a[(d >= r) & (d < r + 2)] *= .82
    return a.clip(0, 255).astype(np.uint8)
def tex_grain(base):                                  # long grain streaks along u, fine pores, a few dark growth rings
    r = np.random.default_rng(abs(hash(base)) % 9999)
    row = r.random(N); row = (row + np.roll(row, 1) + np.roll(row, -1)) / 3
    st = np.tile(row[:, None], (1, N)) * .7 + (r.random((N, N)) - .5) * .06
    sl = noise(N, 3)
    st += (sl - .5) * .5
    a = tint(base, (st - .35) * .55).astype(float)
    return a.clip(0, 255).astype(np.uint8)
def tex_stone(base):                                  # coursed ashlar: 8 rows, random block lengths, bevelled blocks, light mortar joints
    r = np.random.default_rng(5); rows = 8; rh = N // rows
    a = np.zeros((N, N, 3)); mort = np.array([150., 142., 128.])
    fine = (noise(N, 1) - .5) * .10 + (r.random((N, N)) - .5) * .07; big = (noise(N, 4) - .5) * .25
    h = np.array([int(base[i:i+2], 16) for i in (1, 3, 5)], float)
    for ro in range(rows):
        cuts, x = [], int(r.integers(0, 90))
        while x < N + 90:
            cuts.append(x); x += int(r.integers(95, 220))
        cuts = [c for c in cuts if c < N + 0]
        edges = sorted(set(cuts))
        if edges[0] > 0: edges.insert(0, edges[0] - 150)
        edges.append(edges[0] + N)
        for e0, e1 in zip(edges, edges[1:]):
            tone = 1 + (r.random() - .5) * .30; warm = np.array([1 + (r.random() - .5) * .08, 1, 1 - (r.random() - .5) * .10])
            for yy in range(rh):
                y = ro * rh + yy
                bev = 1.0
                if yy < 3: mix = 0.0
                elif yy < 6: bev = 1.18
                elif yy > rh - 8: bev = .78 + .22 * (rh - yy) / 8
                for xx in range(e0, e1):
                    xm = xx % N; dx = min(xx - e0, e1 - 1 - xx)
                    if yy < 3 or dx < 2: a[y, xm] = mort; continue
                    f = bev * (1.12 if dx < 5 else 1.0) if dx < 5 and xx - e0 < 5 else bev * (.85 if dx < 5 else 1.0)
                    a[y, xm] = h * tone * warm * f
    a *= (1 + fine + big)[..., None]
    a[::1] *= 1.0
    return a.clip(0, 255).astype(np.uint8)
FLAT = {"#2e2016", "#b8bec6", "#d9a441", "#f0c050", "#d8c49a", "#3a3f47", "#e8e2d0", "#2f3640", "#23272e", "#c0392b", "#b9a77a", "#5a432d"}
SPECIAL = {"#dccaa2": ("plasterin", tex_plaster, 2.0), "#6a4a30": ("wain", tex_boards, 2.0), "#8b7b66": ("stone", tex_stone, 2.0), "#4a3322": ("floor0", tex_grain, 2.0), "#4f3724": ("floor1", tex_grain, 2.0), "#45301f": ("floor2", tex_grain, 2.0), "#523a27": ("floor3", tex_grain, 2.0), "#b8905f": ("boards", tex_boards, 2.0), "#6b3a2a": ("roof", tex_roof, 1.5), "#8fd3f4": ("glass", tex_glass, 3.0), "#6e6a64": ("floor", tex_floor, 1.5), "#7a3b2e": ("brick", tex_brick, 1.5), "#e0cba0": ("plaster", tex_plaster, 2.0),
           "#8a6a4a": ("floorb", tex_floorboards, 1.5), "#9a958c": ("floor", tex_floor, 1.5)}
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
out = pathlib.Path(os.environ.get("OUT", "projects/dig_shop/export")); out.mkdir(parents=True, exist_ok=True)
sc.export(out/"dig_shop.glb"); sc.export(out/"dig_shop.obj")
print(len(scene.faces), "tris", len(sc.geometry), "materials")
