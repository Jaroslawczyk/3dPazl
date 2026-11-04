"""Boats and ships. Hull = convex hull of the deck outline and a smaller keel outline; on top sits the thick bright rim that
carries the look of the reference boats. Hull colours are bands cut into the surface, portholes are tiny separate rings."""
from __future__ import annotations

from .. import geo
from .kit import Kit, block, cylx, plan, rect, ring, side


def deck(L, B, bow=0.34, stern=0.8):
    """Deck outline: wide square stern, sharp bow; stern = share of the beam kept at the transom."""
    h = B / 2
    return [(-L / 2, -h * stern), (-L * 0.42, -h), (L * 0.1, -h), (L * bow, -h * 0.62), (L / 2, 0),
            (L * bow, h * 0.62), (L * 0.1, h), (-L * 0.42, h), (-L / 2, h * stern)]


def hull_shape(pts, D, keel=0.62, rake=0.86):
    return geo.hull([(x, y, D) for x, y in pts] + [(x * rake - 0.02 * abs(x), y * keel, 0) for x, y in pts])


def rim(k: Kit, pts, z0, z1, grow, col="paint2"):
    k.add(plan(geo_points(geo.offset2(geo.poly(pts), grow)), z0, z1), col)


def geo_points(cs):
    """Largest outline of a 2D shape as a point list."""
    return max((list(map(tuple, c)) for c in cs.to_polygons()), key=len)


def open_hull(k: Kit, L, B, D, col="paint", rimw=None, keel=0.62, bow=0.34, stern=0.8, sole=0.42):
    """Hull with a thick rim and an open cockpit down to `sole` of its depth. Returns the deck outline and the hull piece."""
    pts = deck(L, B, bow, stern)
    t = rimw or B * 0.07
    well = plan(geo_points(geo.offset2(geo.poly(pts), -t)), D * sole, D * 2)
    h = k.add(geo.subtract(hull_shape(pts, D, keel), [well]), col)
    collar = plan(geo_points(geo.offset2(geo.poly(pts), t * 0.5)), D * 0.86, D * 1.04)
    k.add(geo.subtract(collar, [well]), "paint2")
    return pts, h


def cabin(k: Kit, x0, x1, w, z0, h, col="white", roof="paint", posts=2, c=0.12):
    """Deckhouse: walls around a glass core, a roof with an overhang."""
    z1 = z0 + h
    wall = block(x0, x1, -w / 2, w / 2, z0, z1, c)
    k.add(block(x0 + 0.03, x1 - 0.03, -w / 2 + 0.03, w / 2 - 0.03, z0, z1, c), "glass")
    wz0, wz1 = z0 + h * 0.42, z1 - h * 0.12
    win = geo.box(x0 + 0.1, -w, wz0, x1 - 0.1, w, wz1)
    win = geo.subtract(win, [geo.box(x0 + (x1 - x0) * (i + 1) / (posts + 1) - 0.05, -w, wz0, x0 + (x1 - x0) * (i + 1) / (posts + 1) + 0.05, w, wz1) for i in range(posts)])
    fr = geo.box(x0 + (x1 - x0) / 2, -w / 2 + 0.12, wz0, x1 + 1, w / 2 - 0.12, wz1)
    bk = geo.box(x0 - 1, -w / 2 + 0.12, wz0, x0 + (x1 - x0) / 2, w / 2 - 0.12, wz1)
    k.add(geo.subtract(wall, [win, fr, bk]), col)
    k.add(block(x0 - 0.08, x1 + 0.12, -w / 2 - 0.08, w / 2 + 0.08, z1, z1 + max(0.08, h * 0.07), c + 0.04), roof)


def funnel(k: Kit, x, z, r, h, col="paint", band="black", y=0.0):
    f = k.add(ring(r, r * 0.16, h, k.seg, z, x, y), col)
    k.paint(f, band, z=(z + h * 0.78, None))


def porthole(k: Kit, x, y, z, r):
    """Ring plus glass: 12-16 triangles each, in the real ones 28."""
    s = 1 if y > 0 else -1
    k.add(geo.cyl(r, 0.02, 8, 0).rotate([-90 * s, 0, 0]).translate([x, y, z]), "chrome", False)
    k.add(geo.cyl(r * 0.68, 0.03, 8, 0).rotate([-90 * s, 0, 0]).translate([x, y, z]), "dark", False)


def rail(k: Kit, pts, z, h=0.5, every=2.0, r=0.02):
    """Handrail along a polyline, with posts."""
    for a, b in zip(pts, pts[1:]):
        k.add(geo.rod((*a, z + h), (*b, z + h), r, 5), "steel", False)
        n = max(1, int(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 / every))
        for i in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            k.add(geo.rod((*p, z), (*p, z + h), r, 5), "steel", False)


def lifering(k: Kit, x, y, z, r=0.3):
    s = 1 if y > 0 else -1
    m = geo.subtract(geo.cyl(r, 0.07, 10, 0), [geo.cyl(r * 0.55, 0.3, 10, -0.1)]).rotate([-90 * s, 0, 0]).translate([x, y, z])
    p = k.add(m, "white", False)
    k.paint(p, "red", x=(x - r * 0.3, x + r * 0.3), grad=False)


def bollard(k: Kit, x, y, z, r=0.07):
    k.add(geo.cyl(r, r * 2.4, 8, z, cx=x, cy=y), "dark", False)
    k.add(geo.cyl(r * 1.45, r * 0.5, 8, z + r * 2.4, cx=x, cy=y), "dark", False)


def mast(k: Kit, x, z, h, r=0.06, y=0.0):
    k.add(geo.cyl(r, h, 8, z, r2=r * 0.5, cx=x, cy=y), "steel", False)


def flag(k: Kit, x, z, w=0.6, h=0.36, col="red", y=0.0):
    k.add(geo.hull([(x, y - 0.012, z), (x, y + 0.012, z), (x, y - 0.012, z + h), (x, y + 0.012, z + h), (x - w, y, z + h * 0.5)]), col, False)


def radar(k: Kit, x, z):
    k.add(geo.cyl(0.04, 0.26, 6, z, cx=x), "steel", False)
    k.add(geo.boxc(0.1, 0.62, 0.06, x, 0, z + 0.26), "white", False)


def rowboat(k: Kit):
    k.default_colors("#c98a5a", "#e2bb8c")
    L, B, D = 3.2 * k.p["length"], 1.15, 0.5
    pts, h = open_hull(k, L, B, D, "paint", keel=0.5, bow=0.3, stern=0.62, sole=0.24)
    k.paint(h, "wood_dark", z=(None, 0.1))
    for x in (-0.95, 0.0, 0.75):
        k.add(geo.boxc(0.26, B * (0.9 if x < 0.5 else 0.72), 0.04, x, 0, D * 0.68), "wood")  # thwarts
    if k.d >= 2:
        for i in range(5):  # ribs inside
            k.add(geo.boxc(0.05, B * 0.76, 0.03, -1.0 + i * 0.5, 0, D * 0.24), "wood_dark", False)
        for s in (-1, 1):  # oars and rowlocks
            k.add(geo.beam((-0.55, s * 0.5, D + 0.06), (0.9, s * 0.2, D * 0.75), 0.03, 0.03), "wood", False)
            k.add(geo.boxc(0.34, 0.015, 0.1, 1.04, s * 0.17, D * 0.7), "wood", False)
            k.add(geo.cyl(0.02, 0.08, 6, D, cx=-0.1, cy=s * B * 0.47), "dark", False)
    if k.d >= 3:
        k.add(geo.subtract(geo.cyl(0.06, 0.03, 8, 0).rotate([0, 90, 0]).translate([L / 2 - 0.04, 0, D * 0.8]), [geo.cyl(0.035, 1, 8, -0.5).rotate([0, 90, 0]).translate([L / 2 - 0.04, 0, D * 0.8])]), "dark", False)


def speedboat(k: Kit):
    k.default_colors("#3fae78", "#eef0f4")
    L, B, D = 5.4 * k.p["length"], 2.1, 1.0
    pts, h = open_hull(k, L, B, D, "paint2", keel=0.42, bow=0.26, stern=0.82, sole=0.52)
    k.paint(h, "paint", z=(D * 0.46, D * 0.6))
    k.paint(h, "dark", z=(None, D * 0.16))
    k.add(geo.hull([(L * 0.12, -B * 0.42, D), (L * 0.12, B * 0.42, D), (L * 0.42, 0, D), (L * 0.12, -B * 0.42, D * 0.7), (L * 0.12, B * 0.42, D * 0.7), (L * 0.42, 0, D * 0.7), (L * 0.15, 0, D * 1.1)]), "paint")
    zw = D * 1.02
    k.add(geo.hull([(L * 0.1, -B * 0.42, zw), (L * 0.1, B * 0.42, zw), (L * 0.14, -B * 0.42, zw), (L * 0.14, B * 0.42, zw), (L * 0.02, -B * 0.32, zw + 0.42), (L * 0.02, B * 0.32, zw + 0.42), (L * 0.05, -B * 0.32, zw + 0.42), (L * 0.05, B * 0.32, zw + 0.42)]), "glass")
    for y in (-0.42, 0.42):  # seats
        k.add(block(-0.45, 0.1, y - 0.28, y + 0.28, D * 0.52, D * 0.82, 0.05), "seat")
        k.add(block(-0.55, -0.42, y - 0.27, y + 0.27, D * 0.82, D * 1.28, 0.03), "seat")
    k.add(block(-L * 0.46, -L * 0.3, -B * 0.4, B * 0.4, D * 0.52, D * 0.86, 0.05), "seat")  # rear bench
    # outboard engine
    k.add(block(-L / 2 - 0.42, -L / 2 + 0.02, -0.21, 0.21, D * 0.8, D * 1.32, 0.08), "black")
    k.add(geo.boxc(0.2, 0.14, D * 0.8, -L / 2 - 0.2, 0, D * 0.02), "dark")
    if k.d >= 2:
        k.add(geo.cyl(0.13, 0.05, 8, D * 1.02, cx=L * 0.04, cy=0.42), "black", False)  # steering wheel
        for s in (-1, 1):
            k.add(geo.rod((L * 0.28, s * B * 0.2, D * 1.05), (L * 0.4, s * B * 0.08, D * 1.05), 0.02, 5), "chrome", False)  # bow rails
        k.decal("number:" + (k.p["text"] or str(k.R.randint(1, 99))), (L * 0.2, B / 2 + 0.02, D * 0.72), (0, 1, 0), 0.8, 0.2)
        k.decal("number:" + (k.p["text"] or str(k.R.randint(1, 99))), (L * 0.2, -B / 2 - 0.02, D * 0.72), (0, -1, 0), 0.8, 0.2)
    if k.d >= 3:
        k.add(geo.rod((-L * 0.42, 0, D * 1.02), (-L * 0.42, 0, D * 1.8), 0.012, 5), "steel", False)
        flag(k, -L * 0.42, D * 1.55, 0.36, 0.22, "paint")
        k.add(geo.boxc(0.08, 0.04, 0.03, L * 0.44, 0.04, D * 1.03), "tail", False)
        k.add(geo.boxc(0.08, 0.04, 0.03, L * 0.44, -0.04, D * 1.03), "green", False)


def sailboat(k: Kit):
    k.default_colors("#eef0f4", "#f0683a")
    L, B, D = 7.5 * k.p["length"], 2.5, 1.1
    pts, h = open_hull(k, L, B, D, "paint", keel=0.5, bow=0.3, stern=0.72, sole=0.62)
    k.paint(h, "paint2", z=(D * 0.42, D * 0.5))
    k.paint(h, "hull_red", z=(None, D * 0.18))
    k.add(geo.boxc(1.3, 0.14, 1.3, -0.2, 0, -1.1), "dark")  # keel fin
    k.add(block(-L * 0.08, L * 0.25, -B * 0.32, B * 0.32, D * 0.6, D * 1.32, 0.2), "white")
    for s in (-1, 1):
        for x in (L * 0.0, L * 0.09, L * 0.18):
            porthole(k, x, s * B * 0.32, D * 1.1, 0.07)
    xm, zm, Hm = L * 0.1, D * 1.3, 9.2
    k.add(geo.cyl(0.075, Hm, 8, zm, r2=0.045, cx=xm), "steel", False)
    k.add(cylx(0.05, xm - 3.3, xm, 0, zm + 0.9, 6), "steel", False)  # boom
    n = 4  # mainsail in strips with a little belly
    parts = []
    for i in range(n):
        a, b = i / n, (i + 1) / n
        ya, yb = 0.28 * (4 * a * (1 - a)), 0.28 * (4 * b * (1 - b))
        ha, hb = (Hm - 1.7) * (1 - a), (Hm - 1.7) * (1 - b)
        xa, xb = xm - 0.1 - 3.2 * a, xm - 0.1 - 3.2 * b
        base = zm + 1.0
        pts4 = [(xa, ya, base), (xb, yb, base), (xa, ya, base + ha), (xb, yb, base + hb)]
        parts.append(geo.hull([(x, y + d, z) for x, y, z in pts4 for d in (-0.012, 0.012)]))
    s = k.add(geo.union(parts), "canvas")
    k.paint(s, "paint2", z=(zm + 1.0, zm + 1.6))
    jib = geo.hull([(x, y + d, z) for x, y, z in [(xm + 0.15, 0, zm + 8.0), (L * 0.47, 0, D * 1.15), (xm + 0.3, -0.2, zm + 0.7)] for d in (-0.012, 0.012)])
    k.add(jib, "canvas")
    if k.d >= 2:
        k.add(geo.rod((xm, 0, zm + Hm - 0.1), (L * 0.49, 0, D * 1.04), 0.01, 4), "dark", False)  # forestay
        k.add(geo.rod((xm, 0, zm + Hm - 0.1), (-L / 2 + 0.2, 0, D * 1.04), 0.01, 4), "dark", False)  # backstay
        for sd in (-1, 1):
            k.add(geo.rod((xm, 0, zm + Hm * 0.82), (xm - 0.3, sd * B * 0.48, D * 1.04), 0.008, 4), "dark", False)
        flag(k, xm, zm + Hm - 0.3, 0.6, 0.34, "paint2")
        rail(k, [pts[3], pts[4], pts[5]], D * 1.04, 0.45, 1.3, 0.012)
        k.add(geo.boxc(0.26, 0.04, 0.8, -L * 0.5 - 0.05, 0, D * 0.3), "dark", False)  # rudder
        k.add(geo.boxc(1.1, 0.04, 0.03, -L * 0.42, 0, D * 1.12), "wood", False)  # tiller
    if k.d >= 3:
        lifering(k, -L * 0.42, B * 0.47, D * 1.25, 0.22)
        for x in (-L * 0.3, L * 0.34):
            for sd in (-1, 1):
                bollard(k, x, sd * B * (0.42 if x < 0 else 0.25), D * 1.03, 0.04)


def tug(k: Kit):
    k.default_colors("#f0683a", "#eef0f4")
    L, B, D = 14 * k.p["length"], 5.6, 2.8
    pts = deck(L, B, 0.3, 0.92)
    h = k.add(hull_shape(pts, D, 0.68), "paint")
    k.bands(h, [(D * 0.3, "hull_red"), (D * 0.36, "white"), (D * 0.8, "dark")])
    k.add(plan(geo_points(geo.offset2(geo.poly(pts), 0.22)), D * 0.92, D * 1.1), "paint2")
    well = plan(geo_points(geo.offset2(geo.poly(pts), -0.32)), D * 1.03, D * 1.4)
    k.add(geo.subtract(plan(geo_points(geo.offset2(geo.poly(pts), 0.1)), D, D * 1.2), [well]), "paint")  # bulwark
    z = D * 1.03
    cabin(k, -L * 0.1, L * 0.2, B * 0.62, z, 1.7, "white", "paint", 2)
    top = z + 1.82
    cabin(k, L * 0.02, L * 0.17, B * 0.46, top, 1.5, "white", "paint", 1, 0.1)
    funnel(k, -L * 0.2, z, 0.5, 2.3, "paint", "black")
    z2 = top + 1.62
    mast(k, L * 0.09, z2, 2.0, 0.05)
    if k.d >= 2:
        radar(k, L * 0.06, z2)
        n = 12  # tyre fenders along the hull
        for s in (-1, 1):
            for i in range(n // 2):
                x = -L * 0.42 + i * L * 0.13
                y = s * (B / 2 + 0.17 - (0.5 if x > L * 0.16 else 0))
                t = geo.subtract(geo.cyl(0.42, 0.26, 8, 0), [geo.cyl(0.2, 1, 8, -0.4)]).rotate([0, 90, 0]).translate([x, y, D * 0.72])
                k.add(t, "tyre", False)
        for x in (-L * 0.4, L * 0.32):
            bollard(k, x, 0, z, 0.16)
        for s in (-1, 1):
            lifering(k, L * 0.05, s * (B * 0.31 + 0.02), z + 1.05, 0.28)
            for i in range(3):
                porthole(k, L * (0.1 + 0.1 * i), s * (B / 2 - 0.4 * i), D * 0.56, 0.16)
        k.add(geo.cyl(0.3, 0.9, 8, z, cx=-L * 0.32), "dark")  # tow hook post
        k.add(geo.boxc(0.3, 0.18, 0.12, -L * 0.32 - 0.34, 0, z + 0.7), "dark", False)
        flag(k, -L * 0.48, z + 1.5, 0.7, 0.42, "red")
        k.add(geo.rod((-L * 0.48, 0, D), (-L * 0.48, 0, z + 1.9), 0.03, 5), "steel", False)
    if k.d >= 3:
        k.add(geo.rod((L * 0.09, 0, z2 + 1.9), (L * 0.46, 0, D * 1.2), 0.012, 4), "dark", False)
        for s in (-1, 1):
            k.add(geo.boxc(0.34, 0.1, 0.22, L * 0.14, s * (B * 0.23 + 0.05), top + 0.8), "green" if s < 0 else "tail", False)  # side lights
        k.add(geo.cyl(0.26, 0.2, 8, top + 1.62, cx=L * 0.14), "white", False)  # searchlight
        rail(k, [(-L * 0.1, -B * 0.31), (-L * 0.1, B * 0.31)], top - 0.02, 0.8, 1.2)


def fishing(k: Kit):
    k.default_colors("#4f78c9", "#eef0f4")
    L, B, D = 10 * k.p["length"], 3.6, 1.9
    pts = deck(L, B, 0.28, 0.86)
    h = k.add(hull_shape(pts, D, 0.6), "paint")
    k.bands(h, [(D * 0.3, "hull_red"), (D * 0.35, "white")])
    well = plan(geo_points(geo.offset2(geo.poly(pts), -0.2)), D * 0.86, D * 1.4)
    k.add(geo.subtract(hull_shape(pts, D * 1.14, 0.9, 1.0) ^ geo.box(-50, -50, D * 0.9, 50, 50, 50), [well]), "paint2")
    z = D * 0.88
    cabin(k, L * 0.08, L * 0.3, B * 0.56, z, 1.9, "white", "dark", 1)
    k.add(geo.cyl(0.11, 1.7, 8, z + 1.9, cx=L * 0.1, cy=B * 0.2), "dark", False)
    mast(k, -L * 0.02, z, 5.2, 0.08)
    k.add(geo.beam((-L * 0.02, 0, z + 3.0), (-L * 0.42, 0, z + 1.5), 0.07, 0.07), "steel", False)  # derrick
    if k.d >= 2:
        k.add(geo.rod((-L * 0.42, 0, z + 1.5), (-L * 0.42, 0, z + 0.7), 0.01, 4), "dark", False)
        k.add(block(-L * 0.46, -L * 0.36, -0.5, 0.5, z, z + 0.42, 0.05), "orange")  # fish boxes
        k.add(block(-L * 0.34, -L * 0.25, -0.3, 0.72, z, z + 0.3, 0.05), "sky")
        k.add(geo.cyl(0.42, 0.9, 10, 0).rotate([0, 90, 0]).translate([-L * 0.2, -B * 0.25, z + 0.46]), "green")  # net drum
        for s in (-1, 1):
            k.add(geo.boxc(0.14, 0.14, 1.0, -L * 0.14, s * (B * 0.42), z), "wood_dark", False)
            lifering(k, L * 0.2, s * (B * 0.28 + 0.02), z + 0.75, 0.24)
        radar(k, L * 0.2, z + 2.06)
        flag(k, -L * 0.02, z + 4.6, 0.7, 0.4, "red")
    if k.d >= 3:
        for s in (-1, 1):
            for i in range(4):
                k.add(geo.sphere(0.14, 8, (-L * 0.3 + i * 1.3, s * (B / 2 + 0.05), D * 0.74)), "orange", False)  # buoys on the side
        k.add(geo.rod((-L * 0.02, 0, z + 5.1), (L * 0.47, 0, D * 1.1), 0.01, 4), "dark", False)
        k.add(geo.rod((-L * 0.02, 0, z + 5.1), (-L * 0.48, 0, D * 1.1), 0.01, 4), "dark", False)


def container(k: Kit, x, y, z, col, sides=(-1, 1), door=False):
    """Box with ribs on the visible long sides and two door bars at the end, as on the real container models."""
    w, b, h = 6.1, 2.44, 2.6
    k.add(geo.boxc(w, b, h, x, y, z), col)
    if k.d >= 2:
        for i in range(1, 6):
            for s in sides:
                k.add(geo.boxc(0.34, 0.03, h * 0.8, x - w / 2 + w * i / 6, y + s * (b / 2 + 0.002), z + h * 0.1), col, False)
    if k.d >= 3 and door:
        for s in (-1, 1):
            k.add(geo.boxc(0.05, 0.08, h * 0.86, x + w / 2 + 0.01, y + s * 0.4, z + h * 0.07), "steel", False)


def cargo_ship(k: Kit):
    k.default_colors("#3f4250", "#eef0f4")
    L, B, D = 86 * k.p["length"], 15, 8
    pts = deck(L, B, 0.38, 0.9)
    h = k.add(hull_shape(pts, D, 0.8, 0.92), "paint")
    k.bands(h, [(D * 0.42, "hull_red"), (D * 0.45, "white")])
    k.add(plan(geo_points(geo.offset2(geo.poly(pts), 0.25)), D * 0.96, D * 1.02), "paint2")
    x_house = -L * 0.34
    w = B * 0.76
    cabin(k, x_house - 5, x_house + 5, w, D, 4, "white", "dark", 3, 0.3)
    cabin(k, x_house - 4.4, x_house + 4.4, w * 0.84, D + 4.3, 3.6, "white", "dark", 3, 0.3)
    cabin(k, x_house - 3, x_house + 4, w * 1.2, D + 8.2, 2.6, "white", "dark", 4, 0.3)
    funnel(k, x_house - 8.5, D, 1.8, 8, "paint2", "paint")
    k.add(geo.cyl(0.5, 3, 8, D + 10.9, cx=x_house + 1), "steel", False)
    if k.d >= 2:
        radar(k, x_house + 1, D + 13.8)
    colors = ["red", "blue", "green", "orange", "yellow", "teal", "steel", "paint2"]
    rows = int((L * 0.62) / 6.4)
    tiers = {1: 1, 2: 2, 3: 3}[k.d]
    for i in range(rows):
        x = x_house + 8.5 + i * 6.4
        for j in (-1, 0, 1):
            top = tiers - (1 if i in (0, rows - 1) and j else 0)
            for t in range(top if x < L * 0.2 else max(1, top - 1)):
                container(k, x, j * 2.6, D + t * 2.62, k.R.choice(colors), (j,) if j else (), i == rows - 1)
    if k.d >= 2:
        for x in (-L * 0.46, L * 0.3):
            for s in (-1, 1):
                bollard(k, x, s * B * 0.3, D, 0.35)
        k.add(block(L * 0.34, L * 0.44, -2.2, 2.2, D, D + 0.9, 0.3), "dark")  # bow winch deck
        k.add(geo.boxc(0.6, 1.0, 2.8, L * 0.44, 3.0, D - 3.5), "dark", False)  # anchor
        k.add(geo.boxc(0.6, 1.0, 2.8, L * 0.44, -3.0, D - 3.5), "dark", False)
        k.decal("text:ГРУЗЫ", (-L * 0.1, B / 2 + 0.02, D * 0.73), (0, 1, 0), 14, 3.0, t=0.03)
        k.decal("text:ГРУЗЫ", (-L * 0.1, -B / 2 - 0.02, D * 0.73), (0, -1, 0), 14, 3.0, t=0.03)
    if k.d >= 3:
        for s in (-1, 1):
            k.add(block(x_house - 3.5, x_house - 0.5, s * (w * 0.5 + 1.4) - 0.8, s * (w * 0.5 + 1.4) + 0.8, D + 3, D + 4.2, 0.3), "orange")  # lifeboat
            rail(k, [(x_house + 4, s * w * 0.6), (x_house - 3, s * w * 0.6)], D + 10.9, 1.0, 2.5, 0.04)


def liner(k: Kit):
    k.default_colors("#2e3440", "#eef0f4")
    L, B, D = 120 * k.p["length"], 19, 13
    pts = deck(L, B, 0.32, 0.72)
    h = k.add(hull_shape(pts, D, 0.8, 0.92), "paint")
    k.bands(h, [(D * 0.36, "hull_red"), (D * 0.39, "gold")])
    k.paint(h, "paint2", z=(D * 0.92, None))
    k.add(plan(geo_points(geo.offset2(geo.poly(pts), 0.3)), D * 0.98, D * 1.02), "chrome")
    if k.d >= 2:
        n = 14 if k.d == 2 else 22
        for s in (-1, 1):
            for i in range(n):
                x = -L * 0.42 + i * L * 0.78 / n
                porthole(k, x, s * (B / 2 - (0.3 if x < L * 0.1 else (x - L * 0.1) / L * 18) - 0.25), D * 0.72, 0.42)
    # decks: each tier a smaller outline with a row of windows, the lit ones picked per seed
    z = D
    tiers = [(0.76, 0.84, 3.2), (0.68, 0.8, 3.0), (0.54, 0.72, 2.8), (0.3, 0.6, 2.6)]
    for i, (ls, ws, hh) in enumerate(tiers):
        lt, wt = L * ls, B * ws
        cx = -L * 0.04
        tier = plan(rect(lt, wt, 2.0, cx, 0), z, z + hh)
        core = plan(rect(lt - 0.5, wt - 0.5, 2.0, cx, 0), z, z + hh)
        k.add(core, "glass_dark")
        n = 18 if k.d == 1 else 30
        win = [geo.box(cx - lt / 2 + 3 + (lt - 6) * j / n, -B, z + hh * 0.34, cx - lt / 2 + 3 + (lt - 6) * (j + 0.66) / n, B, z + hh * 0.76) for j in range(n)]
        k.add(geo.subtract(tier, win), "white")
        k.add(plan(rect(lt + 1.0, wt + 0.8, 2.0, cx, 0), z + hh, z + hh + 0.22), "chrome" if i % 2 else "white")
        if k.d >= 2:
            rail(k, [(cx - lt / 2, -wt / 2 - 0.2), (cx + lt / 2, -wt / 2 - 0.2)], z + hh + 0.22, 1.0, lt / 8, 0.06)
            rail(k, [(cx - lt / 2, wt / 2 + 0.2), (cx + lt / 2, wt / 2 + 0.2)], z + hh + 0.22, 1.0, lt / 8, 0.06)
        z += hh + 0.22
    # bridge in front of the top tier
    cabin(k, L * 0.11, L * 0.2, B * 0.9, D + 3.42 + 3.22, 2.8, "white", "white", 6, 0.6)
    for x in (-L * 0.1, -L * 0.2):
        funnel(k, x, z, 2.6, 8, "paint", "gold")
    if k.d >= 2:
        mast(k, L * 0.12, z, 7.5, 0.28)
        radar(k, L * 0.12, z + 7.4)
        for s in (-1, 1):  # lifeboats on davits along the upper deck
            for i in range(5):
                x = -L * 0.26 + i * L * 0.09
                y = s * (B * 0.34 + 2.0)
                zt = D + 3.42 + 3.22 + 3.0
                k.add(block(x - 3, x + 3, y - 1.0, y + 1.0, zt, zt + 1.2, 0.5), "orange")
                k.add(block(x - 2.8, x + 2.8, y - 0.8, y + 0.8, zt + 1.2, zt + 1.6, 0.5), "white")
                for dx in (-2.2, 2.2):
                    k.add(geo.beam((x + dx, y - s * 2.0, zt - 0.2), (x + dx, y, zt + 2.1), 0.14, 0.14), "steel", False)
        k.decal("sign:КРУИЗ", (L * 0.34, B * 0.31 + 0.02, D * 0.8), (0, 1, 0), 9, 2.2, t=0.03)
        k.decal("sign:КРУИЗ", (L * 0.34, -B * 0.31 - 0.02, D * 0.8), (0, -1, 0), 9, 2.2, t=0.03)
    if k.d >= 3:
        k.add(block(-L * 0.42, -L * 0.3, -B * 0.28, B * 0.28, D - 0.1, D + 0.05, 1.0), "sky", False)  # pool
        k.add(geo.rod((L * 0.12, 0, z + 7), (L * 0.49, 0, D * 1.02), 0.05, 4), "dark", False)
        k.add(geo.rod((L * 0.12, 0, z + 7), (-L * 0.49, 0, D * 1.02), 0.05, 4), "dark", False)
        flag(k, -L * 0.49, D * 1.5, 2.2, 1.3, "red")
        k.add(geo.rod((-L * 0.49, 0, D), (-L * 0.49, 0, D * 1.65), 0.09, 5), "steel", False)
        for i in range(3):
            lifering(k, -L * 0.2 + i * 12, B / 2 - 0.2, D + 1.2, 0.5)


def galleon(k: Kit):
    """Sailing ship: high stern, three masts, square sails."""
    k.default_colors("#b9714a", "#ece3cd")
    L, B, D = 30 * k.p["length"], 8, 4.5
    pts = deck(L, B, 0.26, 0.8)
    h = k.add(hull_shape(pts, D, 0.55, 0.85), "paint")
    k.bands(h, [(D * 0.26, "dark"), (D * 0.3, "gold"), (D * 0.7, "wood_dark"), (D * 0.74, "gold")])
    k.add(plan(geo_points(geo.offset2(geo.poly(pts), 0.12)), D * 0.97, D * 1.05), "wood_dark")
    well = plan(geo_points(geo.offset2(geo.poly(pts), -0.28)), D, D * 2)
    k.add(geo.subtract(plan(pts, D, D * 1.22), [well]), "wood")  # bulwark
    aft = side([(-L / 2, D), (-L / 2 - 0.5, D * 1.9), (-L * 0.32, D * 1.82), (-L * 0.32, D * 1.5), (-L * 0.18, D * 1.5), (-L * 0.18, D)], B * 0.78)
    a = k.add(aft, "paint")
    k.paint(a, "wood_dark", z=(D * 1.74, None))
    k.add(block(L * 0.26, L * 0.4, -B * 0.28, B * 0.28, D, D * 1.5, 0.3), "paint")  # forecastle
    k.add(geo.beam((L * 0.48, 0, D), (L * 0.64, 0, D * 1.5), 0.3, 0.3), "wood_dark", False)  # bowsprit
    sail_col = "paint2"
    for x, Hm, sw in ((-L * 0.25, 15, 7), (L * 0.05, 19, 10), (L * 0.3, 15.5, 8)):
        k.add(geo.cyl(0.26, Hm, 8, D, r2=0.14, cx=x), "wood_dark")
        z = D + Hm * 0.32
        for i, (w, hh) in enumerate(((sw, Hm * 0.3), (sw * 0.74, Hm * 0.24))):
            k.add(cylx(0.09, -w / 2 - 0.5, w / 2 + 0.5, 0, 0, 6).rotate([0, 0, 90]).translate([x, 0, z + hh]), "wood_dark", False)  # yard
            parts = []
            n = 3
            for j in range(n):
                b0, b1 = j / n, (j + 1) / n
                ya, yb = (w * (b0 - 0.5), w * (b1 - 0.5))
                belly = lambda t: 0.9 * (1 - (2 * t - 1) ** 2)  # noqa: E731
                q = [(x + 0.2, ya, z + hh), (x + 0.2, yb, z + hh), (x + 0.2 + belly(0.5) * (1 - abs(2 * (b0 + 0.0) - 1)), ya, z + hh * 0.5), (x + 0.2 + belly(0.5) * (1 - abs(2 * b1 - 1)), yb, z + hh * 0.5),
                     (x + 0.2, ya, z), (x + 0.2, yb, z)]
                parts.append(geo.hull([(px + d, py, pz) for px, py, pz in q for d in (0.0, 0.03)]))
            s = k.add(geo.union(parts), sail_col)
            if i == 0 and k.d >= 2:
                k.paint(s, "red", z=(z + hh * 0.44, z + hh * 0.56))
            z += hh + 0.3
        if k.d >= 2:
            k.add(geo.cyl(0.85, 0.5, 8, D + Hm * 0.76, r2=1.0, cx=x), "wood_dark")  # crow's nest
            flag(k, x, D + Hm - 0.9, 2.0, 1.0, "red")
    if k.d >= 2:
        for s in (-1, 1):
            for i in range(7):  # cannon ports
                x = -L * 0.3 + i * L * 0.09
                y = s * (B / 2 - 0.15 - (0.8 if x > L * 0.14 else 0))
                k.add(geo.boxc(0.6, 0.12, 0.55, x, y, D * 0.5), "black", False)
                k.add(cylx(0.09, 0, 0.5, 0, 0, 6).rotate([0, 0, 90 * s]).translate([x, y, D * 0.58]), "dark", False)
        for i in range(4):  # stern windows
            k.add(geo.boxc(0.04, 0.7, 0.8, -L / 2 - 0.3, -2.4 + i * 1.6, D * 1.4), "lit", False)
        for y in (-1, 1):
            k.add(geo.cyl(0.3, 0.8, 6, D * 1.88, cx=-L / 2 + 0.4, cy=y * B * 0.3), "lit")  # stern lanterns
    if k.d >= 3:
        for x in (-L * 0.25, L * 0.05, L * 0.3):
            for s in (-1, 1):
                k.add(geo.rod((x, 0, D + 12), (x - 0.8, s * B * 0.52, D * 1.1), 0.03, 4), "dark", False)  # shrouds
                k.add(geo.rod((x, 0, D + 10), (x + 0.8, s * B * 0.52, D * 1.1), 0.03, 4), "dark", False)
        k.add(geo.rod((L * 0.3, 0, D + 15), (L * 0.64, 0, D * 1.5), 0.03, 4), "dark", False)
