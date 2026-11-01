"""Macros for world styles: Egypt, Mesopotamia, Mesoamerica, Byzantium, Caucasus, Islam (Ottoman, Persian, Moorish,
Mughal), India, China, Japan, Scandinavia, Netherlands, Victorian, Alpine, Art Deco, Brutalism, industry, military."""
from __future__ import annotations

from ..registry import P, element
from .macros import E, _part


@element("egyptian_temple", "macros", "Egyptian temple: pylon with flagstaff niches, pair of obelisks, colonnaded court, "
         "hypostyle hall with papyrus columns, sanctuary.",
         {"w": P(40.0, "pylon width"), "length": P(70.0, ""), "material": P("sandstone", "")},
         macro=True, title_ru="Египетский храм")
def egyptian_temple(p, ctx):
    W, L, m = p["w"], p["length"], p["material"]
    return _part([
        E("pylon", "pylon", None, [0, -L / 2], w=W, d=8, h=18, gate_w=5, gate_h=10, material=m),
        E("relief_l", "panel", "pylon:front_l", ["50%", 3], kind="relief", w=10, h=11, frame=False,
          subject="egyptian pharaoh smiting enemies, sunk relief, hieroglyphs, painted"),
        E("relief_r", "panel", "pylon:front_r", ["50%", 3], kind="relief", w=10, h=11, frame=False,
          subject="egyptian gods procession, sunk relief, hieroglyphs, painted"),
        E("obelisk_l", "obelisk", None, [-6, -L / 2 - 6], w=1.6, h=18, material="granite"),
        E("obelisk_r", "obelisk", None, [6, -L / 2 - 6], w=1.6, h=18, material="granite"),
        E("court", "block", None, [0, -L / 2 + 18.5], w=W * 0.8, d=22, floors=1, floor_h=9, wall_t=1.6, plinth_h=0,
          hollow=True, top_slab=False, material=m),
        E("court_door", "door", "court:front", ["50%", 0], w=5, h=7, open=True, trim="none"),
        E("hall", "block", None, [0, -L / 2 + 39], w=W * 0.7, d=20, floors=1, floor_h=13, wall_t=1.5, plinth_h=0.6, material=m),
        E("hall_door", "door", "hall:front", ["50%", 0.6], w=4, h=7, open=True, trim="none"),
        E("hall_cols", "colonnade", "hall:front", order="egyptian", count=6, h=10, r=0.9, depth=2.5, margin=3, length=W * 0.7 - 6,
          pediment=False, steps=1, ent_h=2.0, material=m, trim_material=m),
        E("hall_roof", "roof", "hall:top", type="flat", parapet_h=0.4, overhang=0.3, material=m, gable_material=m),
        E("hall_cornice", "cornice", "hall:top", kind="crown", h=1.2, out=0.8, material=m),
        E("sanctuary", "block", None, [0, -L / 2 + 55.5], w=W * 0.4, d=14, floors=1, floor_h=9, wall_t=1.5, plinth_h=0.6, material=m),
        E("sanct_roof", "roof", "sanctuary:top", type="flat", parapet_h=0.3, material=m, gable_material=m),
    ])


@element("giza_pyramid", "macros", "Egyptian pyramid complex: smooth pyramid with gilded capstone, mortuary temple, causeway.",
         {"w": P(80.0, ""), "h": P(52.0, ""), "material": P("sandstone", "")}, macro=True, title_ru="Египетская пирамида")
def giza_pyramid(p, ctx):
    w, h = p["w"], p["h"]
    return _part([
        E("pyramid", "step_pyramid", w=w, d=w, h=h, levels=0, material=p["material"]),
        E("cap", "step_pyramid", "pyramid:top", w=3.0, d=3.0, h=2.0, levels=0, material="gold", _offset=[0, 0, -1.9]),
        E("temple", "block", None, [0, -w / 2 - 8], w=24, d=14, floors=1, floor_h=7, wall_t=1.5, plinth_h=0.3, material=p["material"]),
        E("temple_roof", "roof", "temple:top", type="flat", parapet_h=0.3, material=p["material"], gable_material=p["material"]),
        E("causeway", "box", None, [0, -w / 2 - 15 - 20], w=5, d=40, h=1.2, material=p["material"]),
    ])


@element("ziggurat", "macros", "Mesopotamian ziggurat: mud-brick stepped platform with triple staircase and a shrine on top.",
         {"w": P(60.0, ""), "d": P(45.0, ""), "h": P(21.0, ""), "material": P("adobe", "")}, macro=True, title_ru="Зиккурат")
def ziggurat(p, ctx):
    w, d, h = p["w"], p["d"], p["h"]
    return _part([
        E("base", "step_pyramid", w=w, d=d, h=h, top_w=w * 0.35, top_d=d * 0.35, levels=3, stairs="front", stair_w=6,
          material=p["material"], stair_material="brick_yellow"),
        E("shrine", "block", "base:top", w=w * 0.22, d=d * 0.22, floors=1, floor_h=6, wall_t=0.8, plinth_h=0, material="brick_yellow"),
        E("shrine_door", "door", "shrine:front", ["50%", 0], w=1.6, h=3.0, kind="arch"),
        E("shrine_roof", "roof", "shrine:top", type="flat", parapet_h=0.6, material="adobe", gable_material="brick_yellow"),
        E("shrine_cren", "battlements", "shrine:top", h=0.8, t=0.4, merlon_w=0.6, crenel_w=0.5, crenel_h=0.4, material="brick_yellow"),
    ])


@element("maya_pyramid", "macros", "Mesoamerican (Maya/Aztec) temple-pyramid: stepped body, steep staircases, temple with "
         "roof comb on top.",
         {"w": P(30.0, ""), "h": P(24.0, ""), "levels": P(9, ""), "stairs": P("all", ""), "material": P("stone_maya", "")},
         macro=True, title_ru="Пирамида майя / ацтеков")
def maya_pyramid(p, ctx):
    w, h = p["w"], p["h"]
    tw = w * 0.32
    return _part([
        E("pyramid", "step_pyramid", w=w, d=w, h=h, top_w=tw, levels=p["levels"], stairs=p["stairs"], stair_w=w * 0.2,
          material=p["material"], stair_material=p["material"]),
        E("temple", "block", "pyramid:top", w=tw * 0.8, d=tw * 0.6, floors=1, floor_h=5, wall_t=0.9, plinth_h=0.3, material=p["material"]),
        E("temple_door", "door", "temple:front", ["50%", 0.3], w=1.6, h=2.6, open=True, trim="none"),
        E("temple_roof", "roof", "temple:top", type="flat", parapet_h=0.0, overhang=0.2, material=p["material"]),
        E("comb", "wall", "temple_roof:ridge", [-tw * 0.3, 0], length=tw * 0.6, h=4.5, t=0.8, material=p["material"]),
        E("frieze", "panel", "temple:front", ["50%", 3.3], kind="relief", w=tw * 0.7, h=1.4, frame=False,
          subject="maya stucco frieze, glyphs and rain god masks"),
    ])


@element("byzantine_church", "macros", "Byzantine cross-in-square church: cubic core, four cross arms with barrel roofs, "
         "central dome on a tall windowed drum, three apses, brick-and-stone banding.",
         {"size": P(16.0, ""), "h": P(10.0, ""), "material": P("brick_red", ""), "dome_material": P("lead_roof", "")},
         macro=True, title_ru="Византийская крестово-купольная церковь")
def byzantine_church(p, ctx):
    s, h, m = p["size"], p["h"], p["material"]
    arm = s * 0.36
    c = [E("core", "block", w=s, d=s, floors=1, floor_h=h, wall_t=1.0, plinth_h=0.4, material=m),
         E("core_roof", "roof", "core:top", type="pyramid", pitch=18, overhang=0.2, material="clay_tile"),
         E("dome", "dome", "core:top", None, profile="dome", r=s * 0.22, drum_h=s * 0.32, drum_windows=12, cross="orthodox",
           material=p["dome_material"], drum_material=m, _offset=[0, 0, -0.2]),
         E("band", "cornice", "core:floor0", kind="band", h=0.3, out=0.08, material="stone_ashlar", _offset=[0, 0, h * 0.5])]
    for i, (dx, dy, rot) in enumerate(((0, -1, 0), (0, 1, 0), (-1, 0, 90))):
        aid = f"arm{i}"
        c.append(E(aid, "block", None, [dx * (s / 2 + arm / 2 - 0.4), dy * (s / 2 + arm / 2 - 0.4)], w=arm if dy else arm, d=arm,
                   floors=1, floor_h=h * 1.2, wall_t=0.9, plinth_h=0.4, material=m))
        c.append(E(f"{aid}_roof", "roof", f"{aid}:top", type="barrel", ridge="y" if dy else "x", overhang=0.2, material="clay_tile"))
        face = "front" if dy < 0 else ("back" if dy > 0 else "left")
        c.append(E(f"{aid}_win", "windows", f"{aid}:{face}", kind="arch", w=0.9, h=2.0, us=["35%", "50%", "65%"], vs=[h * 0.6],
                   trim="archivolt", mullions=[0, 0]))
    c.append(E("narthex_door", "door", "arm2:left", ["50%", 0.4], kind="arch", w=1.8, h=3.0, orders=1, trim="archivolt"))
    c.append(E("apse", "tower", None, [s / 2, 0], shape="round", r=s * 0.22, h=h * 0.85, floors=1, material=m))
    c.append(E("apse_roof", "roof", "apse:top", type="dome", h=1.5, overhang=0.2, material=p["dome_material"]))
    c.append(E("apse_win", "windows", "apse:face7", kind="arch", w=0.7, h=1.8, us=["50%"], vs=[h * 0.4], trim="archivolt"))
    for k, sy in enumerate((-1, 1)):
        c.append(E(f"apse_s{k}", "tower", None, [s / 2 - 1.2, sy * s * 0.33], shape="round", r=s * 0.11, h=h * 0.65, floors=1, material=m))
        c.append(E(f"apse_s{k}_roof", "roof", f"apse_s{k}:top", type="dome", h=0.8, overhang=0.15, material=p["dome_material"]))
    return _part(c)


@element("caucasian_church", "macros", "Armenian / Georgian church: compact cross plan of stone, tall polygonal drum with a "
         "conical roof, blind arcades, gable roofs on the arms.",
         {"size": P(14.0, ""), "h": P(9.0, ""), "material": P("tufa", "")}, macro=True, title_ru="Армянская / грузинская церковь")
def caucasian_church(p, ctx):
    s, h, m = p["size"], p["h"], p["material"]
    arm = s * 0.4
    c = [E("core", "block", w=s, d=s, floors=1, floor_h=h, wall_t=1.2, plinth_h=0.6, material=m),
         E("core_roof", "roof", "core:top", type="cross_gable", pitch=30, overhang=0.2, material=m, gable_material=m),
         E("drum", "tower", "core:top", [0, 0], shape="octagon", r=s * 0.2, h=s * 0.55, floors=1, wall_t=0.8, material=m,
           _offset=[0, 0, -0.3]),
         E("drum_win", "windows", "drum:face1", kind="arch", w=0.6, h=1.6, us=["50%"], vs=[s * 0.2], trim="archivolt", mullions=[0, 0]),
         E("drum_win2", "windows", "drum:face5", kind="arch", w=0.6, h=1.6, us=["50%"], vs=[s * 0.2], trim="archivolt", mullions=[0, 0]),
         E("cone", "roof", "drum:top", type="cone", pitch=50, overhang=0.25, material=m),
         E("cross", "cross", "cone:ridge", None, kind="latin", size=1.2, _offset=[0, 0, -0.1])]
    for i, (dx, dy) in enumerate(((0, -1), (0, 1), (-1, 0), (1, 0))):
        aid = f"arm{i}"
        c.append(E(aid, "block", None, [dx * (s / 2 + arm / 2 - 0.5), dy * (s / 2 + arm / 2 - 0.5)], w=arm, d=arm, floors=1,
                   floor_h=h * 0.9, wall_t=1.0, plinth_h=0.6, material=m))
        c.append(E(f"{aid}_roof", "roof", f"{aid}:top", type="gable", ridge="y" if dy else "x", pitch=30, material=m, gable_material=m))
        face = {(0, -1): "front", (0, 1): "back", (-1, 0): "left", (1, 0): "right"}[(dx, dy)]
        c.append(E(f"{aid}_niche", "niche", f"{aid}:{face}", kind="arch", w=0.9, h=3.0, us=["30%", "70%"], vs=[1.2], depth=0.25, trim="archivolt"))
        c.append(E(f"{aid}_win", "window", f"{aid}:{face}", ["50%", h * 0.45], kind="arch", w=0.6, h=1.6, trim="archivolt", mullions=[0, 0]))
    c.append(E("door", "door", "arm2:left", ["50%", 0.6], kind="arch", w=1.6, h=2.8, orders=2, trim="archivolt", steps=3))
    return _part(c)


@element("ottoman_mosque", "macros", "Ottoman mosque (Sinan type): square prayer hall, central dome on a windowed drum, "
         "semi-domes, small corner domes, domed portico, pencil minarets with balconies.",
         {"size": P(30.0, "prayer hall side"), "h": P(14.0, ""), "minarets": P(4, "0, 2 or 4"), "material": P("stone_ashlar", ""),
          "dome_material": P("lead_roof", "")}, macro=True, title_ru="Османская мечеть")
def ottoman_mosque(p, ctx):
    s, h, m, dm = p["size"], p["h"], p["material"], p["dome_material"]
    c = [E("hall", "block", w=s, d=s, floors=1, floor_h=h, wall_t=1.5, plinth_h=0.8, material=m),
         E("hall_roof", "roof", "hall:top", type="flat", parapet_h=0.0, overhang=0.1, material=dm),
         E("dome", "dome", "hall:top", None, profile="dome", r=s * 0.3, drum_h=3.5, drum_windows=24, cross="crescent", material=dm,
           drum_material=m, _offset=[0, 0, -0.1]),
         E("win_f", "windows", "hall:front", kind="arch", w=1.4, h=2.6, cols=5, rows=2, sill=2.0, row_step=4.5, trim="simple"),
         E("win_b", "windows", "hall:back", kind="arch", w=1.4, h=2.6, cols=5, rows=2, sill=2.0, row_step=4.5, trim="simple"),
         E("win_r", "windows", "hall:right", kind="arch", w=1.4, h=2.6, cols=5, rows=2, sill=2.0, row_step=4.5, trim="simple")]
    for i, (dx, dy, rot) in enumerate(((0, -1, 0), (0, 1, 180), (1, 0, 90), (-1, 0, -90))):
        c.append(E(f"semi{i}", "dome", "hall:top", [dx * s * 0.3, dy * s * 0.3], profile="dome", r=s * 0.2, cross="none", material=dm,
                   half=True, _rot=rot, _offset=[0, 0, -0.1]))
    for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        c.append(E(f"turret{i}", "dome", "hall:top", [dx * s * 0.42, dy * s * 0.42], profile="dome", r=1.4, drum_h=1.5, cross="spike",
                   material=dm, drum_material=m))
    # portico (son cemaat yeri) on the left (entrance) side
    c.append(E("portico", "block", None, [-s / 2 - 4, 0], w=8, d=s * 0.9, floors=1, floor_h=h * 0.55, wall_t=0.8, plinth_h=0.8,
               material=m, hollow=False))
    c.append(E("portico_roof", "roof", "portico:top", type="flat", parapet_h=0, material=dm))
    for k in range(5):
        c.append(E(f"portico_dome{k}", "dome", "portico:top", [0, (k - 2) * s * 0.17], profile="dome", r=2.2, cross="none",
                   material=dm, _offset=[0, 0, -0.1]))
    c.append(E("portico_arch", "niche", "portico:left", kind="lancet", w=3.0, h=h * 0.4, cols=5, rows=1, vs=[0.8], depth=1.2, margin=1.0))
    c.append(E("door", "door", "hall:left", ["50%", 0.8], kind="lancet", w=2.4, h=4.0, trim="simple"))
    n = int(p["minarets"])
    spots = [(-1, -1), (-1, 1), (1, -1), (1, 1)][:n] if n in (2, 4) else []
    for i, (dx, dy) in enumerate(spots):
        c.append(E(f"minaret{i}", "minaret", None, [dx * (s / 2 + 2.5) - (4 if dx < 0 else 0), dy * (s / 2 + 2.5)], r=1.5, h=h * 3.2,
                   balconies=3 if i < 2 else 2, cap="pencil", material=m, cap_material=dm))
    return _part(c)


@element("persian_mosque", "macros", "Persian / Timurid / Central Asian mosque or madrasa: monumental iwan portal, "
         "tiled bulbous ribbed dome on a high drum, cylindrical minarets, arcaded walls.",
         {"w": P(40.0, ""), "d": P(40.0, ""), "h": P(10.0, "wall height"), "material": P("brick_yellow", ""),
          "tile_material": P("ceramic_blue", "")}, macro=True, title_ru="Персидская / среднеазиатская мечеть, медресе")
def persian_mosque(p, ctx):
    w, d, h, m, tm = p["w"], p["d"], p["h"], p["material"], p["tile_material"]
    return _part([
        E("court", "block", w=w, d=d, floors=1, floor_h=h, wall_t=6.0, plinth_h=0.4, material=m, top_slab=True),
        E("court_roof", "roof", "court:top", type="flat", parapet_h=0.6, overhang=0, material=m, gable_material=m),
        E("arcade_f", "niche", "court:front", kind="lancet", w=2.4, h=5.0, cols=8, vs=[1.0], depth=1.2, margin=4, trim="simple"),
        E("arcade_b", "niche", "court:back", kind="lancet", w=2.4, h=5.0, cols=8, vs=[1.0], depth=1.2, margin=4, trim="simple"),
        E("portal", "iwan", None, [0, -d / 2 - 2.5], w=w * 0.42, h=h * 2.2, d=7, arch="lancet", material=m, tile_material=tm,
          panel_subject="persian muqarnas and blue faience tile mosaic, arabic calligraphy"),
        E("dome_hall", "block", None, [0, d / 2 - 6], w=w * 0.4, d=w * 0.4, floors=1, floor_h=h * 1.8, wall_t=1.5, plinth_h=0.4, material=m),
        E("dome", "dome", "dome_hall:top", None, profile="onion", r=w * 0.14, drum_h=w * 0.18, drum_windows=12, ribs=24,
          cross="crescent", material="dome_blue", drum_material=tm, _offset=[0, 0, -0.2]),
        E("minaret_l", "minaret", None, [-w * 0.21 - 1.5, -d / 2 - 0.5], r=1.6, h=h * 3.2, base_h=0, balconies=1, cap="lantern",
          shape="round", taper=0.8, material=tm, cap_material=tm),
        E("minaret_r", "minaret", None, [w * 0.21 + 1.5, -d / 2 - 0.5], r=1.6, h=h * 3.2, base_h=0, balconies=1, cap="lantern",
          shape="round", taper=0.8, material=tm, cap_material=tm),
    ])


@element("moorish_palace", "macros", "Moorish / Andalusian palace: whitewashed or ochre blocks, horseshoe-arch arcades, "
         "flat roofs with merlons, tower with tiled pyramid roof, courtyard pavilion.",
         {"w": P(36.0, ""), "d": P(28.0, ""), "material": P("plaster_ochre", "")}, macro=True, title_ru="Мавританский дворец")
def moorish_palace(p, ctx):
    w, d, m = p["w"], p["d"], p["material"]
    return _part([
        E("main", "block", w=w, d=d, floors=2, floor_h=4.5, wall_t=0.9, plinth_h=0.4, material=m),
        E("roof", "roof", "main:top", type="flat", parapet_h=0.4, overhang=0, material="clay_tile", gable_material=m),
        E("merlons", "battlements", "main:top", h=1.0, t=0.5, merlon_w=0.6, crenel_w=0.6, crenel_h=0.5, style="swallowtail", material=m),
        E("arcade", "windows", "main:front", kind="horseshoe", w=2.2, h=3.4, cols=7, rows=1, sill=0.4, glazed=False, frame=False,
          trim="archivolt", margin=3, trim_material="ceramic_blue"),
        E("win_up", "windows", "main:front", kind="horseshoe", w=1.0, h=1.8, cols=7, only_rows=[1], margin=3, trim="simple",
          mullions=[1, 0], frame_material="frame_brown"),
        E("win_b", "windows", "main:back", kind="horseshoe", w=1.0, h=1.8, cols=6, margin=3, trim="simple", mullions=[1, 0]),
        E("tower", "tower", None, [w / 2 - 3, -d / 2 + 3], shape="square", r=4.0, h=16, floors=4, material=m),
        E("tower_win", "windows", "tower:face2", kind="horseshoe", w=1.0, h=2.0, us=["35%", "65%"], vs=[12], mullions=[0, 0]),
        E("tower_roof", "roof", "tower:top", type="pyramid", pitch=30, overhang=0.3, material="glazed_tile_green"),
        E("door", "door", "main:left", ["50%", 0.4], kind="horseshoe", w=2.2, h=3.6, trim="archivolt", trim_material="ceramic_blue"),
    ])


@element("mughal_mausoleum", "macros", "Mughal mausoleum (Taj Mahal type): high plinth, chamfered main block with iwans on "
         "each side, bulbous onion dome on a drum, four chhatris, four minarets.",
         {"size": P(56.0, "main block side"), "h": P(28.0, ""), "material": P("marble", ""), "plinth_material": P("red_sandstone", "")},
         macro=True, title_ru="Могольский мавзолей (тип Тадж-Махал)")
def mughal_mausoleum(p, ctx):
    s, h, m = p["size"], p["h"], p["material"]
    ch = s * 0.18
    poly = [[-s / 2 + ch, -s / 2], [s / 2 - ch, -s / 2], [s / 2, -s / 2 + ch], [s / 2, s / 2 - ch], [s / 2 - ch, s / 2],
            [-s / 2 + ch, s / 2], [-s / 2, s / 2 - ch], [-s / 2, -s / 2 + ch]]
    P_ = s * 1.7
    c = [E("plinth", "platform", w=P_, d=P_, h=6.0, steps=1, material=p["plinth_material"]),
         E("main", "block", "plinth:top", poly=poly, floors=2, floor_h=h / 2, wall_t=2.5, plinth_h=0, material=m),
         E("roof", "roof", "main:top", type="flat", parapet_h=0.8, overhang=0, material=m, gable_material=m),
         E("drum", "tower", "main:top", [0, 0], shape="round", r=s * 0.22, h=h * 0.3, floors=1, wall_t=1.5, material=m,
           _offset=[0, 0, -0.2]),
         E("dome", "dome", "drum:top", None, profile="onion", r=s * 0.22, cross="spike", material=m, _offset=[0, 0, -0.1])]
    for i, (face, rot) in enumerate((("face0", 0), ("face2", 90), ("face4", 180), ("face6", 270))):
        c.append(E(f"iwan{i}", "niche", f"main:{face}", kind="ogee", w=s * 0.28, h=h * 0.85, us=["50%"], vs=[0], depth=2.0, trim="simple"))
    for i, face in enumerate(("face1", "face3", "face5", "face7")):
        c.append(E(f"side_niche{i}", "niche", f"main:{face}", kind="ogee", w=ch * 0.8, h=h * 0.38, us=["50%"], vs=["8%", "55%"], depth=1.2))
    for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        c.append(E(f"chhatri{i}", "chhatri", "main:top", [dx * s * 0.3, dy * s * 0.3], w=5, h=4, cols=8, dome="onion",
                   material=m, dome_material=m))
        c.append(E(f"minaret{i}", "minaret", "plinth:top", [dx * (P_ / 2 - 3), dy * (P_ / 2 - 3)], r=2.0, h=h * 1.6, base_h=0,
                   balconies=3, cap="lantern", shape="round", taper=0.8, finial="spike", material=m, cap_material=m))
    return _part(c)


@element("hindu_temple", "macros", "Hindu temple: raised platform (jagati), pillared hall (mandapa) with stepped roof, "
         "sanctum with a curvilinear shikhara (Nagara) or pyramidal vimana (Dravida).",
         {"style": P("nagara", "", ["nagara", "dravida"]), "size": P(14.0, "sanctum width"), "material": P("sandstone", "")},
         macro=True, title_ru="Индуистский храм")
def hindu_temple(p, ctx):
    s, m = p["size"], p["material"]
    drav = p["style"] == "dravida"
    return _part([
        E("jagati", "platform", w=s * 4.0, d=s * 2.2, h=2.0, steps=2, material=m),
        E("sanctum", "block", "jagati:top", [s * 0.9, 0], w=s, d=s, floors=1, floor_h=s * 0.7, wall_t=1.5, plinth_h=0.6, material=m),
        E("tower", "shikhara", "sanctum:top", w=s * 1.05, h=s * (1.4 if drav else 2.0), tiers=7 if drav else 14, stepped=drav,
          rathas=0 if drav else 2, material=m, _offset=[0, 0, -0.05]),
        E("mandapa", "block", "jagati:top", [-s * 0.6, 0], w=s * 1.6, d=s * 1.2, floors=1, floor_h=s * 0.55, wall_t=0.6, plinth_h=0.6,
          material=m),
        E("mandapa_roof", "roof", "mandapa:top", type="pagoda", tiers=3, overhang=0.6, material=m, gable_material=m),
        E("porch", "colonnade", "mandapa:left", order="square", count=4, h=s * 0.45, r=0.35, depth=2.5, margin=1.2, length=s * 1.2 - 2.4,
          pediment=False, steps=0, ent_h=0.8, material=m, trim_material=m),
        E("door", "door", "mandapa:left", ["50%", 0.6], w=1.8, h=3.0, open=True, trim="simple"),
        E("niches", "niche", "sanctum:front", kind="rect", w=1.2, h=2.4, us=["50%"], vs=[1.5], depth=0.5),
        E("niches_b", "niche", "sanctum:back", kind="rect", w=1.2, h=2.4, us=["50%"], vs=[1.5], depth=0.5),
    ])


@element("chinese_temple", "macros", "Chinese temple hall: stone terrace, red lacquered columns, double-eave glazed hip roof "
         "with upturned corners, optional pagoda.",
         {"w": P(24.0, ""), "d": P(14.0, ""), "pagoda": P(True, ""), "roof_material": P("glazed_tile_yellow", "")},
         macro=True, title_ru="Китайский храм / дворцовый зал")
def chinese_temple(p, ctx):
    w, d, rm = p["w"], p["d"], p["roof_material"]
    c = [E("terrace", "platform", w=w + 8, d=d + 8, h=1.6, steps=3, material="stone_ashlar"),
         E("hall", "block", "terrace:top", w=w, d=d, floors=1, floor_h=6.0, wall_t=0.5, plinth_h=0, material="red_paint"),
         E("cols_f", "colonnade", "hall:front", order="plain", count=8, h=5.6, r=0.3, depth=1.6, margin=0.4, length=w - 0.8,
           pediment=False, steps=0, ent_h=0.6, material="red_paint", trim_material="wood_painted_green"),
         E("lattice", "windows", "hall:front", w=2.0, h=3.2, cols=5, rows=1, sill=0.9, trim="none", mullions=[3, 4],
           frame_material="red_paint", glass_material="wood_boards"),
         E("door", "door", "hall:front", ["50%", 0], w=2.6, h=4.2, double=True, trim="none", leaf_material="red_paint"),
         E("roof_low", "roof", "hall:top", type="chinese", pitch=28, overhang=2.4, t=0.25, material=rm, gable_material="red_paint",
           h=1.4),
         E("upper", "block", "hall:top", w=w * 0.75, d=d * 0.6, floors=1, floor_h=2.6, plinth_h=0, material="red_paint",
           _offset=[0, 0, -0.05]),
         E("roof_up", "roof", "upper:top", type="chinese", pitch=38, overhang=1.8, t=0.25, material=rm, gable_material="red_paint")]
    if p["pagoda"]:
        c.append(E("pagoda", "pagoda", None, [w / 2 + 14, 0], tiers=7, w=7.0, material="plaster_white", roof_material="clay_tile_dark"))
    return _part(c)


@element("pagoda", "macros", "East Asian pagoda (Chinese/Japanese): stacked storeys with deep curved eaves, top spire (sorin).",
         {"tiers": P(5, ""), "w": P(8.0, "base width"), "storey_h": P(3.2, ""), "shrink": P(0.88, "per storey"),
          "material": P("wood_dark", ""), "roof_material": P("clay_tile_dark", "")}, macro=True, title_ru="Пагода")
def pagoda(p, ctx):
    n, w, sh, k = int(p["tiers"]), p["w"], p["storey_h"], p["shrink"]
    c = [E("base", "platform", w=w + 3, d=w + 3, h=1.0, steps=2, material="stone_ashlar")]
    prev = "base"
    for i in range(n):
        ww = w * k ** i
        c.append(E(f"s{i}", "block", f"{prev}:top", w=ww, d=ww, floors=1, floor_h=sh, plinth_h=0, wall_t=0.4, material=p["material"],
                   _offset=[0, 0, -0.05]))
        c.append(E(f"r{i}", "roof", f"s{i}:top", type="chinese", pitch=24, overhang=ww * 0.35 + 0.6, t=0.25, h=1.0 + ww * 0.06,
                   material=p["roof_material"], gable_material=p["material"]))
        c.append(E(f"d{i}", "door", f"s{i}:front", ["50%", 0.2], w=1.2, h=2.0, trim="none", leaf_material="red_paint"))
        prev = f"s{i}"
    c.append(E("sorin", "spire", f"r{n - 1}:ridge", None, r=0.35, h=w * 0.9, sides=8, base_h=0.4, material="bronze", finial="ball",
               _offset=[0, 0, -0.3]))
    return _part(c)


@element("japanese_house", "macros", "Japanese traditional house / temple (minka, shoin): raised wooden floor, engawa veranda, "
         "shoji walls, deep irimoya roof.",
         {"w": P(16.0, ""), "d": P(11.0, ""), "roof": P("irimoya", "", ["irimoya", "chinese", "hip", "gable"]),
          "roof_material": P("clay_tile_dark", "")}, macro=True, title_ru="Японский дом / храм")
def japanese_house(p, ctx):
    w, d = p["w"], p["d"]
    return _part([
        E("base", "platform", w=w + 1.6, d=d + 1.6, h=0.7, steps=1, material="stone_ashlar"),
        E("veranda", "platform", "base:top", w=w + 1.2, d=d + 1.2, h=0.15, steps=1, material="wood_floor"),
        E("house", "block", "base:top", w=w, d=d, floors=1, floor_h=3.4, wall_t=0.2, plinth_h=0, material="plaster_white"),
        E("posts", "timber_frame", "house:front", post_spacing=1.8, pattern="grid", material="wood_dark"),
        E("posts_b", "timber_frame", "house:back", post_spacing=1.8, pattern="grid", material="wood_dark"),
        E("shoji", "windows", "house:front", w=1.6, h=2.2, cols=6, rows=1, sill=0.2, trim="none", mullions=[3, 5],
          frame_material="wood_dark", glass_material="paper_shoji"),
        E("shoji_b", "windows", "house:back", w=1.6, h=2.2, cols=6, rows=1, sill=0.2, trim="none", mullions=[3, 5],
          frame_material="wood_dark", glass_material="paper_shoji"),
        E("roof", "roof", "house:top", type=p["roof"], pitch=34, overhang=1.6, t=0.25, material=p["roof_material"], gable_material="wood_dark"),
    ])


@element("stave_church", "macros", "Norwegian stave church (stavkirke): tarred wooden nave on a stone sill, stacked steep "
         "shingled roofs, central tower with spire, dragon-head gables (finials), surrounding gallery.",
         {"w": P(8.0, ""), "length": P(12.0, ""), "material": P("wood_tar", "")}, macro=True, title_ru="Ставкирка (каркасная церковь)")
def stave_church(p, ctx):
    w, L, m = p["w"], p["length"], p["material"]
    return _part([
        E("gallery", "block", w=L + 3, d=w + 3, floors=1, floor_h=2.4, wall_t=0.2, plinth_h=0.6, material=m, plinth_material="stone_rubble"),
        E("gallery_roof", "roof", "gallery:top", type="hip", pitch=35, overhang=0.4, material="shingles_wood"),
        E("nave", "block", "gallery:floor0", w=L, d=w, floors=1, floor_h=7, wall_t=0.25, plinth_h=0, material=m),
        E("nave_roof", "roof", "nave:top", type="gable", pitch=58, overhang=0.4, material="shingles_wood", gable_material=m),
        E("tier2", "block", "nave_roof:ridge", None, w=L * 0.45, d=w * 0.45, floors=1, floor_h=2.2, plinth_h=0, material=m,
          _offset=[0, 0, -1.6]),
        E("tier2_roof", "roof", "tier2:top", type="gable", pitch=55, overhang=0.3, material="shingles_wood", gable_material=m),
        E("tower", "tower", "tier2_roof:ridge", None, shape="square", r=1.1, h=2.4, floors=1, wall_t=0.2, material=m, _offset=[0, 0, -1.0]),
        E("spire", "spire", "tower:top", r=1.3, h=6.5, sides=4, material="shingles_wood", finial="spike"),
        E("dragon_w", "pinnacle", "nave_roof:ridge", [-L / 2 - 0.2, 0], w=0.3, h=1.6, top=0.6, material=m, crockets=False,
          _offset=[0, 0, -0.35]),
        E("dragon_e", "pinnacle", "nave_roof:ridge", [L / 2 + 0.2, 0], w=0.3, h=1.6, top=0.6, material=m, crockets=False,
          _offset=[0, 0, -0.35]),
        E("door", "door", "gallery:left", ["50%", 0.6], kind="arch", w=1.2, h=2.0, trim="simple", trim_material="wood_carved"),
        E("apse", "block", None, [L / 2 + 2.6, 0], w=3, d=w * 0.55, floors=1, floor_h=5, wall_t=0.2, plinth_h=0.6, material=m),
        E("apse_roof", "roof", "apse:top", type="pyramid", pitch=55, overhang=0.3, material="shingles_wood"),
    ])


@element("dutch_house", "macros", "Dutch / Hanseatic canal house: tall narrow brick house with a decorative street gable "
         "(stepped, neck, bell), large windows, hoist beam. `count` builds a terrace row.",
         {"w": P(6.5, ""), "d": P(14.0, ""), "floors": P(4, ""), "gable": P("stepped", "", ["stepped", "neck", "bell", "spout", "curved"]),
          "count": P(1, "houses in a row"), "material": P("brick_red", "")}, macro=True, title_ru="Голландский / ганзейский дом")
def dutch_house(p, ctx):
    c = []
    kinds = ["stepped", "neck", "bell", "spout", "curved"]
    for i in range(int(p["count"])):
        w, d, n = p["w"], p["d"], int(p["floors"])
        x = i * w - (int(p["count"]) - 1) * w / 2
        gk = p["gable"] if i == 0 else kinds[(kinds.index(p["gable"]) + i) % len(kinds)]
        h = f"h{i}"
        c += [E(h, "block", None, [x, 0], w=w, d=d, floors=n, floor_h=3.3, wall_t=0.4, plinth_h=0.6, material=p["material"]),
              E(f"roof{i}", "roof", f"{h}:top", type="gable", ridge="y", pitch=58, overhang=0.05, material="clay_tile_dark",
                gable_material=p["material"]),
              E(f"gable{i}", "gable_wall", f"{h}:front", ["50%", "100%"], kind=gk, h=w * 0.5 * 1.6 + 0.6, material=p["material"],
                trim_material="limestone_trim", _offset=[0, 0.0, -0.05]),
              E(f"gwin{i}", "window", f"gable{i}:face", ["50%", 1.0], w=1.0, h=1.4, trim="simple", frame_material="frame_white"),
              E(f"win{i}", "windows", f"{h}:front", w=1.3, h=2.0, cols=2, margin=1.2, trim="simple", frame_material="frame_white",
                mullions=[1, 2], skip=[[0, 0]]),
              E(f"door{i}", "door", f"{h}:front", [w * 0.27, 0.6], w=1.2, h=2.5, steps=3, transom=True, trim="classic")]
    return _part(c)


@element("victorian_house", "macros", "Victorian / Queen Anne house: asymmetric massing, corner round turret with conical roof, "
         "canted bay windows, wraparound porch, steep cross gables, clapboard.",
         {"w": P(12.0, ""), "d": P(10.0, ""), "material": P("clapboard", "")}, macro=True, title_ru="Викторианский дом")
def victorian_house(p, ctx):
    w, d, m = p["w"], p["d"], p["material"]
    return _part([
        E("main", "block", w=w, d=d, floors=2, floor_h=3.2, wall_t=0.3, plinth_h=0.9, material=m, plinth_material="brick_red"),
        E("roof", "roof", "main:top", type="cross_gable", pitch=50, overhang=0.4, material="slate", gable_material=m),
        E("turret", "tower", None, [w / 2, -d / 2], shape="round", r=1.8, h=8.6, floors=3, wall_t=0.3, material=m),
        E("turret_roof", "roof", "turret:top", type="cone", pitch=65, overhang=0.3, material="slate"),
        E("turret_win", "windows", "turret:face6", w=0.8, h=1.6, us=["50%"], rows=2, sill=1.8, trim="simple"),
        E("bay", "bay_window", "main:left", ["50%", 0.9], kind="canted", w=3.4, depth=1.0, h=3.2, storeys=2, cap="hip",
          material=m, roof_material="slate"),
        E("win_f", "windows", "main:front", w=1.0, h=1.8, us=["25%", "55%"], trim="classic", shutters=True, mullions=[0, 1]),
        E("win_b", "windows", "main:back", w=1.0, h=1.8, cols=3, trim="classic", mullions=[0, 1]),
        E("door", "door", "main:front", ["40%", 0.9], w=1.1, h=2.3, steps=5, transom=True, trim="classic"),
        E("porch", "canopy", "main:front", ["35%", 3.5], kind="shed_porch", w=w * 0.6, d=2.4, posts=True, post_h=2.7,
          material="wood_painted_white", roof_material="slate"),
        E("porch_deck", "box", "main:front", ["35%", 0], w=w * 0.6, d=2.4, h=0.85, material="wood_floor", _offset=[0, 1.15, 0]),
        E("chimney", "chimney", "main:top", [-w * 0.3, d * 0.2], h=6.0, material="brick_red"),
    ])


@element("alpine_chalet", "macros", "Alpine / Swiss chalet: stone ground floor, timber upper floors, very wide low gable roof "
         "with deep overhangs, wooden balconies across the gable front, shutters.",
         {"w": P(12.0, ""), "d": P(10.0, ""), "material": P("wood_boards", "")}, macro=True, title_ru="Альпийское шале")
def alpine_chalet(p, ctx):
    w, d, m = p["w"], p["d"], p["material"]
    return _part([
        E("ground", "block", w=w, d=d, floors=1, floor_h=3.0, wall_t=0.6, plinth_h=0.3, material="stone_rubble"),
        E("upper", "block", "ground:top", w=w, d=d, floors=2, floor_h=2.8, wall_t=0.3, plinth_h=0, material=m, _offset=[0, 0, -0.02]),
        E("roof", "roof", "upper:top", type="gable", ridge="y", pitch=24, overhang=1.8, t=0.25, material="shingles_wood", gable_material=m),
        E("win_g", "windows", "ground:front", w=1.0, h=1.2, cols=3, trim="simple", shutters=True, skip=[[1, 0]], sill=1.0),
        E("door", "door", "ground:front", ["50%", 0.3], kind="segmental", w=1.2, h=2.2, trim="rustic"),
        E("win_u", "windows", "upper:front", w=1.0, h=1.3, cols=4, trim="simple", shutters=True, sill=0.8),
        E("balc", "balconies", "upper:front", kind="balcony", w=w - 0.6, d=1.4, us=["50%"], vs=[0.0, 2.8], railing="wood",
          slab_material="wood_floor", railing_material="wood_carved"),
        E("win_side", "windows", "upper:left", w=1.0, h=1.3, cols=3, trim="simple", shutters=True, sill=0.8),
    ])


@element("art_deco_tower", "macros", "Art Deco skyscraper: stepped setbacks, vertical pilaster strips, ornamental crown and spire.",
         {"w": P(30.0, ""), "floors": P(40, ""), "setbacks": P(4, ""), "material": P("limestone_trim", "")},
         macro=True, title_ru="Небоскрёб ар-деко")
def art_deco_tower(p, ctx):
    w, n, ns, m = p["w"], int(p["floors"]), int(p["setbacks"]), p["material"]
    c = []
    prev = None
    per = max(2, n // (ns + 1))
    for i in range(ns + 1):
        ww = w * (1 - 0.17 * i)
        fl = per if i < ns else n - per * ns
        bid = f"t{i}"
        c.append(E(bid, "block", f"{prev}:top" if prev else None, w=ww, d=ww, floors=fl, floor_h=3.8, plinth_h=0 if prev else 1.2,
                   wall_t=0.4, material=m, _offset=[0, 0, -0.02] if prev else [0, 0, 0]))
        for f in ("front", "back", "left", "right"):
            c.append(E(f"{bid}_pil_{f}", "pilasters", f"{bid}:{f}", w=0.5, depth=0.25, cols=max(3, int(ww / 3)), capital=False))
            c.append(E(f"{bid}_win_{f}", "windows", f"{bid}:{f}", w=1.2, h=2.2, cols=max(2, int(ww / 3) - 1), margin=2.0, trim="none",
                       frame_material="steel", sill=(1.2 if not prev else 0) + 0.9))
        c.append(E(f"{bid}_roof", "roof", f"{bid}:top", type="flat", parapet_h=1.2, overhang=0, material="bitumen", gable_material=m))
        prev = bid
    c.append(E("crown", "step_pyramid", f"{prev}:top", w=w * 0.3, d=w * 0.3, h=8, levels=5, top_w=w * 0.08, material="steel",
               _offset=[0, 0, -0.03]))
    c.append(E("spire", "spire", "crown:top", r=0.6, h=18, sides=8, base_h=0, material="steel", finial="none", _offset=[0, 0, -0.1]))
    c.append(E("door", "door", "t0:front", ["50%", 0], w=4, h=5, double=True, glazed=True, trim="classic"))
    return _part(c)


@element("brutalist_block", "macros", "Brutalist / Soviet modernist building: raw concrete stacked and cantilevered volumes, "
         "deep window recesses, pilotis, rooftop service volumes.",
         {"w": P(40.0, ""), "d": P(16.0, ""), "floors": P(8, ""), "material": P("concrete_raw", "")}, macro=True, title_ru="Брутализм")
def brutalist_block(p, ctx):
    w, d, n, m = p["w"], p["d"], int(p["floors"]), p["material"]
    fh = 3.4
    return _part([
        E("pilotis", "colonnade", None, [-w / 2 + 2, 0], order="square", count=8, h=fh * 1.5, r=0.6, length=w - 4, pediment=False,
          steps=0, ent_h=0.6, material=m, trim_material=m),
        E("core", "block", None, [0, 0], w=w * 0.25, d=d * 0.6, floors=2, floor_h=fh * 0.75, plinth_h=0, material=m),
        E("slab", "block", "core:top", w=w, d=d, floors=n, floor_h=fh, plinth_h=0, wall_t=0.4, material=m, _offset=[0, 0, -0.05]),
        E("win_f", "windows", "slab:front", w=2.6, h=1.6, cols=10, margin=1.5, trim="none", recess=0.5, frame_material="aluminium", sill=0.9),
        E("win_b", "windows", "slab:back", w=2.6, h=1.6, cols=10, margin=1.5, trim="none", recess=0.5, frame_material="aluminium", sill=0.9),
        E("fins", "pilasters", "slab:front", w=0.35, depth=0.8, cols=11, capital=False),
        E("cant", "block", "slab:floor5", [w * 0.35, -d * 0.2], w=w * 0.3, d=d * 1.4, floors=2, floor_h=fh, plinth_h=0, material=m,
          _offset=[0, 0, -0.02]),
        E("cant_win", "windows", "cant:front", w=w * 0.3 - 2, h=1.2, cols=1, margin=1.0, trim="none", mullions=[6, 0], sill=1.0),
        E("roof", "roof", "slab:top", type="flat", parapet_h=1.0, material="bitumen", gable_material=m),
        E("plant", "box", "roof:ridge", [-w * 0.2, 0], w=8, d=d * 0.5, h=3.5, material=m),
        E("mosaic", "panel", "core:front", ["50%", 0.5], kind="mosaic", w=w * 0.22, h=fh * 1.2,
          subject="soviet modernist mosaic panel, cosmonauts and workers, smalt"),
    ])


@element("factory", "macros", "Industrial plant: brick production hall with sawtooth roof, big factory windows, tall chimney "
         "stack, water tower, loading gates.",
         {"w": P(60.0, ""), "d": P(30.0, ""), "h": P(9.0, ""), "material": P("brick_red", "")}, macro=True, title_ru="Завод / фабрика")
def factory(p, ctx):
    w, d, h, m = p["w"], p["d"], p["h"], p["material"]
    return _part([
        E("hall", "block", w=w, d=d, floors=1, floor_h=h, wall_t=0.6, plinth_h=0.5, material=m),
        E("roof", "roof", "hall:top", type="sawtooth", ridge="x", h=4.0, overhang=0.2, material="bitumen"),
        E("win_f", "windows", "hall:front", kind="segmental", w=3.0, h=4.5, cols=10, rows=1, sill=2.0, trim="simple",
          mullions=[3, 4], frame_material="iron", trim_material="brick_yellow"),
        E("win_b", "windows", "hall:back", kind="segmental", w=3.0, h=4.5, cols=10, rows=1, sill=2.0, trim="simple",
          mullions=[3, 4], frame_material="iron"),
        E("gate", "door", "hall:left", ["50%", 0], w=5, h=5.5, leaf_material="corrugated_metal", trim="simple"),
        E("pil", "pilasters", "hall:front", w=0.8, depth=0.3, cols=11, capital=False),
        E("chimney", "minaret", None, [w / 2 + 4, d / 2 - 4], r=2.2, h=45, shape="round", base_h=4, balconies=0, taper=0.55,
          cap="none", finial="none", material=m),
        E("wt_legs1", "beam", None, None, p0=[-w / 2 - 8.5, -d / 2 + 4, 0], p1=[-w / 2 - 8.5, -d / 2 + 4, 17.6], w=0.5, h=0.5,
          material="steel", _repeat={"count": 2, "step": [0, 5.0, 0]}),
        E("wt_legs2", "beam", None, None, p0=[-w / 2 - 3.5, -d / 2 + 4, 0], p1=[-w / 2 - 3.5, -d / 2 + 4, 17.6], w=0.5, h=0.5,
          material="steel", _repeat={"count": 2, "step": [0, 5.0, 0]}),
        E("wt_tank", "cylinder", None, [-w / 2 - 6, -d / 2 + 6.5, 17.5], r=3.2, h=5, material="steel"),
        E("wt_roof", "cylinder", "wt_tank:top", r=3.3, r_top=0.2, h=1.6, material="steel", _offset=[0, 0, -0.05]),
        E("wt_base", "box", None, [-w / 2 - 6, -d / 2 + 6.5, 16.8], w=7, d=7, h=0.8, material="steel"),
    ])


@element("bunker", "macros", "Military pillbox / bunker: thick chamfered reinforced-concrete casemate with embrasures, "
         "earth berm, rear entrance.",
         {"w": P(7.0, ""), "d": P(6.0, ""), "h": P(2.6, ""), "material": P("concrete_raw", "")}, macro=True, title_ru="ДОТ / бункер")
def bunker(p, ctx):
    w, d, h, m = p["w"], p["d"], p["h"], p["material"]
    c = w * 0.18
    return _part([
        E("body", "block", None, None, poly=[[-w / 2 + c, -d / 2], [w / 2 - c, -d / 2], [w / 2, -d / 2 + c], [w / 2, d / 2],
                                              [-w / 2, d / 2], [-w / 2, -d / 2 + c]],
          floors=1, floor_h=h, wall_t=1.2, plinth_h=0, material=m, _offset=[0, 0, -0.6]),
        E("roof", "roof", "body:top", type="flat", parapet_h=0, overhang=0.35, t=0.6, material=m),
        E("slits", "windows", "body:face0", kind="slit", w=1.2, h=0.25, us=["50%"], vs=[1.3], trim="none", glazed=False, frame=False),
        E("slits2", "windows", "body:face1", kind="slit", w=1.0, h=0.25, us=["50%"], vs=[1.3], trim="none", glazed=False, frame=False),
        E("slits3", "windows", "body:face5", kind="slit", w=1.0, h=0.25, us=["50%"], vs=[1.3], trim="none", glazed=False, frame=False),
        E("door", "door", "body:face3", ["50%", 0.6], w=0.9, h=1.8, leaf_material="steel", trim="none"),
        E("berm", "mound", None, None, w=w + 6, d=d + 6, h=h * 0.6, ring=0.6, material="turf"),
    ])
