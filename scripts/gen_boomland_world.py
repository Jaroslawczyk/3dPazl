"""Boomland world props in ONE style (warm wood, grey stone, red roofs, dark steel, gold, glowing lamps), Y-up metres,
front = +Z. Run: .venv/Scripts/python.exe scripts/gen_boomland_world.py  ->  projects/boomland_world/export/*.glb"""
import math, sys
import numpy as np
sys.path.insert(0, "scripts")
from boomland_kit import box, boxc, cyl, cylx, ball, hull, beam, rock, gable, gable_end, frustum, ring, export

WOOD, WOOD_D, PLANK, STONE, STONE_D, STONE_L = "#9a6a40", "#6e4a2e", "#b98552", "#9a948c", "#6f6a64", "#c9c2b5"
ROOF, METAL, METAL_D, GOLD, LAMP, WHITE = "#c94a3a", "#5a606c", "#2b2f3a", "#ffc83c", "#ffe28c", "#f2efe6"
CRYSTAL, FLAME, GLASS, SIGN, BLUE, ROPE = "#7ee8ff", "#ff6a3d", "#cfefff", "#ffd23f", "#3a6fb0", "#cfae78"
ASPH, LINE, YEL, BRICK, MONITOR, DARK = "#3a3d44", "#f4f4f0", "#f2b632", "#b5523b", "#2a2d36", "#15120f"
GREEN_L, ICE, FISH, FISH2, RED = "#9dff7a", "#e6f7ff", "#ff8a3d", "#c8d2dc", "#d93a32"
CONC, CHUTE, RUBBER = "#b8b4ac", "#7a7f8a", "#22252b"


def lantern(x, y, z, s=1.0):
    box(x - .17*s, y, z - .17*s, x + .17*s, y + .04*s, z + .17*s, METAL_D)
    box(x - .12*s, y + .04*s, z - .12*s, x + .12*s, y + .40*s, z + .12*s, LAMP)
    for dx in (-1, 1):
        for dz in (-1, 1):
            box(x + dx*.15*s - .02*s, y + .04*s, z + dz*.15*s - .02*s, x + dx*.15*s + .02*s, y + .42*s, z + dz*.15*s + .02*s, METAL_D)
    hull([[x + dx*.2*s, y + .42*s, z + dz*.2*s] for dx in (-1, 1) for dz in (-1, 1)] + [[x, y + .62*s, z]], METAL_D)
    ball(x, y + .66*s, z, .04*s, METAL_D, 0)


# ---------------------------------------------------------------- street / pier lamp
cyl(0, 0, .2, 0, .16, METAL_D, 8); cyl(0, .2, 3.0, 0, .055, METAL_D, 8)
cyl(0, .9, .98, 0, .09, METAL_D, 8); cyl(0, 2.9, 3.0, 0, .1, METAL_D, 8)
lantern(0, 3.0, 0)
export("lamp_post")

# ---------------------------------------------------------------- mine cart (+ gold variant)
def cart(ore):
    for x in (-.46, .46):
        for z in (-.45, .45):
            cylx(x - .05, x + .05, .18, z, .18, METAL_D, 12); cylx(x - .06, x + .06, .18, z, .07, METAL, 8)
        cylx(-.52, .52, .18, -.45 if x < 0 else .45, .03, METAL)
    box(-.4, .26, -.7, .4, .34, .7, METAL_D)
    hull([[sx * .42, .32, sz * .62] for sx in (-1, 1) for sz in (-1, 1)] + [[sx * .55, .98, sz * .76] for sx in (-1, 1) for sz in (-1, 1)], METAL)
    for sx in (-1, 1): box(sx * .57 - .03, .94, -.78, sx * .57 + .03, 1.02, .78, METAL_D)
    for sz in (-1, 1): box(-.57, .94, sz * .78 - .03, .57, 1.02, sz * .78 + .03, METAL_D)
    for z in (-.4, 0, .4):
        for sx in (-1, 1): beam([sx * .45, .36, z], [sx * .57, .98, z * 1.2], .04, METAL_D)
    for sz in (-1, 1): box(-.05, .25, sz * .78, .05, .32, sz * .92, METAL_D)
    rng = np.random.default_rng(3 if ore == GOLD else 4)
    for i in range(9):
        rock(rng.uniform(-.35, .35), .82, rng.uniform(-.55, .55), rng.uniform(.13, .2), ore if i % 3 else (STONE_D if ore == GOLD else CRYSTAL), i)
cart(STONE_D); export("mine_cart")
cart(GOLD); export("mine_cart_gold")

# ---------------------------------------------------------------- rail, 4 m straight, gauge 0.92
for i in range(8):
    z = -1.75 + i * .5
    box(-.75, 0, z - .11, .75, .12, z + .11, WOOD_D if i % 2 else WOOD)
    for sx in (-1, 1): box(sx * .46 - .09, .12, z - .08, sx * .46 + .09, .14, z + .08, METAL_D)
for sx in (-1, 1):
    box(sx * .46 - .06, .14, -2, sx * .46 + .06, .16, 2, METAL)
    box(sx * .46 - .015, .16, -2, sx * .46 + .015, .24, 2, METAL)
    box(sx * .46 - .04, .24, -2, sx * .46 + .04, .29, 2, METAL)
export("mine_rail")

# ---------------------------------------------------------------- mine portal (tunnel mouth), 4.6 wide
box(-1.8, 0, -3.2, 1.8, 3.6, -3.0, DARK)                       # the dark depth
for sx in (-1, 1):
    box(sx * 1.8 - (.12 if sx > 0 else 0), 0, -3.0, sx * 1.8 + (0 if sx > 0 else .12), 3.6, 0, DARK)
box(-1.8, 3.6, -3.0, 1.8, 3.72, 0, DARK)
for z in (0.0, -1.4, -2.7):                                     # timber sets
    for sx in (-1, 1): box(sx * 1.75 - .2, 0, z - .2, sx * 1.75 + .2, 3.7, z + .2, WOOD_D)
    box(-2.1, 3.7, z - .24, 2.1, 4.15, z + .24, WOOD_D)
for sx in (-1, 1):                                              # knee braces + wing walls
    beam([sx * 1.55, 3.0, .05], [sx * .9, 3.7, .05], .16, WOOD)
    for k in range(6):
        y = .25 + k * .5
        box(sx * 1.95 if sx > 0 else sx * 3.4, y - .22, -.1, sx * 3.4 if sx > 0 else sx * 1.95, y + .22, .12, PLANK if k % 2 else WOOD)
    box(sx * 3.4 - .15, 0, -.15, sx * 3.4 + .15, 3.2, .2, WOOD_D)
gable(-2.6, 2.6, -.9, .9, 4.15, .9, ROOF, over=.2, thick=.14)
hull([[x, 4.15, z] for x in (-2.4, 2.4) for z in (-.9, .9)] + [[x, 5.0, 0] for x in (-2.4, 2.4)], WOOD)
box(-1.3, 3.42, 1.02, 1.3, 3.86, 1.1, SIGN)                     # sign board hung under the front eave (text added in the game)
for sx in (-1, 1): box(sx * 1.1 - .03, 3.86, 1.03, sx * 1.1 + .03, 4.0, 1.09, METAL_D)
for sx in (-1, 1): box(sx * .46 - .05, 0, -3.0, sx * .46 + .05, .12, 1.5, METAL)  # rails coming out
for i in range(9): box(-.7, 0, -2.9 + i * .5 - .1, .7, .07, -2.9 + i * .5 + .1, WOOD_D)
beam([1.4, 3.7, .35], [1.4, 3.2, .35], .03, METAL_D); lantern(1.4, 2.75, .35, .9)
export("mine_portal")

# ---------------------------------------------------------------- boarded-up mouth
for i, a in enumerate((24, -24, 6)):
    boxc(0, 1.2 + i * .9, .25 + i * .02, 3.8, .3, .08, PLANK if i != 2 else WOOD, roll=a)
for sx in (-1, 1): box(sx * 1.6 - .1, 0, .2, sx * 1.6 + .1, 3.4, .32, WOOD_D)
box(-.8, 1.5, .34, .8, 2.1, .4, RED)
export("mine_boards")

# ---------------------------------------------------------------- headframe (winding tower), 9.5 m
for sx in (-1, 1):
    for sz in (-1, 1):
        box(sx * 1.35 - .3, 0, sz * 1.35 - .3, sx * 1.35 + .3, .3, sz * 1.35 + .3, STONE)
        beam([sx * 1.35, .3, sz * 1.35], [sx * .55, 8.0, sz * .55], .26, WOOD_D)
for y in (2.4, 4.8, 7.0):
    s = 1.35 - (y - .3) / 7.7 * .8
    for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        beam([a[0] * s, y, a[1] * s], [b[0] * s, y, b[1] * s], .14, WOOD)
for sz in (-1, 1):
    for (y0, y1) in ((.3, 2.4), (2.4, 4.8), (4.8, 7.0)):
        s0, s1 = 1.35 - (y0 - .3) / 7.7 * .8, 1.35 - (y1 - .3) / 7.7 * .8
        beam([-s0, y0, sz * s0], [s1, y1, sz * s1], .1, WOOD); beam([s0, y0, sz * s0], [-s1, y1, sz * s1], .1, WOOD)
box(-1.0, 8.0, -1.0, 1.0, 8.15, 1.0, PLANK)
for sx in (-1, 1): beam([sx * .9, 8.15, -.9], [sx * .9, 8.15, .9], .06, WOOD_D, .9)
for sx in (-1, 1): beam([sx * .5, 8.0, 0], [sx * .5, .3, -3.6], .22, WOOD)   # back struts
for sx in (-1, 1): box(sx * .5 - .3, 0, -3.9, sx * .5 + .3, .3, -3.3, STONE)
WY = 8.95
for k in range(20):                                             # sheave wheel (in the YZ plane)
    a0, a1 = k / 20 * 2 * math.pi, (k + 1) / 20 * 2 * math.pi
    beam([0, WY + math.sin(a0) * .85, math.cos(a0) * .85], [0, WY + math.sin(a1) * .85, math.cos(a1) * .85], .12, METAL_D)
for k in range(6):
    a = k / 6 * 2 * math.pi
    beam([0, WY, 0], [0, WY + math.sin(a) * .8, math.cos(a) * .8], .05, METAL)
cylx(-.25, .25, WY, 0, .12, RED, 10)
for sx in (-1, 1): beam([sx * .2, 8.15, 0], [sx * .2, WY, 0], .12, WOOD_D)
beam([0, WY - .85, .02], [0, 1.0, .02], .03, METAL_D)
box(-.45, .3, -.45, .45, 1.1, .45, METAL)                       # cage at the bottom
export("headframe")

# ---------------------------------------------------------------- mine office (enterable house with the computer)
HX, HZ, H = 3.0, 2.5, 2.8
box(-HX - .2, 0, -HZ - .2, HX + .2, .35, HZ + .2, STONE)
box(-HX, .35, -HZ, HX, .42, HZ, PLANK)
def wallx(z0, z1, ops):                       # wall along X between z0..z1 thickness, openings (x0, x1, y0, y1)
    cuts = sorted({-HX, HX, *[o[i] for o in ops for i in (0, 1)]})
    for a, b in zip(cuts, cuts[1:]):
        o = next((o for o in ops if o[0] <= a and b <= o[1]), None)
        if o is None: box(a, .42, z0, b, H, z1, WOOD)
        else:
            if o[2] > .42: box(a, .42, z0, b, o[2], z1, WOOD)
            if o[3] < H: box(a, o[3], z0, b, H, z1, WOOD)
def wallz(x0, x1, ops):
    cuts = sorted({-HZ, HZ, *[o[i] for o in ops for i in (0, 1)]})
    for a, b in zip(cuts, cuts[1:]):
        o = next((o for o in ops if o[0] <= a and b <= o[1]), None)
        if o is None: box(x0, .42, a, x1, H, b, WOOD)
        else:
            if o[2] > .42: box(x0, .42, a, x1, o[2], b, WOOD)
            if o[3] < H: box(x0, o[3], a, x1, H, b, WOOD)
DOOR, WINF = (-.7, .7, .42, 2.45), [(-2.4, -1.4, 1.2, 2.2), (1.4, 2.4, 1.2, 2.2)]
wallx(HZ - .18, HZ, [DOOR] + WINF); wallx(-HZ, -HZ + .18, [])
wallz(-HX, -HX + .18, [(-.6, .6, 1.2, 2.2)]); wallz(HX - .18, HX, [(-.6, .6, 1.2, 2.2)])
for sx in (-1, 1):
    for sz in (-1, 1): box(sx * HX - .14, .35, sz * HZ - .14, sx * HX + .14, H + .05, sz * HZ + .14, WOOD_D)
for (a, b, y0, y1) in WINF:                                     # front windows
    box(a, y0, HZ - .1, b, y1, HZ - .06, GLASS)
    for (p0, p1, q0, q1) in ((a - .08, a, y0, y1), (b, b + .08, y0, y1), (a - .08, b + .08, y0 - .08, y0), (a - .08, b + .08, y1, y1 + .08)):
        box(p0, q0, HZ - .02, p1, q1, HZ + .06, WHITE)
for sx in (-1, 1):                                              # side windows: glass inside the wall, white frame outside
    box(sx * (HX - .09) - .02, 1.2, -.6, sx * (HX - .09) + .02, 2.2, .6, GLASS)
    xo = sx * HX
    for (z0, z1, y0, y1) in ((-.68, -.6, 1.12, 2.28), (.6, .68, 1.12, 2.28), (-.68, .68, 1.12, 1.2), (-.68, .68, 2.2, 2.28)):
        box(min(xo - sx * .02, xo + sx * .06), y0, z0, max(xo - sx * .02, xo + sx * .06), y1, z1, WHITE)
for (p0, p1, q0, q1) in ((DOOR[0] - .1, DOOR[0], .42, DOOR[3] + .1), (DOOR[1], DOOR[1] + .1, .42, DOOR[3] + .1), (DOOR[0] - .1, DOOR[1] + .1, DOOR[3], DOOR[3] + .1)):
    box(p0, q0, HZ - .02, p1, q1, HZ + .08, WOOD_D)
box(-1.0, 0, HZ + .2, 1.0, .25, HZ + .8, STONE)                 # step
gable(-HX, HX, -HZ, HZ, H, 1.5, ROOF, over=.35, thick=.14, ridge="z")   # ridge front-to-back: the gable with the sign faces the door
for z in (-HZ, HZ - .18): gable_end(-HX, HX, H, 1.5, PLANK, z, ridge="z")
box(-1.1, 2.62, HZ + .1, 1.1, 3.05, HZ + .18, SIGN)             # sign over the door
lantern(1.0, 2.0, HZ + .3, .7)
# inside: desk + computer at the back wall, chair, shelf with ore, ceiling lamp
box(-1.1, .42, -HZ + .2, 1.1, 1.17, -HZ + .95, WOOD)
box(-1.1, 1.17, -HZ + .2, 1.1, 1.22, -HZ + .95, WOOD_D)
box(-.6, 1.22, -HZ + .45, .6, 1.27, -HZ + .7, METAL_D)          # keyboard tray
box(-.12, 1.22, -HZ + .3, .12, 1.45, -HZ + .4, METAL_D)         # monitor stand
box(-.6, 1.45, -HZ + .28, .6, 2.15, -HZ + .36, MONITOR)         # monitor bezel (the game puts the screen in front)
box(.75, 1.22, -HZ + .3, .95, 1.75, -HZ + .8, METAL_D)          # pc case
box(-.3, .42, -HZ + 1.3, .3, .9, -HZ + 1.85, BLUE); box(-.3, .9, -HZ + 1.8, .3, 1.6, -HZ + 1.9, BLUE)  # chair
box(-HX + .2, .42, 1.0, -HX + .6, 2.2, 2.0, WOOD_D)              # shelf
for i, y in enumerate((.9, 1.4, 1.9)):
    box(-HX + .18, y, 1.0, -HX + .62, y + .05, 2.0, WOOD)
    rock(-HX + .4, y + .05, 1.3 + i * .2, .12, (GOLD, CRYSTAL, STONE_D)[i], i)
cyl(0, H - .1, H + 1.5, 0, .025, METAL_D, 6)                      # rod from the ridge
box(-.25, H - .1, -.25, .25, H, .25, METAL_D); box(-.15, H - .3, -.15, .15, H - .1, .15, LAMP)
export("mine_office")

# ---------------------------------------------------------------- storage shed (open front)
for sx in (-1, 1):
    for sz in (-1, 1): box(sx * 2 - .12, 0, sz * 1.5 - .12, sx * 2 + .12, 2.6 if sz > 0 else 2.2, sz * 1.5 + .12, WOOD_D)
for k in range(5): box(-2, .1 + k * .42, -1.55, 2, .48 + k * .42, -1.45, PLANK if k % 2 else WOOD)
for sx in (-1, 1):
    for k in range(5): box(sx * 2 - .05, .1 + k * .42, -1.5, sx * 2 + .05, .48 + k * .42, 1.5, PLANK if k % 2 else WOOD)
    hull([[sx * 2 + dx, y, z] for dx in (-.05, .05) for (y, z) in ((2.2, -1.5), (2.2, 1.5), (2.6, 1.5))], WOOD)   # side wall up to the sloped roof
boxc(0, 2.5, 0, 4.6, .14, 3.6, ROOF, pitch=-6.3)
box(-2, 0, -1.5, 2, .1, 1.5, PLANK)
export("mine_shed")

# ---------------------------------------------------------------- ore heaps
for i in range(9): rock(math.cos(i) * .9 * (i % 3) / 2, 0, math.sin(i * 1.7) * .8 * (i % 3) / 2, .55 - (i % 3) * .1, STONE_D if i % 2 else STONE, i)
for i in range(5):
    a = i * 1.3
    hull([[math.cos(a) * .5 + dx, .2, math.sin(a) * .5 + dz] for dx, dz in ((-.08, -.08), (.08, -.08), (0, .1))] + [[math.cos(a) * .62, 1.0 + i * .08, math.sin(a) * .62]], CRYSTAL)
export("ore_heap")
for i in range(11): rock(math.cos(i * 2.1) * .8 * (i % 4) / 3, 0, math.sin(i * 2.1) * .7 * (i % 4) / 3, .45 - (i % 4) * .06, GOLD if i % 3 else STONE_D, i + 20)
for i in range(4): boxc(.9 - i * .12, .1 + i * .12, .9, .5, .12, .22, GOLD, yaw=10 * i)
export("gold_heap")

# ---------------------------------------------------------------- drill rig (derrick on a skid, the engine drives the rotary table)
box(-1.7, 0, -1.5, 1.7, .3, 1.7, CONC)                          # concrete pad
for sx in (-1, 1): box(sx * 1.3 - .12, .3, -1.3, sx * 1.3 + .12, .5, 1.5, METAL_D)   # skid runners
for z in (-1.1, 0, 1.1): box(-1.4, .5, z - .08, 1.4, .58, z + .08, METAL_D)          # cross members
box(-1.0, .58, -1.0, 1.0, .64, 1.0, CHUTE)                       # steel floor
DT, DH = .32, 7.0                                                # derrick: legs from the floor corners up to the crown
for sx in (-1, 1):
    for sz in (-1, 1): beam([sx * .9, .64, sz * .9], [sx * DT, DH, sz * DT], .14, YEL)
LEV = (.64, 2.2, 3.7, 5.1, DH)
def dw(y): return .9 - (y - .64) / (DH - .64) * (.9 - DT)
for k, y in enumerate(LEV):
    s0 = dw(y)
    for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        beam([a[0] * s0, y, a[1] * s0], [b[0] * s0, y, b[1] * s0], .09, YEL)
    if k < 4:
        y1 = LEV[k + 1]; s1 = dw(y1)
        for sz in (-1, 1):
            beam([-s0, y, sz * s0], [s1, y1, sz * s1], .06, YEL); beam([s0, y, sz * s0], [-s1, y1, sz * s1], .06, YEL)
        for sx in (-1, 1):
            beam([sx * s0, y, -s0], [sx * s1, y1, s1], .06, YEL); beam([sx * s0, y, s0], [sx * s1, y1, -s1], .06, YEL)
box(-.5, DH, -.5, .5, DH + .35, .5, METAL_D)                     # crown block + sheave
cylx(-.3, .3, DH + .55, 0, .28, CHUTE, 14); box(-.06, DH + .35, -.1, .06, DH + .55, .1, METAL_D)
box(-.45, 3.7, -.6, .45, 3.76, .6, CHUTE)                        # monkey board
for dz in (.25, -.25): beam([0, DH + .3, dz], [0, 4.6, dz], .025, METAL_D)
box(-.22, 4.0, -.3, .22, 4.6, .3, YEL)                           # travelling block
cyl(0, .64, 4.0, 0, .07, METAL, 8)                              # drill pipe
box(-.45, .64, -.45, .45, .82, .45, METAL_D); cyl(0, .82, .9, 0, .3, METAL, 12)      # rotary table
cyl(0, -.3, .3, 0, .09, METAL, 8)                               # pipe on into the ground
box(.9, .64, 1.0, 1.65, 1.35, 1.65, YEL)                          # engine with the winch (drawworks)
for k in range(5): box(1.65, .75 + k * .11, 1.08, 1.69, .8 + k * .11, 1.57, METAL_D)   # radiator grille
cyl(1.45, 1.35, 1.9, 1.5, .05, METAL_D, 8); cyl(1.45, 1.9, 1.95, 1.5, .07, METAL_D, 8)  # exhaust
beam([.9, .76, 1.2], [.3, .76, .5], .07, METAL)                    # drive shaft to the table
cylx(.95, 1.6, 1.55, 1.25, .16, METAL_D, 12)                       # winch drum on top of the engine
beam([1.0, 1.65, 1.25], [.25, DH + .4, .2], .025, METAL_D)          # hoist line up to the crown
for k in range(9): box(-.95, .9 + k * .5, -1.0, -.75, .94 + k * .5, -.94, METAL_D)    # ladder up the back
for dx in (-.95, -.75): beam([dx, .64, -.97], [dx, 5.0, -.97], .03, METAL_D)
for sx in (-1, 1): box(sx * 1.0 - .03, .64, -1.0, sx * 1.0 + .03, 1.6, -.94, YEL)       # handrail at the back
box(-1.0, 1.55, -1.0, 1.0, 1.6, -.94, YEL)
export("drill_rig")

# ---------------------------------------------------------------- boiler house + chimney (real door and windows)
box(-1.75, 0, -1.55, 1.75, .25, 1.65, CONC)                       # footing
box(-1.6, .25, -1.4, 1.6, 2.6, 1.4, BRICK)
box(-1.75, 2.6, -1.55, 1.75, 2.8, 1.55, STONE_D)
for sx in (-1, 1):                                                # windows: sill + lintel, iron frame and glass,
    x = sx * 1.0                                                  # the fire glows behind the glass, inside
    box(x - .38, 1.08, 1.4, x + .38, 1.16, 1.52, STONE_L); box(x - .36, 1.84, 1.4, x + .36, 1.94, 1.48, STONE_L)
    box(x - .3, 1.16, 1.3, x + .3, 1.84, 1.34, FLAME)
    box(x - .3, 1.16, 1.38, x + .3, 1.84, 1.4, GLASS)
    for (p0, p1, q0, q1) in ((x - .3, x - .26, 1.16, 1.84), (x + .26, x + .3, 1.16, 1.84), (x - .3, x + .3, 1.16, 1.2),
                             (x - .3, x + .3, 1.8, 1.84), (x - .02, x + .02, 1.16, 1.84), (x - .3, x + .3, 1.48, 1.52)):
        box(p0, q0, 1.38, p1, q1, 1.45, METAL_D)
box(-.58, .25, 1.4, -.5, 2.05, 1.5, STONE_L); box(.5, .25, 1.4, .58, 2.05, 1.5, STONE_L)   # door frame
box(-.58, 2.05, 1.4, .58, 2.15, 1.52, STONE_L)
box(-.5, .25, 1.36, .5, 2.05, 1.4, WOOD_D)                         # door leaf in the opening
for (y0, y1) in ((.4, 1.05), (1.2, 1.9)):                           # raised panels
    for (x0, x1) in ((-.4, -.04), (.04, .4)): box(x0, y0, 1.4, x1, y1, 1.43, WOOD)
for y in (.55, 1.75): box(-.46, y, 1.4, .1, y + .06, 1.45, METAL_D)  # iron hinge straps
box(.32, 1.05, 1.4, .38, 1.25, 1.47, METAL_D); ball(.35, 1.15, 1.49, .035, GOLD, 0)  # handle
box(-.7, 0, 1.65, .7, .2, 2.0, CONC)                              # step
box(-.05, 2.2, 1.52, .05, 2.3, 1.75, METAL_D); lantern(0, 1.9, 1.72, .5)              # lamp over the door
cyl(.8, 2.8, 8.5, -.6, .38, BRICK, 12)
for y in (4.0, 6.0, 8.2): cyl(.8, y, y + .2, -.6, .43, METAL_D, 12)
cylx(1.6, 2.8, .8, 0, .6, METAL, 12); cylx(2.75, 2.85, .8, 0, .62, METAL_D, 12)
for x in (1.9, 2.5): box(x - .1, 0, -.5, x + .1, .3, .5, METAL_D)
cylx(1.45, 1.62, 1.1, 0, .12, METAL_D, 8)                          # pipe from the boiler into the wall
export("boiler_house")

# ---------------------------------------------------------------- ore conveyor: feed hopper on the ground -> belt -> chute into a cart
ZA, YA, ZB, YB = -2.4, .55, 2.0, 2.45                             # tail / head pulley centres
def onbelt(t, dy=0.0): return ZA + (ZB - ZA) * t, YA + (YB - YA) * t + dy
BL = math.hypot(ZB - ZA, YB - YA); BANG = math.degrees(math.atan2(YB - YA, ZB - ZA))
zc, yc = onbelt(.5)
boxc(0, yc + .06, zc, .62, .03, BL, RUBBER, pitch=-BANG)           # top belt
boxc(0, yc - .12, zc, .62, .03, BL, RUBBER, pitch=-BANG)           # return belt
for sx in (-1, 1): boxc(sx * .37, yc, zc, .06, .3, BL + .3, YEL, pitch=-BANG)   # side frames
for k in range(11):
    z, y = onbelt(k / 10); cylx(-.34, .34, y, z, .05, METAL, 8)
cylx(-.36, .36, YA, ZA, .12, METAL_D, 12); cylx(-.36, .36, YB, ZB, .14, METAL_D, 12)
for t in (.12, .5, .88):                                           # legs on concrete footings, cross braced
    z, y = onbelt(t, -.15)
    for sx in (-1, 1):
        box(sx * .45 - .14, 0, z - .14, sx * .45 + .14, .12, z + .14, CONC)
        beam([sx * .45, .12, z], [sx * .37, y, z], .07, METAL_D)
    if y > .8:
        beam([-.45, .2, z], [.45, y - .1, z], .04, METAL_D); beam([.45, .2, z], [-.45, y - .1, z], .04, METAL_D)
box(.4, YB - .2, ZB - .35, .78, YB + .15, ZB + .05, YEL); cylx(.36, .42, YB, ZB, .1, METAL_D, 8)   # drive motor
box(-.42, YB + .05, ZB - .05, .42, YB + .35, ZB + .22, CHUTE)      # head cover
hull([[sx * .36, YB - .05, ZB + .05] for sx in (-1, 1)] + [[sx * .36, YB + .3, ZB + .25] for sx in (-1, 1)]
     + [[sx * .25, 1.35, ZB + .75] for sx in (-1, 1)] + [[sx * .25, 1.55, ZB + .9] for sx in (-1, 1)], CHUTE)   # discharge chute
box(-.22, 1.2, ZB + .7, .22, 1.35, ZB + .95, CHUTE)               # spout: the cart stands under it
for sx in (-1, 1):
    beam([sx * .3, .05, ZB + .8], [sx * .25, 1.25, ZB + .8], .06, METAL_D)
    box(sx * .3 - .1, 0, ZB + .7, sx * .3 + .1, .05, ZB + .9, CONC)
hull([[sx * .75, .9, ZA - .9 + dz] for sx in (-1, 1) for dz in (0, 1.0)] + [[sx * .3, .45, ZA - .55 + dz] for sx in (-1, 1) for dz in (0, .35)], WOOD)  # feed hopper
for sx in (-1, 1):
    for z0 in (ZA - .9, ZA + .02): box(sx * .62 - .08, 0, z0, sx * .62 + .08, .9, z0 + .1, WOOD_D)
for i in range(5):                                                 # ore riding up
    z, y = onbelt(.15 + i * .17, .14); rock(-.1 + (i % 2) * .2, y, z, .1, STONE_D, i)
export("conveyor")

# ---------------------------------------------------------------- treasury (end of the mine field)
for k, (w, d) in enumerate(((8.4, 7.4), (7.8, 6.8), (7.2, 6.2))):
    box(-w / 2, k * .25, -d / 2, w / 2, (k + 1) * .25, d / 2, STONE if k % 2 else STONE_D)
Y0 = .75
box(-3.1, Y0, -2.8, 3.1, Y0 + 3.8, 1.6, STONE_L)
for x in (-2.4, -.95, .95, 2.4):                                 # portico columns
    box(x - .38, Y0, 2.2, x + .38, Y0 + .25, 2.96, STONE)
    cyl(x, Y0 + .25, Y0 + 3.55, 2.58, .27, WHITE, 12)
    box(x - .38, Y0 + 3.55, 2.2, x + .38, Y0 + 3.8, 2.96, STONE)
box(-3.3, Y0 + 3.8, -2.95, 3.3, Y0 + 4.15, 3.15, STONE)
hull([[x, Y0 + 4.15, z] for x in (-3.3, 3.3) for z in (2.95, 3.15)] + [[0, Y0 + 5.3, z] for z in (2.95, 3.15)] + [[x, Y0 + 4.15, -2.95] for x in (-3.3, 3.3)] + [[0, Y0 + 5.3, -2.95]], STONE_L)
box(-1.0, Y0 + 4.4, 3.12, 1.0, Y0 + 4.9, 3.2, GOLD)               # gold emblem on the pediment
pts = [[math.cos(a) * r * 1.6, Y0 + 4.9 + h * 1.5, math.sin(a) * r * 1.6 - .6] for a in np.linspace(0, 2 * math.pi, 14, endpoint=False) for (r, h) in ((1, 0), (.85, .5), (.5, .85))] + [[0, Y0 + 6.5, -.6]]
hull(pts, GOLD); cyl(0, Y0 + 6.4, Y0 + 7.2, -.6, .05, GOLD, 6); ball(0, Y0 + 7.3, -.6, .14, CRYSTAL, 1)
box(-1.0, Y0, 1.58, 1.0, Y0 + 2.8, 1.7, WOOD_D)                  # big door
for y in (.6, 1.4, 2.2): box(-1.02, Y0 + y, 1.7, 1.02, Y0 + y + .12, 1.76, GOLD)
box(-.04, Y0, 1.7, .04, Y0 + 2.8, 1.76, GOLD); ball(-.25, Y0 + 1.3, 1.78, .07, GOLD, 0); ball(.25, Y0 + 1.3, 1.78, .07, GOLD, 0)
for (p0, p1, q0, q1) in ((-1.25, -1.0, 0, 3.05), (1.0, 1.25, 0, 3.05), (-1.25, 1.25, 2.8, 3.05)):
    box(p0, Y0 + q0, 1.58, p1, Y0 + q1, 1.8, STONE)
for sx in (-1, 1):                                                # torches, gold heaps, gems
    cyl(sx * 1.7, Y0, Y0 + 1.6, 1.9, .07, WOOD_D, 6); hull([[sx * 1.7 + dx, Y0 + 1.6, 1.9 + dz] for dx in (-.15, .15) for dz in (-.15, .15)] + [[sx * 1.7, Y0 + 1.45, 1.9]], METAL_D)
    hull([[sx * 1.7 + dx, Y0 + 1.62, 1.9 + dz] for dx in (-.1, .1) for dz in (-.1, .1)] + [[sx * 1.7, Y0 + 2.1, 1.9]], FLAME)
box(-1.6, Y0 + 3.85, 3.15, 1.6, Y0 + 4.12, 3.22, SIGN)            # name board
export("treasury")

# ---------------------------------------------------------------- fish shop (sea-blue roof, awning, counter with fish)
for x in (-2.4, 2.4):
    for z in (-1.9, 1.9): cyl(x, 0, .5, z, .14, WOOD_D, 8)
box(-2.6, .5, -2.1, 2.6, .62, 2.6, PLANK)                        # deck (front part is the porch)
for k in range(1, 13): box(-2.6 + k * .4 - .02, .62, -2.1, -2.6 + k * .4 + .02, .625, 2.6, WOOD_D)
FH = 3.0
box(-2.3, .62, -1.9, 2.3, FH, -1.7, "#7fb4d6")                    # back wall
for sx in (-1, 1): box(sx * 2.3 - (.2 if sx > 0 else 0), .62, -1.9, sx * 2.3 + (0 if sx > 0 else .2), FH, .9, "#7fb4d6")
box(-2.3, 2.2, .7, 2.3, FH, .9, "#7fb4d6")                       # front lintel over the counter window
for k in range(6): box(-2.32, .9 + k * .35, -1.92, 2.32, .93 + k * .35, -1.68, WHITE)
for sx in (-1, 1): box(sx * 2.3 - .12, .62, .7, sx * 2.3 + .12, FH, .95, WHITE)
box(-2.2, .62, .55, 2.2, 1.6, 1.0, PLANK); box(-2.3, 1.6, .5, 2.3, 1.7, 1.15, WHITE)  # counter
gable(-2.3, 2.3, -1.9, .95, FH, 1.3, BLUE, over=.35, thick=.14, ridge="z")   # ridge front-to-back, white gables front/back
for z in (-1.9, .75): gable_end(-2.3, 2.3, FH, 1.3, WHITE, z, ridge="z")
for i in range(10):                                                # striped awning over the counter
    x0 = -2.4 + i * .48
    boxc(x0 + .24, 2.65, 1.55, .48, .08, 1.3, BLUE if i % 2 else WHITE, pitch=22)   # falls to the front posts
for sx in (-1, 1): cyl(sx * 2.45, .62, 2.42, 2.15, .05, WOOD_D, 6)
for k in range(16):
    a0, a1 = k / 16 * 2 * math.pi, (k + 1) / 16 * 2 * math.pi
    beam([-2.42, 1.9 + math.sin(a0) * .32, -.4 + math.cos(a0) * .32], [-2.42, 1.9 + math.sin(a1) * .32, -.4 + math.cos(a1) * .32], .1, RED if k // 4 % 2 else WHITE)
export("fish_shop")

# ---------------------------------------------------------------- car parking spot (one car), 3.4 x 6 m
box(-1.8, 0, -3.1, 1.8, .06, 3.1, ASPH)
for sx in (-1, 1): box(sx * 1.7 - .06, .06, -3.0, sx * 1.7 + .06, .07, 3.0, LINE)
box(-1.7, .06, -3.0, 1.7, .07, -2.88, LINE)
box(-.9, .06, -2.6, .9, .2, -2.4, YEL)
for k in range(4): box(-.9 + k * .45, .2, -2.6, -.9 + k * .45 + .22, .205, -2.4, METAL_D)
for sx in (-1, 1):
    cyl(sx * 1.8, 0, .9, 3.1, .1, YEL, 8); cyl(sx * 1.8, .4, .55, 3.1, .105, METAL_D, 8)
cyl(-2.2, 0, 2.2, -2.9, .05, METAL_D, 6)
box(-2.55, 1.6, -2.94, -1.85, 2.3, -2.86, BLUE)
box(-2.38, 1.7, -2.86, -2.28, 2.2, -2.82, LINE); box(-2.38, 2.1, -2.86, -2.05, 2.2, -2.82, LINE); box(-2.38, 1.92, -2.86, -2.05, 2.0, -2.82, LINE); box(-2.12, 1.95, -2.86, -2.03, 2.15, -2.82, LINE)
export("car_pad")

# ---------------------------------------------------------------- helipad
cyl(0, 0, .3, 0, 4.4, STONE, 8); cyl(0, .3, .33, 0, 4.0, ASPH, 8)
for k in range(28):
    a0, a1 = k / 28 * 2 * math.pi, (k + 1) / 28 * 2 * math.pi
    beam([math.cos(a0) * 3.3, .345, math.sin(a0) * 3.3], [math.cos(a1) * 3.3, .345, math.sin(a1) * 3.3], .22, LINE, .03)
box(-1.0, .33, -1.2, -.6, .36, 1.2, YEL); box(.6, .33, -1.2, 1.0, .36, 1.2, YEL); box(-.6, .33, -.2, .6, .36, .2, YEL)
for k in range(8):
    a = k / 8 * 2 * math.pi + math.pi / 8
    ball(math.cos(a) * 4.15, .38, math.sin(a) * 4.15, .09, GREEN_L, 0)
cyl(4.6, 0, 3.0, 0, .05, METAL_D, 6)
hull([[4.62, 2.95 + dy, dz] for dy in (-.18, .18) for dz in (-.18, .18)] + [[4.62, 2.95, -1.3]], FLAME)
export("helipad")
