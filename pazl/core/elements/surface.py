"""Surface & inside: decals, automatic weathering, and interior generation (rooms, corridors, doors, stairs,
elevators, furniture) inside a block. Decals live in the overlay layer (not welded into the watertight shell)."""
from __future__ import annotations

import math

from .. import geo as g
from ..decals import DECAL_KINDS
from ..registry import P, Part, element, pct
from .common import clip_to, is_rect

# ------------------------------------------------------------------ decals
DECAL_OFFSET = 0.006  # distance from the wall; each decal gets a unique extra offset -> no z-fighting


@element("decal", "decor", "Decal on a face (overlay layer, no geometry change): graffiti, dirt, soot, moss, rust, water_stain, "
         "crack, peeling, poster, scuff. `at`=[u, v] = bottom centre.",
         {"kind": P("graffiti", "", DECAL_KINDS), "w": P(3.0, ""), "h": P(2.0, ""), "variant": P(None, "0-3, default random"),
          "count": P(1, "scatter this many along the face"), "spread": P(0.0, "random spread along u (m)")},
         attach="face", title_ru="Декаль (граффити, грязь, мох…)")
def decal(p, ctx):
    part = Part()
    for i in range(int(p["count"])):
        v = int(p["variant"]) if p["variant"] is not None else ctx.rng.randrange(4)
        du = ctx.rng.uniform(-1, 1) * float(p["spread"]) if p["spread"] else 0.0
        _quad(part, du, 0.0, float(p["w"]), float(p["h"]), f"decal_{p['kind']}_{v}", ctx)
    return part


def _quad(part, u, v, w, h, mat, ctx, kind="decal"):
    y = DECAL_OFFSET  # the builder staggers every decal to its own depth
    part.decal([[u - w / 2, y, v], [u + w / 2, y, v], [u + w / 2, y, v + h], [u - w / 2, y, v + h]], mat, kind)


def _era(ctx):
    y = ctx.style.get("years") or [1800, 1900]
    return y[0]


@element("weathering", "decor", "Automatic weathering on all walls of a building (`top` anchor): dirt at the base, soot/streaks, "
         "moss on old buildings, graffiti and posters on 20th-century ground floors, cracks, peeling paint.",
         {"amount": P(0.6, "0..1"), "graffiti": P("auto", "", ["auto", "yes", "no"]), "moss": P("auto", "", ["auto", "yes", "no"]),
          "height": P(None, "wall height (default host height)")},
         attach="top", title_ru="Состаривание (грязь, граффити, мох)")
def weathering(p, ctx):
    a = ctx.anchor
    fp = a.footprint if a and a.footprint else [(-5, -4), (5, -4), (5, 4), (-5, 4)]
    H = float(p["height"]) if p["height"] else (a.height if a else 8)
    amt = float(p["amount"])
    year = _era(ctx)
    graffiti = p["graffiti"] == "yes" or (p["graffiti"] == "auto" and year >= 1900)
    moss = p["moss"] == "yes" or (p["moss"] == "auto" and year < 1900)
    part = Part()
    n = len(fp)
    for i in range(n):
        x0, y0 = fp[i]
        x1, y1 = fp[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1:
            continue
        xa = [(x1 - x0) / L, (y1 - y0) / L, 0.0]
        na = [xa[1], -xa[0], 0.0]
        F = g.mat_frame([x0, y0, -H], xa, na, [0, 0, 1])
        sub = Part()
        # dirt band along the whole base (tiles of ~4 m)
        k = max(1, int(L / 4))
        for j in range(k):
            _quad(sub, L * (j + 0.5) / k, 0.0, L / k * 1.15, 1.2 + amt, f"decal_dirt_{ctx.rng.randrange(4)}", ctx)
        for _ in range(int(L / 6 * amt) + 1):  # streaks / stains
            kind = ctx.rng.choice(["soot", "water_stain", "rust", "crack", "peeling", "scuff"])
            w = ctx.rng.uniform(1.0, 3.0)
            hh = ctx.rng.uniform(1.5, min(5.0, H * 0.8))
            u = ctx.rng.uniform(w / 2, max(w / 2 + 0.01, L - w / 2))
            vz = ctx.rng.uniform(0.3, max(0.31, H - hh - 0.3)) if kind != "soot" else max(0.0, H - hh - 0.1)
            _quad(sub, u, vz, w, hh, f"decal_{kind}_{ctx.rng.randrange(4)}", ctx)
        if moss:
            for _ in range(int(L / 5 * amt) + 1):
                w = ctx.rng.uniform(1.0, 2.5)
                _quad(sub, ctx.rng.uniform(w / 2, max(w / 2 + 0.01, L - w / 2)), 0.0, w, ctx.rng.uniform(0.6, 1.5),
                      f"decal_moss_{ctx.rng.randrange(4)}", ctx)
        if graffiti and ctx.rng.random() < 0.4 + amt * 0.5:
            w = ctx.rng.uniform(2.0, 4.0)
            kind = "graffiti" if ctx.rng.random() < 0.75 else "poster"
            _quad(sub, ctx.rng.uniform(w / 2, max(w / 2 + 0.01, L - w / 2)), 0.25, w, w * (0.55 if kind == "graffiti" else 1.2),
                  f"decal_{kind}_{ctx.rng.randrange(4)}", ctx)
        for d in sub.decals:
            d["pts"] = [list((F @ [*q, 1.0])[:3]) for q in d["pts"]]
            d["n"] = list(F[:3, :3] @ d["n"])
            part.decals.append(d)
    return part


# ------------------------------------------------------------------ interiors
PROGRAMS = ["auto", "residential", "office", "school", "shop", "palace", "worship", "hall", "industrial", "none"]
ROOM_SIZE = {"residential": 4.0, "office": 5.0, "school": 7.0, "shop": 8.0, "palace": 7.0, "hall": 99, "worship": 99,
             "industrial": 99}
NAMES = {"residential": ["living", "bedroom", "kitchen", "bath", "bedroom"], "office": ["office", "office", "meeting", "office", "wc"],
         "school": ["classroom", "classroom", "classroom", "wc"], "shop": ["shop", "storage"], "palace": ["salon", "hall", "cabinet", "bedroom"],
         "hall": ["hall"], "worship": ["nave"], "industrial": ["workshop"]}
NAMES_RU = {"living": "гостиная", "bedroom": "спальня", "kitchen": "кухня", "bath": "санузел", "office": "кабинет",
            "meeting": "переговорная", "wc": "туалет", "classroom": "класс", "shop": "торговый зал", "storage": "склад",
            "salon": "салон", "hall": "зал", "cabinet": "кабинет", "nave": "главный зал", "workshop": "цех",
            "corridor": "коридор", "stairs": "лестница", "elevator": "лифт"}


def _split(a0, a1, target, min_w=2.4):
    n = max(1, round((a1 - a0) / target))
    while n > 1 and (a1 - a0) / n < min_w:
        n -= 1
    return [a0 + (a1 - a0) * i / n for i in range(n + 1)]


def _furniture(name, x0, y0, x1, y1, z, ctx, part, low):
    """Simple box furniture by room type (centred, against walls)."""
    if low:
        return
    W, D = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wood, fab, white, metal = ctx.mat("#8a5a3a"), ctx.mat("#6a7d9a"), ctx.mat("#e8e6e0"), ctx.mat("#707478")
    B = lambda w, d, h, x, y, m: part.add(g.boxc(w, d, h + 0.02, x, y, z - 0.02), m)  # noqa: E731
    if name in ("bedroom",) and W > 2.4 and D > 2.4:
        B(1.6, 2.0, 0.5, cx, y0 + 1.1, fab)
        B(1.2, 0.6, 2.0, x1 - 0.7, y1 - 0.35, wood)
    elif name == "living" and W > 3:
        B(2.2, 0.9, 0.8, cx, y0 + 0.55, fab)
        B(1.2, 0.7, 0.45, cx, cy, wood)
        B(1.8, 0.45, 1.8, cx, y1 - 0.3, wood)
    elif name == "kitchen":
        B(min(W - 0.4, 2.6), 0.6, 0.9, cx, y1 - 0.35, white)
        B(1.0, 0.8, 0.75, cx, cy, wood)
    elif name in ("bath", "wc"):
        B(0.75, min(1.7, D - 0.3), 0.6, x0 + 0.45, cy, white)
    elif name in ("office", "cabinet", "classroom"):
        n = max(1, int(W / 1.8))
        for i in range(n):
            x = x0 + W * (i + 0.5) / n
            B(1.4, 0.7, 0.75, x, cy, wood)
            B(0.5, 0.5, 0.45, x, cy - 0.7, metal)
    elif name == "meeting" or name == "salon":
        B(min(W - 1.2, 3.0), 1.1, 0.75, cx, cy, wood)
    elif name in ("shop",):
        for i in range(max(1, int(D / 2.2))):
            B(W * 0.6, 0.5, 1.6, cx, y0 + 1.2 + i * 2.2, white)
    elif name == "nave":  # pews and altar at +X end
        rows = max(2, int((W - 6) / 1.1))
        for i in range(rows):
            x = x0 + 2.0 + i * 1.1
            B(0.45, D * 0.35, 0.9, x, cy - D * 0.22, wood)
            B(0.45, D * 0.35, 0.9, x, cy + D * 0.22, wood)
        B(1.0, 2.0, 1.1, x1 - 1.5, cy, ctx.mat("#c9a227"))
    elif name == "workshop":
        for i in range(max(1, int(W / 6))):
            for j in range(max(1, int(D / 6))):
                B(2.0, 1.2, 1.4, x0 + 3 + i * 6, y0 + 3 + j * 6, metal)


def _u_stairs(part, x0, y0, x1, y1, z0, fh, slab_t, mat, along_x=True):
    """U-shaped stair from z0 to z0+fh inside rect (two flights + landing)."""
    rise = 0.17
    n = max(4, int(round(fh / 2 / rise)))
    rh = fh / 2 / n
    if along_x:
        L = (x1 - x0) - 1.2
        run = L / n
        ym = (y0 + y1) / 2
        for i in range(n):  # flight 1: +X, lower half of y
            part.add(g.box(x0 + i * run, y0, z0 - 0.02, x0 + (i + 1) * run + 0.02, ym - 0.05, z0 + (i + 1) * rh), mat)
        part.add(g.box(x1 - 1.2, y0, z0 + fh / 2 - 0.25, x1, y1, z0 + fh / 2), mat)  # landing
        for i in range(n):  # flight 2: -X, upper half of y
            part.add(g.box(x1 - 1.2 - (i + 1) * run - 0.02, ym + 0.05, z0 + fh / 2 - 0.02, x1 - 1.2 - i * run, y1, z0 + fh / 2 + (i + 1) * rh), mat)
    else:
        L = (y1 - y0) - 1.2
        run = L / n
        xm = (x0 + x1) / 2
        for i in range(n):
            part.add(g.box(x0, y0 + i * run, z0 - 0.02, xm - 0.05, y0 + (i + 1) * run + 0.02, z0 + (i + 1) * rh), mat)
        part.add(g.box(x0, y1 - 1.2, z0 + fh / 2 - 0.25, x1, y1, z0 + fh / 2), mat)
        for i in range(n):
            part.add(g.box(xm + 0.05, y1 - 1.2 - (i + 1) * run - 0.02, z0 + fh / 2 - 0.02, x1, y1 - 1.2 - i * run, z0 + fh / 2 + (i + 1) * rh), mat)


def _spiral(part, cx, cy, r, z0, fh, mat, seg):
    n = max(12, int(fh / 0.18))
    part.add(g.cyl(0.18, fh + 0.04, 12, z0 - 0.02, None, cx, cy), mat)
    for i in range(n):
        a0 = 2 * math.pi * i / 14
        a1 = a0 + 2 * math.pi / 14 * 1.15
        z = z0 + fh * (i + 1) / n
        pts = [[cx, cy, z - 0.18], [cx, cy, z]]
        for a in (a0, a1):
            pts += [[cx + r * math.cos(a), cy + r * math.sin(a), z - 0.18], [cx + r * math.cos(a), cy + r * math.sin(a), z]]
        part.add(g.hull(pts), mat)


def _fit_core(fp, core, elev, X0, X1, Y0, Y1):
    """Slide the stair core (and the lift next to it) over the bounding box until both lie fully inside the footprint;
    no stairs if nothing fits."""
    shape = g.poly(fp)

    def inside(q):
        return q is None or (shape ^ g.poly([(q[0], q[1]), (q[2], q[1]), (q[2], q[3]), (q[0], q[3])])).area() >=             0.98 * (q[2] - q[0]) * (q[3] - q[1])
    if inside(core) and inside(elev):
        return core, elev
    cands = []
    x, step = X0 - core[0], 0.5
    while core[2] + x <= X1 + 1e-6:
        y = Y0 - core[1]
        while core[3] + y <= Y1 + 1e-6:
            cands.append((abs(x) + abs(y), x, y))
            y += step
        x += step
    for _, dx, dy in sorted(cands):
        c = (core[0] + dx, core[1] + dy, core[2] + dx, core[3] + dy)
        e = elev and (elev[0] + dx, elev[1] + dy, elev[2] + dx, elev[3] + dy)
        if inside(c) and inside(e):
            return c, e
    return None, None


@element("interior", "structure", "Interior of a block (attach to `<block>:inner`): rooms by program and era (corridor + rooms, "
         "enfilade for palaces, open halls for churches/factories), partition walls with doors, stairs (U or spiral), "
         "elevators (from ~1880 when tall), slab openings, simple furniture. `plan` lets you give your own rooms per floor: "
         "[{\"floor\":0, \"rooms\":[{\"name\":\"kitchen\",\"rect\":[x0,y0,x1,y1]}]}] (meters from the inner corner).",
         {"program": P("auto", "", PROGRAMS), "plan": P(None, "explicit floor plans"), "corridor": P("auto", "", ["auto", "none", "center"]),
          "stairs": P("auto", "", ["auto", "none", "u", "spiral"]), "elevator": P("auto", "", ["auto", "yes", "no"]),
          "room_size": P(None, "target room width (m)"), "wall_t": P(0.12, ""), "door_w": P(0.9, ""), "door_h": P(2.1, ""),
          "furniture": P(True, ""), "material": P("interior", ""), "stairs_material": P("stairs", "")},
         attach="top", title_ru="Интерьер (комнаты, лестницы, лифты)")
def interior(p, ctx):
    a = ctx.anchor
    part = Part()
    if a is None or not a.footprint:
        part.notes.append("interior needs <block>:inner")
        return part
    ex = a.extra
    floors, fh = a.floors, a.floor_h
    ph, st = float(ex.get("plinth_h", 0)), float(ex.get("slab_t", 0.25))
    fp = a.footprint
    X0, X1 = min(q[0] for q in fp), max(q[0] for q in fp)
    Y0, Y1 = min(q[1] for q in fp), max(q[1] for q in fp)
    prog = p["program"]
    year = _era(ctx)
    if prog == "auto":
        prog = ctx.style.get("_program") or "residential"
    if prog == "none":
        return part
    wt = float(p["wall_t"])
    wm, sm = ctx.mat(p["material"]), ctx.mat(p["stairs_material"])
    seg = 16
    long_x = (X1 - X0) >= (Y1 - Y0)
    open_plan = prog in ("worship", "hall", "industrial")
    want_elev = p["elevator"] == "yes" or (p["elevator"] == "auto" and year >= 1880 and
                                           ((prog == "residential" and floors >= 6) or (prog in ("office", "school", "shop") and floors >= 4)))
    stairs = p["stairs"]
    if stairs == "auto":
        stairs = "none" if floors < 2 else ("spiral" if (year < 1500 or (X1 - X0) < 6 or (Y1 - Y0) < 6) else "u")
    plan_out = []
    # ---- core (stairs + elevator) along the back wall, in the middle of the long side
    core = None
    if stairs == "u":
        cw, cl = 2.7, min(5.5, ((X1 - X0) if long_x else (Y1 - Y0)) * 0.4)
        if long_x:
            cx = (X0 + X1) / 2
            core = (cx - cl / 2, Y1 - cw, cx + cl / 2, Y1)
        else:
            cy = (Y0 + Y1) / 2
            core = (X1 - cw, cy - cl / 2, X1, cy + cl / 2)
    elif stairs == "spiral":
        r = min(1.4, (min(X1 - X0, Y1 - Y0)) * 0.22)
        core = (X1 - 2 * r - 0.2, Y1 - 2 * r - 0.2, X1, Y1)
    elev = None
    if want_elev and core:
        if long_x:
            elev = (core[2], Y1 - 2.2, core[2] + 2.2, Y1)
        else:
            elev = (X1 - 2.2, core[3], X1, core[3] + 2.2)
    if core and not is_rect(fp):  # L / round / wedge footprints: move stairs (+ lift) to a spot fully inside
        core, elev = _fit_core(fp, core, elev, X0, X1, Y0, Y1)
    for f in range(floors):
        z0 = ph + f * fh + (st if (f > 0 or ph < st) else 0.0)
        z1 = ph + (f + 1) * fh - st
        if z1 - z0 < 1.8:
            continue
        rooms = []
        user = None
        if p["plan"]:
            for fl in p["plan"]:
                if fl.get("floor", f) == f or fl.get("floor") == "all":
                    user = fl["rooms"]
        if user:
            rooms = [(r_.get("name", "room"), X0 + r_["rect"][0], Y0 + r_["rect"][1], X0 + r_["rect"][2], Y0 + r_["rect"][3]) for r_ in user]
            corr = None
        elif open_plan:
            rooms = [(NAMES[prog][0], X0, Y0, X1, Y1)]
            corr = None
        else:
            target = float(p["room_size"] or ROOM_SIZE.get(prog, 4.0))
            depth = (Y1 - Y0) if long_x else (X1 - X0)
            use_corr = p["corridor"] == "center" or (p["corridor"] == "auto" and depth >= 8.5 and prog != "palace")
            names = NAMES.get(prog, ["room"])
            k = 0
            if long_x:
                bands = [(Y0, (Y0 + Y1) / 2 - 0.8), ((Y0 + Y1) / 2 + 0.8, Y1)] if use_corr else [(Y0, Y1)]
                corr = (X0, (Y0 + Y1) / 2 - 0.8, X1, (Y0 + Y1) / 2 + 0.8) if use_corr else None
                for b0, b1 in bands:
                    xs = _split(X0, X1, target)
                    for xa, xb in zip(xs[:-1], xs[1:]):
                        rooms.append((names[k % len(names)], xa, b0, xb, b1))
                        k += 1
            else:
                bands = [(X0, (X0 + X1) / 2 - 0.8), ((X0 + X1) / 2 + 0.8, X1)] if use_corr else [(X0, X1)]
                corr = ((X0 + X1) / 2 - 0.8, Y0, (X0 + X1) / 2 + 0.8, Y1) if use_corr else None
                for b0, b1 in bands:
                    ys = _split(Y0, Y1, target)
                    for ya, yb in zip(ys[:-1], ys[1:]):
                        rooms.append((names[k % len(names)], b0, ya, b1, yb))
                        k += 1
            if f == 0 and prog == "shop":
                rooms = [("shop", X0, Y0, X1, Y1)]
                corr = None
        # remove rooms that the core occupies (keep the remainder as a room)
        if core:
            rooms = [r_ for r_ in rooms if not (r_[1] >= core[0] - 0.01 and r_[3] <= core[2] + 0.01 and r_[2] >= core[1] - 0.01 and r_[4] <= core[3] + 0.01)]
        walls, doors = [], []
        h = z1 - z0 + 0.04
        zw = z0 - 0.02

        def wall_seg(xa, ya, xb, yb):
            if abs(xa - xb) < 1e-6 and (abs(xa - X0) < 0.05 or abs(xa - X1) < 0.05):
                return  # on the outer wall
            if abs(ya - yb) < 1e-6 and (abs(ya - Y0) < 0.05 or abs(ya - Y1) < 0.05):
                return
            if abs(xa - xb) < 1e-6:
                walls.append(g.box(xa - wt / 2, min(ya, yb) - 0.06, zw, xa + wt / 2, max(ya, yb) + 0.06, zw + h))
            else:
                walls.append(g.box(min(xa, xb) - 0.06, ya - wt / 2, zw, max(xa, xb) + 0.06, ya + wt / 2, zw + h))

        def door_at(x, y, vertical):
            dw, dh = float(p["door_w"]), float(p["door_h"])
            if vertical:
                doors.append(g.box(x - wt, y - dw / 2, z0, x + wt, y + dw / 2, z0 + dh))
            else:
                doors.append(g.box(x - dw / 2, y - wt, z0, x + dw / 2, y + wt, z0 + dh))

        for name, xa, ya, xb, yb in rooms:
            for (p0, p1) in (((xa, ya), (xb, ya)), ((xb, ya), (xb, yb)), ((xb, yb), (xa, yb)), ((xa, yb), (xa, ya))):
                wall_seg(p0[0], p0[1], p1[0], p1[1])
            # door: towards the corridor if there is one, else towards the building centre / next room
            if corr:
                if long_x:
                    yd = ya if abs(ya - corr[3]) < 0.05 else yb
                    door_at((xa + xb) / 2 + ctx.rng.uniform(-0.25, 0.25) * (xb - xa), yd, False)
                else:
                    xd = xa if abs(xa - corr[2]) < 0.05 else xb
                    door_at(xd, (ya + yb) / 2 + ctx.rng.uniform(-0.25, 0.25) * (yb - ya), True)
            else:  # enfilade / small houses: door on the side towards the next room along the long axis
                if long_x and xb < X1 - 0.05:
                    door_at(xb, (ya + yb) / 2, True)
                elif not long_x and yb < Y1 - 0.05:
                    door_at((xa + xb) / 2, yb, False)
                if long_x and abs(ya - Y0) > 0.05:
                    door_at((xa + xb) / 2, ya, False)
            _furniture(name, xa + wt, ya + wt, xb - wt, yb - wt, z0, ctx, part, ctx.low)
            plan_out.append({"floor": f, "name": name, "name_ru": NAMES_RU.get(name, name),
                             "rect": [round(xa - X0, 2), round(ya - Y0, 2), round(xb - X0, 2), round(yb - Y0, 2)],
                             "area": round((xb - xa) * (yb - ya), 1)})
        if corr:
            plan_out.append({"floor": f, "name": "corridor", "name_ru": "коридор",
                             "rect": [round(corr[0] - X0, 2), round(corr[1] - Y0, 2), round(corr[2] - X0, 2), round(corr[3] - Y0, 2)]})
        if core and stairs == "u":  # stairwell walls with a door to the corridor/hall
            cx0, cy0, cx1, cy1 = core
            for (p0, p1) in (((cx0, cy0), (cx1, cy0)), ((cx0, cy0), (cx0, cy1)), ((cx1, cy0), (cx1, cy1))):
                wall_seg(p0[0], p0[1], p1[0], p1[1])
            if long_x:
                door_at((cx0 + cx1) / 2, cy0, False)
            else:
                door_at(cx0, (cy0 + cy1) / 2, True)
        if elev:
            ex0, ey0, ex1, ey1 = elev
            for (p0, p1) in (((ex0, ey0), (ex1, ey0)), ((ex0, ey0), (ex0, ey1)), ((ex1, ey0), (ex1, ey1))):
                wall_seg(p0[0], p0[1], p1[0], p1[1])
            if long_x:
                door_at((ex0 + ex1) / 2, ey0, False)
            else:
                door_at(ex0, (ey0 + ey1) / 2, True)
        if walls:
            ws = g.union(walls)
            if doors:
                ws = ws - g.union(doors)
            part.add(ws, wm)
        # stairs to the next floor + slab opening above
        if core and f < floors - 1:
            cx0, cy0, cx1, cy1 = core
            if stairs == "u":
                _u_stairs(part, cx0 + wt, cy0 + wt, cx1 - wt / 2, cy1, z0, fh, st, sm, along_x=long_x)
            else:
                r = (cx1 - cx0 - 0.2) / 2
                _spiral(part, (cx0 + cx1) / 2, (cy0 + cy1) / 2, r, z0, fh, sm, seg)
            part.cut(g.box(cx0 + wt, cy0 + 0.02, z1 - 0.05, cx1 - 0.02, cy1 - 0.02, z1 + st + 0.05))
            plan_out.append({"floor": f, "name": "stairs", "name_ru": "лестница",
                             "rect": [round(cx0 - X0, 2), round(cy0 - Y0, 2), round(cx1 - X0, 2), round(cy1 - Y0, 2)]})
        if elev:
            ex0, ey0, ex1, ey1 = elev
            if f < floors - 1:
                part.cut(g.box(ex0 + wt, ey0 + wt, z1 - 0.05, ex1 - 0.02, ey1 - 0.02, z1 + st + 0.05))
            if f == 0:  # the car
                part.add(g.box(ex0 + 0.3, ey0 + 0.3, z0 - 0.02, ex1 - 0.3, ey1 - 0.3, z0 + 2.3), ctx.mat("steel"))
            plan_out.append({"floor": f, "name": "elevator", "name_ru": "лифт",
                             "rect": [round(ex0 - X0, 2), round(ey0 - Y0, 2), round(ex1 - X0, 2), round(ey1 - Y0, 2)]})
    clip_to(part, fp)  # rooms of L / U / round footprints stay inside the walls
    part.info["plan"] = plan_out
    part.info["program"] = prog
    part.info["summary"] = {"floors": floors, "rooms": len([r_ for r_ in plan_out if r_["name"] not in ("corridor", "stairs", "elevator")]),
                            "stairs": stairs, "elevator": bool(elev)}
    return part
