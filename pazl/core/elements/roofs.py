"""Roofs, domes, spires, crosses, chimneys, dormers. Roofs attach to a `top` anchor."""
from __future__ import annotations

import math

import numpy as np

from .. import geo as g
from ..registry import Anchor, P, Part, element
from .common import top_anchor

ROOF_TYPES = ["gable", "hip", "pyramid", "tent", "shed", "mansard", "gambrel", "flat", "cone", "dome", "onion",
              "helmet", "bell", "barrel", "cross_gable", "half_hip", "pagoda"]


def _bbox(fp):
    xs, ys = [p[0] for p in fp], [p[1] for p in fp]
    return min(xs), max(xs), min(ys), max(ys)


def _roof_points(kind, a, b, H, o, ze, p):
    """Outer roof volume points in a frame where the ridge runs along X; footprint half-sizes a (X) and b (Y)."""
    A, B = a + o, b + o
    if kind == "gable":
        return [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze], [-A, 0, H], [A, 0, H]]
    if kind == "half_hip":
        k = 0.35
        return [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze], [-A * (1 - k * 0.3), 0, H], [A * (1 - k * 0.3), 0, H],
                [-A, -B * k, ze + (H - ze) * (1 - k)], [-A, B * k, ze + (H - ze) * (1 - k)],
                [A, -B * k, ze + (H - ze) * (1 - k)], [A, B * k, ze + (H - ze) * (1 - k)]]
    if kind == "hip":
        r = max(0.0, a - b)
        return [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze], [-r, 0, H], [r, 0, H]]
    if kind in ("pyramid", "tent"):
        return [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze], [0, 0, H]]
    if kind == "shed":
        return [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze], [-A, B, H], [A, B, H]]
    if kind in ("mansard", "gambrel"):
        ins = float(p.get("break_in", 0.25)) * b
        hb = ze + float(p.get("break_h", 0.6)) * (H - ze)
        pts = [[-A, -B, ze], [A, -B, ze], [-A, B, ze], [A, B, ze]]
        if kind == "mansard":
            ins_x = ins
            pts += [[-A + ins_x, -B + ins, hb], [A - ins_x, -B + ins, hb], [-A + ins_x, B - ins, hb], [A - ins_x, B - ins, hb]]
            r = max(0.0, (a - ins) - (b - ins))
            pts += [[-r, 0, H], [r, 0, H]]
        else:
            pts += [[-A, -B + ins, hb], [A, -B + ins, hb], [-A, B - ins, hb], [A, B - ins, hb], [-A, 0, H], [A, 0, H]]
        return pts
    raise ValueError(kind)


def dome_profile(kind: str, r: float, h: float, n=24) -> list[tuple[float, float]]:
    """(radius, z) outer profile from base (r,0) to tip (0,h)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        if kind == "dome":           # hemisphere / elliptic
            a = t * math.pi / 2
            pts.append((r * math.cos(a), h * math.sin(a)))
        elif kind == "onion":        # bulb: swells to 1.25r then pinches to a point
            z = t * h
            if t < 0.45:
                rr = r * (1.0 + 0.28 * math.sin(t / 0.45 * math.pi / 2))
            else:
                s = (t - 0.45) / 0.55
                rr = r * 1.28 * (math.cos(s * math.pi / 2) ** 1.6) * (1 - 0.15 * s)
            pts.append((rr, z))
        elif kind == "helmet":       # шлем: pointed ogival dome
            a = t * math.pi / 2
            pts.append((r * math.cos(a) ** 1.2, h * math.sin(a) ** 0.85))
        elif kind == "bell":         # baroque bell-shaped helmet
            z = t * h
            rr = r * (1 - t) ** 0.6 * (1 + 0.25 * math.sin(t * math.pi * 1.2))
            pts.append((rr, z))
        elif kind == "cone":
            pts.append((r * (1 - t), h * t))
        elif kind == "saucer":
            a = t * math.pi / 2
            pts.append((r * math.cos(a), h * 0.45 * math.sin(a)))
    pts[-1] = (0.0, pts[-1][1])
    return pts


def _revolve_roof(kind, r, h, seg, base_z=0.0):
    prof = [(0.0, 0.0)] + dome_profile(kind, r, h, 10 if seg < 16 else 28)
    return g.revolve(prof, seg).translate([0, 0, base_z])


@element("roof", "roofs", "Roof on a `top` anchor. Types: " + ", ".join(ROOF_TYPES) + ". Hip/gable/etc use the footprint "
         "bounding box; gable ends are filled with wall material, so the building stays closed.",
         {"type": P("gable", "", ROOF_TYPES), "pitch": P(35.0, "slope in degrees (ignored if h given)"),
          "h": P(None, "ridge height above the wall top (m)"), "overhang": P(0.4, "eave overhang"),
          "t": P(0.18, "roof thickness"), "ridge": P("auto", "ridge direction", ["auto", "x", "y"]),
          "material": P("roof", ""), "gable_material": P("gable", ""),
          "closed_eaves": P(False, "fill the whole eave area (temples, pediments over porticoes)"),
          "parapet_h": P(0.6, "flat roof parapet height"), "break_in": P(0.25, "mansard/gambrel break inset"),
          "break_h": P(0.6, "mansard/gambrel break height (fraction)"), "tiers": P(3, "pagoda tiers")},
         attach="top", title_ru="Крыша", anchors="ridge (point), top (apex top-anchor)")
def roof(p, ctx):
    a_ = ctx.anchor
    fp = a_.footprint if (a_ and a_.footprint) else [(-5, -4), (5, -4), (5, 4), (-5, 4)]
    x0, x1, y0, y1 = _bbox(fp)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b = (x1 - x0) / 2, (y1 - y0) / 2
    kind = p["type"]
    rot = 0.0
    ridge = p["ridge"]
    if (ridge == "y") or (ridge == "auto" and b > a and kind not in ("shed",)):
        a, b, rot = b, a, 90.0
    o, t = float(p["overhang"]), float(p["t"])
    pitch = math.radians(float(p["pitch"]))
    mat, gmat = ctx.mat(p["material"]), ctx.mat(p["gable_material"])
    part = Part()
    is_round = a_ and a_.extra.get("round")
    seg = ctx.seg(max(a, b), 10, 64)
    place = g.mat_t(cx, cy, 0) @ g.mat_rz(rot)

    if kind == "flat":
        cs = g.poly(fp)
        part.add(g.extrude(g.offset2(cs, o), t, -0.02), mat)
        ph = float(p["parapet_h"])
        if ph > 0:
            ring = g.offset2(cs, min(o, 0.05)) - g.offset2(cs, -0.3)
            part.add(g.extrude(ring, ph, -0.02), gmat)
        part.anchors["top"] = top_anchor(fp, t, t)
        part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, t - 0.05))  # slightly embedded: things placed here connect
        return part

    if kind in ("dome", "onion", "helmet", "bell", "cone") or (is_round and kind in ("pyramid", "tent")):
        r = (a_.extra.get("r") if is_round else min(a, b)) + o
        hk = {"dome": 1.0, "onion": 1.6, "helmet": 1.4, "bell": 1.5, "cone": 2.2}.get(kind, 2.2)
        H = float(p["h"]) if p["h"] else r * hk if kind != "cone" else r * math.tan(pitch)
        prof = "cone" if kind in ("pyramid", "tent") else kind
        sides = seg if is_round or kind != "cone" else seg
        part.add(g.xf(_revolve_roof(prof, r, H, sides, -0.02), g.mat_t(cx, cy, 0)), mat)
        part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, H - 0.05))
        part.anchors["top"] = top_anchor([(cx - .2, cy - .2), (cx + .2, cy - .2), (cx + .2, cy + .2), (cx - .2, cy + .2)], H - 0.05, H)
        return part

    if kind == "barrel":
        A = a + o
        cs = g.circle2(b + o, seg)
        vault = g.prism_yz(cs, -A, A).trim_by_plane([0, 0, 1], 0)
        inner = g.prism_yz(g.circle2(b + o - t, seg), -A - 1, A + 1)
        shell = vault - inner
        part.add(g.xf(shell, place), mat)
        part.add(g.xf(g.prism_yz(g.circle2(b, seg), -a, a).trim_by_plane([0, 0, 1], 0), place), gmat)
        part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, b + o))
        return part

    if kind == "pagoda":
        tiers = int(p["tiers"])
        z = 0.0
        sa, sb = a, b
        for i in range(tiers):
            hh = max(0.6, sb * math.tan(math.radians(25)))
            pts = _roof_points("hip", sa, sb, hh, o * 1.8, -o * 0.4, p)
            outer = g.hull(pts)
            part.add(g.xf((outer - outer.translate([0, 0, -t * 2])).translate([0, 0, z]), place), mat)
            part.add(g.xf(g.boxc(sa * 2 * 0.98, sb * 2 * 0.98, hh * 0.6 + 0.3, 0, 0, z), place), gmat)
            z += hh * 0.6 + 0.3
            sa, sb = sa * 0.72, sb * 0.72
            if i < tiers - 1:
                part.add(g.xf(g.boxc(sa * 2, sb * 2, 1.0, 0, 0, z - 0.2), place), gmat)
                z += 0.8
        part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, z))
        return part

    if kind == "cross_gable":
        H = float(p["h"]) if p["h"] else b * math.tan(pitch)
        ze = -o * H / b
        outs = [g.hull(_roof_points("gable", a, b, H, o, ze, p)),
                g.hull(_roof_points("gable", b, a, H, o, ze, p)).rotate([0, 0, 90])]
        outer = g.union(outs)
        H2 = H
    else:
        if p["h"]:
            H = float(p["h"])
        elif kind == "tent":
            H = b * math.tan(math.radians(max(float(p["pitch"]), 60)))
        else:
            H = b * math.tan(pitch)
        if kind == "shed":
            H = 2 * b * math.tan(pitch) if not p["h"] else H
        slope = H / (2 * b if kind == "shed" else b)
        ze = -o * slope
        outer = g.hull(_roof_points(kind, a, b, H, o, ze, p))
        H2 = H
    # shell: outer volume minus the same volume shifted down by the thickness
    cosp = math.cos(math.atan(H2 / max(b, 0.01)))
    inner = outer.translate([0, 0, -t / max(cosp, 0.2)])
    shell = outer - inner
    # gable/attic fill: footprint prism clipped by the inner surface (slight overlap with the shell)
    fill_poly = g.poly([(x - cx, y - cy) for x, y in fp])
    fill_poly = fill_poly.rotate(-rot)
    if p["closed_eaves"]:
        fill_poly = g.offset2(fill_poly, o - 0.08)
    fill = g.extrude(fill_poly, H2 + 1, -0.02) ^ inner.translate([0, 0, 0.03])
    part.add(g.xf(shell, place), mat)
    part.add(g.xf(fill, place), gmat)
    part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, H2))
    # slope anchors for dormers etc: face-like frames on the two main slopes
    for nm, sgn in (("slope_front", -1), ("slope_back", 1)):
        ang = math.atan2(H2, b)
        m = place @ g.mat_t(0, sgn * b, 0) @ g.mat_rz(0 if sgn < 0 else 180) @ g.mat_rx(0)
        part.anchors[nm] = Anchor(m, "point", w=2 * a, extra={"pitch_deg": math.degrees(ang)})
    return part


@element("dome", "roofs", "Dome on a drum: hemisphere, onion (луковица), helmet (шлем), bell (барочная), saucer, cone. "
         "Optional drum with windows, kokoshniki ring, lantern, cross. Attach to a `top` anchor or place free.",
         {"profile": P("dome", "", ["dome", "onion", "helmet", "bell", "saucer", "cone"]), "r": P(3.0, "dome base radius"),
          "h": P(None, "dome height (default by profile)"), "drum_h": P(0.0, "drum height (0 = none)"),
          "drum_r": P(None, "drum radius (default r*0.95)"), "drum_windows": P(0, "number of windows in the drum"),
          "neck_h": P(0.0, "thin neck between drum and onion"), "kokoshniki": P(0, "ring of decorative arched gables"),
          "lantern": P(False, "small lantern on top"), "cross": P("none", "", ["none", "orthodox", "latin", "crescent", "spike", "ball"]),
          "material": P("dome", ""), "drum_material": P("wall", ""), "ribs": P(0, "dome ribs count")},
         attach="any", title_ru="Купол / глава", anchors="top (apex)")
def dome(p, ctx):
    r = float(p["r"])
    prof = p["profile"]
    hk = {"dome": 1.0, "onion": 1.7, "helmet": 1.3, "bell": 1.5, "saucer": 0.6, "cone": 2.0}[prof]
    H = float(p["h"]) if p["h"] else r * hk
    seg = ctx.seg(r, 10, 64)
    part = Part()
    z = 0.0
    dh = float(p["drum_h"])
    dmat, mat = ctx.mat(p["drum_material"]), ctx.mat(p["material"])
    if dh > 0:
        dr = float(p["drum_r"]) if p["drum_r"] else r * 0.95
        drum = g.cyl(dr, dh, seg)
        n = int(p["drum_windows"])
        if n:
            ww = min(2 * math.pi * dr / n * 0.45, 1.4)
            wh = min(dh * 0.6, ww * 2.4)
            from .common import opening_shape
            shp = opening_shape("arch", ww, wh, 16)
            cuts, glass = [], []
            for i in range(n):
                R = g.mat_rz(360 * i / n) @ g.mat_t(0, -dr, (dh - wh) / 2)
                cuts.append(g.xf(g.prism_xz(shp, -0.6, 0.3), R))
                glass.append(g.xf(g.prism_xz(g.offset2(shp, 0.04), 0.1, 0.15), R))  # local +y points inward here
            drum = g.subtract(g.tag(drum, dmat), [g.tag(c, dmat) for c in cuts])
            drum = drum + g.cyl(dr - 0.35, dh, seg)  # inner core keeps it solid
            for gl in glass:
                part.add(gl, ctx.mat("glass"))
        part.add(drum, dmat)
        part.add(g.cyl(dr + 0.12, 0.25, seg, dh - 0.25), ctx.mat("trim"))
        k = int(p["kokoshniki"])
        if k:
            from .common import opening_shape
            kw = 2 * math.pi * dr / k * 0.95
            shp = opening_shape("ogee", kw, kw * 0.9, 16)
            for i in range(k):
                R = g.mat_rz(360 * (i + 0.5) / k) @ g.mat_t(0, -dr + 0.1, -kw * 0.25)
                part.add(g.xf(g.prism_xz(shp, -0.4, 0.15), R), dmat)
        z = dh
    nh = float(p["neck_h"])
    if nh > 0:
        part.add(g.cyl(r * 0.55, nh + 0.05, seg, z - 0.02), dmat)
        z += nh
    rr = r if prof != "onion" else r / 1.28
    d = _revolve_roof(prof, rr, H, seg, z - 0.02)
    part.add(d, mat)
    ribs = int(p["ribs"])
    if ribs and not ctx.low:
        for i in range(ribs):
            rib = g.revolve([(0, 0)] + dome_profile(prof, rr + 0.08, H + 0.08, 20), 4)
            rib = rib ^ g.boxc(0.12, rr * 3, H * 2, 0, 0, -1).rotate([0, 0, 360 * i / ribs])
            part.add(rib.translate([0, 0, z - 0.02]), ctx.mat("trim"))
    top = z + H - 0.05
    if p["lantern"]:
        lr = r * 0.2
        part.add(g.cyl(lr, lr * 2.2, ctx.seg(lr), top - 0.2), dmat)
        part.add(_revolve_roof("dome", lr * 1.1, lr * 1.2, ctx.seg(lr), top + lr * 2.2 - 0.25), mat)
        top += lr * 2.2 - 0.25 + lr * 1.2 - 0.08  # just below the lantern apex
    _cross(p["cross"], top, max(0.6, r * 0.45), part, ctx)
    part.anchors["top"] = top_anchor([(-.2, -.2), (.2, -.2), (.2, .2), (-.2, .2)], top, top)
    return part


def _cross(kind, z, size, part, ctx):
    if kind == "none":
        return
    m = ctx.mat("cross")
    t = size * 0.07
    if kind in ("orthodox", "latin"):
        part.add(g.box(-t, -t, z - 0.1, t, t, z + size), m)
        part.add(g.box(-size * 0.32, -t, z + size * 0.62, size * 0.32, t, z + size * 0.62 + 2 * t), m)
        if kind == "orthodox":
            part.add(g.box(-size * 0.17, -t, z + size * 0.82, size * 0.17, t, z + size * 0.82 + 1.6 * t), m)
            part.add(g.beam([-size * 0.2, 0, z + size * 0.25], [size * 0.2, 0, z + size * 0.38], 2 * t, 1.6 * t), m)
        part.add(g.sphere(size * 0.09, 12, (0, 0, z)), m)
    elif kind == "ball":
        part.add(g.sphere(size * 0.25, ctx.seg(size * .25), (0, 0, z + size * 0.2)), m)
    elif kind == "spike":
        part.add(g.cyl(size * 0.06, size, 8, z - 0.1, 0.005), m)
    elif kind == "crescent":
        c = g.circle2(size * 0.3, 24) - g.circle2(size * 0.26, 24, size * 0.1, 0.0)
        part.add(g.prism_xz(c, -t, t).translate([0, 0, z + size * 0.5]), m)
        part.add(g.cyl(t, size * 0.25, 8, z - 0.1), m)


@element("cross", "roofs", "Cross / finial on top of a dome, spire or gable (orthodox, latin, ball, spike, crescent).",
         {"kind": P("orthodox", "", ["orthodox", "latin", "ball", "spike", "crescent"]), "size": P(1.5, "")},
         title_ru="Крест / навершие")
def cross(p, ctx):
    part = Part()
    _cross(p["kind"], 0.0, float(p["size"]), part, ctx)
    return part


@element("spire", "roofs", "Spire / шпиль / шатёр: tall pointed roof on a polygonal base, optional base ring and lucarnes.",
         {"r": P(2.0, "base radius"), "h": P(12.0, ""), "sides": P(8, "0 = round"), "base_h": P(0.6, "base ring"),
          "material": P("roof", ""), "finial": P("ball", "", ["none", "ball", "spike", "orthodox", "latin"]),
          "lucarnes": P(0, "small gabled openings around the base"), "needle": P(False, "soviet-style thin needle with star")},
         attach="any", title_ru="Шпиль / шатёр", anchors="top")
def spire(p, ctx):
    r, H = float(p["r"]), float(p["h"])
    n = int(p["sides"]) or ctx.seg(r)
    part = Part()
    bh = float(p["base_h"])
    if bh > 0:
        part.add(g.cyl(r * 1.08, bh, n), ctx.mat("trim"))
    part.add(g.cyl(r, H, n, bh - 0.02, 0.02), ctx.mat(p["material"]))
    for i in range(int(p["lucarnes"])):
        a = 360 * i / int(p["lucarnes"])
        lw = r * 0.5
        luc = g.hull([[-lw / 2, -r * 0.2, 0], [lw / 2, -r * 0.2, 0], [-lw / 2, -r * 1.0, 0], [lw / 2, -r * 1.0, 0],
                      [0, -r * 0.2, lw * 1.3], [0, -r * 1.0, lw * 1.3]])
        part.add(g.xf(luc, g.mat_rz(a) @ g.mat_t(0, 0, bh + H * 0.12)), ctx.mat(p["material"]))
    top = bh + H
    if p["needle"]:
        part.add(g.cyl(r * 0.05, H * 0.35, 8, top - 0.3, 0.01), ctx.mat("accent"))
        star = g.poly([(math.cos(math.pi / 2 + i * math.pi / 5) * (0.6 if i % 2 == 0 else 0.25) * r * 0.4,
                        math.sin(math.pi / 2 + i * math.pi / 5) * (0.6 if i % 2 == 0 else 0.25) * r * 0.4) for i in range(10)])
        part.add(g.prism_xz(star, -0.1, 0.1).translate([0, 0, top + H * 0.3]), ctx.mat("accent"))
        top += H * 0.45
    elif p["finial"] != "none":
        _cross(p["finial"], top - 0.1, max(0.5, r * 0.5), part, ctx)
    part.anchors["top"] = top_anchor([(-.1, -.1), (.1, -.1), (.1, .1), (-.1, .1)], top, top)
    return part


@element("chimney", "roofs", "Chimney stack on a `top` anchor at [x, y]; starts below the roof so it always connects.",
         {"w": P(0.6, ""), "d": P(0.6, ""), "h": P(4.0, "height above the wall top"), "material": P("chimney", ""),
          "cap": P(True, "")}, attach="top", title_ru="Дымовая труба")
def chimney(p, ctx):
    w, d, h = float(p["w"]), float(p["d"]), float(p["h"])
    m = ctx.mat(p["material"])
    part = Part().add(g.boxc(w, d, h + 0.5, 0, 0, -0.5), m)
    if p["cap"]:
        part.add(g.boxc(w + 0.12, d + 0.12, 0.12, 0, 0, h - 0.1), m)
    return part


@element("dormer", "roofs", "Dormer on a `top` anchor (of the walls) at [x, y]: small gabled box poking out of the roof. "
         "Exposes `front` face for a window.",
         {"w": P(1.6, ""), "h": P(1.6, "wall height"), "depth": P(2.5, "how far back into the roof"),
          "pitch": P(45.0, ""), "material": P("wall", ""), "roof_material": P("roof", ""), "facing": P("front", "", ["front", "back", "left", "right"])},
         attach="top", title_ru="Слуховое окно (дормер)", anchors="front (face)")
def dormer(p, ctx):
    w, h, D = float(p["w"]), float(p["h"]), float(p["depth"])
    rh = w / 2 * math.tan(math.radians(float(p["pitch"])))
    part = Part()
    rot = {"front": 0, "back": 180, "left": -90, "right": 90}[p["facing"]]
    R = g.mat_rz(rot)
    body = g.box(-w / 2, 0, -0.3, w / 2, D, h)
    gab = g.hull([[-w / 2, 0, h - 0.01], [w / 2, 0, h - 0.01], [0, 0, h + rh], [-w / 2, D, h - 0.01], [w / 2, D, h - 0.01], [0, D, h + rh]])
    part.add(g.xf(body + gab, R), ctx.mat(p["material"]))
    o = 0.15
    roofv = g.hull([[-w / 2 - o, -o, h - o * rh / (w / 2)], [w / 2 + o, -o, h - o * rh / (w / 2)], [0, -o, h + rh + 0.05],
                    [-w / 2 - o, D, h - o * rh / (w / 2)], [w / 2 + o, D, h - o * rh / (w / 2)], [0, D, h + rh + 0.05]])
    part.add(g.xf(roofv - roofv.translate([0, 0, -0.15]), R), ctx.mat(p["roof_material"]))
    part.anchors["front"] = Anchor(R @ g.mat_frame([-w / 2, 0, 0], [1, 0, 0], [0, -1, 0], [0, 0, 1]), "face", w=w, h=h, depth=0.3,
                                   floors=1, floor_h=h)
    return part


@element("pinnacle", "decor", "Gothic pinnacle / obelisk / finial post: square shaft + pyramid top.",
         {"w": P(0.6, ""), "h": P(3.0, "total height"), "top": P(0.45, "fraction that is the pointed top"),
          "material": P("trim", ""), "crockets": P(True, "small knobs (realistic)")}, title_ru="Пинакль / обелиск")
def pinnacle(p, ctx):
    w, h = float(p["w"]), float(p["h"])
    ht = h * float(p["top"])
    m = ctx.mat(p["material"])
    part = Part().add(g.boxc(w, w, h - ht + 0.02), m)
    part.add(g.hull([[-w * .6, -w * .6, h - ht], [w * .6, -w * .6, h - ht], [-w * .6, w * .6, h - ht], [w * .6, w * .6, h - ht], [0, 0, h]]), m)
    if p["crockets"] and not ctx.low:
        for k in range(3):
            z = h - ht + ht * (k + 1) / 4
            s = w * 0.6 * (1 - (k + 1) / 4)
            for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                part.add(g.sphere(w * 0.09, 8, (sx * s, sy * s, z)), m)
    return part
