import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pazl.core import geo, vehicles  # noqa: E402
from pazl.core.vehicles import kit  # noqa: E402


def glb_json(path):
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + n])


def area(p):
    T = p.V[p.F]
    return np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2


@pytest.mark.parametrize("kind", list(vehicles.FUNCS))
def test_every_kind_builds_on_the_ground_within_budget(kind):
    low, full = vehicles.build(kind, {"detail": 1}), vehicles.build(kind, {"detail": 3})
    for k in (low, full):
        lo, hi = k.bounds()
        assert abs(lo[2]) < 1e-6 and (hi - lo).min() > 0.3
        assert all(np.isfinite(p.V).all() for p in k.pieces)
    tris = lambda k: sum(len(p.F) for p in k.pieces)  # noqa: E731
    assert tris(low) < tris(full) < 12000


@pytest.mark.parametrize("kind", ["sedan", "bus", "truck_tank", "locomotive", "wagon"])
def test_wheels_stand_on_the_ground(kind):
    k = vehicles.build(kind)
    wheels = [p for p in k.pieces if p.node.startswith("wheel") and p.col == "tyre"]
    assert len(wheels) >= 2
    assert min(p.V[:, 2].min() for p in wheels) == pytest.approx(0, abs=0.01)
    for name, piv in k.pivots.items():
        tyre = next(p for p in wheels if p.node == name)
        assert piv[2] == pytest.approx(tyre.V[:, 2].max() / 2, abs=0.02)  # the pivot is the middle of the wheel


def test_glb_has_one_texture_and_spinning_nodes(tmp_path):
    path = tmp_path / "car.glb"
    info = vehicles.export_glb("taxi", {"text": "А123ВС"}, path)
    j = glb_json(path)
    assert len(j["images"]) == 1 and len(j["materials"]) == 1
    names = {n.get("name"): n for n in j["nodes"]}
    assert {"body", "wheel_0", "wheel_3"} <= set(names)
    assert any(c.startswith("plate:А123ВС") for c in info["decals"])
    x, y, z = names["wheel_0"]["translation"] if "translation" in names["wheel_0"] else names["wheel_0"]["matrix"][12:15]
    assert z > 0.5 and y == pytest.approx(0.33, abs=0.02)  # front axle is towards +Z; the height is the wheel radius, less the flat of a 10-sided tyre


def test_paint_cuts_the_surface_without_changing_it():
    k = kit.Kit({"detail": 2}, None)
    p = k.add(geo.boxc(2, 2, 2), "paint")
    before = area(p)
    q = k.paint(p, "red", x=(0.5, None), z=(0.5, 1.5))
    assert area(p) + area(q) == pytest.approx(before)
    assert q.V[np.unique(q.F)][:, 0].min() == pytest.approx(0.5)


def test_seed_repeats_and_changes_the_model():
    a, b, c = (vehicles.build("sedan", {"seed": s}) for s in (1, 1, 2))
    assert a.colors == b.colors and a.cells == b.cells
    assert a.cells != c.cells


def test_atlas_keeps_strips_and_cells_apart():
    im = kit.atlas({"paint": "#102030"}, ["plate:A1", "hazard"])
    a = np.asarray(im)
    slot = kit.SLOTS["paint"] * kit.STRIP
    at = int((1 - kit.FLAT_T) * kit.BAND)
    assert abs(a[at, slot + 4].astype(int) - (0x10, 0x20, 0x30)).max() <= 3  # flat point of a strip = the colour itself
    assert a[kit.BAND + 10, 10].sum() > 500 and tuple(a[-1, -1]) == (128, 128, 128)


def test_unknown_kind_is_refused():
    with pytest.raises(KeyError):
        vehicles.build("spaceship")
