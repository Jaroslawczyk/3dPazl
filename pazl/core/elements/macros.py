"""Macros: whole buildings / building parts expanded into plain, editable elements.

A macro returns Part(children=[element dicts]). Child ids are local (prefixed with the macro id
by the builder), `on` may reference sibling ids. Children without `on` are placed in the macro's frame.
Use them as a fast start, then patch individual children (e.g. "church/main", "church/dome1").
"""
from __future__ import annotations

import math

from ..registry import P, Part, element


def E(id_, type_, on=None, at=None, **params):
    e = {"id": id_, "type": type_, "params": {k: v for k, v in params.items() if not k.startswith("_")}}
    if on:
        e["on"] = on
    if at is not None:
        e["at"] = at
    for k in ("_offset", "_rot", "_repeat", "_mirror_u", "_cut", "_subtract"):
        if k in params:
            e[k[1:]] = params[k]
    return e


def _part(children):
    p = Part()
    p.children = children
    return p


@element("house", "macros", "Generic house: walls, windows on all sides, front door, roof, chimney. Fast start for any dwelling.",
         {"w": P(10.0, ""), "d": P(8.0, ""), "floors": P(2, ""), "floor_h": P(3.0, ""), "roof": P("gable", ""),
          "pitch": P(35.0, ""), "window": P("rect", ""), "trim": P("simple", ""), "chimney": P(True, ""),
          "shutters": P(False, ""), "porch": P(False, "")},
         macro=True, title_ru="Дом (быстрый старт)")
def house(p, ctx):
    w, d = p["w"], p["d"]
    c = [E("main", "block", w=w, d=d, floors=ctx.pick(p["floors"]), floor_h=p["floor_h"]),
         E("win_f", "windows", "main:front", kind=p["window"], trim=p["trim"], shutters=p["shutters"],
           skip=[[_mid_col(w), 0]]),
         E("win_b", "windows", "main:back", kind=p["window"], trim=p["trim"], shutters=p["shutters"]),
         E("win_l", "windows", "main:left", kind=p["window"], trim=p["trim"], cols=max(1, int(d / 4))),
         E("win_r", "windows", "main:right", kind=p["window"], trim=p["trim"], cols=max(1, int(d / 4))),
         E("door", "door", "main:front", [_mid_u(w), 0.6], steps=3, canopy="gable" if p["porch"] else "none"),
         E("roof", "roof", "main:top", type=p["roof"], pitch=p["pitch"])]
    if p["chimney"]:
        c.append(E("chimney", "chimney", "main:top", [w * 0.25, d * 0.15], h=p["floor_h"] + d * 0.5 * math.tan(math.radians(p["pitch"])) * 0.8 + 1))
    return _part(c)


def _cols(w, margin=1.0, wi=1.2):
    gap = max(wi * 0.9, 0.6)
    return max(1, int((w - 2 * margin + gap) // (wi + gap)))


def _mid_u(w, margin=1.0):
    n = _cols(w)
    return margin + (w - 2 * margin) * (n // 2 + 0.5) / n


@element("izba", "macros", "Russian izba (изба): log crib, steep gable roof with planks, carved window casings "
         "(наличники), shutters, porch (крыльцо), stove chimney.",
         {"w": P(6.5, ""), "d": P(6.5, ""), "h": P(2.8, ""), "windows": P(3, "front windows"), "porch": P(True, "")},
         macro=True, title_ru="Изба")
def izba(p, ctx):
    w, d, h = p["w"], p["d"], p["h"]
    n = int(p["windows"])
    us = [w * (i + 1) / (n + 1) for i in range(n)]
    c = [E("crib", "log_cabin", w=w, d=d, h=h),
         E("win_f", "windows", "crib:front", w=0.8, h=1.0, us=us, vs=[1.0], trim="nalichnik", shutters=True,
           trim_material="wood_carved", frame_material="wood_painted_white", mullions=[1, 1]),
         E("win_side", "windows", "crib:left", w=0.8, h=1.0, us=[d * 0.5], vs=[1.0], trim="nalichnik",
           trim_material="wood_carved", frame_material="wood_painted_white"),
         E("door", "door", "crib:right", [d * 0.65, 0.5], w=0.9, h=1.8, steps=3, leaf_material="wood_door",
           canopy="gable" if p["porch"] else "none", trim="none"),
         E("roof", "roof", "crib:top", type="gable", pitch=42, overhang=0.6, ridge="y", material="shingles_wood",
           gable_material="wood_boards"),
         E("chimney", "chimney", "crib:top", [w * 0.15, -d * 0.1], h=3.6, material="brick_red")]
    return _part(c)


@element("dugout", "macros", "Dugout / землянка: shallow pit with low log walls, steep turf roof, earth berm, entrance with steps.",
         {"w": P(4.0, ""), "d": P(5.0, ""), "wall_h": P(0.9, "log wall above ground")},
         macro=True, title_ru="Землянка")
def dugout(p, ctx):
    w, d = p["w"], p["d"]
    return _part([
        E("pit", "log_cabin", None, None, w=w, d=d, h=p["wall_h"] + 1.0, material="log_dark", corner="lapa", _offset=[0, 0, -1.0]),
        E("roof", "roof", "pit:top", type="gable", pitch=50, overhang=0.9, ridge="y", material="turf", gable_material="log_dark", t=0.35),
        E("berm", "mound", None, None, w=w + 3.5, d=d + 3.5, h=p["wall_h"] + 0.3, ring=0.72, material="earth"),
        E("door", "door", "pit:front", ["50%", 0.0], w=0.9, h=1.6, leaf_material="wood_door", trim="none",
          _cut=["roof"]),
    ])


@element("fachwerk_house", "macros", "German half-timbered house (Fachwerkhaus): stone ground floor, jettied timber-framed "
         "upper floors, steep gable roof with dormers.",
         {"w": P(9.0, ""), "d": P(8.0, ""), "upper_floors": P(2, ""), "jetty": P(0.35, "overhang of each upper floor"),
          "pattern": P("mann", "")},
         macro=True, title_ru="Фахверковый дом")
def fachwerk_house(p, ctx):
    w, d = p["w"], p["d"]
    fh = 2.9
    c = [E("ground", "block", w=w, d=d, floors=1, floor_h=3.0, material="stone_rubble", plinth_h=0.3),
         E("gwin", "windows", "ground:front", w=1.0, h=1.3, trim="simple", skip=[[1, 0]], frame_material="frame_brown"),
         E("door", "door", "ground:front", [w * 0.3, 0.3], kind="segmental", w=1.2, h=2.3, steps=2, trim="rustic")]
    prev = "ground"
    for i in range(int(ctx.pick(p["upper_floors"]))):
        j = p["jetty"] * (i + 1)
        uid = f"up{i}"
        c.append(E(uid, "block", f"{prev}:top", None, w=w + 2 * j, d=d + 2 * j, floors=1, floor_h=fh, plinth_h=0,
                   material="plaster_white", _offset=[0, 0, -0.01]))
        c.append(E(f"tf{i}", "timber_frame", f"{uid}:front", pattern=p["pattern"]))
        c.append(E(f"tfb{i}", "timber_frame", f"{uid}:back", pattern=p["pattern"]))
        c.append(E(f"tfl{i}", "timber_frame", f"{uid}:left", pattern="cross"))
        c.append(E(f"tfr{i}", "timber_frame", f"{uid}:right", pattern="cross"))
        c.append(E(f"w{i}", "windows", f"{uid}:front", w=0.9, h=1.3, sill=0.9, cols=3, frame_material="frame_white", trim="none"))
        c.append(E(f"wb{i}", "windows", f"{uid}:back", w=0.9, h=1.3, sill=0.9, cols=3, frame_material="frame_white", trim="none"))
        prev = uid
    c.append(E("roof", "roof", f"{prev}:top", type="gable", pitch=55, overhang=0.35, ridge="x", material="clay_tile",
               gable_material="plaster_white"))
    c.append(E("dormer", "dormer", f"{prev}:top", [0, -d / 2 + 0.3], w=1.6, h=1.5))
    c.append(E("dwin", "window", "dormer:front", ["50%", 0.3], w=0.8, h=0.9, trim="none"))
    c.append(E("chimney", "chimney", f"{prev}:top", [w * 0.3, d * 0.15], h=6.0, material="brick_red"))
    return _part(c)


SERIES = {
    "1-464": dict(floors=5, floor_h=2.8, sections=4, sec_len=15.0, d=11.5, mat="concrete_panel", panel=True,
                  balcony="balcony", rail="solid", win_w=1.5, win_h=1.4),
    "1-447": dict(floors=5, floor_h=2.8, sections=4, sec_len=15.0, d=12.0, mat="brick_silicate", panel=False,
                  balcony="balcony", rail="bars", win_w=1.4, win_h=1.4),
    "II-18": dict(floors=12, floor_h=2.8, sections=1, sec_len=21.0, d=21.0, mat="concrete_tile", panel=True,
                  balcony="loggia", rail="solid", win_w=1.5, win_h=1.4),
    "P-44": dict(floors=17, floor_h=2.8, sections=2, sec_len=22.0, d=14.0, mat="concrete_panel", panel=True,
                 balcony="loggia", rail="solid", win_w=1.5, win_h=1.45),
    "121": dict(floors=9, floor_h=2.8, sections=3, sec_len=16.0, d=12.5, mat="concrete_tile", panel=True,
                balcony="balcony", rail="solid", win_w=1.5, win_h=1.4),
}


@element("panel_building", "macros", "Soviet residential building by series: 1-464 / 1-447 (khrushchyovka), 121, P-44, II-18 "
         "(point tower). Panels with joints, windows, balconies/loggias, entrances with canopies, flat roof.",
         {"series": P("1-464", "", list(SERIES)), "floors": P(None, "override"), "sections": P(None, "override (entrances)")},
         macro=True, title_ru="Советский панельный дом (серии)")
def panel_building(p, ctx):
    s = dict(SERIES[p["series"]])
    if isinstance(p["floors"], dict) and "mix" in p["floors"]:
        return _part(_panel_sections(p, ctx, s))
    floors = int(ctx.pick(p["floors"]) or s["floors"])
    secs = int(p["sections"] or s["sections"])
    L, D, fh = s["sec_len"] * secs, s["d"], s["floor_h"]
    ww = s["win_w"]
    per_sec = max(2, int(s["sec_len"] / 3.0))
    us = [s["sec_len"] * k + s["sec_len"] * (i + 0.5) / per_sec for k in range(secs) for i in range(per_sec)]
    entr = [s["sec_len"] * (k + 0.5) for k in range(secs)]
    c = [E("body", "block", w=L, d=D, floors=floors, floor_h=fh, wall_t=0.35, plinth_h=0.9, material=s["mat"],
           plinth_material="concrete_raw"),
         E("win_f", "windows", "body:front", w=ww, h=s["win_h"], us=us, trim="soviet", frame_material="frame_white", mullions=[1, 0]),
         E("roof", "roof", "body:top", type="flat", overhang=0.0, parapet_h=0.5, material="bitumen", gable_material=s["mat"])]
    back_us = [u for u in us if min(abs(u - e) for e in entr) > 1.2]
    c.append(E("win_b", "windows", "body:back", w=ww, h=s["win_h"], us=back_us, trim="soviet", frame_material="frame_white", mullions=[1, 0]))
    # stairwell windows between floors above the entrances (back side)
    c.append(E("stair_win", "windows", "body:back", w=1.2, h=1.0, us=[L - e for e in entr],
               sill=0.9 + fh * 1.5, rows=floors - 1, trim="soviet", mullions=[1, 0]))
    for k, e in enumerate(entr):
        c.append(E(f"door{k}", "door", "body:back", [L - e, 0.9], w=1.4, h=2.2, double=True, steps=4, canopy="slab", trim="none"))
    if p["series"] in ("II-18",):
        c.append(E("win_l", "windows", "body:left", w=ww, h=s["win_h"], cols=4, trim="soviet"))
        c.append(E("win_r", "windows", "body:right", w=ww, h=s["win_h"], cols=4, trim="soviet"))
    else:
        c.append(E("win_l", "windows", "body:left", w=1.0, h=s["win_h"], cols=2, trim="soviet"))
        c.append(E("win_r", "windows", "body:right", w=1.0, h=s["win_h"], cols=2, trim="soviet"))
    bal_us = [us[i] for i in range(1, len(us), 3)]
    c.append(E("balc", "balconies", "body:front", kind=s["balcony"], w=2.6, us=bal_us, railing=s["rail"],
               slab_material="concrete_raw"))
    if s["panel"]:
        for f in ("front", "back", "left", "right"):
            c.append(E(f"seams_{f}", "panel_grid", f"body:{f}", panel_w=3.0))
    for k, e in enumerate(entr):
        c.append(E(f"roofexit{k}", "box", "roof:ridge", [e - L / 2, 0], w=2.5, d=3.0, h=2.0, material=s["mat"]))
    return _part(c)


def _panel_sections(p, ctx, s):
    """Mixed heights: every entrance section is its own block with a random floor count from {"mix":[a,b]}."""
    secs = int(p["sections"] or s["sections"])
    sl, D, fh, ww = s["sec_len"], s["d"], s["floor_h"], s["win_w"]
    per = max(2, int(sl / 3.0))
    c = []
    for k in range(secs):
        n = int(ctx.pick(p["floors"], k + 1))
        b = f"sec{k}"
        x = -sl * secs / 2 + sl * (k + 0.5)
        us = [0.05 + sl * (i + 0.5) / per for i in range(per)]
        c += [E(b, "block", None, [x, 0], w=sl + 0.1, d=D, floors=n, floor_h=fh, wall_t=0.35, plinth_h=0.9, material=s["mat"],
                plinth_material="concrete_raw"),
              E(f"{b}_wf", "windows", f"{b}:front", w=ww, h=s["win_h"], us=us, trim="soviet", frame_material="frame_white", mullions=[1, 0]),
              E(f"{b}_wb", "windows", f"{b}:back", w=ww, h=s["win_h"], us=[u for u in us if abs(u - sl / 2) > 1.2], trim="soviet",
                frame_material="frame_white", mullions=[1, 0]),
              E(f"{b}_stair", "windows", f"{b}:back", w=1.2, h=1.0, us=["50%"], sill=0.9 + fh * 1.5, rows=max(1, n - 1), trim="soviet"),
              E(f"{b}_door", "door", f"{b}:back", ["50%", 0.9], w=1.4, h=2.2, double=True, steps=4, canopy="slab", trim="none"),
              E(f"{b}_balc", "balconies", f"{b}:front", kind=s["balcony"], w=2.6, us=us[1::3] or us[:1], railing=s["rail"],
                slab_material="concrete_raw"),
              E(f"{b}_roof", "roof", f"{b}:top", type="flat", overhang=0.0, parapet_h=0.5, material="bitumen", gable_material=s["mat"]),
              E(f"{b}_exit", "box", f"{b}_roof:ridge", [0, 0], w=2.5, d=3.0, h=2.0, material=s["mat"])]
        if s["panel"]:
            c += [E(f"{b}_seams_{f}", "panel_grid", f"{b}:{f}", panel_w=3.0) for f in ("front", "back", "left", "right")]
        for f in (("left",) if k == 0 else ()) + (("right",) if k == secs - 1 else ()):
            c.append(E(f"{b}_w{f}", "windows", f"{b}:{f}", w=1.0, h=s["win_h"], cols=2, trim="soviet"))
    return c


@element("gothic_cathedral", "macros", "Gothic cathedral: nave with clerestory, lower aisles, transept, apse, flying buttresses, "
         "two west towers with spires, rose window, triple lancet portals.",
         {"length": P(60.0, "nave length (west-east, along X)"), "nave_w": P(12.0, ""), "nave_h": P(26.0, ""),
          "aisle_w": P(7.0, ""), "aisle_h": P(12.0, ""), "transept": P(True, ""), "towers": P(2, "0, 1 or 2 west towers"),
          "tower_h": P(42.0, ""), "spire_h": P(30.0, ""), "material": P("stone", "")},
         macro=True, title_ru="Готический собор")
def gothic_cathedral(p, ctx):
    L, nw, nh, aw, ah = p["length"], p["nave_w"], p["nave_h"], p["aisle_w"], p["aisle_h"]
    m = p["material"]
    bays = max(3, int(L / 6))
    c = [E("nave", "block", w=L, d=nw, floors=1, floor_h=nh, wall_t=1.2, plinth_h=0.5, material=m),
         E("nave_roof", "roof", "nave:top", type="gable", pitch=55, overhang=0.3, material="lead_roof"),
         E("clerestory_s", "windows", "nave:front", kind="lancet", w=2.4, h=7.0, cols=bays, margin=2, sill=ah + 2.5, rows=1,
           mullions=[1, 0], trim="gothic_hood", stained=True, subject="gothic stained glass with saints, deep blue and red"),
         E("clerestory_n", "windows", "nave:back", kind="lancet", w=2.4, h=7.0, cols=bays, margin=2, sill=ah + 2.5, rows=1,
           mullions=[1, 0], trim="gothic_hood", stained=True, subject="gothic stained glass with saints, deep blue and red")]
    for side, sgn in (("s", -1), ("n", 1)):
        aid = f"aisle_{side}"
        c.append(E(aid, "block", None, [0, sgn * (nw / 2 + aw / 2 - 0.6)], w=L, d=aw, floors=1, floor_h=ah, wall_t=1.0,
                   plinth_h=0.5, material=m))
        c.append(E(f"{aid}_roof", "roof", f"{aid}:top", type="shed", ridge="x", pitch=25, overhang=0.3, material="lead_roof",
                   _rot=0 if sgn < 0 else 180))
        face = "front" if sgn < 0 else "back"
        c.append(E(f"{aid}_win", "windows", f"{aid}:{face}", kind="lancet", w=2.0, h=6.0, cols=bays, margin=2, rows=1, sill=2.5,
                   mullions=[1, 0], trim="gothic_hood", stained=True, subject="gothic stained glass, biblical scenes"))
        c.append(E(f"{aid}_butt", "buttresses", f"{aid}:{face}", w=1.0, depth=1.6, h=ah * 0.95,
                   us=[2 + (L - 4) * i / bays for i in range(bays + 1)], flying=False, pinnacle=True))
        c.append(E(f"{aid}_fly", "buttresses", f"nave:{face}", w=0.8, depth=0.6, h=1.0, steps=1, pinnacle=False,
                   us=[2 + (L - 4) * i / bays for i in range(bays + 1)], flying=True, fly_dist=aw + 1.2,
                   fly_h=nh * 0.8, pier_h=ah + 4.0))
    if p["transept"]:
        tw = nw + 2 * aw + 8
        c.append(E("transept", "block", None, [L * 0.18, 0], w=nw, d=tw, floors=1, floor_h=nh, wall_t=1.2, plinth_h=0.5, material=m))
        c.append(E("transept_roof", "roof", "transept:top", type="gable", pitch=55, ridge="y", overhang=0.3, material="lead_roof"))
        c.append(E("rose_s", "window", "transept:front", ["50%", nh * 0.45], kind="rose", w=7, h=7, stained=True, trim="simple",
                   subject="gothic rose window stained glass, radial"))
        c.append(E("rose_n", "window", "transept:back", ["50%", nh * 0.45], kind="rose", w=7, h=7, stained=True, trim="simple",
                   subject="gothic rose window stained glass, radial"))
        c.append(E("portal_s", "door", "transept:front", ["50%", 0.5], kind="lancet", w=3, h=6, orders=3, trim="gothic_hood", double=True))
        c.append(E("crossing_spire", "spire", "transept:top", [0, 0], r=3.0, h=18, sides=8, finial="latin",
                   _offset=[0, 0, 0], material="lead_roof"))
    # apse at the east end
    c.append(E("apse", "tower", None, [L / 2 - 0.5, 0], shape="round", r=nw / 2, h=nh, wall_t=1.2, floors=1, material=m))
    c.append(E("apse_roof", "roof", "apse:top", type="cone", pitch=50, overhang=0.3, material="lead_roof"))
    c.append(E("apse_win", "windows", "apse:face7", kind="lancet", w=2.0, h=8, us=["50%"], vs=[6], stained=True))
    c.append(E("apse_win2", "windows", "apse:face0", kind="lancet", w=2.0, h=8, us=["50%"], vs=[6], stained=True))
    c.append(E("apse_win3", "windows", "apse:face6", kind="lancet", w=2.0, h=8, us=["50%"], vs=[6], stained=True))
    # west front
    c.append(E("rose_w", "window", "nave:left", ["50%", nh * 0.5], kind="rose", w=8, h=8, stained=True,
               subject="great west rose window, gothic stained glass, last judgement"))
    c.append(E("portal_w", "door", "nave:left", ["50%", 0.5], kind="lancet", w=3.5, h=7.5, orders=4, trim="gothic_hood", double=True,
               steps=3, step_h=0.17))
    nt = int(p["towers"])
    ts = 9.0
    for k, sgn in enumerate((-1, 1)[:nt] if nt == 2 else ((0,) if nt == 1 else ())):
        y = sgn * (nw / 2 + aw / 2 - 0.6) if nt == 2 else 0
        tid = f"tower{k}"
        c.append(E(tid, "tower", None, [-L / 2 - ts / 2 + 1.5, y], shape="square", r=ts / 2, h=p["tower_h"], floors=5, wall_t=1.4, material=m))
        c.append(E(f"{tid}_win", "windows", f"{tid}:face0", kind="lancet", w=2.0, h=6, us=["50%"], vs=[p["tower_h"] * 0.65],
                   glazed=False, mullions=[1, 0]))
        c.append(E(f"{tid}_win2", "windows", f"{tid}:face2", kind="lancet", w=2.0, h=6, us=["50%"], vs=[p["tower_h"] * 0.65],
                   glazed=False, mullions=[1, 0]))
        c.append(E(f"{tid}_cren", "battlements", f"{tid}:top", h=1.2, t=0.5, merlon_w=0.8))
        c.append(E(f"{tid}_spire", "spire", f"{tid}:top", r=ts / 2 * 0.85, h=p["spire_h"], sides=8, finial="latin", lucarnes=4))
        c.append(E(f"{tid}_portal", "door", f"{tid}:face1", ["50%", 0.5], kind="lancet", w=2.4, h=5, orders=2, trim="gothic_hood"))
    if nt == 0:
        c.append(E("west_gable_pinn", "pinnacle", "nave:top", [-L / 2, 0], w=0.8, h=4))
    return _part(c)


@element("orthodox_church", "macros", "Russian orthodox church: cubic main volume (четверик), apse, refectory (трапезная), "
         "bell tower with tent roof (шатровая колокольня), 1 or 5 onion domes on drums with kokoshniki.",
         {"size": P(12.0, "main cube side"), "h": P(12.0, "main volume height"), "domes": P(5, "1 or 5"),
          "bell_tower": P(True, ""), "refectory": P(True, ""), "material": P("wall", ""), "dome_material": P("dome", ""),
          "wooden": P(False, "log church (Kizhi-like materials)")},
         macro=True, title_ru="Православный храм")
def orthodox_church(p, ctx):
    s, h = p["size"], p["h"]
    wall = "log_pine" if p["wooden"] else p["material"]
    dm = "shingles_wood" if p["wooden"] else p["dome_material"]
    c = [E("main", "block", w=s, d=s, floors=1, floor_h=h, wall_t=1.0, plinth_h=0.8, material=wall),
         E("main_roof", "roof", "main:top", type="hip", pitch=20, overhang=0.3, material="metal_roof_green"),
         E("main_cor", "cornice", "main:top", kind="dentil", h=0.6, out=0.3),
         E("win_s", "windows", "main:front", kind="arch", w=1.2, h=2.4, cols=3, margin=2.5, trim="nalichnik", sill=2.5, rows=2, row_step=4.5),
         E("win_n", "windows", "main:back", kind="arch", w=1.2, h=2.4, cols=3, margin=2.5, trim="nalichnik", sill=2.5, rows=2, row_step=4.5),
         E("pil_s", "pilasters", "main:front", w=0.7, cols=4),
         E("pil_n", "pilasters", "main:back", w=0.7, cols=4),
         E("apse", "tower", None, [s / 2 - 0.5, 0], shape="round", r=s * 0.32, h=h * 0.7, floors=1, material=wall),
         E("apse_roof", "roof", "apse:top", type="dome", h=1.6, overhang=0.2, material="metal_roof_green"),
         E("apse_win", "windows", "apse:face7", kind="arch", w=1.0, h=2.0, us=["50%"], vs=[3.0], trim="nalichnik"),
         E("dome_c", "dome", "main_roof:ridge", None, profile="onion", r=s * 0.16, drum_h=s * 0.45, drum_windows=8, kokoshniki=8,
           cross="orthodox", material="gold" if p["domes"] == 1 else dm, drum_material=wall, neck_h=0.5, _offset=[0, 0, -1.0])]
    if int(p["domes"]) == 5:
        for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            c.append(E(f"dome{i}", "dome", "main:top", [dx * s * 0.3, dy * s * 0.3], profile="onion", r=s * 0.1, drum_h=s * 0.35,
                       drum_windows=6, cross="orthodox", material=dm, drum_material=wall, neck_h=0.3))
    if p["refectory"]:
        c.append(E("refectory", "block", None, [-s / 2 - s * 0.45 + 0.5, 0], w=s * 0.9, d=s * 0.8, floors=1, floor_h=h * 0.55,
                   plinth_h=0.8, material=wall))
        c.append(E("ref_roof", "roof", "refectory:top", type="hip", pitch=25, material="metal_roof_green"))
        c.append(E("ref_win", "windows", "refectory:front", kind="arch", w=1.1, h=2.0, cols=3, trim="nalichnik"))
        c.append(E("ref_win2", "windows", "refectory:back", kind="arch", w=1.1, h=2.0, cols=3, trim="nalichnik"))
    if p["bell_tower"]:
        bx = -s / 2 - (s * 0.9 if p["refectory"] else 0) - s * 0.2
        c.append(E("bell", "tower", None, [bx, 0], shape="square", r=s * 0.22, h=h * 1.6, floors=3, material=wall))
        c.append(E("bell_open", "windows", "bell:face0", kind="arch", w=1.6, h=3.0, us=["50%"], vs=[h * 1.6 - 4.0], glazed=False, frame=False))
        c.append(E("bell_open2", "windows", "bell:face2", kind="arch", w=1.6, h=3.0, us=["50%"], vs=[h * 1.6 - 4.0], glazed=False, frame=False))
        c.append(E("bell_open3", "windows", "bell:face1", kind="arch", w=1.6, h=3.0, us=["50%"], vs=[h * 1.6 - 4.0], glazed=False, frame=False))
        c.append(E("bell_open4", "windows", "bell:face3", kind="arch", w=1.6, h=3.0, us=["50%"], vs=[h * 1.6 - 4.0], glazed=False, frame=False))
        c.append(E("bell_tent", "spire", "bell:top", r=s * 0.24, h=h * 0.9, sides=8, material=dm, finial="none", lucarnes=4 if not p["wooden"] else 0))
        c.append(E("bell_dome", "dome", "bell_tent:top", None, profile="onion", r=s * 0.05, cross="orthodox", material="gold", _offset=[0, 0, -0.3]))
        c.append(E("door", "door", "bell:face1", ["50%", 0.8], kind="arch", w=1.6, h=2.8, steps=4, orders=2, trim="nalichnik"))
    else:
        c.append(E("door", "door", "main:left", ["50%", 0.8], kind="arch", w=1.8, h=3.0, steps=4, orders=2))
    return _part(c)


@element("greek_temple", "macros", "Greek/Roman peripteral temple: stepped stylobate, cella, colonnades on all sides, "
         "entablature, gable roof with pediments.",
         {"w": P(16.0, "front width (stylobate)"), "d": P(32.0, "depth"), "col_h": P(8.0, ""), "order": P("doric", ""),
          "front_cols": P(6, ""), "side_cols": P(13, ""), "material": P("marble", "")},
         macro=True, title_ru="Античный храм")
def greek_temple(p, ctx):
    W, D, ch = p["w"], p["d"], p["col_h"]
    m = p["material"]
    r = W / p["front_cols"] / 4.5
    steps, sh = 3, 0.4
    stH = steps * sh
    cw, cd = W - 4 * r * 2.6, D - 4 * r * 2.6
    eh = ch * 0.25
    c = [E("base", "platform", w=W + 1.4, d=D + 1.4, h=stH, steps=steps, step_out=0.5, material=m),
         E("cella", "block", "base:top", w=cw, d=cd, floors=1, floor_h=ch + eh, wall_t=0.8, plinth_h=0, material=m),
         E("door", "door", "cella:left", ["50%", 0], w=2.5, h=ch * 0.7, trim="classic"),
         E("roof", "roof", "cella:top", type="gable", ridge="x", pitch=14, overhang=(W - cw) / 2 + 0.3, t=0.3,
           material="clay_tile", gable_material=m, closed_eaves=True)]
    # four colonnades without pediments; columns stand at r*2.4 from the stylobate edge
    for name, face, n, span in (("cf", "left", p["front_cols"], cd), ("cb", "right", p["front_cols"], cd),
                                ("cs", "front", p["side_cols"], cw), ("cn", "back", p["side_cols"], cw)):
        dist = ((W - cw) / 2 if face in ("front", "back") else (D - cd) / 2) - r * 1.6
        full = (D if face in ("left", "right") else W) - r * 3.2 * 2 + 0.4
        margin = (span - (full - 0.4)) / 2 + 0.2
        c.append(E(name, "colonnade", f"cella:{face}", order=p["order"], count=n, h=ch, r=r, depth=dist, length=full - 0.4,
                   margin=margin, pediment=False, steps=0, ent_h=eh, material=m, trim_material=m))
    return _part(c)


@element("castle_keep", "macros", "Medieval stone keep (донжон) with corner turrets, battlements, machicolations, arrow slits, "
         "optional curtain wall with gate.",
         {"w": P(14.0, ""), "d": P(14.0, ""), "h": P(20.0, ""), "turrets": P(True, ""), "curtain": P(True, ""),
          "court": P(40.0, "curtain wall square size"), "material": P("stone_rubble", "")},
         macro=True, title_ru="Замок / донжон")
def castle_keep(p, ctx):
    w, d, h, m = p["w"], p["d"], p["h"], p["material"]
    c = [E("keep", "block", w=w, d=d, floors=4, floor_h=h / 4, wall_t=2.0, plinth_h=0, material=m),
         E("mach", "cornice", "keep:top", kind="machicolation", h=0.9, out=0.6, material=m),
         E("cren", "battlements", "keep:top", out=0.6, t=0.6, material=m),
         E("roof", "roof", "keep:top", type="pyramid", pitch=40, overhang=-1.0, material="slate"),
         E("slits_f", "windows", "keep:front", kind="slit", w=0.25, h=1.4, cols=3, sill=4, trim="none", glazed=False, frame=False),
         E("slits_b", "windows", "keep:back", kind="slit", w=0.25, h=1.4, cols=3, sill=4, trim="none", glazed=False, frame=False),
         E("win_top", "windows", "keep:left", kind="arch", w=1.0, h=1.8, cols=2, only_rows=[2, 3], trim="simple", mullions=[1, 0]),
         E("door", "door", "keep:front", ["50%", 3.0], kind="arch", w=1.6, h=2.8, steps=12, step_h=0.25, orders=1, trim="rustic")]
    if p["turrets"]:
        for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            c.append(E(f"turret{i}", "tower", None, [sx * w / 2, sy * d / 2], shape="round", r=2.0, h=h + 4, floors=5, material=m))
            c.append(E(f"turret{i}_roof", "roof", f"turret{i}:top", type="cone", pitch=62, overhang=0.3, material="slate"))
    if p["curtain"]:
        S = p["court"]
        for i in range(4):
            c.append(E(f"cw{i}", "wall", None, [S / 2 * [-1, 1, 1, -1][i], S / 2 * [-1, -1, 1, 1][i]], length=S, h=8, t=2.0,
                       battlements=True, walkway=True, material=m, _rot=[0, 90, 180, 270][i]))
            c.append(E(f"ct{i}", "tower", None, [S / 2 * [-1, 1, 1, -1][i], S / 2 * [-1, -1, 1, 1][i]], shape="round", r=3, h=11,
                       floors=3, material=m, batter=0.8))
            c.append(E(f"ct{i}_cren", "battlements", f"ct{i}:top", t=0.6, material=m))
        c.append(E("gate", "door", "cw0:front", ["50%", 0], kind="arch", w=3.5, h=4.5, open=True, orders=1, trim="rustic"))
    return _part(c)


@element("glass_tower", "macros", "Modern office tower: podium + glass curtain-wall shaft + roof crown/plant.",
         {"w": P(30.0, ""), "d": P(30.0, ""), "floors": P(30, ""), "floor_h": P(3.8, ""), "podium_floors": P(3, ""),
          "crown": P(True, "")},
         macro=True, title_ru="Стеклянный небоскрёб")
def glass_tower(p, ctx):
    w, d, n, fh = p["w"], p["d"], int(ctx.pick(p["floors"])), p["floor_h"]
    pf = int(p["podium_floors"])
    c = [E("podium", "block", w=w + 16, d=d + 12, floors=pf, floor_h=4.5, plinth_h=0, material="granite"),
         E("pod_glass", "curtain_wall", "podium:front", spacing=3.0, glass_material="glass"),
         E("pod_roof", "roof", "podium:top", type="flat", parapet_h=1.0, material="gravel", overhang=0),
         E("shaft", "block", "podium:top", w=w, d=d, floors=n - pf, floor_h=fh, plinth_h=0, material="concrete_raw", _offset=[0, 0, -0.02]),
         E("door", "door", "podium:front", ["50%", 0], w=4, h=3.5, glazed=True, double=True, canopy="slab", trim="none")]
    for f in ("front", "back", "left", "right"):
        c.append(E(f"cw_{f}", "curtain_wall", f"shaft:{f}", spacing=1.5))
    c.append(E("roof", "roof", "shaft:top", type="flat", parapet_h=1.2, material="bitumen", gable_material="aluminium"))
    if p["crown"]:
        c.append(E("plant", "box", "roof:ridge", [0, 0], w=w * 0.5, d=d * 0.5, h=5, material="aluminium"))
    return _part(c)


@element("lithuanian_church", "macros", "Lithuanian wooden church (medinė bažnyčia): board-clad nave, steep gable roof, "
         "front bell tower with baroque helmet, small apse.",
         {"w": P(10.0, ""), "d": P(20.0, ""), "h": P(7.0, ""), "material": P("wood_boards", ""), "roof_material": P("shingles_wood", "")},
         macro=True, title_ru="Литовский деревянный костёл")
def lithuanian_church(p, ctx):
    w, d, h, m, rm = p["w"], p["d"], p["h"], p["material"], p["roof_material"]
    return _part([
        E("nave", "block", w=d, d=w, floors=1, floor_h=h, wall_t=0.3, plinth_h=0.6, material=m, plinth_material="stone_rubble"),
        E("roof", "roof", "nave:top", type="gable", pitch=55, overhang=0.6, material=rm, gable_material=m),
        E("win_s", "windows", "nave:front", kind="segmental", w=1.2, h=2.4, cols=4, trim="nalichnik", frame_material="frame_white",
          trim_material="wood_painted_white", sill=2.0),
        E("win_n", "windows", "nave:back", kind="segmental", w=1.2, h=2.4, cols=4, trim="nalichnik", frame_material="frame_white",
          trim_material="wood_painted_white", sill=2.0),
        E("apse", "block", None, [d / 2 + 2.0, 0], w=4.5, d=w * 0.6, floors=1, floor_h=h * 0.85, wall_t=0.3, plinth_h=0.6, material=m,
          poly=[[-2.5, -w * 0.3], [0.8, -w * 0.3], [2.2, -w * 0.15], [2.2, w * 0.15], [0.8, w * 0.3], [-2.5, w * 0.3]]),
        E("apse_roof", "roof", "apse:top", type="hip", pitch=50, overhang=0.5, material=rm),
        E("tower", "tower", None, [-d / 2 - 2.0, 0], shape="square", r=2.5, h=h + 7, floors=3, wall_t=0.3, material=m),
        E("tower_open", "windows", "tower:face0", kind="arch", w=1.0, h=1.6, us=["50%"], vs=[h + 4], glazed=False),
        E("tower_open2", "windows", "tower:face2", kind="arch", w=1.0, h=1.6, us=["50%"], vs=[h + 4], glazed=False),
        E("helmet", "dome", "tower:top", None, profile="bell", r=2.4, h=3.2, lantern=True, cross="latin", material=rm),
        E("door", "door", "tower:face1", ["50%", 0.6], kind="segmental", w=1.6, h=2.6, double=True, steps=3, trim="nalichnik",
          trim_material="wood_painted_white"),
        E("fence", "fence", None, None, points=[[-d / 2 - 8, -w / 2 - 5], [d / 2 + 8, -w / 2 - 5], [d / 2 + 8, w / 2 + 5],
                                                 [-d / 2 - 8, w / 2 + 5]], closed=True, kind="picket", h=1.2),
    ])


@element("palazzo", "macros", "Renaissance palazzo: rusticated ground floor, piano nobile with pedimented windows, heavy crowning "
         "cornice, arched portal, optional inner courtyard.",
         {"w": P(36.0, ""), "d": P(30.0, ""), "floors": P(3, ""), "floor_h": P(5.0, ""), "courtyard": P(True, "")},
         macro=True, title_ru="Ренессансное палаццо")
def palazzo(p, ctx):
    w, d, n, fh = p["w"], p["d"], int(ctx.pick(p["floors"])), p["floor_h"]
    c = [E("body", "block", w=w, d=d, floors=n, floor_h=fh, wall_t=0.9, plinth_h=0.8, material="plaster_ochre", plinth_material="rustication"),
         E("rust", "block", w=w + 0.12, d=d + 0.12, floors=1, floor_h=fh, plinth_h=0.8, material="rustication", hollow=False, _offset=[0, 0, 0]),
         E("win_g", "windows", "rust:front", kind="arch", w=1.2, h=2.0, sill=2.8, rows=1, trim="rustic", skip=[[_mid_col(w, 2.0, 1.6), 0]], margin=2.0, _cut=["body"]),
         E("win_1", "windows", "body:front", kind="rect", w=1.6, h=2.8, only_rows=[1], margin=2.0, trim="pediment"),
         E("win_2", "windows", "body:front", kind="arch", w=1.4, h=2.4, only_rows=[2], margin=2.0, trim="classic"),
         E("win_b", "windows", "body:back", kind="rect", w=1.4, h=2.4, only_rows=[1, 2], margin=2.0, trim="simple"),
         E("win_l", "windows", "body:left", kind="rect", w=1.4, h=2.4, only_rows=[1, 2], margin=2.0, trim="simple"),
         E("win_r", "windows", "body:right", kind="rect", w=1.4, h=2.4, only_rows=[1, 2], margin=2.0, trim="simple"),
         E("band1", "cornice", "body:floor1", kind="band", h=0.3, out=0.15),
         E("cornice", "cornice", "body:top", kind="dentil", h=1.4, out=1.2),
         E("portal", "door", "rust:front", ["50%", 0], kind="arch", w=3.0, h=4.6, trim="rustic", double=True, _cut=["body"]),
         E("roof", "roof", "body:top", type="hip", pitch=22, overhang=1.0, material="clay_tile")]
    if p["courtyard"]:
        c.append(E("court", "box", None, [0, 0, 0.8], w=w * 0.45, d=d * 0.4, h=n * fh + 20, _subtract=True,
                   _cut=["body", "rust", "roof"]))
    return _part(c)


def _mid_col(w, margin=1.0, wi=1.2):
    gap = max(wi * 0.9, 0.6)
    return max(1, int((w - 2 * margin + gap) // (wi + gap))) // 2


@element("stalinka", "macros", "Stalinist empire residential building (сталинка): granite base, rusticated lower floors, "
         "symmetrical facade with central risalit, columns, balconies with balusters, heavy cornice, optional spire tower.",
         {"w": P(60.0, ""), "d": P(16.0, ""), "floors": P(7, ""), "floor_h": P(3.4, ""), "tower": P(False, "central spire tower (высотка)")},
         macro=True, title_ru="Сталинка / сталинский ампир")
def stalinka(p, ctx):
    w, d, n, fh = p["w"], p["d"], int(ctx.pick(p["floors"])), p["floor_h"]
    rw = w * 0.22
    c = [E("body", "block", w=w, d=d, floors=n, floor_h=fh, plinth_h=1.2, material="plaster_ochre", plinth_material="granite"),
         E("risalit", "block", None, [0, -0.6], w=rw, d=d + 1.2, floors=n + 1, floor_h=fh, plinth_h=1.2, material="plaster_ochre",
           plinth_material="granite"),
         E("rust", "block", None, [0, 0], w=w + 0.1, d=d + 0.1, floors=2, floor_h=fh, plinth_h=1.2, material="rustication", hollow=False),
         E("win", "windows", "body:front", w=1.5, h=2.0, trim="classic", only_rows=list(range(2, n)), margin=2.0),
         E("win_low", "windows", "rust:front", w=1.5, h=2.0, trim="rustic", rows=2, margin=2.0, skip=[[i, 0] for i in range(10, 14)], _cut=["body"]),
         E("win_back", "windows", "body:back", w=1.4, h=1.9, trim="simple", margin=2.0),
         E("rwin", "windows", "risalit:front", kind="arch", w=1.6, h=2.4, cols=3, margin=1.5, trim="pediment", only_rows=list(range(2, n + 1))),
         E("cols", "colonnade", "risalit:front", None, order="corinthian", count=4, h=fh * 2, r=0.45, depth=0.9, margin=1.6,
           length=rw - 3.2, pediment=False, steps=0, _offset=[0, 0, 1.2 + fh * (n - 2)]),
         E("balc", "balconies", "body:front", w=2.0, d=0.9, railing="balusters", only_rows=[2, 4], rows=n - 1, margin=4.0, cols=6),
         E("cornice", "cornice", "body:top", kind="dentil", h=1.2, out=0.9),
         E("rcornice", "cornice", "risalit:top", kind="dentil", h=1.2, out=0.9),
         E("bal_top", "balustrade", "risalit:top", h=1.0),
         E("roof", "roof", "body:top", type="hip", pitch=20, overhang=0.5, material="metal_roof_red"),
         E("rroof", "roof", "risalit:top", type="flat", parapet_h=0, overhang=0.0, material="metal_roof_red"),
         E("portal", "door", "risalit:front", ["50%", 1.2], kind="arch", w=2.6, h=4.0, double=True, steps=6, trim="rustic")]
    if p["tower"]:
        c.append(E("tower", "tower", "risalit:top", [0, 0], shape="square", r=rw * 0.3, h=fh * 5, floors=5, material="plaster_ochre",
                   _offset=[0, 0, -0.05]))
        c.append(E("tower_win", "windows", "tower:face0", kind="arch", w=1.2, h=2.2, us=["50%"], trim="classic", sill=1.0))
        c.append(E("spire", "spire", "tower:top", r=rw * 0.22, h=fh * 5, sides=8, needle=True, material="gold"))
    return _part(c)


@element("romanesque_church", "macros", "Romanesque church/basilica: thick walls, small round-arched windows, lombard bands, "
         "semicircular apse, square crossing/bell tower with pyramid roof.",
         {"length": P(30.0, ""), "w": P(12.0, ""), "h": P(12.0, ""), "material": P("sandstone", "")},
         macro=True, title_ru="Романская церковь")
def romanesque_church(p, ctx):
    L, w, h, m = p["length"], p["w"], p["h"], p["material"]
    return _part([
        E("nave", "block", w=L, d=w, floors=1, floor_h=h, wall_t=1.6, plinth_h=0.4, material=m),
        E("roof", "roof", "nave:top", type="gable", pitch=30, overhang=0.3, material="clay_tile"),
        E("lombard", "cornice", "nave:top", kind="lombard", h=0.5, out=0.25, spacing=1.0, material=m),
        E("win_s", "windows", "nave:front", kind="arch", w=0.9, h=2.0, cols=5, sill=h * 0.55, rows=1, trim="archivolt", mullions=[0, 0]),
        E("win_n", "windows", "nave:back", kind="arch", w=0.9, h=2.0, cols=5, sill=h * 0.55, rows=1, trim="archivolt", mullions=[0, 0]),
        E("pil_s", "pilasters", "nave:front", w=0.9, depth=0.25, cols=6, capital=False),
        E("pil_n", "pilasters", "nave:back", w=0.9, depth=0.25, cols=6, capital=False),
        E("apse", "tower", None, [L / 2 - 0.5, 0], shape="round", r=w / 2 - 1, h=h * 0.8, floors=1, material=m),
        E("apse_roof", "roof", "apse:top", type="cone", pitch=30, overhang=0.3, material="clay_tile"),
        E("apse_win", "windows", "apse:face7", kind="arch", w=0.8, h=1.8, us=["50%"], vs=[h * 0.4], trim="archivolt", mullions=[0, 0]),
        E("portal", "door", "nave:left", ["50%", 0.4], kind="arch", w=2.2, h=3.6, orders=3, trim="archivolt", double=True, steps=2),
        E("oculus", "window", "nave:left", ["50%", h * 0.62], kind="round", w=2.2, h=2.2, mullions=[0, 0]),
        E("tower", "tower", None, [-L / 2 + 4, 0], shape="square", r=3.5, h=h * 2.2, floors=4, wall_t=1.5, material=m),
        E("tower_bif", "windows", "tower:face0", kind="arch", w=1.0, h=1.8, us=["35%", "65%"], vs=[h * 1.7], glazed=False, mullions=[0, 0]),
        E("tower_bif2", "windows", "tower:face2", kind="arch", w=1.0, h=1.8, us=["35%", "65%"], vs=[h * 1.7], glazed=False, mullions=[0, 0]),
        E("tower_roof", "roof", "tower:top", type="pyramid", pitch=35, overhang=0.3, material="clay_tile"),
    ])


@element("baroque_church", "macros", "Baroque church: plastered facade with pilasters, volutes-like pediment, two towers with bell "
         "helmets and lanterns, central dome on a drum with lantern.",
         {"length": P(34.0, ""), "w": P(18.0, ""), "h": P(16.0, ""), "material": P("plaster_pink", ""), "towers": P(True, "")},
         macro=True, title_ru="Барочный костёл / церковь")
def baroque_church(p, ctx):
    L, w, h, m = p["length"], p["w"], p["h"], p["material"]
    c = [E("nave", "block", w=L, d=w, floors=1, floor_h=h, wall_t=1.2, plinth_h=0.8, material=m),
         E("roof", "roof", "nave:top", type="gable", pitch=40, overhang=0.4, material="copper_green"),
         E("cor", "cornice", "nave:top", kind="crown", h=1.0, out=0.6),
         E("win_s", "windows", "nave:front", kind="segmental", w=2.0, h=4.0, cols=4, sill=4.0, rows=1, trim="baroque", margin=3),
         E("win_n", "windows", "nave:back", kind="segmental", w=2.0, h=4.0, cols=4, sill=4.0, rows=1, trim="baroque", margin=3),
         E("pil_s", "pilasters", "nave:front", w=0.9, cols=5, material="plaster_white"),
         E("pil_n", "pilasters", "nave:back", w=0.9, cols=5, material="plaster_white"),
         E("drum", "dome", "nave:top", [L * 0.2, 0], profile="dome", r=w * 0.32, drum_h=5, drum_windows=8, lantern=True,
           cross="latin", material="copper_green", drum_material=m, ribs=8, _offset=[0, 0, -0.2]),
         E("portal", "door", "nave:left", ["50%", 0.8], kind="arch", w=3.0, h=5.0, double=True, steps=5, trim="baroque"),
         E("ped", "pediment", "nave:left", ["50%", h - 0.1], w=w * 0.55, h=2.6, kind="segmental"),
         E("fwin", "window", "nave:left", ["50%", h * 0.55], kind="round", w=2.4, h=2.4, trim="baroque")]
    if p["towers"]:
        for k, sgn in enumerate((-1, 1)):
            t = f"tower{k}"
            c.append(E(t, "tower", None, [-L / 2 + 2.5, sgn * (w / 2 - 2.5)], shape="square", r=3.0, h=h + 12, floors=4, material=m))
            c.append(E(f"{t}_cor", "cornice", f"{t}:top", kind="crown", h=0.8, out=0.5))
            c.append(E(f"{t}_open", "windows", f"{t}:face1", kind="arch", w=1.6, h=3.0, us=["50%"], vs=[h + 6], glazed=False, trim="classic"))
            c.append(E(f"{t}_clock", "panel", f"{t}:face1", ["50%", h + 2.0], kind="clock", shape="round", w=2.0, h=2.0, subject="baroque tower clock face"))
            c.append(E(f"{t}_helm", "dome", f"{t}:top", None, profile="bell", r=3.0, h=4.0, lantern=True, cross="latin", material="copper_green"))
    return _part(c)


@element("constructivist", "macros", "Soviet constructivism (1920-30s): intersecting rectilinear volumes, ribbon windows, "
         "glazed cylindrical stair tower, flat roofs, cantilevered balconies.",
         {"w": P(40.0, ""), "d": P(14.0, ""), "floors": P(4, "")},
         macro=True, title_ru="Конструктивизм")
def constructivist(p, ctx):
    w, d, n = p["w"], p["d"], int(ctx.pick(p["floors"]))
    fh = 3.4
    return _part([
        E("a", "block", w=w, d=d, floors=n, floor_h=fh, plinth_h=0.3, material="plaster_grey"),
        E("b", "block", None, [w / 2 - 6, d / 2 + 5], w=12, d=12, floors=n + 2, floor_h=fh, plinth_h=0.3, material="plaster_white"),
        E("ribbon", "windows", "a:front", kind="ribbon", w=w - 4, h=1.4, cols=1, margin=2, trim="none", mullions=[12, 0], frame_material="steel"),
        E("ribbon_b", "windows", "a:back", kind="ribbon", w=w - 16, h=1.4, us=[(w - 16) / 2 + 1.5], margin=2, trim="none", mullions=[10, 0], frame_material="steel"),
        E("ribbon_c", "windows", "b:left", kind="ribbon", w=9, h=1.4, cols=1, margin=1.5, trim="none", mullions=[4, 0], frame_material="steel"),
        E("stair", "tower", None, [-w / 2 + 6, -d / 2 - 1.5], shape="round", r=3.2, h=(n + 1) * fh, floors=n + 1, wall_t=0.3, material="glass"),
        E("stair_roof", "roof", "stair:top", type="flat", parapet_h=0.4, material="bitumen"),
        E("roof_a", "roof", "a:top", type="flat", parapet_h=1.0, material="bitumen", gable_material="plaster_grey"),
        E("roof_b", "roof", "b:top", type="flat", parapet_h=1.0, material="bitumen", gable_material="plaster_white"),
        E("balc", "balconies", "b:front", kind="balcony", w=10, d=1.5, us=["50%"], railing="solid", slab_material="plaster_white"),
        E("door", "door", "a:front", [w * 0.7, 0.3], w=3.0, h=2.6, glazed=True, double=True, canopy="slab", trim="none"),
    ])


@element("roman_pantheon", "macros", "Roman rotunda (Pantheon type): cylindrical drum with saucer dome and oculus, "
         "rectangular portico with Corinthian columns and pediment.",
         {"r": P(22.0, "rotunda radius"), "h": P(21.0, "drum height"), "material": P("stone_ashlar", "")},
         macro=True, title_ru="Римская ротонда (Пантеон)")
def roman_pantheon(p, ctx):
    r, h, m = p["r"], p["h"], p["material"]
    return _part([
        E("drum", "tower", None, None, shape="round", r=r, h=h, wall_t=6.0, floors=1, material=m, faces=16),
        E("dome", "dome", "drum:top", None, profile="saucer", r=r, h=r * 1.0, material="lead_roof", cross="none", _offset=[0, 0, -0.2]),
        E("porch", "block", None, [-r - 7, 0], w=16, d=34, floors=1, floor_h=h * 0.8, plinth_h=1.2, material=m),
        E("porch_cols", "colonnade", "porch:left", order="corinthian", count=8, h=h * 0.6, r=0.75, depth=6.0, margin=2.0,
          length=30.0, pediment=True, steps=3, step_h=0.4, material="granite"),
        E("porch_roof", "roof", "porch:top", type="gable", ridge="x", pitch=22, material="lead_roof"),
        E("door", "door", "porch:left", ["50%", 1.2], w=6, h=10, double=True, trim="classic"),
        E("cor", "cornice", "drum:top", kind="dentil", h=1.2, out=0.8),
    ])
