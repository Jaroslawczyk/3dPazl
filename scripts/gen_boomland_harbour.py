"""Boomland harbour + town set in the world-pass style (textured by boomland_kit.export): the pier that grows with the
"Причал" upgrade (base + stage 2 + stage 3 pieces), the lighthouse, a round and a square fountain. Y-up metres, front = +Z.
Run: .venv/Scripts/python.exe scripts/gen_boomland_harbour.py  ->  projects/boomland_world/export/*.glb

The pier pieces are drawn in the place's own studs (Island 1, deck top 232.6, 1 stud = 0.28 m) so the three pieces fit
together; each export prints the world bottom-centre (studs) where the piece must stand."""
import math, sys
import numpy as np
sys.path.insert(0, "scripts")
import boomland_kit as K
from boomland_kit import box, boxc, cyl, cylx, ball, hull, beam, frustum, ring, export

WOOD, WOOD_D, PLANK, STONE, STONE_D, STONE_L = "#9a6a40", "#6e4a2e", "#b98552", "#9a948c", "#6f6a64", "#c9c2b5"
METAL, METAL_D, LAMP, WHITE, GLASS, YEL = "#5a606c", "#2b2f3a", "#ffe28c", "#f2efe6", "#cfefff", "#f2b632"
NAVY, LH_RED, CONC, ROPE, DARK, RED = "#1e3c6e", "#d9452f", "#b8b4ac", "#cfae78", "#15120f", "#d93a32"
WATER, MARBLE, ASHLAR = "#5ec8ff", "#e9e4d8", "#8c8579"


def where(name):
    """World bottom-centre and size (studs) of the pier piece being drawn, for the Studio placement script."""
    v = np.vstack([m.vertices for m in K.P]); lo, hi = v.min(0), v.max(0)
    c = (lo + hi) / 2 / .28 + np.array([-30, 0, 0]); bot = lo[1] / .28 + 232.6
    print(f"{name}: bottom-centre studs ({c[0]:.2f}, {bot:.2f}, {c[2]:.2f}) size {((hi - lo) / .28).round(2).tolist()}")


# ============================================================ pier, in studs of the place -> metres around (-30, 232.6, 0)
S = .28
TOP = 232.6
def p(x, y, z): return [(x + 30) * S, (y - TOP) * S, z * S]
def B(x0, y0, z0, x1, y1, z1, c): a, b = p(x0, y0, z0), p(x1, y1, z1); return box(*a, *b, c)
def BM(a, b, w, c, h=None): return beam(p(*a), p(*b), w * S, c, h * S if h else None)
def CY(x, y0, y1, z, r, c, n=10): return cyl((x + 30) * S, (y0 - TOP) * S, (y1 - TOP) * S, z * S, r * S, c, n)

def deck_x(x0, x1, z0, z1):                      # planks across X (walkway), z0..z1
    k = 0
    for z in np.arange(z0, z1 - .01, 2):
        B(x0, TOP - .7, z + .08, x1, TOP, z + 1.92, PLANK if k % 3 else WOOD); k += 1
def deck_z(x0, x1, z0, z1):                      # planks along Z (head / fingers), x0..x1
    k = 0
    for x in np.arange(x0, x1 - .01, 2):
        B(x + .08, TOP - .7, z0, x + 1.92, TOP, z1, PLANK if k % 3 else WOOD); k += 1
def piling(x, z, cap=True):
    CY(x, 212, TOP + (1.6 if cap else -.7), z, .9, WOOD_D)
    if cap: CY(x, TOP + 1.6, TOP + 2, z, 1.05, METAL_D)
def rail(a, b):
    d = np.array(b, float) - np.array(a, float); n = max(1, int(np.linalg.norm(d) // 4))
    for i in range(n + 1):
        q = np.array(a, float) + d * i / n; BM([q[0], TOP, q[2]], [q[0], TOP + 3.2, q[2]], .5, WOOD_D)
    BM([a[0], TOP + 3.2, a[2]], [b[0], TOP + 3.2, b[2]], .55, WOOD); BM([a[0], TOP + 1.6, a[2]], [b[0], TOP + 1.6, b[2]], .3, WOOD)
def lamp(x, z, h=9):
    BM([x, TOP, z], [x, TOP + h, z], .6, METAL_D); B(x - 1.1, TOP + h + .9, z - 1.1, x + 1.1, TOP + h + 1.4, z + 1.1, METAL_D)
    B(x - .8, TOP + h, z - .8, x + .8, TOP + h + .9, z + .8, LAMP)
    for dx in (-1, 1):
        for dz in (-1, 1): B(x + dx * .8 - .1, TOP + h, z + dz * .8 - .1, x + dx * .8 + .1, TOP + h + .9, z + dz * .8 + .1, METAL_D)
    B(x - .9, TOP, z - .9, x + .9, TOP + .4, z + .9, METAL_D)
def cleat(x, z, along_x=True):
    B(x - (1 if along_x else .3), TOP, z - (.3 if along_x else 1), x + (1 if along_x else .3), TOP + .35, z + (.3 if along_x else 1), METAL_D)
    B(x - .25, TOP, z - .25, x + .25, TOP + .6, z + .25, METAL_D)

# ---- base (stage 1): walkway + head, rails, lamps, entrance arch with the name board, ladder, life ring
X0, X1, Z0, Z1 = -37, -23, 14, 44
HX0, HX1, HZ0, HZ1 = -48, -12, 44, 62
deck_x(X0, X1, Z0, Z1); deck_z(HX0, HX1, HZ0, HZ1)
for x in (X0 + .6, X1 - .6): B(x - .6, TOP - 1.9, Z0, x + .6, TOP - .7, Z1, WOOD_D)
for z in (HZ0 + .6, HZ1 - .6): B(HX0, TOP - 1.9, z - .6, HX1, TOP - .7, z + .6, WOOD_D)
for z in range(Z0 + 4, Z1 + 1, 6): piling(X0 - .4, z); piling(X1 + .4, z)
for x in range(HX0, HX1 + 1, 6): piling(x, HZ1 + .4)
piling(HX0 - .4, HZ0 + 6); piling(HX1 + .4, HZ0 + 6)
rail((X0 + .3, 0, Z0), (X0 + .3, 0, Z0 + 12)); rail((X1 - .3, 0, Z0), (X1 - .3, 0, Z0 + 12))
rail((HX0 + .3, 0, HZ1 - .3), (HX1 - .3, 0, HZ1 - .3))
for z in (HZ0 + 12, HZ0 + 16): cleat(HX0 + 1.2, z, False); cleat(HX1 - 1.2, z, False)
for z in (Z0 + 18, Z0 + 26): cleat(X0 + 1, z, False); cleat(X1 - 1, z, False)
for (x, z) in ((HX0 + 1.5, HZ1 - 1.5), (HX1 - 1.5, HZ1 - 1.5), (X0 - 1.5, Z0 + 1), (X1 + 1.5, Z0 + 1)): lamp(x, z)
for x in (X0 - 1.5, X1 + 1.5):                                   # entrance arch
    B(x - .6, TOP - 1, Z0 - 1.6, x + .6, TOP + 12.2, Z0 - .4, WOOD_D)
    BM([x, TOP + 6.5, Z0 - 1], [x + (3 if x < -30 else -3), TOP + 9.4, Z0 - 1], .5, WOOD)
B(X0 - 2.4, TOP + 11.6, Z0 - 1.7, X1 + 2.4, TOP + 12.4, Z0 - .3, WOOD_D)
B(X0 - 1, TOP + 8.6, Z0 - 1.3, X1 + 1, TOP + 11.4, Z0 - .7, NAVY)   # name board (the game writes "⚓ ПРИЧАЛ" on it)
B(X0 - 1.2, TOP + 8.4, Z0 - 1.35, X1 + 1.2, TOP + 8.6, Z0 - .65, WOOD); B(X0 - 1.2, TOP + 11.4, Z0 - 1.35, X1 + 1.2, TOP + 11.6, Z0 - .65, WOOD)
cx = (HX0 + HX1) / 2                                              # ladder down to the water at the head
for i in range(6): B(cx - 1.5, TOP - 1.15 - i * 1.4, HZ1 + .15, cx + 1.5, TOP - .85 - i * 1.4, HZ1 + .45, WOOD_D)
for x in (cx - 1.6, cx + 1.6): BM([x, TOP + 1, HZ1 + .3], [x, TOP - 9, HZ1 + .3], .35, WOOD_D)
for k in range(16):                                               # life ring on the walkway rail
    a0, a1 = k / 16 * 2 * math.pi, (k + 1) / 16 * 2 * math.pi
    BM([X0 - .2, TOP + 2 + math.sin(a0) * 1.2, Z0 + 6 + math.cos(a0) * 1.2], [X0 - .2, TOP + 2 + math.sin(a1) * 1.2, Z0 + 6 + math.cos(a1) * 1.2], .45, RED if k // 2 % 2 else WHITE)
where("pier_base"); export("pier_base")

# ---- stage 2: a finger pier on each side of the head (second boat place)
for (x0, x1) in ((-62, -48), (-12, 2)):
    deck_z(x0, x1, 46, 60)
    xo = x0 if x0 < -30 else x1
    for z in (46, 52, 58): piling(xo + (-.4 if x0 < -30 else .4), z)
    piling((x0 + x1) / 2, 60.4)
    B(min(x0, x1), TOP - 1.9, 59.4 - .6, max(x0, x1), TOP - .7, 59.4 + .6, WOOD_D)
    rail((xo + (.3 if x0 < -30 else -.3), 0, 46.5), (xo + (.3 if x0 < -30 else -.3), 0, 59.5))
    lamp(x0 + 2 if x0 < -30 else x1 - 2, 58)
    for x in (x0 + 4, x1 - 4): cleat(x, 46.6)
where("pier_stage2"); export("pier_stage2")

# ---- stage 3: wide outer deck (fishing ship) + a cargo crane
deck_z(-48, -12, 62, 74)
for x in range(-48, -11, 6): piling(x, 74.4)
for x in (-48.4, -11.6): piling(x, 68)
B(-48, TOP - 1.9, 73.4 - .6, -12, TOP - .7, 73.4 + .6, WOOD_D)
for x in (-44, -36, -28, -20): cleat(x, 73.2)
lamp(-46, 72); lamp(-24, 64)
cx, cz = -16, 68                                                  # crane: slewing base, lattice tower, cab, jib, counterweight
B(cx - 2.6, TOP, cz - 2.6, cx + 2.6, TOP + 1.2, cz + 2.6, METAL_D)
CY(cx, TOP + 1.2, TOP + 1.8, cz, 2.2, METAL, 16)
for dx in (-1, 1):
    for dz in (-1, 1): BM([cx + dx * 1.3, TOP + 1.8, cz + dz * 1.3], [cx + dx * 1.0, TOP + 16, cz + dz * 1.0], .45, YEL)
for k, y in enumerate((TOP + 1.8, TOP + 5.4, TOP + 9, TOP + 12.6, TOP + 16)):
    s0 = 1.3 - (y - TOP - 1.8) / 14.2 * .3
    for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        BM([cx + a[0] * s0, y, cz + a[1] * s0], [cx + b[0] * s0, y, cz + b[1] * s0], .3, YEL)
    if k < 4:
        y1 = y + 3.6; s1 = 1.3 - (y1 - TOP - 1.8) / 14.2 * .3
        for sd in (-1, 1):
            BM([cx - s0, y, cz + sd * s0], [cx + s1, y1, cz + sd * s1], .22, YEL)
            BM([cx + sd * s0, y, cz - s0], [cx + sd * s1, y1, cz + s1], .22, YEL)
B(cx - 1.6, TOP + 16, cz - 1.6, cx + 1.6, TOP + 16.6, cz + 1.6, METAL_D)
B(cx + 1.0, TOP + 16.6, cz - 1.0, cx + 3.4, TOP + 19.2, cz + 1.4, YEL)          # operator cab
B(cx + 3.38, TOP + 17.6, cz - .7, cx + 3.42, TOP + 18.9, cz + 1.1, GLASS)
for sd in (-1, 1): BM([cx + sd * .9, TOP + 16.8, cz], [cx + sd * .9, TOP + 16.8, cz + 18], .4, YEL)   # jib chords
BM([cx, TOP + 19, cz], [cx, TOP + 17.2, cz + 18], .35, YEL)
for k in range(9):
    z = cz + k * 2; BM([cx - .9, TOP + 16.8, z], [cx + .9, TOP + 16.8, z], .2, YEL)
    yt = TOP + 19 - 1.8 * k / 9
    for sd in (-1, 1): BM([cx + sd * .9, TOP + 16.8, z], [cx, yt, z + 1], .18, YEL)
BM([cx, TOP + 16.8, cz], [cx, TOP + 16.8, cz - 7], .5, YEL)                         # counter-jib + counterweight
B(cx - 1.2, TOP + 15.2, cz - 8, cx + 1.2, TOP + 17.4, cz - 5.6, CONC)
BM([cx, TOP + 19, cz], [cx, TOP + 16.8, cz - 7], .15, METAL_D)
B(cx - .6, TOP + 16.3, cz + 14.4, cx + .6, TOP + 16.8, cz + 15.6, METAL_D)       # trolley
BM([cx, TOP + 16.3, cz + 15], [cx, TOP + 9.6, cz + 15], .12, METAL_D)              # hoist cable
B(cx - .7, TOP + 8.6, cz + 14.4, cx + .7, TOP + 9.6, cz + 15.6, YEL)              # hook block
BM([cx, TOP + 8.6, cz + 15], [cx, TOP + 7.6, cz + 15], .25, METAL_D)
for i, (dx, dz) in enumerate(((-.8, -.6), (.8, -.6), (0, .8), (0, 0))):           # cargo net with sacks
    ball((cx + dx + 30) * S, (TOP + 5.6 + (1.1 if i == 3 else 0) - TOP) * S, (cz + 15 + dz) * S, 1.1 * S, ROPE, 1)
for dx, dz in ((-1.2, -1), (1.2, -1), (0, 1.3)): BM([cx, TOP + 7.6, cz + 15], [cx + dx, TOP + 5.4, cz + 15 + dz], .1, ROPE)
where("pier_stage3"); export("pier_stage3")

# ============================================================ lighthouse (metres, door +Z), ~21 m
frustum(0, 0, 0, .9, 4.4, 4.2, ASHLAR, 12)                       # plinth + steps up to the door
frustum(0, 0, .9, 1.2, 3.8, 3.7, STONE_D, 12)
for k in range(3): box(-1.0, k * .3, 4.1 + (2 - k) * .35, 1.0, (k + 1) * .3, 4.45 + (2 - k) * .35, ASHLAR)
y, r = 1.2, 2.8
for i in range(8):                                                # tapering red / white bands
    y1, r1 = y + 1.82, r - .12
    frustum(0, 0, y, y1, r, r1, WHITE if i % 2 == 0 else LH_RED, 20); y, r = y1, r1
TT = y
box(-.62, 1.2, 2.55, -.5, 3.45, 2.95, WHITE); box(.5, 1.2, 2.55, .62, 3.45, 2.95, WHITE); box(-.62, 3.35, 2.55, .62, 3.55, 2.98, WHITE)  # door frame
box(-.5, 1.2, 2.5, .5, 3.35, 2.82, WOOD_D)                        # door + panels, hinges, handle
for (y0, y1) in ((1.4, 2.2), (2.35, 3.15)): box(-.4, y0, 2.82, .4, y1, 2.86, PLANK)
for yy in (1.5, 3.0): box(-.48, yy, 2.82, -.1, yy + .07, 2.88, METAL_D)
ball(.32, 2.25, 2.88, .05, METAL_D, 0)
boxc(0, 3.75, 2.95, 1.6, .12, .9, LH_RED, pitch=18)               # little roof over the door
for i, (a, h) in enumerate(((60, 5.0), (200, 7.6), (320, 10.0), (100, 12.5), (250, 14.4))):   # windows round the tower
    t = math.radians(a); rr = 2.8 - (h - 1.2) / 1.82 * .12 - .02
    x, z = math.sin(t) * rr, math.cos(t) * rr
    boxc(x, h, z, .55, .85, .14, DARK, yaw=a); boxc(x + math.sin(t) * .05, h, z + math.cos(t) * .05, .7, 1.0, .08, WHITE, yaw=a)
    boxc(x + math.sin(t) * .1, h, z + math.cos(t) * .1, .45, .75, .04, GLASS, yaw=a)
frustum(0, 0, TT, TT + .3, 2.7, 2.7, METAL_D, 20)                 # gallery + railing
for k in range(20):
    t = k / 20 * 2 * math.pi; beam([math.cos(t) * 2.55, TT + .3, math.sin(t) * 2.55], [math.cos(t) * 2.55, TT + 1.25, math.sin(t) * 2.55], .05, METAL_D)
ring(0, TT + 1.25, 0, 2.55, .07, METAL_D, 20); ring(0, TT + .75, 0, 2.55, .04, METAL_D, 20)
frustum(0, 0, TT + .3, TT + .7, 1.75, 1.7, WHITE, 16)              # lantern room
cyl(0, TT + .7, TT + 2.7, 0, 1.45, GLASS, 16)
for k in range(8):
    t = k / 8 * 2 * math.pi; beam([math.cos(t) * 1.5, TT + .7, math.sin(t) * 1.5], [math.cos(t) * 1.5, TT + 2.7, math.sin(t) * 1.5], .1, METAL_D)
ball(0, TT + 1.7, 0, .6, LAMP, 2)                                 # the lamp (the game turns it and adds the light)
cyl(0, TT + .7, TT + 1.1, 0, .25, METAL_D, 8)
frustum(0, 0, TT + 2.7, TT + 3.0, 1.85, 1.8, LH_RED, 16); frustum(0, 0, TT + 3.0, TT + 3.6, 1.6, 1.05, LH_RED, 16)
frustum(0, 0, TT + 3.6, TT + 4.1, 1.05, .45, LH_RED, 16); ball(0, TT + 4.3, 0, .28, METAL_D, 1)
cyl(0, TT + 4.5, TT + 5.6, 0, .05, METAL_D, 6)
export("lighthouse")

# ============================================================ round fountain (4.6 m)
R = 2.2
cyl(0, 0, .12, 0, R + .1, ASHLAR, 24)                             # paving ring
for k in range(20):                                               # basin wall + rim
    t = (k + .5) / 20 * 2 * math.pi; ch = 2 * R * math.sin(math.pi / 20) + .02
    boxc(math.cos(t) * (R - .15), .4, math.sin(t) * (R - .15), .3, .56, ch, MARBLE, yaw=-math.degrees(t))
    boxc(math.cos(t) * (R - .15), .72, math.sin(t) * (R - .15), .42, .1, ch + .04, ASHLAR, yaw=-math.degrees(t))
cyl(0, .12, .5, 0, R - .29, WATER, 24)                            # water in the basin
frustum(0, 0, .12, 1.3, .5, .3, MARBLE, 12)                       # pedestal, middle bowl, column, top bowl, finial
frustum(0, 0, 1.3, 1.55, .35, 1.05, MARBLE, 16); cyl(0, 1.5, 1.56, 0, .95, WATER, 16)
frustum(0, 0, 1.55, 2.2, .22, .16, MARBLE, 10)
frustum(0, 0, 2.2, 2.38, .18, .55, MARBLE, 12); cyl(0, 2.34, 2.39, 0, .48, WATER, 12)
frustum(0, 0, 2.38, 2.65, .1, .05, MARBLE, 8); ball(0, 2.72, 0, .09, WATER, 1)
for k in range(8):                                                # water falling from both bowls
    t = k / 8 * 2 * math.pi
    beam([math.cos(t) * 1.02, 1.52, math.sin(t) * 1.02], [math.cos(t) * 1.2, .5, math.sin(t) * 1.2], .05, WATER)
    beam([math.cos(t) * .53, 2.36, math.sin(t) * .53], [math.cos(t) * .62, 1.56, math.sin(t) * .62], .035, WATER)
export("fountain_round")

# ============================================================ square fountain (4.6 m)
Q = 2.2
box(-Q - .1, 0, -Q - .1, Q + .1, .12, Q + .1, ASHLAR)
for sx in (-1, 1):                                                # basin walls with a cap
    box(sx * Q - .3 * (sx > 0), .12, -Q, sx * Q + .3 * (sx < 0), .68, Q, MARBLE); box(sx * Q - .36 * (sx > 0) - .04 * (sx < 0), .68, -Q - .04, sx * Q + .36 * (sx < 0) + .04 * (sx > 0), .78, Q + .04, ASHLAR)
    box(-Q, .12, sx * Q - .3 * (sx > 0), Q, .68, sx * Q + .3 * (sx < 0), MARBLE); box(-Q - .04, .68, sx * Q - .36 * (sx > 0) - .04 * (sx < 0), Q + .04, .78, sx * Q + .36 * (sx < 0) + .04 * (sx > 0), ASHLAR)
for sx in (-1, 1):                                                # corner posts with caps
    for sz in (-1, 1):
        box(sx * Q - .25, .12, sz * Q - .25, sx * Q + .25, 1.0, sz * Q + .25, ASHLAR)
        hull([[sx * Q + dx, 1.0, sz * Q + dz] for dx in (-.28, .28) for dz in (-.28, .28)] + [[sx * Q, 1.25, sz * Q]], MARBLE)
box(-Q + .3, .12, -Q + .3, Q - .3, .55, Q - .3, WATER)
box(-.45, .12, -.45, .45, 1.2, .45, MARBLE)                        # column + square bowl + top
hull([[dx, 1.2, dz] for dx in (-.4, .4) for dz in (-.4, .4)] + [[dx, 1.5, dz] for dx in (-1.0, 1.0) for dz in (-1.0, 1.0)], MARBLE)
box(-.9, 1.45, -.9, .9, 1.51, .9, WATER)
box(-.18, 1.5, -.18, .18, 2.1, .18, MARBLE); box(-.42, 2.1, -.42, .42, 2.22, .42, ASHLAR); ball(0, 2.36, 0, .14, MARBLE, 1)
for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):              # four jets from the top into the bowl, bowl into the basin
    beam([dx * .3, 2.2, dz * .3], [dx * .7, 1.52, dz * .7], .05, WATER)
    beam([dx * 1.0, 1.48, dz * 1.0], [dx * 1.35, .55, dz * 1.35], .07, WATER)
export("fountain_square")
