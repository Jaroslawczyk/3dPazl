import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pazl.core import elements  # noqa: F401,E402
from pazl.core.builder import build  # noqa: E402
from pazl.core.mesh import export, validate  # noqa: E402
from pazl.core.registry import ELEMENTS  # noqa: E402
from pazl.core.styles import load_styles  # noqa: E402

HOST = {"id": "h", "type": "block", "params": {"w": 12, "d": 9, "floors": 2}}
PLAIN = [n for n, e in ELEMENTS.items() if not e.macro]
MACROS = [n for n, e in ELEMENTS.items() if e.macro]


def recipe_for(etype):
    et = ELEMENTS[etype]
    if et.attach == "face":
        return [HOST, {"id": "x", "type": etype, "on": "h:front"}]
    if et.attach == "top":
        return [HOST, {"id": "x", "type": etype, "on": "h:top"}]
    return [{"id": "x", "type": etype}]


@pytest.mark.parametrize("etype", PLAIN)
def test_every_element_generates(etype):
    res = build({"style": "generic", "elements": recipe_for(etype)})
    assert not res.errors, res.errors
    assert res.elements["x"].solids or res.elements["h"].solids


def style_for(macro):
    for s in load_styles().values():
        if macro in s.get("macros", []) and s["id"] != "generic":
            return s["id"]
    return "generic"


@pytest.mark.parametrize("macro", MACROS)
def test_macro_is_clean(macro):
    res = build({"style": style_for(macro), "elements": [{"id": "b", "type": macro}]})
    rep = validate(res)
    assert rep["ok"], rep["errors"][:5]
    assert rep["watertight"]


def test_lowpoly_is_lighter():
    r = {"style": "russian_orthodox", "elements": [{"id": "b", "type": "orthodox_church"}]}
    hi = build(r, "realistic").final().num_tri()
    lo = build(r, "lowpoly").final().num_tri()
    assert lo < hi * 0.7


def test_floating_detected():
    res = build({"elements": [HOST, {"id": "f", "type": "box", "at": [0, 20, 3]}]})
    rep = validate(res)
    assert not rep["ok"] and "f" in rep["floating"][0]["elements"]


def test_overrides_and_export(tmp_path):
    r = {"style": "russian_wooden", "elements": [{"id": "b", "type": "izba",
                                                   "overrides": {"chimney": {"remove": True}, "roof": {"params": {"pitch": 50}}}}]}
    res = build(r)
    assert "b/chimney" not in res.elements and "b/roof" in res.elements
    out, ntri = export(res.final(), tmp_path / "m.glb", "glb")
    scene = trimesh.load(out)
    assert len(scene.geometry) > 3 and ntri > 1000


def test_random_floors_and_mix():
    r = {"seed": 5, "elements": [{"id": "b", "type": "panel_building", "params": {"floors": {"mix": [5, 9]}, "sections": 4}}]}
    res = build(r)
    floors = [v.params["floors"] for k, v in res.elements.items() if v.type == "block"]
    assert len(floors) == 4 and all(5 <= f <= 9 for f in floors) and len(set(floors)) > 1
    assert floors == [v.params["floors"] for k, v in build(r).elements.items() if v.type == "block"]  # stable per seed
    one = build({"elements": [{"id": "h", "type": "block", "params": {"floors": {"rand": [2, 4]}}}]})
    assert 2 <= one.elements["h"].params["floors"] <= 4
    assert validate(res)["ok"]


def test_style_mix_and_paint():
    from pazl.core.styles import get_style
    st = get_style("gothic+russian_orthodox")
    assert st["materials"]["wall"] == "stone_ashlar" and st["materials"]["cross"] == "gold"
    res = build({"style": "gothic", "elements": [{"id": "h", "type": "house", "colors": {"wall": "#aa3322"}}]})
    from pazl.core.mesh import manifold_to_arrays, tri_materials
    mats, _ = tri_materials(manifold_to_arrays(res.final())[2])
    assert any(m.endswith("#aa3322") for m in mats)


def test_interior_and_overlay_clean():
    r = {"style": "soviet_panel", "elements": [
        {"id": "b", "type": "block", "params": {"w": 30, "d": 12, "floors": 6, "floor_h": 2.8}},
        {"id": "w", "type": "windows", "on": "b:front"},
        {"id": "i", "type": "interior", "on": "b:inner", "params": {"program": "residential"}},
        {"id": "dirt", "type": "weathering", "on": "b:top"},
        {"id": "g", "type": "decal", "on": "b:front", "at": [5, 0.3]}]}
    res = build(r)
    rep = validate(res)
    assert rep["ok"], rep["errors"][:3]
    info = res.elements["i"].info
    assert info["summary"]["elevator"] and info["summary"]["stairs"] == "u" and info["summary"]["rooms"] > 20
    kinds = {d["kind"] for _, d in res.overlay()}
    assert kinds == {"interior", "decal"}
    assert rep["surfaces"]["zfight"] == 0 and rep["surfaces"]["decal_zfight"] == 0


def test_textured_export_has_overlay(tmp_path):
    res = build({"style": "russian_wooden", "elements": [{"id": "b", "type": "izba"}, {"id": "w", "type": "weathering", "on": "b/crib:top"}]})
    out, _ = export(res.final(), tmp_path / "t.glb", "glb", textured=True, result=res)
    scene = trimesh.load(out)
    assert any(k.startswith("overlay|interior_") for k in scene.geometry)
    assert any(k.startswith("overlay|decal_") for k in scene.geometry)


# ---------------------------------------------------------------- doors, bricks, destruction
def test_door_leaf_is_separate_and_opens_inward():
    from pazl.core.mesh import movable_parts
    r = build({"style": "generic", "elements": [{"id": "h", "type": "house"}]})
    parts = movable_parts(r)
    assert len(parts) == 1
    _, eid, V, F, mats, hinge, axis, deg = parts[0]
    assert eid == "h/door" and set(mats) == {"wood_door"}
    a = np.radians(deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    assert (Rz @ (V.mean(0) - hinge) + hinge)[1] > hinge[1]  # front wall at -Y: open leaf goes into the house
    assert validate(r)["ok"]


def test_bricks_mesh_is_watertight_and_keeps_openings():
    import trimesh
    from pazl.core.bricks import brick_mesh, bricks_of
    r = build({"style": "blocky_toy_classic", "elements": [{"id": "h", "type": "game_house"}], "build_mode": "bricks", "brick_size": 0.5})
    V, F, M, E, L = brick_mesh(bricks_of(r), cull=True)
    assert trimesh.Trimesh(V, F, process=True).is_watertight
    full = brick_mesh(bricks_of(r), cull=False)[1]
    assert len(full) == 12 * len(bricks_of(r)["ijk"])  # every brick a full cube when culling is off
    assert "plastic_yellow" in set(M)


def test_fracture_keeps_volume():
    from pazl.core.fracture import fracture_solid
    r = build({"style": "generic", "elements": [{"id": "h", "type": "house"}]})
    f = r.final()
    chunks = fracture_solid(f, 20, seed=3)
    assert len(chunks) >= 20
    assert abs(sum(c[2] for c in chunks) - f.volume()) / f.volume() < 1e-3
