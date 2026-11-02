"""Props: decorations and small objects - street furniture, garden and roof equipment, facade details.
A prop stands on the ground (no `on`), on a `top` anchor (roofs, platforms) or on a face (wall-mounted kinds).
Origin = bottom centre (wall kinds: on the wall surface, Y = outward). Every prop is one closed solid that
touches what it stands on, so nothing floats."""
from __future__ import annotations

import math

from .. import geo as g
from ..registry import P, Part, element

WALL_KINDS = ["flower_box", "ac_unit", "wall_lamp", "sign", "mailbox", "awning", "satellite_dish", "drainpipe", "clock"]
GROUND_KINDS = ["bench", "street_lamp", "planter", "trash_bin", "bollard", "hydrant", "bike_rack", "barrel", "crate",
                "tree", "bush", "fountain", "table_umbrella", "flag", "bus_stop", "statue", "well", "lantern_post"]
ROOF_KINDS = ["antenna", "satellite_dish", "water_tank", "solar_panel", "vent", "rooftop_unit", "chimney_pot"]
KINDS = sorted(set(WALL_KINDS + GROUND_KINDS + ROOF_KINDS))
KIND_RU = {
    "bench": "скамейка", "street_lamp": "фонарь", "planter": "кадка с растением", "trash_bin": "урна", "bollard": "столбик",
    "hydrant": "гидрант", "bike_rack": "велопарковка", "barrel": "бочка", "crate": "ящик", "tree": "дерево",
    "bush": "куст", "fountain": "фонтан", "table_umbrella": "столик с зонтом", "flag": "флагшток", "bus_stop": "остановка",
    "statue": "статуя", "well": "колодец", "lantern_post": "садовый фонарь", "flower_box": "ящик с цветами",
    "ac_unit": "кондиционер", "wall_lamp": "настенный фонарь", "sign": "вывеска", "mailbox": "почтовый ящик",
    "awning": "маркиза", "satellite_dish": "спутниковая тарелка", "drainpipe": "водосток", "clock": "часы",
    "antenna": "антенна", "water_tank": "водяной бак", "solar_panel": "солнечная панель", "vent": "вентиляция",
    "rooftop_unit": "кондиционер на крыше", "chimney_pot": "дымник",
}


@element("prop", "props", "Decoration / small object: " + ", ".join(KINDS) + ". Ground kinds stand free (no `on`) or on a "
         "`top`; wall kinds go on a face at [u, v]. `scale` resizes it.",
         {"kind": P("bench", "", KINDS), "scale": P(1.0, ""), "material": P(None, "main material (default per kind)"),
          "accent": P(None, "second material (default per kind)")},
         attach="any", title_ru="Украшение / мелкий объект")
def prop(p, ctx):
    k, s = p["kind"], float(p["scale"])
    seg = 10 if ctx.low else 18
    m = ctx.mat(p["material"] or DEFAULT_MAT.get(k, "steel"))
    a = ctx.mat(p["accent"] or DEFAULT_ACC.get(k, "wood_boards"))
    part = Part()
    for solid, which in BUILD[k](seg):
        part.add(solid.scale([s, s, s]), m if which == 0 else a)
    return part


DEFAULT_MAT = {"bench": "iron", "street_lamp": "iron", "planter": "concrete_raw", "trash_bin": "iron", "bollard": "iron",
               "hydrant": "red_paint", "bike_rack": "steel", "barrel": "wood_dark", "crate": "wood_boards", "tree": "wood_dark",
               "bush": "turf", "fountain": "stone_ashlar", "table_umbrella": "aluminium", "flag": "aluminium", "bus_stop": "aluminium",
               "statue": "stone_ashlar", "well": "stone_rubble", "lantern_post": "iron", "flower_box": "wood_painted_white",
               "ac_unit": "aluminium", "wall_lamp": "iron", "sign": "iron", "mailbox": "iron", "awning": "iron",
               "satellite_dish": "aluminium", "drainpipe": "zinc", "clock": "iron", "antenna": "steel", "water_tank": "wood_dark",
               "solar_panel": "aluminium", "vent": "zinc", "rooftop_unit": "aluminium", "chimney_pot": "terracotta"}
DEFAULT_ACC = {"bench": "wood_boards", "street_lamp": "glass", "planter": "turf", "trash_bin": "iron", "hydrant": "iron",
               "barrel": "iron", "crate": "wood_dark", "tree": "turf", "fountain": "glass", "table_umbrella": "red_paint",
               "flag": "red_paint", "bus_stop": "glass", "well": "wood_dark", "lantern_post": "glass", "flower_box": "turf",
               "ac_unit": "steel", "wall_lamp": "glass", "sign": "red_paint", "mailbox": "red_paint", "awning": "red_paint",
               "clock": "plaster_white", "water_tank": "iron", "solar_panel": "glass_dark", "rooftop_unit": "steel",
               "satellite_dish": "steel"}


def _post(r, h, seg, x=0.0, y=0.0):
    return g.cyl(r, h, seg, 0.0, None, x, y)


BUILD = {
    "bench": lambda seg: [(g.box(-0.85, -0.25, 0, -0.75, 0.2, 0.45), 0), (g.box(0.75, -0.25, 0, 0.85, 0.2, 0.45), 0),
                          (g.box(-0.95, -0.25, 0.42, 0.95, 0.2, 0.48), 1), (g.box(-0.95, 0.15, 0.45, 0.95, 0.22, 0.9), 1)],
    "street_lamp": lambda seg: [(_post(0.07, 4.2, seg), 0), (g.cyl(0.18, 0.12, seg, -0.02, 0.12), 0),
                                (g.box(-0.08, -0.04, 4.1, 0.9, 0.04, 4.2), 0), (g.cyl(0.18, 0.35, seg, 3.8, 0.1, 0.85, 0), 1)],
    "planter": lambda seg: [(g.cyl(0.45, 0.6, seg, 0, 0.38), 0), (g.sphere(0.45, seg, (0, 0, 0.85)), 1)],
    "trash_bin": lambda seg: [(g.cyl(0.25, 0.85, seg), 0), (g.cyl(0.27, 0.05, seg, 0.83), 1)],
    "bollard": lambda seg: [(_post(0.1, 0.9, seg), 0), (g.sphere(0.1, seg, (0, 0, 0.9)), 0)],
    "hydrant": lambda seg: [(_post(0.13, 0.7, seg), 0), (g.sphere(0.14, seg, (0, 0, 0.7)), 0),
                            (g.rod([-0.22, 0, 0.45], [0.22, 0, 0.45], 0.05, seg), 1)],
    "bike_rack": lambda seg: [(g.rod([x, 0, 0], [x, 0, 0.8], 0.025, 8) + g.rod([x, 0, 0.8], [x, 0.6, 0.8], 0.025, 8)
                               + g.rod([x, 0.6, 0.8], [x, 0.6, 0], 0.025, 8), 0) for x in (-0.6, -0.2, 0.2, 0.6)],
    "barrel": lambda seg: [(g.cyl(0.3, 0.45, seg, 0, 0.34) + g.cyl(0.34, 0.45, seg, 0.45, 0.3), 0),
                           (g.cyl(0.345, 0.05, seg, 0.43), 1)],
    "crate": lambda seg: [(g.box(-0.4, -0.4, 0, 0.4, 0.4, 0.8), 0),
                          (g.box(-0.42, -0.42, 0.05, 0.42, 0.42, 0.15) + g.box(-0.42, -0.42, 0.65, 0.42, 0.42, 0.75), 1)],
    "tree": lambda seg: [(g.cyl(0.18, 2.6, seg, 0, 0.12), 0),
                         (g.sphere(1.5, seg, (0, 0, 3.4)) + g.sphere(1.1, seg, (0.6, 0.3, 4.3)) + g.sphere(1.0, seg, (-0.5, -0.4, 4.1)), 1)],
    "bush": lambda seg: [(g.sphere(0.6, seg, (0, 0, 0.45)) + g.sphere(0.45, seg, (0.45, 0.1, 0.4)), 0)],
    "fountain": lambda seg: [(g.cyl(1.8, 0.5, seg * 2) - g.cyl(1.55, 0.6, seg * 2, 0.15), 0), (g.cyl(1.56, 0.36, seg * 2, 0.1), 1),
                             (_post(0.18, 1.6, seg) + g.cyl(0.6, 0.15, seg, 1.5, 0.4), 0)],
    "table_umbrella": lambda seg: [(g.cyl(0.5, 0.05, seg, 0.72), 0), (_post(0.03, 2.3, 8), 0),
                                   (g.cyl(0.04, 0.72, 8) + g.cyl(0.3, 0.04, seg), 0), (g.cyl(1.3, 0.5, seg, 1.9, 0.05), 1)],
    "flag": lambda seg: [(_post(0.05, 7.0, seg) + g.cyl(0.25, 0.3, seg), 0), (g.box(0.03, -0.01, 5.6, 1.9, 0.01, 6.8), 1)],
    "bus_stop": lambda seg: [(g.box(-2, 0.6, 0, -1.9, 0.7, 2.5) + g.box(1.9, 0.6, 0, 2, 0.7, 2.5)
                              + g.box(-2.1, -0.6, 2.5, 2.1, 0.8, 2.6) + g.box(-1.95, 0.3, 0.42, 1.95, 0.65, 0.48), 0),
                             (g.box(-1.9, 0.62, 0.3, 1.9, 0.66, 2.4), 1)],
    "statue": lambda seg: [(g.box(-0.6, -0.6, 0, 0.6, 0.6, 1.2) + g.cyl(0.3, 1.0, seg, 1.2, 0.25)
                            + g.sphere(0.25, seg, (0, 0, 2.38)), 0)],
    "well": lambda seg: [(g.cyl(0.9, 0.9, seg * 2) - g.cyl(0.7, 1.0, seg * 2, 0.2), 0),
                         (g.box(-0.85, -0.06, 0.8, -0.75, 0.06, 2.3) + g.box(0.75, -0.06, 0.8, 0.85, 0.06, 2.3)
                          + g.hull([[-1.1, -0.7, 2.2], [1.1, -0.7, 2.2], [-1.1, 0.7, 2.2], [1.1, 0.7, 2.2],
                                    [-1.1, 0, 2.8], [1.1, 0, 2.8]]), 1)],
    "lantern_post": lambda seg: [(_post(0.04, 1.0, 8), 0), (g.cyl(0.12, 0.25, seg, 1.0, 0.1), 1)],
    # wall kinds: origin on the wall surface, +Y outward, 2 cm into the wall
    "flower_box": lambda seg: [(g.box(-0.6, -0.02, 0, 0.6, 0.25, 0.22), 0), (g.box(-0.55, 0.02, 0.2, 0.55, 0.22, 0.4), 1)],
    "ac_unit": lambda seg: [(g.box(-0.45, -0.02, 0, 0.45, 0.35, 0.6), 0), (g.cyl(0.2, 0.02, seg, 0.0, None, 0, 0.36).translate([0, 0, 0.1]), 1)],
    "wall_lamp": lambda seg: [(g.box(-0.08, -0.02, 0, 0.08, 0.3, 0.06), 0), (g.cyl(0.12, 0.36, seg, -0.3, 0.08, 0, 0.2), 1)],
    "sign": lambda seg: [(g.box(-0.03, -0.02, 0.5, 0.03, 0.7, 0.56), 0), (g.box(-0.02, 0.25, -0.2, 0.02, 0.85, 0.53), 1)],
    "mailbox": lambda seg: [(g.box(-0.2, -0.02, 0, 0.2, 0.22, 0.4), 1), (g.box(-0.15, 0.22, 0.28, 0.15, 0.23, 0.31), 0)],
    "awning": lambda seg: [(g.box(-1.4, -0.02, 0, 1.4, 0.06, 0.08), 0),
                           (g.hull([[-1.4, 0, 0], [1.4, 0, 0], [-1.4, 1.2, -0.5], [1.4, 1.2, -0.5],
                                    [-1.4, 0, 0.04], [1.4, 0, 0.04], [-1.4, 1.2, -0.46], [1.4, 1.2, -0.46]]), 1)],
    "drainpipe": lambda seg: [(g.rod([0, 0.08, -8.0], [0, 0.08, 0.0], 0.05, 10) + g.box(-0.03, -0.02, -4.0, 0.03, 0.08, -3.95), 0)],
    "clock": lambda seg: [(g.rod([0, -0.02, 0.5], [0, 0.1, 0.5], 0.5, seg * 2), 0), (g.rod([0, 0.09, 0.5], [0, 0.12, 0.5], 0.44, seg * 2), 1)],
    # roof kinds
    "antenna": lambda seg: [(_post(0.03, 3.0, 8) + g.box(-0.6, -0.02, 2.2, 0.6, 0.02, 2.24) + g.box(-0.4, -0.02, 2.6, 0.4, 0.02, 2.64), 0)],
    "satellite_dish": lambda seg: [(g.rod([0, 0, 0], [0, 0.3, 0.8], 0.04, 8), 1),
                                   (g.revolve([[0, 0], [0.45, 0.12], [0.45, 0.15], [0, 0.04]], seg).translate([0, 0, -0.05])
                                    .rotate([60, 0, 0]).translate([0, 0.3, 0.85]), 0)],
    "water_tank": lambda seg: [(g.box(-1.2, -1.2, 0, 1.2, 1.2, 0.15) + sum((_post(0.08, 2.0, 8, x, y) for x in (-0.7, 0.7) for y in (-0.7, 0.7)),
                                                                          start=g.box(0, 0, 0, 0.01, 0.01, 0.01)), 1),
                               (g.cyl(1.1, 2.0, seg * 2, 1.95) + g.cyl(1.15, 0.7, seg * 2, 3.9, 0.05), 0)],
    "solar_panel": lambda seg: [(g.box(-0.05, -0.05, 0, 0.05, 0.05, 0.5) + g.box(-0.05, 0.85, 0, 0.05, 0.95, 1.1), 0),
                                (g.hull([[-0.85, -0.1, 0.45], [0.85, -0.1, 0.45], [-0.85, 1.0, 1.1], [0.85, 1.0, 1.1],
                                         [-0.85, -0.1, 0.5], [0.85, -0.1, 0.5], [-0.85, 1.0, 1.15], [0.85, 1.0, 1.15]]), 1)],
    "vent": lambda seg: [(g.cyl(0.18, 0.7, seg) + g.cyl(0.3, 0.15, seg, 0.7, 0.05), 0)],
    "rooftop_unit": lambda seg: [(g.box(-1.2, -0.8, 0, 1.2, 0.8, 1.2), 0), (g.cyl(0.45, 0.1, seg, 1.2, None, -0.5, 0)
                                                                              + g.cyl(0.45, 0.1, seg, 1.2, None, 0.5, 0), 1)],
    "chimney_pot": lambda seg: [(g.cyl(0.15, 0.5, seg, 0, 0.12), 0)],
}
for _k in KINDS:
    assert _k in BUILD, _k


@element("props_cluster", "props", "Several props of one kind in a row or around: count, spacing, ring=true puts them "
         "in a circle (radius). On the ground (no `on`) or a `top`.",
         {"kind": P("bench", "", KINDS), "count": P(4, ""), "spacing": P(3.0, "m between items (row)"),
          "ring": P(False, "in a circle"), "radius": P(5.0, "circle radius"), "scale": P(1.0, "")},
         attach="any", title_ru="Группа украшений")
def props_cluster(p, ctx):
    part = Part()
    n = max(1, int(p["count"]))
    for i in range(n):
        if p["ring"]:
            a = 2 * math.pi * i / n
            T = g.mat_t(float(p["radius"]) * math.cos(a), float(p["radius"]) * math.sin(a), 0) @ g.mat_rz(math.degrees(a) + 90)
        else:
            T = g.mat_t((i - (n - 1) / 2) * float(p["spacing"]), 0, 0)
        sub = prop({"kind": p["kind"], "scale": p["scale"], "material": None, "accent": None}, ctx)
        for m, mat in sub.solids:
            part.add(g.xf(m, T), mat)
    return part


@element("mast", "roofs", "Lattice mast / spire for towers: tapering 3- or 4-legged truss with horizontal ring platforms "
         "and a light at the top. On a `top` anchor at [x, y].",
         {"h": P(80.0, "height"), "base_r": P(3.0, "radius at the base"), "top_r": P(0.6, "radius at the top"),
          "legs": P(4, "3 or 4"), "rings": P(5, "ring platforms"), "ring_r": P(1.8, "ring radius / leg circle radius"),
          "material": P("panel_white", ""), "light_material": P("red_paint", "")},
         attach="any", title_ru="Решётчатая мачта / шпиль небоскрёба")
def mast(p, ctx):
    H, r0, r1, n = float(p["h"]), float(p["base_r"]), float(p["top_r"]), max(3, int(p["legs"]))
    mat, lm = ctx.mat(p["material"]), ctx.mat(p["light_material"])
    part = Part()

    def rad(z):
        return r0 + (r1 - r0) * z / H

    def pt(i, z):
        a = 2 * math.pi * i / n + math.pi / n
        return [rad(z) * math.cos(a), rad(z) * math.sin(a), z]
    bars = [g.rod(pt(i, 0)[:2] + [-0.3], pt(i, H), 0.18, 8) for i in range(n)]
    steps = max(4, int(H / 6))
    for k in range(steps):
        z0, z1 = H * k / steps, H * (k + 1) / steps
        for i in range(n):
            bars.append(g.rod(pt(i, z0), pt(i + 1, z1), 0.07, 6))
            bars.append(g.rod(pt(i, z1), pt(i + 1, z1), 0.07, 6))
    part.add(g.union(bars), mat)
    nr = int(p["rings"])
    for k in range(nr):
        z = H * (0.25 + 0.6 * k / max(1, nr - 1))
        R = rad(z) * float(p["ring_r"])
        part.add(g.cyl(R, 0.5, 24, z - 0.25) - g.cyl(rad(z) * 0.9, 0.7, 24, z - 0.35), mat)
    part.add(g.cyl(r1 * 1.1, 1.5, 12, H - 0.3) + g.sphere(r1 * 0.9, 12, (0, 0, H + 1.4)), lm)
    return part


@element("crown_frame", "decor", "Open frame around the top of a tower (white fins and rings around the glass, like Varso's "
         "crown). On a `top` anchor; spans w x d and h downward (use offset [0, 0, -h]).",
         {"w": P(30.0, ""), "d": P(30.0, ""), "h": P(20.0, ""), "fins": P(3.0, "fin spacing (m)"), "depth": P(0.8, "fin depth"),
          "material": P("panel_white", "")},
         attach="top", title_ru="Корона-каркас небоскрёба")
def crown_frame(p, ctx):
    W, D, H, sp, dp = float(p["w"]), float(p["d"]), float(p["h"]), float(p["fins"]), float(p["depth"])
    solids = []
    for L, ax in ((W, 0), (D, 1)):
        n = max(2, round(L / sp))
        for side in (-1, 1):
            for i in range(n + 1):
                t = -L / 2 + L * i / n
                if ax == 0:
                    y = side * D / 2
                    solids.append(g.box(t - 0.15, min(y, y + side * dp) - 0.05, 0, t + 0.15, max(y, y + side * dp) + 0.05, H + 2.0))
                else:
                    x = side * W / 2
                    solids.append(g.box(min(x, x + side * dp) - 0.05, t - 0.15, 0, max(x, x + side * dp) + 0.05, t + 0.15, H + 2.0))
    for z in (H * 0.5, H + 1.4):
        ring = g.box(-W / 2 - dp, -D / 2 - dp, z, W / 2 + dp, D / 2 + dp, z + 0.6)
        solids.append(ring - g.box(-W / 2 + 0.3, -D / 2 + 0.3, z - 1, W / 2 - 0.3, D / 2 - 0.3, z + 2))
    return Part().add(g.union(solids), ctx.mat(p["material"]))


@element("skyscraper", "macros", "Skyscraper from interlocking glass volumes (Varso, Shard, One WTC style): `volumes` = "
         "[{x, y, w, d, h}] in metres (x, y = centre, h = total height from the ground), each a curtain-walled shaft; "
         "optional `podium` {w, d, h}, an open white `crown` frame on volume `crown_on` and a lattice `mast` on `mast_on`.",
         {"volumes": P([{"x": 0, "y": 0, "w": 30, "d": 30, "h": 120}], "list of {x, y, w, d, h}"), "floor_h": P(4.0, ""),
          "podium": P({"w": 60, "d": 50, "h": 16}, "{w, d, h} or null"), "glass_material": P("glass_dark", ""),
          "frame_material": P("aluminium", ""), "mullion": P(1.5, "vertical mullion spacing"),
          "crown_on": P(0, "volume index with an open crown frame (null = none)"), "crown_h": P(20.0, ""),
          "crown_material": P("panel_white", ""), "mast_on": P(0, "volume index carrying the mast"),
          "mast_h": P(0.0, "0 = no mast"), "mast_at": P([0, 0], "mast position on that volume's top (m from its centre)")},
         macro=True, title_ru="Небоскрёб из объёмов")
def skyscraper(p, ctx):
    from .macros import E, _part
    fh = float(p["floor_h"])
    c = []
    pz = 0.0
    pd = p.get("podium")
    if pd:
        pz = float(pd["h"])
        nf = max(1, round(pz / 4.5))
        c += [E("podium", "block", w=pd["w"], d=pd["d"], floors=nf, floor_h=pz / nf, plinth_h=0, material="granite"),
              E("podium_roof", "roof", "podium:top", type="flat", parapet_h=1.0, overhang=0, material="gravel")]
        for f in ("front", "back", "left", "right"):
            c.append(E(f"podium_cw_{f}", "curtain_wall", f"podium:{f}", spacing=3.0, glass_material="glass", material=p["frame_material"]))
        c.append(E("entrance", "door", "podium:front", ["50%", 0], w=5, h=4, glazed=True, double=True, canopy="slab", trim="none"))
    for i, v in enumerate(p["volumes"]):
        h = float(v["h"]) - pz
        floors = max(1, round(h / fh))  # one floor height for all volumes: facade rows line up (no flicker)
        vid = f"v{i}"
        c.append(E(vid, "block", "podium:top" if pd else None, [float(v["x"]), float(v["y"])], w=v["w"], d=v["d"],
                   floors=floors, floor_h=fh, plinth_h=0, wall_t=0.4, material="concrete_raw", hollow=False,
                   _offset=[0, 0, -0.02]))
        for f in ("front", "back", "left", "right"):
            c.append(E(f"{vid}_cw_{f}", "curtain_wall", f"{vid}:{f}", spacing=p["mullion"], glass_material=p["glass_material"],
                       material=p["frame_material"], v0=0))
        c.append(E(f"{vid}_roof", "roof", f"{vid}:top", type="flat", parapet_h=1.5, overhang=0, material="bitumen",
                   gable_material=p["frame_material"]))
    ci = p.get("crown_on")
    if ci is not None and int(ci) < len(p["volumes"]):
        v = p["volumes"][int(ci)]
        c.append(E("crown", "crown_frame", f"v{int(ci)}:top", w=v["w"], d=v["d"], h=p["crown_h"], material=p["crown_material"],
                   _offset=[0, 0, -float(p["crown_h"])]))
    mi = p.get("mast_on")
    if float(p.get("mast_h") or 0) > 0 and mi is not None and int(mi) < len(p["volumes"]):
        c.append(E("mast", "mast", f"v{int(mi)}_roof:top", list(p["mast_at"]), h=p["mast_h"], material=p["crown_material"]))
    return _part(c)
