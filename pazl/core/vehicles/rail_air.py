"""Rail and air: locomotive, wagons, plane, airliner, helicopter. Rail wheels are the same spinning nodes as on the road;
propellers and rotors are nodes too. Fuselages are lofted eight-sided sections."""
from __future__ import annotations

from .. import geo
from .kit import Kit, block, cylx, cyly, front, loft, oct_section, ring, side

GAUGE = 1.5


def bogie(k: Kit, x, tag, r=0.46):
    """Two-axle truck under a wagon."""
    k.add(geo.boxc(2.4, GAUGE + 0.3, 0.3, x, 0, r + 0.02), "dark")
    for i, dx in enumerate((-0.8, 0.8)):
        for j, s in enumerate((-1, 1)):
            k.wheel(x + dx, s * GAUGE / 2, r, 0.14, f"wheel_{tag}{i * 2 + j}", hub="dark", rim=0.5, nuts=False)
    if k.d >= 3:
        for s in (-1, 1):
            k.add(cyly(0.08, s * (GAUGE / 2 + 0.1) - 0.06, s * (GAUGE / 2 + 0.1) + 0.06, x, r + 0.16, 8), "chrome", False)


def coupler(k: Kit, x, z):
    s = 1 if x > 0 else -1
    k.add(geo.boxc(0.5, 0.12, 0.12, x + s * 0.2, 0, z), "dark", False)
    k.add(geo.boxc(0.12, 0.26, 0.2, x + s * 0.46, 0, z - 0.04), "dark", False)


def locomotive(k: Kit):
    """Steam engine: boiler with bands, domes, a stack, a cab and big driving wheels joined by a rod."""
    k.default_colors("#3f4250", "#c8342c")
    L, W = 11 * k.p["length"], 2.7
    xf, xr = L / 2, -L / 2
    zc, R = 2.3, 0.9
    xb = xr + 3.0
    seg = k.seg + 4
    bo = k.add(cylx(R, xb, xf - 1.0, 0, zc, seg), "paint")
    k.add(cylx(R * 1.06, xf - 1.0, xf - 0.8, 0, zc, seg), "dark")
    k.add(cylx(R * 0.96, xf - 0.8, xf - 0.72, 0, zc, seg, r2=R * 0.78), "paint2")
    k.add(cylx(R * 0.3, xf - 0.72, xf - 0.68, 0, zc, 10), "chrome", False)
    for i in range(4):
        x = xb + 0.5 + i * (xf - 1.4 - xb) / 3.2
        k.add(cylx(R + 0.02, x - 0.04, x + 0.04, 0, zc, seg), "gold", False)
    k.paint(bo, "dark", z=(zc + R - 0.2, None))
    # running board and frame
    k.add(block(xr, xf - 0.5, -W / 2, W / 2, 1.28, 1.38, 0.1), "paint2")
    k.add(geo.box(xr + 0.2, -0.55, 0.62, xf - 0.5, 0.55, 1.3), "dark")
    # stack, domes
    xs = xf - 1.8
    k.add(ring(0.33, 0.06, 1.0, seg, zc + R - 0.1, xs), "dark")
    k.add(geo.subtract(geo.cyl(0.33, 0.45, seg, zc + R + 0.85, r2=0.5, cx=xs), [geo.cyl(0.24, 1, seg, zc + R + 0.95, cx=xs)]), "paint2")
    for x, r, h, col in ((xs - 2.6, 0.42, 0.72, "gold"), (xs - 1.5, 0.3, 0.5, "paint2")):
        k.add(geo.cyl(r, h, 12, zc + R - 0.12, r2=r * 0.72, cx=x), col)
    # cab with inset windows
    cz, ch = 1.38, 2.3
    cab = block(xr, xb + 0.2, -W / 2 + 0.05, W / 2 - 0.05, cz, cz + ch, 0.06)
    k.add(block(xr + 0.04, xb + 0.16, -W / 2 + 0.09, W / 2 - 0.09, cz, cz + ch - 0.05, 0.06), "glass_dark")
    win = geo.box(xr + 0.55, -W, cz + 1.0, xb - 0.55, W, cz + 1.95)
    fwin = [geo.box(xb - 1, s * 0.75 - 0.32, cz + 1.2, xb + 2, s * 0.75 + 0.32, cz + 1.95) for s in (-1, 1)]
    c = k.add(geo.subtract(cab, [win] + fwin), "paint2")
    k.paint(c, "dark", z=(None, cz + 0.28))
    roof = side([(xr - 0.3, cz + ch), (xr - 0.3, cz + ch + 0.08), (xb + 0.4, cz + ch + 0.08), (xb + 0.4, cz + ch)], W * 0.6) + \
        front([(-W / 2 - 0.1, cz + ch), (-W / 2 - 0.1, cz + ch + 0.08), (-W * 0.28, cz + ch + 0.35), (W * 0.28, cz + ch + 0.35), (W / 2 + 0.1, cz + ch + 0.08), (W / 2 + 0.1, cz + ch)], xr - 0.3, xb + 0.4)
    k.add(roof, "dark")
    # cowcatcher
    k.add(geo.hull([(xf - 0.6, -W / 2, 1.1), (xf - 0.6, W / 2, 1.1), (xf - 0.6, -W / 2, 0.6), (xf - 0.6, W / 2, 0.6), (xf + 0.7, 0, 0.16), (xf + 0.7, -0.5, 0.16), (xf + 0.7, 0.5, 0.16)]), "paint2")
    k.add(geo.boxc(0.3, W, 0.34, xf - 0.5, 0, 1.0), "paint2")
    # wheels: three drivers and a leading axle
    rd, rl = 0.78, 0.42
    xs_d = [xr + 2.0, xr + 3.8, xr + 5.6]
    n = 0
    for x in xs_d:
        for s in (-1, 1):
            k.wheel(x, s * GAUGE / 2, rd, 0.16, f"wheel_{n}", hub="paint2", rim=0.62, nuts=False)
            n += 1
    for s in (-1, 1):
        k.wheel(xf - 1.0, s * GAUGE / 2, rl, 0.14, f"wheel_{n}", hub="paint2", rim=0.58, nuts=False)
        n += 1
        y = s * (GAUGE / 2 + 0.14)
        k.add(geo.boxc(xs_d[-1] - xs_d[0] + 0.3, 0.05, 0.12, (xs_d[0] + xs_d[-1]) / 2, y, rd - 0.05), "chrome", False)  # coupling rod
        k.add(cylx(0.3, xf - 2.3, xf - 1.1, s * 1.05, 1.1, 10), "dark")  # cylinder
        k.add(geo.boxc(xf - 1.2 - xs_d[-1], 0.05, 0.08, (xf - 1.2 + xs_d[-1]) / 2, y + 0.03, rd + 0.28), "steel", False)  # piston rod
    if k.d >= 2:
        k.add(cylx(0.2, xf - 0.72, xf - 0.5, 0, zc + 1.0, 10), "chrome")  # headlamp
        k.add(cylx(0.15, xf - 0.5, xf - 0.48, 0, zc + 1.0, 10), "lamp", False)
        k.add(geo.boxc(0.1, 0.1, 0.25, xf - 0.65, 0, zc + 0.8), "dark", False)
        for s in (-1, 1):
            k.add(geo.rod((xb + 0.3, s * (R + 0.08), zc + 0.2), (xf - 1.3, s * (R + 0.08), zc + 0.2), 0.025, 5), "gold", False)  # handrails
            k.decal("number:" + (k.p["text"] or str(k.R.randint(100, 999))), ((xr + xb) / 2 + 0.1, s * (W / 2 - 0.04), cz + 0.62), (0, s, 0), 1.0, 0.3)
            k.add(geo.boxc(1.1, 0.05, 0.35, xs + 0.3, s * (R + 0.14), 1.38), "paint2", False)
        coupler(k, xr, 0.95)
        k.add(geo.cyl(0.05, 0.3, 6, zc + R + 0.36, cx=xs - 2.6), "chrome", False)  # whistle
        k.add(geo.cyl(0.14, 0.16, 8, zc + R + 0.03, cx=xs - 0.8, r2=0.1), "gold", False)  # bell
    if k.d >= 3:
        for i in range(9):  # rivets along the running board
            for s in (-1, 1):
                k.add(geo.cyl(0.03, 0.03, 5, 0).rotate([-90 * s, 0, 0]).translate([xr + 0.6 + i * 1.0, s * W / 2, 1.33]), "gold", False)
        k.add(geo.boxc(0.04, 0.26, 0.04, xf + 0.1, 0, 1.02), "gold", False)
        k.decal("number:" + (k.p["text"] or "1"), (xf - 0.671, 0, zc), (1, 0, 0), 0.4, 0.14)


def tender(k: Kit):
    k.default_colors("#3f4250", "#c8342c")
    L, W = 6.2 * k.p["length"], 2.6
    xf, xr = L / 2, -L / 2
    k.add(geo.box(xr, -W / 2, 1.0, xf, W / 2, 1.14), "dark")
    t = geo.subtract(block(xr, xf, -W / 2, W / 2, 1.14, 3.0, 0.12), [block(xr + 0.15, xf - 0.15, -W / 2 + 0.15, W / 2 - 0.15, 2.5, 4, 0.1)])
    b = k.add(t, "paint")
    k.paint(b, "paint2", z=(1.2, 1.32))
    k.paint(b, "paint2", z=(2.76, 2.86))
    pile = [(xr + 0.6 + 1.0 * i + 0.3 * k.R.random(), 0.8 * (k.R.random() - 0.5), 2.45 + 0.25 * k.R.random()) for i in range(5)]
    k.add(geo.union([block(xr + 0.16, xf - 0.16, -W / 2 + 0.16, W / 2 - 0.16, 2.2, 2.68)] + [geo.sphere(0.55, 5, p) for p in pile]), "black", False)
    bogie(k, xf - 1.5, "a")
    bogie(k, xr + 1.5, "b")
    if k.d >= 2:
        coupler(k, xf, 0.95)
        coupler(k, xr, 0.95)
        for s in (-1, 1):
            k.decal("number:" + (k.p["text"] or str(k.R.randint(100, 999))), (0, s * (W / 2 + 0.002), 2.1), (0, s, 0), 1.4, 0.4)
            for x in (xf - 0.16, xr + 0.16):
                k.add(geo.boxc(0.04, 0.04, 1.6, x, s * (W / 2 + 0.04), 1.2), "steel", False)
    if k.d >= 3:
        for i in range(4):
            k.add(geo.boxc(0.3, 0.03, 0.03, xr - 0.02, 0.9, 1.3 + i * 0.3), "steel", False)


def wagon(k: Kit, kind):
    k.default_colors("#c8342c" if kind == "passenger" else "#8a5238", "#eef0f4")
    L, W = 15 * k.p["length"] if kind == "passenger" else 12 * k.p["length"], 2.8
    xf, xr = L / 2, -L / 2
    z0 = 1.1
    k.add(geo.box(xr, -W / 2 + 0.06, z0, xf, W / 2 - 0.06, z0 + 0.2), "dark")
    bogie(k, xf - 2.4, "a")
    bogie(k, xr + 2.4, "b")
    if kind == "passenger":
        H = 3.7
        k.add(block(xr + 0.08, xf - 0.08, -W / 2 + 0.05, W / 2 - 0.05, z0 + 0.2, H - 0.05, 0.1), "lit")
        body = block(xr, xf, -W / 2, W / 2, z0 + 0.2, H, 0.1)
        n = 9
        win = [geo.box(xr + 1.2 + (L - 2.4) * i / n + 0.14, -W, z0 + 1.05, xr + 1.2 + (L - 2.4) * (i + 1) / n - 0.14, W, z0 + 2.0) for i in range(n)]
        b = k.add(geo.subtract(body, win), "paint")
        k.paint(b, "paint2", z=(z0 + 0.72, z0 + 0.84))
        k.paint(b, "paint2", z=(z0 + 2.12, z0 + 2.22))
        roof = front([(-W / 2 - 0.06, H), (-W / 2 - 0.06, H + 0.06), (-W * 0.32, H + 0.34), (W * 0.32, H + 0.34), (W / 2 + 0.06, H + 0.06), (W / 2 + 0.06, H)], xr - 0.04, xf + 0.04)
        k.add(roof, "dark")
        if k.d >= 2:
            for s in (-1, 1):  # end doors and steps
                for x in (xr + 0.6, xf - 0.6):
                    k.add(geo.boxc(0.74, 0.03, 2.1, x, s * (W / 2 + 0.002), z0 + 0.22), "dark", False)
                    k.add(geo.boxc(0.5, 0.012, 0.8, x, s * (W / 2 + 0.018), z0 + 1.3), "glass", False)
                    k.add(geo.boxc(0.8, 0.26, 0.05, x, s * (W / 2 - 0.05), z0 - 0.3), "steel", False)
                k.decal("sign:" + (k.p["text"] or "ЭКСПРЕСС"), (0, s * (W / 2 + 0.002), z0 + 2.6), (0, s, 0), 2.6, 0.34)
            for i in range(4):
                k.add(block(xr + 2 + i * (L - 4) / 3 - 0.3, xr + 2 + i * (L - 4) / 3 + 0.3, -0.3, 0.3, H + 0.32, H + 0.5, 0.1), "steel")  # roof vents
    elif kind == "box":
        H = 3.9
        k.add(block(xr, xf, -W / 2, W / 2, z0 + 0.2, H, 0.05), "paint")
        k.add(front([(-W / 2 - 0.05, H), (-W * 0.3, H + 0.26), (W * 0.3, H + 0.26), (W / 2 + 0.05, H)], xr - 0.04, xf + 0.04), "dark")
        if k.d >= 2:
            for s in (-1, 1):
                k.add(geo.boxc(2.4, 0.04, 2.3, 0, s * (W / 2 + 0.004), z0 + 0.3), "wood_dark")  # sliding door
                k.add(geo.boxc(2.6, 0.06, 0.06, 0, s * (W / 2 + 0.02), z0 + 2.62), "steel", False)
                k.add(geo.boxc(0.06, 0.06, 0.5, 0.3, s * (W / 2 + 0.03), z0 + 1.2), "steel", False)
                n = 10
                for i in range(n + 1):
                    x = xr + 0.1 + (L - 0.2) * i / n
                    if abs(x) > 1.3:
                        k.add(geo.boxc(0.06, 0.02, H - z0 - 0.4, x, s * (W / 2 + 0.004), z0 + 0.3), "wood_dark", False)
                k.decal("number:" + (k.p["text"] or str(k.R.randint(10000, 99999))), (xf - 2.7, s * (W / 2 + 0.008), z0 + 1.9), (0, s, 0), 1.5, 0.36)
    elif kind == "tank":
        R, zc = 1.3, z0 + 1.5
        seg = k.seg + 4
        k.add(block(xr + 0.2, xf - 0.2, -0.8, 0.8, z0 + 0.2, zc - 0.7), "dark")
        t = k.add(cylx(R, xr + 0.5, xf - 0.5, 0, zc, seg), "paint")
        k.paint(t, "paint2", z=(zc - 0.2, zc + 0.2))
        k.add(cylx(R * 0.7, xr + 0.2, xr + 0.5, 0, zc, seg, r2=R), "paint")
        k.add(cylx(R, xf - 0.5, xf - 0.2, 0, zc, seg, r2=R * 0.7), "paint")
        k.add(geo.cyl(0.5, 0.42, 10, zc + R - 0.08), "steel")
        k.add(geo.cyl(0.54, 0.05, 10, zc + R + 0.34), "steel", False)
        if k.d >= 2:
            for x in (xr + 2.0, xf - 2.0, -3, 3):
                k.add(cylx(R + 0.02, x - 0.04, x + 0.04, 0, zc, seg), "dark", False)
            for s in (-1, 1):
                k.add(geo.rod((xr + 1, s * 0.5, zc + R + 0.35), (xf - 1, s * 0.5, zc + R + 0.35), 0.025, 5), "steel", False)
                k.decal("hazard", (0, s * (R + 0.002), zc - 0.34), (0, s, 0), 2.4, 0.3)
    else:  # flat with logs
        k.add(geo.box(xr, -W / 2, z0 + 0.2, xf, W / 2, z0 + 0.3), "wood")
        for s in (-1, 1):
            for x in (xr + 1, -2.5, 2.5, xf - 1):
                k.add(geo.boxc(0.1, 0.1, 1.9, x, s * (W / 2 - 0.08), z0 + 0.3), "dark")
        r = 0.32
        for row, ys in enumerate(((-0.96, -0.32, 0.32, 0.96), (-0.64, 0, 0.64), (-0.32, 0.32))):
            for y in ys:
                dx = 0.3 * k.R.random()
                lg = cylx(r, xr + 0.3 + dx, xf - 0.3 - dx, y, z0 + 0.3 + r + row * r * 1.72, 8)
                k.add(lg, "wood_dark")
                if k.d >= 2:
                    k.add(cylx(r * 0.8, xf - 0.3 - dx, xf - 0.295 - dx, y, z0 + 0.3 + r + row * r * 1.72, 8), "canvas", False)
                    k.add(cylx(r * 0.8, xr + 0.295 + dx, xr + 0.3 + dx, y, z0 + 0.3 + r + row * r * 1.72, 8), "canvas", False)
    if k.d >= 2:
        coupler(k, xf, 0.95)
        coupler(k, xr, 0.95)


# ------------------------------------------------------------------ air
def wing_shape(x_root, y_root, c_root, x_tip, y_tip, c_tip, z, t=0.16, dz=0.0):
    pts = []
    for x, y, c, zz, th in ((x_root, y_root, c_root, z, t), (x_tip, y_tip, c_tip, z + dz, t * 0.5)):
        pts += [(x, y, zz), (x - c * 0.3, y, zz + th), (x - c, y, zz + th * 0.15), (x - c * 0.3, y, zz - th * 0.25)]
    return geo.hull(pts)


def prop_blades(k: Kit, x, z, r, name, n=3, col="dark", axis="x"):
    """Spinning blades: one node with its pivot on the hub."""
    parts = []
    for i in range(n):
        b = geo.hull([(-0.02, -0.03, 0), (0.02, 0.03, 0), (-0.02, -0.06, r * 0.5), (0.02, 0.06, r * 0.5), (0, -0.03, r), (0, 0.03, r)])
        parts.append(b.rotate([360 * i / n, 0, 0]))
    m = geo.union(parts)
    if axis == "z":
        m = m.rotate([0, 90, 0])
    k.pivots[name] = (x, 0.0, z)
    k.add(m.translate([x, 0, z]), col, False, node=name)


def light_plane(k: Kit):
    k.default_colors("#eef0f4", "#d9483b")
    L = 8.0 * k.p["length"]
    xf, xr = L / 2, -L / 2
    z = 1.5
    secs = [(xf - 0.2, oct_section(0.5, 0.5, z)), (xf - 0.9, oct_section(1.1, 1.1, z)), (xf - 2.6, oct_section(1.25, 1.55, z + 0.15)), (xf - 3.8, oct_section(1.1, 1.3, z + 0.2)),
            (xr + 0.3, oct_section(0.16, 0.34, z + 0.45))]
    f = k.add(loft(secs), "paint")
    k.paint(f, "paint2", z=(z - 0.12, z + 0.08))
    # cabin glass painted onto the fuselage with a rear stop: pillars remain
    k.paint(f, "glass", x=(xf - 3.3, xf - 2.75), z=(z + 0.42, None), grad=False)
    k.paint(f, "glass", x=(xf - 3.3 - 1.05, xf - 3.35), z=(z + 0.34, z + 0.72), grad=False)
    k.paint(f, "glass", x=(xf - 2.7, xf - 2.1), z=(z + 0.26, None), grad=False)
    wz = z + 0.84
    for s in (-1, 1):
        k.add(wing_shape(xf - 2.3, s * 0.5, 1.55, xf - 2.55, s * 5.2, 1.05, wz, 0.13, -0.05), "paint")
        k.add(geo.beam((xf - 3.0, s * 0.6, z - 0.2), (xf - 3.1, s * 2.4, wz), 0.06, 0.05), "steel", False)  # strut
    k.add(geo.hull([(xr + 1.2, -0.05, z + 0.5), (xr + 1.2, 0.05, z + 0.5), (xr + 0.3, -0.05, z + 0.5), (xr + 0.3, 0.05, z + 0.5), (xr + 0.65, -0.03, z + 1.5), (xr + 0.65, 0.03, z + 1.5), (xr + 0.2, -0.03, z + 1.5), (xr + 0.2, 0.03, z + 1.5)]), "paint2")
    for s in (-1, 1):
        k.add(wing_shape(xr + 1.2, s * 0.05, 0.85, xr + 0.95, s * 1.6, 0.5, z + 0.48, 0.05), "paint")
    k.add(cylx(0.28, xf - 0.02, xf + 0.3, 0, z, 10, r2=0.05), "paint2")
    prop_blades(k, xf + 0.1, z, 0.95, "propeller", 2)
    for s in (-1, 1):  # main gear
        k.add(geo.beam((xf - 2.3, s * 0.45, z - 0.55), (xf - 2.45, s * 1.15, 0.28), 0.06, 0.05), "dark", False)
        k.wheel(xf - 2.45, s * 1.15, 0.28, 0.14, f"wheel_{0 if s > 0 else 1}", hub="paint2")
    k.add(geo.rod((xf - 0.7, 0, z - 0.3), (xf - 0.72, 0, 0.26), 0.035, 6), "dark", False)
    k.wheel(xf - 0.72, 0, 0.22, 0.11, "wheel_2", hub="paint2")
    if k.d >= 2:
        for s in (-1, 1):
            k.add(geo.boxc(0.3, 0.02, 0.1, xf - 2.3, s * 5.2, wz - 0.06), "red" if s > 0 else "green", False)  # nav lights
            k.decal("number:" + (k.p["text"] or f"AB-{k.R.randint(100, 999)}"), (xr + 2.0, s * 0.42, z + 0.3), (0, s, 0), 1.5, 0.3)
            k.add(geo.boxc(0.3, 0.025, 0.04, xf - 3.6, s * 0.63, z + 0.3), "dark", False)
        k.add(geo.rod((xf - 3.2, 0, z + 0.9), (xf - 3.35, 0, z + 1.25), 0.008, 4), "dark", False)
    if k.d >= 3:
        k.add(geo.hull([(xr + 0.2, -0.02, z + 1.48), (xr + 0.2, 0.02, z + 1.48), (xr + 0.3, 0, z + 1.56)]), "tail", False)
        for s in (-1, 1):
            k.add(geo.boxc(1.2, 0.3, 0.015, xf - 3.0, s * 4.2, wz - 0.018), "dark", False)  # aileron
        k.add(cylx(0.05, xf - 1.1, xf - 0.7, 0.3, z - 0.4, 6), "dark", False)  # exhaust


def airliner(k: Kit):
    k.default_colors("#eef0f4", "#4f78c9")
    L = 38 * k.p["length"]
    xf, xr = L / 2, -L / 2
    R = 2.1
    z = 3.6
    secs = [(xf, oct_section(0.3, 0.3, z - 0.2)), (xf - 0.8, oct_section(1.9, 1.9, z - 0.15)), (xf - 3, oct_section(3.8, 3.9, z)), (xf - 6, oct_section(2 * R, 2 * R, z)), (xr + 11, oct_section(2 * R, 2 * R, z)),
            (xr + 3, oct_section(1.8, 2.1, z + 0.85)), (xr, oct_section(0.3, 0.5, z + 1.45))]
    f = k.add(loft(secs), "paint")
    k.paint(f, "paint2", z=(None, z - 1.0))
    k.paint(f, "paint2", z=(z - 0.2, z - 0.05), x=(xr + 3, xf - 1.0))
    k.paint(f, "glass_dark", x=(xf - 3.2, xf - 1.9), z=(z + 0.55, z + 1.1), grad=False)
    wz = z - 1.3
    for s in (-1, 1):
        k.add(wing_shape(xf - 13, s * 1.4, 8, xf - 21, s * 17, 2.4, wz, 0.5, 1.5), "paint")
        k.add(wing_shape(xr + 6, s * 0.4, 3.6, xr + 3, s * 6.6, 1.8, z + 1.3, 0.2, 0.5), "paint2")
        k.add(geo.hull([(xf - 21, s * 17, wz + 1.5), (xf - 23.4, s * 17, wz + 1.5), (xf - 22.8, s * 17.2, wz + 3.4), (xf - 23.8, s * 17.2, wz + 3.4)]), "paint2")  # winglet
        ey = s * 6.3
        ez = wz - 0.95
        eng = cylx(0.95, xf - 16.3, xf - 12.8, ey, ez, k.seg + 2)
        k.add(geo.subtract(eng, [cylx(0.76, xf - 13.4, xf - 12, ey, ez, k.seg + 2)]), "paint2")
        k.add(cylx(0.74, xf - 13.5, xf - 13.4, ey, ez, 10), "dark", False)
        k.add(cylx(0.22, xf - 13.45, xf - 13.15, ey, ez, 8, r2=0.05), "chrome", False)
        k.add(cylx(0.5, xf - 17.1, xf - 16.3, ey, ez, 10, r2=0.9), "dark")
        k.add(geo.beam((xf - 15, ey, ez + 0.8), (xf - 15.3, ey, wz + 0.4), 0.3, 1.0), "paint2")
    tail = geo.hull([(xr + 7, -0.15, z + 1.7), (xr + 7, 0.15, z + 1.7), (xr + 1, -0.15, z + 1.7), (xr + 1, 0.15, z + 1.7), (xr + 2.2, -0.08, z + 7.3), (xr + 2.2, 0.08, z + 7.3), (xr + 0.2, -0.08, z + 7.3), (xr + 0.2, 0.08, z + 7.3)])
    t = k.add(tail, "paint2")
    k.paint(t, "paint", z=(z + 3.4, z + 4.2))
    n = 30 if k.d >= 2 else 0
    for i in range(n):  # cabin windows: painted, so they follow the fuselage
        x = xf - 7.2 - i * (L - 18) / 30
        for s in (-1, 1):
            k.paint(f, "glass_dark", x=(x - 0.14, x + 0.14), y=sorted((s * 0.9, s * 3)), z=(z + 0.44, z + 0.8), grad=False)
    gear = [(xf - 15.5, 2.6, "wheel_0"), (xf - 15.5, -2.6, "wheel_1")]
    for x, y, name in gear:
        k.add(geo.rod((x, y * 0.7, z - 1.8), (x, y, 0.5), 0.13, 8), "steel", False)
        k.wheel(x, y, 0.55, 0.42, name, hub="dark")
    k.add(geo.rod((xf - 3.8, 0, z - 1.9), (xf - 3.8, 0, 0.44), 0.1, 8), "steel", False)
    k.wheel(xf - 3.8, 0, 0.42, 0.3, "wheel_2", hub="dark")
    if k.d >= 2:
        for s in (-1, 1):
            for x in (xf - 5.3, xr + 8.2):
                k.paint(f, "paint2", x=(x - 0.45, x + 0.45), y=sorted((s * 1.0, s * 3)), z=(z - 0.6, z + 1.25), grad=False)  # doors
                k.paint(f, "glass_dark", x=(x - 0.16, x + 0.16), y=sorted((s * 1.0, s * 3)), z=(z + 0.45, z + 0.8), grad=False)
        k.decal("number:" + (k.p["text"] or f"RA-{k.R.randint(10000, 99999)}"), (xr + 3.4, 0.14, z + 2.0), (0, 1, 0), 2.6, 0.5, t=0.01)
        k.decal("number:" + (k.p["text"] or f"RA-{k.R.randint(10000, 99999)}"), (xr + 3.4, -0.14, z + 2.0), (0, -1, 0), 2.6, 0.5, t=0.01)
        k.add(geo.boxc(0.8, 0.1, 0.25, xf - 7, 0, z + R - 0.05), "dark", False)
    if k.d >= 3:
        for s in (-1, 1):
            k.add(geo.boxc(0.3, 0.05, 0.1, xf - 22, s * 17.2, wz + 1.5), "green" if s > 0 else "tail", False)
            for x in (xf - 17, xf - 20):
                k.add(geo.boxc(1.2, 0.18, 0.2, x, s * 7.6, wz + 0.1), "paint2")  # flap fairings
        k.add(geo.boxc(0.6, 0.04, 0.6, xf - 10, 0, z + R), "dark", False)
        k.add(geo.boxc(0.4, 0.12, 0.2, xf - 6, 0, z - R - 0.12), "tail", False)


def helicopter(k: Kit):
    k.default_colors("#d9483b", "#eef0f4")
    L = 10 * k.p["length"]
    z = 1.5
    xf = 2.2
    secs = [(xf, oct_section(0.5, 0.7, z - 0.05)), (xf - 0.5, oct_section(1.3, 1.35, z)), (xf - 1.6, oct_section(1.7, 1.8, z + 0.1)), (xf - 3.0, oct_section(1.6, 1.7, z + 0.15)), (xf - 3.7, oct_section(0.7, 0.9, z + 0.35)), (xf - 7.2 * k.p["length"], oct_section(0.2, 0.28, z + 0.55))]
    f = k.add(loft(secs), "paint")
    k.paint(f, "glass", x=(xf - 1.5, None), z=(z - 0.3, None), grad=False)
    k.paint(f, "glass", x=(xf - 2.65, xf - 1.65), z=(z + 0.1, z + 0.7), grad=False)
    k.paint(f, "paint2", z=(z - 0.4, z - 0.24), x=(None, xf - 1.4))
    k.add(block(xf - 2.9, xf - 1.5, -0.5, 0.5, z + 0.9, z + 1.25, 0.2), "paint")  # engine housing
    k.add(geo.cyl(0.11, 0.42, 8, z + 1.2, cx=xf - 2.2), "dark")
    k.add(geo.cyl(0.24, 0.1, 8, z + 1.6, cx=xf - 2.2), "steel")
    xt = xf - 7.2 * k.p["length"]
    k.add(geo.hull([(xt + 0.5, -0.05, z + 0.5), (xt + 0.5, 0.05, z + 0.5), (xt, -0.05, z + 0.5), (xt, 0.05, z + 0.5), (xt - 0.2, -0.03, z + 1.5), (xt - 0.2, 0.03, z + 1.5), (xt - 0.5, -0.03, z + 1.5), (xt - 0.5, 0.03, z + 1.5)]), "paint")
    k.add(geo.boxc(0.5, 1.4, 0.05, xt + 0.9, 0, z + 0.5), "paint2")  # stabiliser
    name = "rotor_main"
    k.pivots[name] = (xf - 2.2, 0.0, z + 1.8)
    n = 4
    R = L * 0.52
    bl = [geo.box(0, -0.13, -0.025, R, 0.13, 0.025).rotate([0, 0, 360 * i / n + 20]) for i in range(n)]
    k.add(geo.union(bl).translate([xf - 2.2, 0, z + 1.8]), "dark", False, node=name)
    k.add(geo.cyl(0.2, 0.2, 8, z + 1.72, cx=xf - 2.2), "dark", False, node=name)
    # tail rotor spins around Y
    name = "rotor_tail"
    k.pivots[name] = (xt - 0.15, 0.2, z + 1.15)
    t1 = geo.union([geo.box(-0.68, -0.012, -0.04, 0.68, 0.012, 0.04), geo.box(-0.04, -0.012, -0.68, 0.04, 0.012, 0.68)])
    k.add(t1.translate([xt - 0.15, 0.2, z + 1.15]), "dark", False, node=name)
    k.add(cyly(0.1, 0.05, 0.2, xt - 0.15, z + 1.15, 8), "dark", False)
    # skids
    for s in (-1, 1):
        k.add(geo.rod((xf + 0.1, s * 1.0, 0.12), (xf - 3.6, s * 1.0, 0.06), 0.05, 6), "dark", False)
        k.add(geo.rod((xf + 0.1, s * 1.0, 0.12), (xf + 0.3, s * 1.0, 0.32), 0.05, 6), "dark", False)
        for x in (xf - 0.9, xf - 2.7):
            k.add(geo.rod((x, s * 1.0, 0.1), (x, s * 0.6, z - 0.62), 0.045, 6), "dark", False)
    if k.d >= 2:
        for s in (-1, 1):
            k.decal("number:" + (k.p["text"] or f"H-{k.R.randint(100, 999)}"), (xf - 4.8, s * 0.21, z + 0.4), (0, s, 0), 1.1, 0.22, t=0.008)
        k.add(geo.boxc(0.1, 0.1, 0.2, xf - 0.6, 0, z - 0.82), "steel", False)
        k.add(geo.cyl(0.14, 0.05, 8, z - 0.7, cx=xf - 1.0), "lamp", False)
        k.add(geo.boxc(0.8, 0.3, 0.1, xf - 2.8, 0, z + 1.2), "dark", False)
    if k.d >= 3:
        k.add(geo.rod((xf - 3.3, 0, z + 1.28), (xf - 3.8, 0, z + 1.68), 0.008, 4), "black", False)
        k.add(geo.cyl(0.06, 0.08, 6, z + 1.28, cx=xf - 3.2), "tail", False)
        k.add(geo.rod((xf + 0.1, 0.25, z - 0.1), (xf + 0.65, 0.25, z - 0.05), 0.015, 4), "dark", False)  # pitot
