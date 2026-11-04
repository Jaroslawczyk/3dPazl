import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pazl.core import skins  # noqa: E402
from pazl.core.chars import body, cloth  # noqa: E402
from pazl.core.chars.field import Grid, ellipsoid, surface_nets  # noqa: E402


def test_surface_nets_closed_sphere():
    g = Grid((-1.2, -1.2, -1.2), (1.2, 1.2, 1.2), .1)
    f = g.empty()
    ellipsoid(g, f, (0, 0, 0), (1, 1, 1))
    m = trimesh.Trimesh(*surface_nets(f, g.lo, g.cell), process=False)
    assert m.is_watertight and m.is_winding_consistent
    assert abs(abs(m.volume) - 4.19) < .2


@pytest.mark.parametrize("preset", list(body.PRESETS))
def test_body_is_one_skin_on_the_ground(preset):
    kind, p = body.params_for(preset)
    m, bones = body.build(kind, p, cell=float(p["height"]) * .02)
    assert len(m.split(only_watertight=False)) <= 3  # skin + two eyes
    assert abs(m.bounds[0][1]) < .02 and bones


@pytest.mark.parametrize("kind", ["tshirt", "pants", "dress", "hair_short", "wrap"])
def test_same_garment_fits_different_bodies(kind):
    sizes = []
    for preset in ("man", "chubby"):
        k, p = body.params_for(preset)
        m, bones = body.build(k, p, cell=.02)
        fit = cloth.Fit(np.asarray(m.vertices), m.faces, np.asarray(m.vertex_normals), bones)
        V, F, _ = cloth.make(fit, kind, {}, "humanoid")
        assert len(F) > 100
        sizes.append(np.ptp(V, 0))
    assert not np.allclose(sizes[0], sizes[1])


def test_quality_limits_triangles_and_blocky_wears_clothes():
    k, p = body.params_for("blocky")
    m, bones = body.build(k, p, target=1500)
    assert len(m.faces) < 3500  # 1500 + two eyes
    fit = cloth.Fit(np.asarray(m.vertices), m.faces, np.asarray(m.vertex_normals), bones)
    V, F, _ = cloth.make(fit, "tshirt", {}, "humanoid", 800)
    assert 100 < len(F) <= 900


def test_wrong_skeleton_is_refused():
    k, p = body.params_for("dog")
    m, bones = body.build(k, p, cell=.02)
    fit = cloth.Fit(np.asarray(m.vertices), m.faces, np.asarray(m.vertex_normals), bones)
    with pytest.raises(ValueError):
        cloth.make(fit, "pants", {}, "quadruped")


@pytest.mark.parametrize("pattern", [k for k in skins.PATTERNS if k != "image"])
def test_patterns_render(pattern):
    a = skins.tile_array({"pattern": pattern, "colors": ["#102030", "#a0b0c0", "#ff0000"]})
    assert a.shape == (skins.N, skins.N, 3) and np.isfinite(a).all()


def test_box_uv_keeps_shape():
    m = trimesh.creation.box()
    idx, F, uv = skins.box_uv(np.asarray(m.vertices), np.asarray(m.faces), .5)
    assert len(F) == len(m.faces) and len(idx) == len(uv) and len(idx) > 8
