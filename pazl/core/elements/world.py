"""World architecture parts: eastern roofs, sawtooth roofs, pyramids, obelisks, pylons, minarets, chhatris,
shikharas, stupas, iwans, decorative gable walls (Dutch/Hanseatic), bay windows."""
from __future__ import annotations

import math

from .. import geo as g
from ..registry import Anchor, P, Part, element
from .common import face_anchors, opening_shape, top_anchor
from .openings import _window


# ------------------------------------------------------------------ roofs used by roofs.roof()
def _finish_roof(outer, t, fp, cx, cy, rot, place, mat, gmat, H, part, extra=()):
    inner = outer.translate([0, 0, -t * 1.6])
    part.add(g.xf(g.union([outer - inner] + list(extra)), place), mat)
    fill_poly = g.poly([(x - cx, y - cy) for x, y in fp]).rotate(-rot)
    part.add(g.xf(g.extrude(fill_poly, H + 1, -0.02) ^ inner.translate([0, 0, 0.03]), place), gmat)
    part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, H - 0.05))
    part.anchors["top"] = top_anchor([(cx - .3, cy - .3), (cx + .3, cy - .3), (cx + .3, cy + .3), (cx - .3, cy + .3)], H - 0.05, H)
    return part


def eastern_roof(kind, a, b, o, t, pitch, p, place, mat, gmat, fp, cx, cy, rot, ctx):
    """Chinese/Japanese roofs: concave (curved) hip with upturned corners; irimoya = hip below + gable above."""
    part = Part()
    o = max(o, 0.8)
    H = float(p["h"]) if p["h"] else b * math.tan(pitch)
    A, B = a + o, b + o
    ze = -o * 0.25
    if kind == "chinese":
        n = 3 if ctx.low else 6
        levels = []
        for i in range(n + 1):
            s = i / n
            d = B * s                                   # inset from the eave
            z = ze + (H - ze) * s ** 1.7                # concave profile: flat eaves, steep near the ridge
            levels.append((max(A - d, a - b if a > b else 0.0), max(B - d, 0.0), z))
        parts = []
        for (a0, b0, z0), (a1, b1, z1) in zip(levels[:-1], levels[1:]):
            pts = [[sx * a0, sy * b0, z0] for sx in (-1, 1) for sy in (-1, 1)]
            pts += [[sx * max(a1, 0.01), sy * max(b1, 0.01), z1] for sx in (-1, 1) for sy in (-1, 1)]
            parts.append(g.hull(pts))
        outer = g.union(parts)
    else:  # irimoya
        hm = ze + (H - ze) * 0.5
        ins = B * 0.45
        lower = g.hull([[sx * A, sy * B, ze] for sx in (-1, 1) for sy in (-1, 1)] +
                       [[sx * (A - ins), sy * (B - ins), hm] for sx in (-1, 1) for sy in (-1, 1)])
        ag, bg = A - ins * 0.6, B - ins
        upper = g.hull([[sx * ag, sy * bg, hm - 0.05] for sx in (-1, 1) for sy in (-1, 1)] + [[-ag, 0, H], [ag, 0, H]])
        outer = lower + upper
    # upturned eave corners (added to the shell, they overlap its eave edge)
    extra = []
    if not ctx.low:
        k = 0.9
        for sx in (-1, 1):
            for sy in (-1, 1):
                extra.append(g.hull([[sx * (A - 1.2), sy * B, ze], [sx * A, sy * (B - 1.2), ze], [sx * A, sy * B, ze],
                                        [sx * (A + 0.35), sy * (B + 0.35), ze + k], [sx * (A - 1.2), sy * B, ze + t * 2],
                                        [sx * A, sy * (B - 1.2), ze + t * 2]]))
    return _finish_roof(outer, t, fp, cx, cy, rot, place, mat, gmat, H, part, extra)


def sawtooth_roof(kind, a, b, o, t, pitch, p, place, mat, gmat, fp, cx, cy, rot, ctx):
    """Factory sawtooth (shed) roof: teeth along the long axis with glazed vertical faces."""
    part = Part()
    n = max(2, int(p.get("tiers") or 0) if int(p.get("tiers") or 0) > 3 else round(a * 2 / 6))
    w = 2 * a / n
    h = float(p["h"]) if p["h"] else w * math.tan(math.radians(25))
    B = b + min(o, 0.3)
    glass = ctx.mat("glass")
    for i in range(n):
        x0 = -a + i * w
        x1 = x0 + w
        tooth = g.hull([[x0, -B, -0.05], [x0, B, -0.05], [x1, -B, -0.05], [x1, B, -0.05], [x1, -B, h], [x1, B, h]])
        part.add(g.xf(tooth, place), mat)
        if h > 0.6:
            part.add(g.xf(g.box(x1 - 0.06, -B + 0.4, 0.2, x1 + 0.03, B - 0.4, h - 0.15), place), glass)
    part.anchors["ridge"] = Anchor(g.mat_t(cx, cy, h - 0.05))
    return part


# ------------------------------------------------------------------ monuments
@element("step_pyramid", "structure", "Pyramid: smooth (levels=0, Egypt) or stepped (Maya/Aztec, ziggurat) with optional "
         "staircases. Truncated if top_w>0 — exposes `top` for a temple.",
         {"w": P(40.0, "base width"), "d": P(40.0, "base depth"), "h": P(25.0, ""), "top_w": P(0.0, "top platform width (0 = pointed)"),
          "top_d": P(None, "top depth (default = top_w)"), "levels": P(0, "0 = smooth faces"),
          "stairs": P("none", "", ["none", "front", "front_back", "all"]), "stair_w": P(6.0, ""),
          "material": P("stone", ""), "stair_material": P("stairs", "")},
         title_ru="Пирамида / ступенчатая пирамида / зиккурат", anchors="top, front/right/back/left")
def step_pyramid(p, ctx):
    w, d, h = float(p["w"]), float(p["d"]), float(p["h"])
    tw = float(p["top_w"])
    td = float(p["top_d"]) if p["top_d"] is not None else tw
    n = int(p["levels"])
    m = ctx.mat(p["material"])
    part = Part()
    if n <= 0:
        top = [[sx * max(tw, 0.01) / 2, sy * max(td, 0.01) / 2, h] for sx in (-1, 1) for sy in (-1, 1)]
        part.add(g.hull([[sx * w / 2, sy * d / 2, 0] for sx in (-1, 1) for sy in (-1, 1)] + top), m)
    else:
        for i in range(n):
            k = i / n
            lw, ld = w - (w - tw) * k, d - (d - td) * k
            part.add(g.boxc(lw, ld, h / n + 0.02, 0, 0, h * k - 0.01), m)
            if not ctx.low:  # slight batter on each level
                part.add(g.hull([[sx * lw / 2, sy * ld / 2, h * k] for sx in (-1, 1) for sy in (-1, 1)] +
                                [[sx * (lw / 2 + 0.3), sy * (ld / 2 + 0.3), h * k] for sx in (-1, 1) for sy in (-1, 1)] +
                                [[sx * lw / 2, sy * ld / 2, h * k + h / n * 0.4] for sx in (-1, 1) for sy in (-1, 1)]), m)
    sides = {"none": [], "front": [0], "front_back": [0, 180], "all": [0, 90, 180, 270]}[p["stairs"]]
    sw = float(p["stair_w"])
    sm = ctx.mat(p["stair_material"])
    for ang in sides:
        depth_base, depth_top = (d, td) if ang in (0, 180) else (w, tw)
        run = (depth_base - depth_top) / 2
        steps = max(4, int(h / 0.35))
        st = []
        for k in range(steps):
            z1 = h * (k + 1) / steps
            y0 = -depth_base / 2 - 0.4 + run * k / steps
            st.append(g.box(-sw / 2, y0, -0.01, sw / 2, -depth_top / 2 + 0.2, z1))
        part.add(g.union(st).rotate([0, 0, ang]), sm)
        if not ctx.low:  # balustrade ramps (alfardas)
            for sx in (-1, 1):
                ramp = g.hull([[sx * (sw / 2 + 0.5), -depth_base / 2 - 0.4, 0], [sx * (sw / 2 - 0.05), -depth_base / 2 - 0.4, 0],
                               [sx * (sw / 2 + 0.5), -depth_top / 2 + 0.2, h + 0.4], [sx * (sw / 2 - 0.05), -depth_top / 2 + 0.2, h + 0.4],
                               [sx * (sw / 2 + 0.5), -depth_top / 2 + 0.2, h - 0.5], [sx * (sw / 2 - 0.05), -depth_top / 2 + 0.2, h - 0.5]])
                part.add(ramp.rotate([0, 0, ang]), m)
    fp = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    part.anchors.update(face_anchors(fp, h, 1.0, 1, h, 0))
    tfp = [(-max(tw, .2) / 2, -max(td, .2) / 2), (max(tw, .2) / 2, -max(td, .2) / 2), (max(tw, .2) / 2, max(td, .2) / 2), (-max(tw, .2) / 2, max(td, .2) / 2)]
    part.anchors["top"] = top_anchor(tfp, h - 0.03, h)
    return part


@element("obelisk", "decor", "Obelisk: tapered square shaft with pyramidion on a stepped base.",
         {"w": P(1.8, "shaft base width"), "h": P(20.0, ""), "taper": P(0.65, "top/bottom width"), "base": P(True, ""),
          "material": P("stone", ""), "tip_material": P("accent", "")}, title_ru="Обелиск")
def obelisk(p, ctx):
    w, h, k = float(p["w"]), float(p["h"]), float(p["taper"])
    m = ctx.mat(p["material"])
    part = Part()
    z = 0.0
    if p["base"]:
        part.add(g.boxc(w * 2.2, w * 2.2, w * 0.5), m)
        part.add(g.boxc(w * 1.6, w * 1.6, w * 0.5, 0, 0, w * 0.45), m)
        z = w * 0.9
    sh = h * 0.92
    part.add(g.extrude(g.rect2(w, w, 0, -w / 2), sh, z, (k, k)), m)
    tw = w * k
    part.add(g.hull([[sx * tw / 2, sy * tw / 2, z + sh - 0.02] for sx in (-1, 1) for sy in (-1, 1)] + [[0, 0, z + h]]), ctx.mat(p["tip_material"]))
    return part


@element("pylon", "structure", "Egyptian temple pylon: two battered towers with a gate between, cavetto cornices. "
         "Origin: front-bottom centre, front faces -Y. Exposes `front_l`, `front_r` faces for reliefs.",
         {"w": P(40.0, "total width"), "d": P(8.0, ""), "h": P(18.0, ""), "gate_w": P(5.0, ""), "gate_h": P(10.0, ""),
          "batter": P(0.12, "inward slope ratio"), "material": P("stone", "")},
         title_ru="Пилон (египетский)", anchors="front_l, front_r (face)")
def pylon(p, ctx):
    W, D, H = float(p["w"]), float(p["d"]), float(p["h"])
    gw, gh, bt = float(p["gate_w"]), float(p["gate_h"]), float(p["batter"])
    m = ctx.mat(p["material"])
    part = Part()
    tw = (W - gw) / 2 + 0.3
    sl = H * bt
    for sx in (-1, 1):
        xin = sx * (gw / 2 - 0.3)
        xout = sx * W / 2
        pts = [[xin, 0, 0], [xout, 0, 0], [xin, D, 0], [xout, D, 0],
               [xin, sl, H], [xout - sx * sl, sl, H], [xin, D - sl, H], [xout - sx * sl, D - sl, H]]
        part.add(g.hull(pts), m)
        # cavetto cornice
        x0, x1 = sorted([xin, xout - sx * sl])
        part.add(g.box(x0 - 0.05, sl - 0.6, H - 0.2, x1 + 0.6 * (1 if sx > 0 else 0), D - sl + 0.6, H + 0.9), m)
    gate = g.box(-gw / 2 - 0.4, 0.4, 0, gw / 2 + 0.4, D - 0.4, gh + 2.5)
    gate = gate - g.box(-gw / 2, -1, -0.1, gw / 2, D + 1, gh)
    part.add(gate, m)
    part.add(g.box(-gw / 2 - 0.6, 0.2, gh + 2.2, gw / 2 + 0.6, D - 0.2, gh + 3.0), m)
    for nm, sx in (("front_l", -1), ("front_r", 1)):
        x_left = -W / 2 + sl if sx < 0 else gw / 2
        part.anchors[nm] = Anchor(g.mat_frame([x_left, sl * 0.5, 0], [1, 0, 0], [0, -1, 0], [0, 0, 1]), "face",
                                  w=tw - sl - 0.3, h=H * 0.9, depth=1.0)
    return part


# ------------------------------------------------------------------ islamic / indian
@element("minaret", "structure", "Minaret: square base, shaft (round/octagonal), balconies (şerefe) and a cap: "
         "pencil (Ottoman), onion, lantern, cone, dome. Also usable as a slender tower or chimney stack.",
         {"r": P(1.6, "shaft radius"), "h": P(40.0, "height to the top of the shaft"), "shape": P("round", "", ["round", "octagon", "square"]),
          "base_h": P(6.0, "square base height (0 = none)"), "balconies": P(2, ""), "taper": P(0.85, "top/bottom radius"),
          "cap": P("pencil", "", ["pencil", "onion", "lantern", "cone", "dome", "none"]), "finial": P("crescent", "", ["crescent", "ball", "spike", "none"]),
          "material": P("stone", ""), "cap_material": P("dome", "")},
         title_ru="Минарет", anchors="top")
def minaret(p, ctx):
    from .roofs import _cross, _revolve_roof
    r, H = float(p["r"]), float(p["h"])
    m, cm = ctx.mat(p["material"]), ctx.mat(p["cap_material"])
    n = {"round": ctx.seg(r, 10, 40), "octagon": 8, "square": 4}[p["shape"]]
    part = Part()
    bh = float(p["base_h"])
    if bh > 0:
        part.add(g.boxc(r * 2.6, r * 2.6, bh), m)
        part.add(g.hull([[sx * r * 1.3, sy * r * 1.3, bh - 0.02] for sx in (-1, 1) for sy in (-1, 1)] + [[0, 0, bh + r * 0.8]]), m)
    k = float(p["taper"])
    part.add(g.cyl(r, H - bh + 0.02, n, bh - 0.02, r * k).rotate([0, 0, 22.5 if n == 8 else 45 if n == 4 else 0]), m)
    nb = int(p["balconies"])
    for i in range(nb):
        z = bh + (H - bh) * (0.55 + 0.4 * i / max(1, nb)) if nb > 1 else bh + (H - bh) * 0.8
        rr = r * (1 - (1 - k) * (z - bh) / (H - bh))
        part.add(g.cyl(rr, 0.6, n, z - 0.6, rr * 1.55), m)                 # corbelled underside
        part.add(g.cyl(rr * 1.55, 0.25, n, z - 0.02), m)                   # floor
        part.add(g.cyl(rr * 1.55, 1.0, n, z + 0.2) - g.cyl(rr * 1.45, 1.2, n, z + 0.15), m)  # parapet
    top = H
    rt = r * k
    cap = p["cap"]
    if cap == "pencil":
        part.add(g.cyl(rt * 1.08, rt * 4.5, n, H - 0.05, 0.02), cm)
        top = H + rt * 4.5
    elif cap in ("onion", "dome"):
        part.add(_revolve_roof(cap, rt * (0.95 if cap == "dome" else 0.8), rt * (1.2 if cap == "dome" else 2.0), ctx.seg(rt), H - 0.05), cm)
        top = H + rt * (1.2 if cap == "dome" else 2.0)
    elif cap == "lantern":
        part.add(g.cyl(rt * 0.75, rt * 1.8, n, H - 0.05), m)
        part.add(_revolve_roof("onion", rt * 0.75, rt * 1.8, ctx.seg(rt), H + rt * 1.75 - 0.05), cm)
        top = H + rt * 3.5
    elif cap == "cone":
        part.add(g.cyl(rt * 1.15, rt * 2.5, n, H - 0.05, 0.02), cm)
        top = H + rt * 2.5
    if p["finial"] != "none" and cap != "none":
        _cross(p["finial"], top - 0.15, max(0.8, rt * 0.9), part, ctx)
    part.anchors["top"] = top_anchor([(-.2, -.2), (.2, -.2), (.2, .2), (-.2, .2)], top, top)
    return part


@element("chhatri", "decor", "Chhatri / kiosk / gazebo / bell-cote: columns on a platform, wide eave slab (chhajja), dome. "
         "Use on roofs (Mughal, Rajput) or as a garden pavilion.",
         {"w": P(3.0, ""), "h": P(2.6, "column height"), "cols": P(4, "4, 6 or 8"), "dome": P("onion", "", ["onion", "dome", "bell", "cone", "flat"]),
          "material": P("stone", ""), "dome_material": P("dome", "")}, title_ru="Чхатри / беседка-павильон", anchors="top")
def chhatri(p, ctx):
    from .roofs import _cross, _revolve_roof
    w, h, n = float(p["w"]), float(p["h"]), int(p["cols"])
    m = ctx.mat(p["material"])
    part = Part()
    part.add(g.boxc(w + 0.4, w + 0.4, 0.3), m)
    R = w / 2 - 0.2
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        x, y = R * math.cos(a), R * math.sin(a)
        part.add(g.cyl(0.13, h + 0.1, 8, 0.25, None, x, y), m)
    zt = 0.3 + h
    part.add(g.extrude(g.circle2(w / 2 + 0.6, n * 2 if n > 4 else 8), 0.18, zt - 0.02), m)
    part.add(g.extrude(g.circle2(w / 2 - 0.05, 16), 0.5, zt + 0.1), m)
    if p["dome"] != "flat":
        rr = w / 2 - 0.1
        hh = {"onion": rr * 1.6, "dome": rr, "bell": rr * 1.4, "cone": rr * 1.8}[p["dome"]]
        part.add(_revolve_roof(p["dome"], rr / (1.28 if p["dome"] == "onion" else 1), hh, ctx.seg(rr), zt + 0.55), ctx.mat(p["dome_material"]))
        top = zt + 0.55 + hh
        _cross("spike", top - 0.1, 0.8, part, ctx)
    else:
        top = zt + 0.6
    part.anchors["top"] = top_anchor([(-.2, -.2), (.2, -.2), (.2, .2), (-.2, .2)], top, top)
    return part


@element("shikhara", "roofs", "Hindu temple tower (shikhara / vimana): curvilinear tiers with projecting rathas, "
         "amalaka ring and kalasha finial. Place on a `top` anchor of the sanctum (garbhagriha).",
         {"w": P(8.0, "base width"), "h": P(18.0, ""), "tiers": P(12, ""), "rathas": P(2, "projections per side (0-3)"),
          "curve": P(1.6, "curvature exponent"), "stepped": P(False, "Dravidian pyramidal tiers (vimana/gopuram)"),
          "material": P("stone", ""), "finial_material": P("accent", "")}, title_ru="Шикхара / вимана", anchors="top")
def shikhara(p, ctx):
    w, H, n = float(p["w"]), float(p["h"]), max(3, int(p["tiers"]))
    if ctx.low:
        n = max(3, n // 2)
    m = ctx.mat(p["material"])
    part = Part()
    kc = float(p["curve"])
    th = H / n
    for i in range(n):
        t = i / n
        s = w * (1 - 0.62 * t ** kc) if not p["stepped"] else w * (1 - 0.6 * t)
        z = i * th
        part.add(g.boxc(s, s, th + 0.03, 0, 0, z - 0.01), m)
        if p["stepped"] and not ctx.low:  # miniature pavilions on each tier
            for k in range(-1, 2):
                for sx, sy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    cx = sx * s / 2 + (k * s / 3 if sx == 0 else 0)
                    cy = sy * s / 2 + (k * s / 3 if sy == 0 else 0)
                    part.add(g.boxc(s * 0.12, s * 0.12, th * 0.6, cx, cy, z + th * 0.9), m)
        for j in range(int(p["rathas"])):
            f = 0.55 - j * 0.2
            out = w * 0.04 * (j + 1)
            part.add(g.boxc(s * f, s + 2 * out, th * 0.92, 0, 0, z), m)
            part.add(g.boxc(s + 2 * out, s * f, th * 0.92, 0, 0, z), m)
    st = w * (1 - 0.62) if not p["stepped"] else w * 0.4
    seg = ctx.seg(st, 12, 32)
    am = g.cyl(st * 0.62, st * 0.22, seg, H - 0.02)
    if not ctx.low:
        ribs = [g.sphere(st * 0.09, 6, (math.cos(a) * st * 0.6, math.sin(a) * st * 0.6, H + st * 0.11))
                for a in [2 * math.pi * k / 16 for k in range(16)]]
        am = am + g.union(ribs)
    part.add(am, m)
    zt = H + st * 0.2
    kal = g.revolve([(0, 0), (st * 0.25, 0), (st * 0.3, st * 0.25), (st * 0.12, st * 0.45), (st * 0.18, st * 0.6), (0.02, st * 0.95), (0, st * 0.95)], ctx.seg(st * 0.3))
    part.add(kal.translate([0, 0, zt - 0.02]), ctx.mat(p["finial_material"]))
    top = zt + st * 0.9
    part.anchors["top"] = top_anchor([(-.2, -.2), (.2, -.2), (.2, .2), (-.2, .2)], top, top)
    return part


@element("stupa", "structure", "Buddhist stupa / dagoba / chorten: terraces, hemispherical or bell dome, harmika and "
         "a spire of umbrella discs.",
         {"r": P(8.0, "dome radius"), "profile": P("dome", "", ["dome", "bell"]), "terraces": P(2, ""), "rings": P(9, "chattra discs"),
          "material": P("plaster_white", ""), "spire_material": P("accent", "")}, title_ru="Ступа", anchors="top")
def stupa(p, ctx):
    from .roofs import _revolve_roof
    r = float(p["r"])
    m = ctx.mat(p["material"])
    part = Part()
    z = 0.0
    for i in range(int(p["terraces"])):
        s = r * 2.6 - i * r * 0.35
        part.add(g.boxc(s, s, r * 0.18 + 0.02, 0, 0, z - 0.01), m)
        z += r * 0.18
    part.add(g.cyl(r * 1.02, r * 0.2, ctx.seg(r), z - 0.01), m)
    z += r * 0.2
    hh = r * (0.95 if p["profile"] == "dome" else 1.25)
    part.add(_revolve_roof(p["profile"], r, hh, ctx.seg(r), z - 0.02), m)
    z += hh * 0.92
    part.add(g.boxc(r * 0.45, r * 0.45, r * 0.3, 0, 0, z - 0.05), m)
    z += r * 0.25
    sm = ctx.mat(p["spire_material"])
    n = int(p["rings"])
    for i in range(n):
        rr = r * 0.28 * (1 - i / (n + 2))
        part.add(g.cyl(rr, r * 0.08, ctx.seg(rr, 8, 24), z + i * r * 0.12), sm)
    part.add(g.cyl(r * 0.05, n * r * 0.12 + r * 0.4, 8, z), sm)
    top = z + n * r * 0.12 + r * 0.4
    part.anchors["top"] = top_anchor([(-.2, -.2), (.2, -.2), (.2, .2), (-.2, .2)], top, top)
    return part


@element("iwan", "structure", "Iwan / pishtaq: monumental portal block with a deep arched niche (Persian, Timurid, Mughal), "
         "framed by a tile band, optional corner turrets (guldasta). Origin front-bottom centre, front faces -Y.",
         {"w": P(14.0, ""), "h": P(18.0, ""), "d": P(6.0, "block depth"), "niche_w": P(None, "default 0.6*w"),
          "niche_h": P(None, "default 0.75*h"), "niche_d": P(4.0, ""), "arch": P("lancet", "", ["lancet", "arch", "ogee", "horseshoe"]),
          "turrets": P(True, ""), "material": P("wall", ""), "tile_material": P("ceramic_blue", ""),
          "panel_subject": P(None, "art inside the niche (unique texture)")},
         title_ru="Айван / пештак", anchors="front (face), top")
def iwan(p, ctx):
    W, H, D = float(p["w"]), float(p["h"]), float(p["d"])
    nw = float(p["niche_w"] or W * 0.6)
    nh = float(p["niche_h"] or H * 0.75)
    nd = min(float(p["niche_d"]), D - 0.8)
    m, tm = ctx.mat(p["material"]), ctx.mat(p["tile_material"])
    shp = opening_shape(p["arch"], nw, nh, ctx.seg(nw / 2, 8, 40))
    body = g.tag(g.box(-W / 2, 0, 0, W / 2, D, H), m)
    body = body - g.tag(g.prism_xz(shp, -0.1, nd), tm)
    part = Part().add(body, m)
    frame = g.offset2(shp, 1.2) - g.offset2(shp, 0.25)
    frame = frame ^ g.rect2(W - 1.0, H, 0, 0)
    part.add(g.prism_xz(frame, -0.08, 0.05).translate([0, 0, 0]), tm)
    part.add(g.box(-W / 2, -0.08, H - 1.0, W / 2, 0.05, H - 0.3), tm)
    if p["panel_subject"]:
        part.add(g.prism_xz(g.offset2(shp, -0.3), nd - 0.05, nd + 0.05), ctx.art("mosaic", p["panel_subject"]))
    if p["turrets"]:
        for sx in (-1, 1):
            part.add(g.cyl(0.6, 3.0, ctx.seg(.6, 8, 16), H - 0.05, None, sx * (W / 2 - 0.6), 0.6), m)
            part.add(g.cyl(0.75, 1.2, ctx.seg(.75, 8, 16), H + 2.9, 0.02, sx * (W / 2 - 0.6), 0.6), tm)
    part.anchors["front"] = Anchor(g.mat_frame([-W / 2, 0, 0], [1, 0, 0], [0, -1, 0], [0, 0, 1]), "face", w=W, h=H, depth=D)
    part.anchors["top"] = top_anchor([(-W / 2, 0), (W / 2, 0), (W / 2, D), (-W / 2, D)], H, H)
    return part


# ------------------------------------------------------------------ facades
@element("gable_wall", "decor", "Decorative street gable above the eaves (Dutch / Hanseatic / Baltic / baroque): stepped, "
         "neck, bell, curved or plain triangle. Put on a face at [\"50%\", face height]. Exposes `face` for windows.",
         {"kind": P("stepped", "", ["stepped", "neck", "bell", "curved", "triangle", "spout"]), "w": P(None, "width (default face width)"),
          "h": P(5.0, "height above the anchor point"), "steps": P(5, "for stepped"), "t": P(None, "thickness (default wall)"),
          "finial": P("ball", "", ["ball", "spike", "none"]), "material": P("wall", ""), "trim_material": P("trim", ""),
          "proud": P(0.12, "how far it stands in front of the face: covers the roof's edge and overhang")},
         attach="face", title_ru="Фигурный щипец (голландский, ступенчатый)", anchors="face")
def gable_wall(p, ctx):
    from .roofs import _cross
    a = ctx.anchor
    W = float(p["w"]) if p["w"] else (a.w if a else 6.0)
    H = float(p["h"])
    t = float(p["t"]) if p["t"] else (a.depth if a else 0.5)
    k = p["kind"]
    if k == "stepped":
        n = max(2, int(p["steps"]))
        shp = g.union_cs([g.rect2(W * (1 - i / (n + 0.6)), H * (i + 1) / n - (H * i / n) + 0.02, 0, H * i / n - 0.01) for i in range(n)])
    elif k == "neck":
        shp = g.union_cs([g.rect2(W, H * 0.35), g.rect2(W * 0.38, H)] +
                         [g.circle2(W * 0.17, 24, sx * W * 0.19, H * 0.35) ^ g.rect2(W * 0.31, H, sx * W * 0.345, 0) for sx in (-1, 1)])
    elif k == "bell":
        shp = g.union_cs([g.rect2(W, H * 0.3), opening_shape("ogee", W * 0.8, H, 32), g.rect2(W * 0.3, H * 1.05)])
    elif k == "curved":
        shp = g.union_cs([g.rect2(W, H * 0.25), opening_shape("segmental", W, H, 32)])
    elif k == "spout":
        shp = g.union_cs([opening_shape("triangle", W, H * 0.9, 4), g.rect2(W * 0.25, H)])
    else:
        shp = opening_shape("triangle", W, H, 4)
    pr = float(p["proud"])
    part = Part()
    part.add(g.prism_xz(shp, -t, pr), ctx.mat(p["material"]))
    part.add(g.prism_xz(g.offset2(shp, 0.08) - g.offset2(shp, -0.12), pr - 0.04, pr + 0.08) - g.box(-W, -1, -1, W, 1, 0.05),
             ctx.mat(p["trim_material"]))
    if p["finial"] != "none":
        _cross(p["finial"], H - 0.05, 0.8, part, ctx)
    part.anchors["face"] = Anchor(g.mat_t(-W / 2, pr, 0), "face", w=W, h=H, depth=t + pr, floors=1, floor_h=H)
    return part


@element("bay_window", "openings", "Bay / oriel window (эркер): projecting canted, box or round bay with windows on each facet, "
         "corbel below and a cap. On a face at [u, v]; v>0 makes it an oriel.",
         {"kind": P("canted", "", ["canted", "box", "round"]), "w": P(3.2, ""), "depth": P(1.0, ""), "h": P(3.0, ""),
          "win_w": P(0.9, ""), "win_h": P(1.6, ""), "sill": P(0.8, ""), "storeys": P(1, "stacked storeys"),
          "cap": P("hip", "", ["flat", "hip", "cone", "dome"]), "corbel": P(True, "corbel below (oriel)"),
          "material": P("wall", ""), "roof_material": P("roof", ""), "trim": P("simple", "")},
         attach="face", title_ru="Эркер", anchors="top")
def bay_window(p, ctx):
    w, d, h = float(p["w"]), float(p["depth"]), float(p["h"])
    k = p["kind"]
    if k == "box":
        pts = [(-w / 2, -0.1), (w / 2, -0.1), (w / 2, d), (-w / 2, d)]
    elif k == "round":
        pts = [(-w / 2, -0.1), (w / 2, -0.1)] + [(w / 2 * math.cos(math.pi * i / 10), d * math.sin(math.pi * i / 10)) for i in range(1, 10)]
    else:
        c = d * 0.7
        pts = [(-w / 2, -0.1), (w / 2, -0.1), (w / 2 - c, d), (-w / 2 + c, d)]
    pts = g.ccw(pts)
    cs = g.poly(pts)
    m = ctx.mat(p["material"])
    floors = max(1, int(p["storeys"]))
    H = h * floors
    body = g.tag(g.extrude(cs, H), m)
    part = Part()
    sub = Part()
    # windows on each outward facet (all edges except the one on the wall line y=-0.1)
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        if y0 < 0 and y1 < 0:
            continue
        L = math.hypot(x1 - x0, y1 - y0)
        ww = min(float(p["win_w"]), L - 0.3)
        if ww < 0.3:
            continue
        xa = [(x1 - x0) / L, (y1 - y0) / L, 0]
        na = [xa[1], -xa[0], 0]
        F = g.mat_frame([x0, y0, 0], xa, na, [0, 0, 1])
        for f in range(floors):
            tmp = Part()
            _window({"trim": p["trim"], "mullions": [0, 1]}, ctx, ww, float(p["win_h"]), 0.25, "rect", tmp, L / 2, float(p["sill"]) + f * h)
            for s, mt in tmp.solids:
                sub.add(g.xf(s, F), mt)
            for c, _ in tmp.cutters:
                body = body - g.tag(g.xf(c, F), m)
    part.add(body, m)
    part.solids += sub.solids
    rm = ctx.mat(p["roof_material"])
    part.add(g.extrude(g.offset2(cs, 0.12), 0.2, H - 0.02), m)
    if p["cap"] == "hip":
        part.add(g.extrude(g.offset2(cs, 0.15), d * 0.6, H + 0.15, (0.35, 0.35)), rm)
    elif p["cap"] in ("cone", "dome"):
        from .roofs import _revolve_roof
        r = w / 2
        part.add((_revolve_roof(p["cap"], r, r * (1.6 if p["cap"] == "cone" else 0.8), ctx.seg(r), H + 0.15)
                  .trim_by_plane([0, 1, 0], -0.1)), rm)
    if p["corbel"]:
        part.add(g.extrude(cs, 0.9, -0.88, (1.0, 1.0)) ^ g.hull([[x, y, 0] for x, y in pts] + [[x * 0.3, min(y, 0.0) - 0.1, -0.9] for x, y in pts]), m)
    part.anchors["top"] = top_anchor(pts, H, H)
    return part
