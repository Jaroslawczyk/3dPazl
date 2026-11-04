"""Road vehicles. Bodies are three views intersected (side profile x plan x front section): that gives the cut corners of the
reference models for very few triangles. Glass is a smaller core inside a body with window holes, so every window comes out
inset and framed at once."""
from __future__ import annotations

import math

from .. import geo
from .kit import Kit, block, chamfer, cylx, cyly, front, plan, rect, side

# L, W, H, wheel r, hood height, belt line, front overhang, rear overhang
CARS = {
    "sedan": (4.5, 1.8, 1.42, 0.33, 0.78, 0.90, 0.88, 0.95), "hatch": (3.9, 1.75, 1.5, 0.32, 0.82, 0.95, 0.8, 0.62),
    "suv": (4.7, 1.92, 1.8, 0.39, 1.02, 1.16, 0.88, 0.85), "sport": (4.4, 1.92, 1.18, 0.34, 0.62, 0.76, 0.92, 0.82),
    "pickup": (5.3, 1.95, 1.84, 0.41, 1.05, 1.18, 0.92, 1.15), "van": (5.0, 2.0, 2.3, 0.36, 1.05, 1.22, 0.7, 0.82),
}


def outer(xr, xf, W, depth):
    """Only the outer `depth` of the width: wheel arches stop there, so the wheel well stays closed inside."""
    return geo.box(xr, W / 2 - depth, -1, xf, W, 5) + geo.box(xr, -W, -1, xf, -W / 2 + depth, 5)


def glasshouse(k: Kit, W, belt, H, xb_r, xt_r, xt_f, xb_f, pillars=(), col="paint", rear_cut=True):
    """Cabin with inset windows. xb_/xt_: its rear and front ends at the belt and at the roof; pillars: x of extra posts."""
    prof = [(xb_r, belt - 0.03), (xt_r, H - 0.03), (xt_r + 0.1, H), (xt_f - 0.1, H), (xt_f, H - 0.03), (xb_f, belt - 0.03)]
    half = W / 2
    sec = [(-half * 0.97, belt - 0.04), (-half * 0.8, H - 0.07), (-half * 0.7, H), (half * 0.7, H), (half * 0.8, H - 0.07), (half * 0.97, belt - 0.04)]
    span = abs(xb_r) + abs(xb_f) + 4
    mid = (xb_r + xb_f) / 2

    def shape(pr, se):
        return side(pr, W + 1) ^ front(se, -span, span)

    i = 0.03
    core = shape([(x + (i if x < mid else -i), z - (i if z > belt else 0)) for x, z in prof], [(y * (1 - 2 * i / W), z - (i if z > belt else 0)) for y, z in sec])
    m = 0.075
    hole = geo.offset2(geo.poly(prof), -m) - geo.rect2(100, 50, 0, belt + 0.05 - 50)  # a sill stays under the windows
    win = geo.subtract(geo.prism_xz(hole, -W, W), [geo.box(x - 0.045, -W, 0, x + 0.045, W, H + 1) for x in pillars])
    g = half * 0.8 - m
    pane = [(-half * 0.86, belt + 0.06), (-g * 0.92, H - m), (g * 0.92, H - m), (half * 0.86, belt + 0.06)]
    cuts = [win, front(pane, mid, span)] + ([front(pane, -span, mid)] if rear_cut else [])
    k.add(geo.subtract(shape(prof, sec), cuts), col)
    k.add(core, "glass")


def seams(k: Kit, body, W, xs, z0, z1):
    """Door lines: thin dark cuts in the surface of the body."""
    for x in xs:
        for s in (-1, 1):
            k.paint(body, "dark", x=(x, x + 0.016), y=sorted((s * W * 0.42, s * W)), z=(z0, z1), grad=False)


def handles(k: Kit, W, xs, z):
    for x in xs:
        for s in (-1, 1):
            k.add(geo.boxc(0.15, 0.03, 0.03, x, s * (W / 2 + 0.002), z), "chrome", False)


def mirrors(k: Kit, x, y, z, big=False):
    w, h = (0.1, 0.32) if big else (0.09, 0.11)
    for s in (-1, 1):
        k.add(geo.hull([(x - w, s * y, z - h / 2), (x - w, s * (y + 0.2), z - h / 2), (x - w, s * (y + 0.2), z + h / 2), (x - w, s * y, z + h / 2),
                        (x, s * (y + 0.03), z - h / 3), (x, s * (y + 0.17), z - h / 3), (x, s * (y + 0.17), z + h / 3), (x, s * (y + 0.03), z + h / 3)]), "paint")
        k.add(geo.boxc(0.025, 0.14, 0.02, x - w / 2, s * (y - 0.02), z - h / 3), "dark", False)


def wipers(k: Kit, x, z, W):
    for y in (-W * 0.22, W * 0.12):
        k.add(geo.beam((x, y, z), (x + 0.05, y + W * 0.24, z + 0.015), 0.022, 0.012), "black", False)


def number(k: Kit, letter="A"):
    return k.p["text"] or f"{letter}{k.R.randint(100, 999)}BC"


def bumper(k: Kit, outline, x0, x1, z):
    """Follows the body outline a little proud of it and wraps around the corners."""
    wrap = geo.box(x0, -9, 0, x1, 9, 9)
    k.add(plan(outline, z, z + 0.16) ^ wrap, "dark")
    if k.d >= 2:
        k.add(plan(outline, z + 0.066, z + 0.094) ^ wrap, "steel", False)


def car(k: Kit, style, livery=None):
    L, W, H, r, hood, belt, fo, ro = CARS[style]
    L *= k.p["length"]
    xf, xr = L / 2, -L / 2
    axf, axr = xf - fo, xr + ro
    sill = r * 0.72
    cab_f, cab_r = {"sedan": (axf - 0.5, axr + 0.1), "hatch": (axf - 0.25, xr + 0.06), "suv": (axf - 0.35, xr + 0.1), "sport": (axf - 0.75, axr - 0.25),
                    "pickup": (axf - 0.5, axr + 1.5), "van": (axf + 0.3, xr + 0.04)}[style]
    tail = belt + 0.05 if style in ("sedan", "sport") else belt - 0.04
    prof = [(xr, sill + 0.14), (xr + 0.02, tail - 0.08), (xr + 0.12, tail), (cab_f, belt + 0.02), (xf - 0.42, hood + 0.05), (xf - 0.1, hood - 0.03), (xf, hood - 0.16),
            (xf, sill + 0.14), (xf - 0.14, sill), (xr + 0.14, sill)]
    sec = [(-W / 2 + 0.05, 0), (-W / 2, sill + 0.2), (-W / 2, belt - 0.18), (-W / 2 + 0.09, belt + 0.1), (W / 2 - 0.09, belt + 0.1), (W / 2, belt - 0.18), (W / 2, sill + 0.2), (W / 2 - 0.05, 0)]
    outline = chamfer(rect(L, W), [0.26, 0.34, 0.34, 0.26])
    lower = side(prof, W) ^ plan(outline, 0, 5) ^ front(sec, xr - 1, xf + 1)
    cuts = [cyly(r * 1.18, -W, W, x, r, k.seg) ^ outer(xr, xf, W, 0.3) for x in (axf, axr)]
    if style == "pickup":
        cuts.append(block(xr + 0.1, cab_r - 0.08, -W / 2 + 0.09, W / 2 - 0.09, belt - 0.48, 2))
    body = k.add(geo.subtract(lower, cuts), "paint")
    xt_f = cab_f - {"sedan": 0.65, "hatch": 0.6, "suv": 0.5, "sport": 0.72, "pickup": 0.5, "van": 0.75}[style]
    xt_r = cab_r + {"sedan": 0.62, "hatch": 0.14, "suv": 0.12, "sport": 0.9, "pickup": 0.1, "van": 0.08}[style]
    mid = (xt_f + xt_r) / 2
    if style == "van":
        glasshouse(k, W, belt, H, cab_r, xt_r, xt_f, cab_f, [xt_f - 0.1], rear_cut=False)
        k.add(geo.box(xr + 0.07, -W / 2 + 0.03, belt - 0.1, xt_f - 0.25, W / 2 - 0.03, H - 0.04), "paint")  # blind cargo wall
    else:
        glasshouse(k, W, belt, H, cab_r, xt_r, xt_f, cab_f, [] if style in ("sport", "pickup") else [mid])
    zl, zt = hood - 0.25, tail - 0.2
    for s in (-1, 1):  # lamps are painted into the body, so they follow its cut corners
        y = sorted((s * W * 0.2, s * W * 0.52))
        k.paint(body, "lamp", x=(xf - 0.3, None), y=y, z=(zl - 0.075, zl + 0.075), grad=False)
        k.paint(body, "tail", x=(None, xr + (0.09 if style == "pickup" else 0.25)), y=y, z=(zt - 0.07, zt + 0.07), grad=False)  # a pickup has a bed behind that wall
        if k.d >= 2:
            k.paint(body, "amber", x=(xf - 0.3, None), y=sorted((s * W * 0.2, s * W * 0.3)), z=(zl - 0.14, zl - 0.09), grad=False)
    k.paint(body, "dark", z=(None, sill + 0.09))
    zb = sill + 0.1
    proud = chamfer(rect(L + 0.1, W + 0.03), [0.28, 0.36, 0.36, 0.28])
    bumper(k, proud, xf - 0.42, xf + 1, zb)
    bumper(k, proud, xr - 1, xr + 0.42, zb)
    gz = hood - 0.27
    k.paint(body, "dark", x=(xf - 0.05, None), y=(-W * 0.19, W * 0.19), z=(gz - 0.1, gz + 0.1), grad=False)
    if k.d >= 2:
        for i in range(2):
            k.add(geo.boxc(0.02, W * 0.36, 0.022, xf + 0.003, 0, gz - 0.04 + i * 0.06), "chrome", False)
        t = number(k)
        k.decal("plate:" + t, (xf + 0.058, 0, zb + 0.08), (1, 0, 0), 0.5, 0.125)
        k.decal("plate:" + t, (xr - 0.058, 0, zb + 0.08), (-1, 0, 0), 0.5, 0.125)
        mirrors(k, cab_f - 0.12, W / 2 - 0.02, belt + 0.1)
        doors = [cab_f - 0.05, mid + 0.04] + ([] if style in ("van", "sport", "pickup") else [cab_r + 0.25])
        seams(k, body, W, doors, sill + 0.09, belt)
        handles(k, W, [d - 0.17 for d in doors[1:]], belt - 0.09)
        wipers(k, cab_f - 0.05, belt + 0.05, W)
    if k.d >= 3:
        k.add(cylx(0.035, xr - 0.1, xr + 0.15, -W * 0.3, sill + 0.03, 8), "chrome", False)  # exhaust
        k.add(geo.rod((xt_r + 0.15, W * 0.2, H - 0.01), (xt_r - 0.2, W * 0.2, H + 0.3), 0.006, 5), "black", False)  # antenna
        k.add(cyly(0.055, W / 2 - 0.01, W / 2 + 0.003, axr + 0.1 + r * 1.3, belt - 0.12, 8), "dark", False)  # fuel cap
        for x in (axf - r * 1.2, axr - r * 1.2):
            for s in (-1, 1):
                k.add(geo.boxc(0.02, 0.2, 0.17, x, s * (W / 2 - 0.13), sill - 0.14), "black", False)  # mud flaps
    if style == "suv":
        for s in (-1, 1):
            k.add(geo.boxc(abs(xt_f - xt_r) * 0.86, 0.04, 0.05, mid, s * W * 0.34, H + 0.02), "steel", False)  # roof rails
    if style == "pickup":
        for s in (-1, 1):
            k.add(geo.box(xr + 0.12, s * W / 2 - 0.05, belt - 0.02, cab_r, s * W / 2 + 0.05, belt + 0.03), "dark", False)
    for i, (x, y) in enumerate([(axf, W / 2 - 0.13), (axf, -W / 2 + 0.13), (axr, W / 2 - 0.13), (axr, -W / 2 + 0.13)]):
        k.wheel(x, y, r, 0.25, f"wheel_{i}")
    if livery:
        livery(k, body, dict(L=L, W=W, H=H, belt=belt, sill=sill, mid=mid, xf=xf, xr=xr, cab_f=cab_f, cab_r=cab_r, hood=hood))
    return body


# ------------------------------------------------------------------ liveries: repaints of the same body
def side_stripe(k, body, g):
    W, z = g["W"], (g["belt"] - 0.24, g["belt"] - 0.16)
    k.paint(body, "paint2", y=(W * 0.36, None), z=z)
    k.paint(body, "paint2", y=(None, -W * 0.36), z=z)


def racing(k, body, g):
    y, z = (-g["W"] * 0.14, g["W"] * 0.14), (g["hood"] - 0.05, None)
    k.paint(body, "paint2", y=y, z=z, x=(g["cab_f"] - 0.02, None))
    k.paint(body, "paint2", y=y, z=z, x=(None, g["cab_r"]))


def two_tone(k, body, g):
    k.paint(body, "paint2", z=(g["sill"] + 0.09, g["belt"] - 0.3))


LIVERIES = {"plain": None, "stripe": side_stripe, "racing": racing, "two_tone": two_tone}


def taxi(k, body, g):
    W, belt, x, H = g["W"], g["belt"], g["mid"], g["H"]
    for s in (-1, 1):
        k.decal("checker", (x + 0.02, s * (W / 2 + 0.001), belt - 0.28), (0, s, 0), 2.1, 0.22)
    k.add(block(x - 0.08, x + 0.08, -0.26, 0.26, H - 0.01, H + 0.05, 0.02), "black", False)
    k.add(geo.hull([(x - 0.09, -0.25, H + 0.05), (x + 0.09, -0.25, H + 0.05), (x + 0.09, 0.25, H + 0.05), (x - 0.09, 0.25, H + 0.05),
                    (x - 0.03, -0.23, H + 0.2), (x + 0.03, -0.23, H + 0.2), (x + 0.03, 0.23, H + 0.2), (x - 0.03, 0.23, H + 0.2)]), "yellow")
    a = math.atan2(0.06, 0.15)
    n, up = (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a))
    k.decal("text:ТАКСИ", (x + 0.062, 0, H + 0.125), n, 0.42, 0.11, up=up)


def lightbar(k, x, z, w=0.55):
    k.add(block(x - 0.11, x + 0.11, -w, w, z, z + 0.04, 0.03), "black", False)
    k.add(block(x - 0.1, x + 0.1, -w * 0.96, -0.03, z + 0.04, z + 0.14, 0.03), "red")
    k.add(block(x - 0.1, x + 0.1, 0.03, w * 0.96, z + 0.04, z + 0.14, 0.03), "blue")


def police(k, body, g):
    k.paint(body, "paint2", x=(g["cab_r"] + 0.25, g["cab_f"] - 0.05), z=(g["sill"] + 0.09, None))
    lightbar(k, g["mid"], g["H"] - 0.01)
    for s in (-1, 1):
        k.decal("text:ПОЛИЦИЯ", (g["mid"] + 0.06, s * (g["W"] / 2 + 0.001), g["belt"] - 0.3), (0, s, 0), 1.1, 0.24)


# ------------------------------------------------------------------ bus
def bus(k: Kit):
    L, W, H, r = 11.5 * k.p["length"], 2.5, 3.1, 0.5
    xf, xr = L / 2, -L / 2
    sill, belt = 0.42, 1.35
    lower = block(xr, xf, -W / 2, W / 2, sill, belt, 0.18) ^ side([(xr, sill), (xr, belt), (xf - 0.05, belt), (xf, belt - 0.3), (xf, sill + 0.1), (xf - 0.1, sill)], W + 1)
    axf, axr = xf - 2.6, xr + 3.1
    body = k.add(geo.subtract(lower, [cyly(r * 1.2, -W, W, x, r, k.seg) ^ outer(xr, xf, W, 0.34) for x in (axf, axr)]), "paint")
    prof = [(xr, belt - 0.02), (xr, H - 0.1), (xr + 0.12, H), (xf - 0.42, H), (xf - 0.12, H - 0.25), (xf - 0.02, belt - 0.02)]
    sec = [(-W / 2, belt - 0.03), (-W / 2 + 0.05, H - 0.14), (-W / 2 + 0.2, H), (W / 2 - 0.2, H), (W / 2 - 0.05, H - 0.14), (W / 2, belt - 0.03)]
    shell = side(prof, W + 1) ^ front(sec, xr - 1, xf + 1) ^ plan(rect(L, W, 0.18), 0, 5)
    core = side([(x + (0.04 if x < 0 else -0.04), z - (0.04 if z > belt else 0)) for x, z in prof], W + 1) ^ front([(y * 0.97, z - 0.05) for y, z in sec], xr - 1, xf + 1) ^ plan(rect(L - 0.08, W - 0.06, 0.18), 0, 5)
    n = 7
    hole = geo.subtract(geo.box(xr + 0.25, -W, belt + 0.1, xf - 0.25, W, H - 0.55),
                        [geo.box(xr + 0.25 + (L - 0.5) * i / n - 0.05, -W, 0, xr + 0.25 + (L - 0.5) * i / n + 0.05, W, H) for i in range(1, n)])
    wind = front([(-W / 2 + 0.2, belt + 0.08), (-W / 2 + 0.25, H - 0.45), (W / 2 - 0.25, H - 0.45), (W / 2 - 0.2, belt + 0.08)], 0, xf + 1)
    rear = front([(-W / 2 + 0.28, belt + 0.25), (-W / 2 + 0.28, H - 0.6), (W / 2 - 0.28, H - 0.6), (W / 2 - 0.28, belt + 0.25)], xr - 1, 0)
    top = k.add(geo.subtract(shell, [hole, wind, rear]), "paint")
    k.add(core, "glass")
    k.paint(top, "paint2", z=(H - 0.55, H - 0.42))
    k.paint(body, "paint2", z=(belt - 0.3, belt - 0.14))
    k.paint(body, "dark", z=(None, sill + 0.1))
    for s in (-1, 1):
        y = sorted((s * W * 0.2, s * W * 0.48))
        k.paint(body, "lamp", x=(xf - 0.15, None), y=y, z=(0.72, 0.9), grad=False)
        k.paint(body, "tail", x=(None, xr + 0.1), y=y, z=(1.0, 1.25), grad=False)
    if k.d >= 2:
        for x in (xf - 1.25, -0.4):  # two doors on the right side (-Y)
            k.add(geo.boxc(1.15, 0.03, 2.2, x, -W / 2 - 0.002, sill + 0.05), "dark", False)
            for dx in (-0.28, 0.28):
                k.add(geo.boxc(0.46, 0.012, 1.9, x + dx, -W / 2 - 0.02, sill + 0.22), "glass", False)
                k.add(geo.boxc(0.02, 0.02, 0.5, x + dx * 0.25, -W / 2 - 0.03, sill + 0.9), "chrome", False)
        route = k.p["text"] or f"{k.R.randint(2, 99)} ЦЕНТР"
        k.decal("sign:" + route, (xf - 0.2, 0, H - 0.34), (1, 0, 0), 1.5, 0.3)
        k.decal("sign:" + route, (1.5, -W / 2 - 0.002, H - 0.7), (0, -1, 0), 1.3, 0.22)
        t = number(k)
        k.decal("plate:" + t, (xf + 0.03, 0, 0.6), (1, 0, 0), 0.5, 0.125)
        k.decal("plate:" + t, (xr - 0.03, 0, 0.6), (-1, 0, 0), 0.5, 0.125)
        k.add(block(-1.0, 1.0, -0.65, 0.65, H - 0.01, H + 0.22, 0.12), "steel")  # roof air conditioner
        k.add(block(-3.5, -2.8, -0.4, 0.4, H - 0.01, H + 0.08, 0.05), "dark")  # roof hatch
        for s in (-1, 1):
            y = s * (W / 2 + 0.22)
            k.add(geo.rod((xf - 0.3, s * W / 2, H - 0.3), (xf + 0.05, y, H - 0.5), 0.02, 6), "dark", False)
            k.add(block(xf - 0.02, xf + 0.08, y - 0.1, y + 0.1, H - 0.95, H - 0.5, 0.02), "dark")
    if k.d >= 3:
        k.decal("vent", (xr - 0.002, 0, 0.72), (-1, 0, 0), 1.6, 0.4)
        for s in (-1, 1):
            k.add(geo.beam((xf - 0.22, s * 0.75, belt + 0.08), (xf - 0.08, -s * 0.05, belt + 0.1), 0.025, 0.015), "black", False)
    for i, (x, y) in enumerate([(axf, W / 2 - 0.17), (axf, -W / 2 + 0.17), (axr, W / 2 - 0.17), (axr, -W / 2 + 0.17)]):
        k.wheel(x, y, r, 0.32, f"wheel_{i}")


# ------------------------------------------------------------------ trucks
TW, TH, TR = 2.45, 3.0, 0.52  # width, cab height, wheel radius


def truck_cab(k: Kit, xf):
    """Flat-nosed cab, 2.1 m long, ending at xf."""
    W, H = TW, TH
    xr = xf - 2.1
    belt, sill = 1.55, 0.72
    low = block(xr, xf, -W / 2, W / 2, sill, belt, 0.16) ^ side([(xr, sill), (xr, belt), (xf - 0.02, belt), (xf, belt - 0.2), (xf, sill)], W + 1)
    body = k.add(geo.subtract(low, [cyly(TR * 1.2, -W, W, xf - 1.1, TR, k.seg)]), "paint")
    glasshouse(k, W, belt, H, xr, xr + 0.02, xf - 0.28, xf - 0.04, rear_cut=False)
    k.add(geo.box(xr + 0.02, -W / 2 + 0.05, belt - 0.03, xr + 0.5, W / 2 - 0.05, H - 0.05), "paint")  # sleeper wall
    k.paint(body, "dark", x=(xf - 0.05, None), y=(-W * 0.34, W * 0.34), z=(1.0, 1.38), grad=False)
    for s in (-1, 1):
        k.paint(body, "lamp", x=(xf - 0.2, None), y=sorted((s * W * 0.34, s * W * 0.49)), z=(1.08, 1.28), grad=False)
    k.add(block(xf - 0.12, xf + 0.1, -W / 2, W / 2, 0.58, 0.8, 0.05), "dark")
    if k.d >= 2:
        for i in range(4):
            k.add(geo.boxc(0.02, W * 0.64, 0.03, xf + 0.003, 0, 1.06 + i * 0.09), "chrome", False)
        k.decal("plate:" + number(k, "T"), (xf + 0.105, 0, 0.69), (1, 0, 0), 0.5, 0.125)
        mirrors(k, xf - 0.2, W / 2, H - 0.75, big=True)
        seams(k, body, W, [xf - 0.55, xr + 0.52], sill + 0.06, belt)
        handles(k, W, [xr + 0.75], belt - 0.1)
        for s in (-1, 1):
            k.add(geo.boxc(0.6, 0.16, 0.05, xf - 1.85, s * (W / 2 - 0.06), 0.5), "steel", False)  # step under the door
        k.add(block(xf - 0.9, xf - 0.5, -W * 0.3, W * 0.3, H - 0.01, H + 0.13, 0.06), "paint")  # roof fairing
    if k.d >= 3:
        for i in (-1, 0, 1):
            k.add(geo.boxc(0.1, 0.12, 0.05, xf - 0.32, i * 0.4, H - 0.01), "amber", False)  # marker lamps
        wipers(k, xf - 0.1, belt + 0.03, W)
    return xr


def mudguard(k: Kit, x, s):
    y0, y1 = sorted((s * (TW / 2 - 0.42), s * (TW / 2 + 0.03)))
    k.add(geo.subtract(cyly(TR * 1.22, y0, y1, x, TR, k.seg), [cyly(TR * 1.14, -TW, TW, x, TR, k.seg), geo.box(x - 2, -TW, -1, x + 2, TW, TR)]), "dark")


def cargo_box(k: Kit, x0, x1, zb):
    W, H = TW, TH + 0.5
    k.add(block(x0, x1, -W / 2, W / 2, zb + 0.14, H, 0.05), "paint2")
    k.add(geo.box(x0, -W / 2 + 0.04, zb, x1, W / 2 - 0.04, zb + 0.14), "dark")
    if k.d >= 2:
        n = max(3, int((x1 - x0) / 0.7))
        for i in range(n + 1):  # ribs, like a container wall
            x = x0 + 0.04 + (x1 - x0 - 0.08) * i / n
            for s in (-1, 1):
                k.add(geo.boxc(0.05, 0.02, H - 0.22 - zb, x, s * (W / 2 + 0.006), zb + 0.2), "steel", False)
        for s in (-1, 1):
            k.decal("text:ГРУЗЫ", ((x0 + x1) / 2, s * (W / 2 + 0.018), 2.4), (0, s, 0), 3.2, 0.8)
            k.add(geo.boxc(0.04, 0.04, H - 0.3 - zb, x0 - 0.01, s * 0.4, zb + 0.3), "steel", False)  # door rods
        k.decal("hazard", (x0 - 0.004, 0, zb + 0.28), (-1, 0, 0), 2.2, 0.28)


def cargo_tank(k: Kit, x0, x1, zb):
    R0 = 1.0
    zc = zb + 0.15 + R0
    seg = k.seg + 2
    k.add(block(x0, x1, -0.6, 0.6, zb, zc - 0.5), "dark")
    t = k.add(cylx(R0, x0 + 0.25, x1 - 0.25, 0, zc, seg), "paint2")
    k.add(cylx(R0 * 0.72, x0, x0 + 0.25, 0, zc, seg, r2=R0), "paint2")
    k.add(cylx(R0, x1 - 0.25, x1, 0, zc, seg, r2=R0 * 0.72), "paint2")
    k.paint(t, "paint", z=(zc - 0.2, zc + 0.2))
    for x in (x0 + 0.8, (x0 + x1) / 2, x1 - 0.8):
        k.add(cylx(R0 + 0.025, x - 0.05, x + 0.05, 0, zc, seg), "steel", False)
        k.add(geo.cyl(0.26, 0.14, 8, zc + R0 - 0.03, cx=x), "steel")
    if k.d >= 2:
        for s in (-1, 1):
            k.add(geo.rod((x0 + 0.8, s * 0.3, zc + R0 + 0.3), (x1 - 0.8, s * 0.3, zc + R0 + 0.3), 0.025, 6), "steel", False)  # handrail
            for x in (x0 + 0.8, x1 - 0.8):
                k.add(geo.rod((x, s * 0.3, zc + R0 - 0.05), (x, s * 0.3, zc + R0 + 0.3), 0.02, 6), "steel", False)
            k.add(geo.boxc(0.03, 0.03, 1.9, x0 + 0.1, s * 0.17, zb + 0.4), "steel", False)
        for i in range(6):
            k.add(geo.boxc(0.03, 0.34, 0.02, x0 + 0.1, 0, zb + 0.5 + i * 0.32), "steel", False)  # ladder at the back


def cargo_dump(k: Kit, x0, x1, zb):
    W = TW
    z0, z1 = zb + 0.12, 2.5
    outer_ = side([(x0, z0 + 0.25), (x0 - 0.1, z1), (x1 + 0.05, z1 + 0.25), (x1, z0)], W)
    inner = side([(x0 + 0.1, z0 + 0.33), (x0, z1 + 1), (x1 - 0.05, z1 + 1), (x1 - 0.1, z0 + 0.12)], W - 0.2)
    k.add(geo.subtract(outer_, [inner]), "paint2")
    k.add(geo.boxc(x1 - x0 - 0.3, W - 0.24, 0.5, (x0 + x1) / 2, 0, z1 - 0.72), "rust")  # load of earth
    if k.d >= 2:
        for i in range(1, 4):
            for s in (-1, 1):
                k.add(geo.boxc(0.08, 0.05, z1 - z0 - 0.2, x0 + (x1 - x0) * i / 4, s * (W / 2 + 0.02), z0 + 0.1), "paint2")
        k.add(geo.box(x1 - 0.1, -W / 2 + 0.2, z1 + 0.2, x1 + 0.45, W / 2 - 0.2, z1 + 0.28), "paint2")  # cab guard
        k.decal("hazard", (x0 - 0.06, 0, z0 + 0.6), (-1, 0, 0), 1.8, 0.26)


CARGO = {"box": cargo_box, "tank": cargo_tank, "dump": cargo_dump}


def truck(k: Kit, cargo):
    W = TW
    L = 8.2 * k.p["length"]
    xf, xr = L / 2, -L / 2
    cab_end = truck_cab(k, xf)
    k.add(geo.box(xr + 0.15, -W * 0.33, 0.6, cab_end + 0.2, W * 0.33, 0.85), "dark")  # chassis
    k.add(geo.box(xr + 0.02, -W * 0.45, 0.46, xr + 0.12, W * 0.45, 0.72), "dark")  # rear bar
    axs = [xf - 1.1, xr + 1.3] + ([xr + 2.5] if L > 7.5 else [])
    CARGO[cargo](k, xr + 0.1, cab_end - 0.14, 0.85)
    for x in axs[1:]:
        for s in (-1, 1):
            mudguard(k, x, s)
    if k.d >= 2:
        for s in (-1, 1):
            k.add(cylx(0.2, cab_end - 1.05, cab_end - 0.15, s * (W / 2 - 0.2), 0.66, 10), "steel")  # fuel tank
    if k.d >= 3:
        k.add(geo.cyl(0.07, 1.8, 8, 1.5, cx=cab_end - 0.08, cy=W * 0.3), "chrome", False)  # exhaust stack
        for s in (-1, 1):
            k.add(geo.boxc(0.16, 0.06, 0.05, xr + 0.08, s * W * 0.3, 0.68), "tail", False)
    for i, x in enumerate(axs):
        for j, s in enumerate((-1, 1)):
            k.wheel(x, s * (W / 2 - 0.2), TR, 0.38, f"wheel_{i * 2 + j}")


def fire_truck(k: Kit):
    k.default_colors("#d42a22", "#eef0f4")
    W, H = TW, TH
    L = 8.4 * k.p["length"]
    xf, xr = L / 2, -L / 2
    cab_end = truck_cab(k, xf)
    k.add(geo.box(xr + 0.15, -W * 0.33, 0.6, cab_end + 0.2, W * 0.33, 0.85), "dark")
    box = k.add(block(xr + 0.05, cab_end - 0.1, -W / 2, W / 2, 0.75, H - 0.1, 0.06), "paint")
    k.paint(box, "paint2", z=(1.65, 1.82))
    x0, x1 = xr + 2.0, cab_end - 0.3
    n = 2
    for i in range(n):  # roller shutters of the equipment lockers
        a, b = x0 + (x1 - x0) * i / n + 0.06, x0 + (x1 - x0) * (i + 1) / n - 0.06
        for s in (-1, 1):
            k.add(geo.boxc(b - a, 0.03, 0.95, (a + b) / 2, s * (W / 2 + 0.002), 1.85), "steel")
            if k.d >= 2:
                for j in range(5):
                    k.add(geo.boxc(b - a, 0.012, 0.018, (a + b) / 2, s * (W / 2 + 0.02), 1.95 + j * 0.17), "dark", False)
    if k.d >= 2:
        k.decal("hazard", (xr + 0.048, 0, 1.0), (-1, 0, 0), 2.1, 0.26)
        for s in (-1, 1):
            k.decal("text:ПОЖАРНАЯ", (xr + 1.05, s * (W / 2 + 0.002), 1.25), (0, s, 0), 1.7, 0.42)
    lightbar(k, xf - 0.7, H + 0.13, 0.7)
    z = H - 0.1
    k.add(geo.union([geo.box(xr - 0.1, s * 0.42 - 0.04, z + 0.2, cab_end + 0.5, s * 0.42 + 0.04, z + 0.34) for s in (-1, 1)]), "steel")  # ladder
    for i in range(int((cab_end + 0.6 - xr) / 0.4)):
        k.add(geo.boxc(0.05, 0.84, 0.05, xr + 0.1 + i * 0.4, 0, z + 0.25), "steel", False)
    k.add(block(xr + 1.1, xr + 1.9, -0.5, 0.5, z - 0.02, z + 0.2, 0.06), "dark")
    for s in (-1, 1):
        k.add(geo.boxc(0.14, 0.1, 0.24, cab_end - 0.3, s * 0.42, z - 0.02), "dark")
    if k.d >= 3:
        for s in (-1, 1):  # hose reels on the back
            k.add(cylx(0.3, xr - 0.08, xr + 0.06, s * 0.6, 2.1, 12), "wood_dark")
            k.add(cylx(0.08, xr - 0.11, xr - 0.07, s * 0.6, 2.1, 8), "chrome", False)
    for i, x in enumerate((xf - 1.1, xr + 1.7)):
        for j, s in enumerate((-1, 1)):
            k.wheel(x, s * (W / 2 - 0.2), TR, 0.38, f"wheel_{i * 2 + j}")


# ------------------------------------------------------------------ tractor, motorcycle
def tractor(k: Kit):
    rf, rr = 0.46, 0.82
    k.default_colors("#3fae78", "#f8c13a")
    zb = 0.72
    hood = side([(-0.5, zb), (-0.5, 1.5), (1.45, 1.42), (1.7, 1.3), (1.75, 1.0), (1.72, zb)], 0.86) ^ front([(-0.43, 0), (-0.43, 1.28), (-0.3, 1.5), (0.3, 1.5), (0.43, 1.28), (0.43, 0)], -3, 3)
    h = k.add(hood, "paint")
    k.paint(h, "dark", x=(1.65, None), y=(-0.34, 0.34), z=(0.84, 1.27), grad=False)
    k.paint(h, "paint2", z=(1.0, 1.08), x=(None, 1.6))
    for s in (-1, 1):
        k.paint(h, "lamp", x=(1.6, None), y=sorted((s * 0.2, s * 0.4)), z=(1.2, 1.3), grad=False)
    k.add(geo.box(-1.2, -0.42, 0.5, 1.5, 0.42, zb + 0.02), "dark")
    z0, z1 = 1.45, 2.65
    for x, d in ((-1.2, -0.05), (-0.08, 0.1)):  # open frame cab
        for s in (-1, 1):
            k.add(geo.beam((x, s * 0.62, z0 - 0.3), (x + d, s * 0.56, z1), 0.07, 0.07), "dark", False)
    k.add(block(-1.32, 0.16, -0.72, 0.72, z1, z1 + 0.09, 0.08), "paint")
    k.add(geo.box(-1.25, -0.66, z0 - 0.34, 0.02, 0.66, z0 - 0.26), "dark")
    k.add(geo.boxc(0.02, 1.14, 1.0, -0.02, 0, z0 + 0.12), "glass", False)
    k.add(geo.boxc(0.44, 0.46, 0.09, -0.8, 0, z0 - 0.15), "seat")
    k.add(geo.boxc(0.09, 0.44, 0.5, -1.0, 0, z0 - 0.08), "seat")
    k.add(geo.rod((-0.25, 0, z0 - 0.26), (-0.42, 0, z0 + 0.25), 0.018, 6), "black", False)
    k.add(geo.cyl(0.17, 0.03, 12, 0).rotate([0, -30, 0]).translate([-0.43, 0, z0 + 0.25]), "black", False)
    k.add(geo.cyl(0.05, 0.9, 8, 1.42, cx=0.9, cy=0.2), "dark", False)  # exhaust
    k.add(geo.cyl(0.07, 0.04, 8, 2.32, cx=0.9, cy=0.2), "dark", False)
    if k.d >= 2:
        k.add(geo.cyl(0.08, 0.3, 8, 1.4, cx=0.9, cy=-0.2), "chrome", False)  # air intake
        for s in (-1, 1):
            k.add(geo.subtract(cyly(rr * 1.1, s * 0.86 - 0.26, s * 0.86 + 0.26, -0.75, rr, k.seg + 2), [cyly(rr * 1.05, -2, 2, -0.75, rr, k.seg + 2), geo.box(-3, -2, -1, 3, 2, rr + 0.12)]), "paint")
        for i in range(4):
            k.add(geo.boxc(0.1, 0.7, 0.08, 1.8, 0, 0.58 + i * 0.1), "dark", False)  # front ballast
    if k.d >= 3:
        k.add(geo.rod((-1.2, 0, 0.62), (-1.75, 0, 0.62), 0.04, 6), "steel", False)  # hitch
        k.add(geo.cyl(0.07, 0.11, 8, z1 + 0.09, cx=-0.4), "amber", False)  # beacon
    for i, (x, y, r, w, lugs) in enumerate([(1.08, 0.72, rf, 0.26, 12), (1.08, -0.72, rf, 0.26, 12), (-0.75, 0.86, rr, 0.5, 18), (-0.75, -0.86, rr, 0.5, 18)]):
        k.wheel(x, y, r, w, f"wheel_{i}", hub="paint2", lugs=lugs)


def motorcycle(k: Kit):
    r = 0.32
    xf, xr = 0.75, -0.72
    k.wheel(xf, 0, r, 0.12, "wheel_0", hub="dark", rim=0.72)
    k.wheel(xr, 0, r, 0.16, "wheel_1", hub="dark", rim=0.72)
    for s in (-1, 1):  # fork and swingarm
        k.add(geo.rod((xf, s * 0.09, r), (0.48, s * 0.09, 0.86), 0.022, 6), "chrome", False)
        k.add(geo.rod((xr, s * 0.1, r), (-0.12, s * 0.09, 0.4), 0.02, 6), "dark", False)
    k.add(geo.hull([(x, y, z) for x, z in ((-0.25, 0.3), (0.25, 0.3), (-0.2, 0.56), (0.2, 0.56)) for y in (-0.12, 0.12)]), "dark")  # engine
    t = k.add(side([(-0.2, 0.68), (-0.14, 0.86), (0.28, 0.92), (0.45, 0.82), (0.36, 0.66)], 0.26) ^ front([(-0.13, 0.5), (-0.13, 0.84), (-0.06, 0.95), (0.06, 0.95), (0.13, 0.84), (0.13, 0.5)], -1, 1), "paint")
    k.paint(t, "paint2", x=(0.02, 0.1))
    k.add(geo.rod((0.46, 0, 0.84), (-0.1, 0, 0.5), 0.03, 6), "dark", False)
    k.add(side([(-0.65, 0.76), (-0.18, 0.7), (-0.18, 0.76), (-0.6, 0.84)], 0.22), "seat")
    k.add(geo.hull([(x, y, z) for x, y0 in ((-0.82, 0.05), (-0.45, 0.07)) for y in (-y0, y0) for z in (0.71, 0.76)]), "paint")  # tail
    k.add(geo.rod((0.5, -0.34, 1.02), (0.5, 0.34, 1.02), 0.012, 6), "chrome", False)
    k.add(geo.rod((0.48, 0, 0.86), (0.5, 0, 1.02), 0.022, 6), "dark", False)
    k.add(cylx(0.07, 0.5, 0.62, 0, 0.92, 10, r2=0.08), "chrome")
    k.add(cylx(0.055, 0.615, 0.625, 0, 0.92, 10), "lamp", False)
    for s in (-1, 1):
        k.add(cyly(0.02, s * 0.4 - 0.06, s * 0.4 + 0.06, 0.5, 1.02, 6), "black", False)  # grips
    k.add(geo.subtract(cyly(r * 1.15, -0.09, 0.09, xf, r, 12), [cyly(r * 1.06, -1, 1, xf, r, 12), geo.box(0, -1, -1, 2, 1, 0.55)]), "paint")
    k.add(geo.subtract(cyly(r * 1.18, -0.1, 0.1, xr, r, 12), [cyly(r * 1.08, -1, 1, xr, r, 12), geo.box(-2, -1, -1, 0, 1, 0.5)]), "dark")
    k.add(geo.boxc(0.03, 0.09, 0.05, -0.82, 0, 0.72), "tail", False)
    k.add(geo.rod((-0.05, -0.15, 0.32), (-0.72, -0.17, 0.45), 0.04, 8), "chrome", False)  # exhaust
    if k.d >= 2:
        k.add(cylx(0.05, -0.92, -0.72, -0.17, 0.45, 8), "chrome", False)
        for s in (-1, 1):
            k.add(geo.rod((0.46, s * 0.23, 1.02), (0.5, s * 0.25, 1.17), 0.008, 5), "black", False)  # mirrors
            k.add(geo.boxc(0.02, 0.1, 0.06, 0.5, s * 0.25, 1.15), "black", False)
            k.add(geo.boxc(0.14, 0.09, 0.02, -0.16, s * 0.2, 0.3), "black", False)  # foot pegs
    if k.d >= 3:
        k.add(geo.rod((-0.05, -0.1, 0.3), (-0.2, -0.28, 0.02), 0.012, 5), "steel", False)  # side stand
