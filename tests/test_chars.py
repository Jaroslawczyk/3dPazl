import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pazl.core import skins  # noqa: E402
from pazl.core.rig import skeleton as chars_skeleton  # noqa: E402
from pazl.core.chars import body, cloth, importer  # noqa: E402
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
    assert kind == "blocky" or len(m.split(only_watertight=False)) <= 3  # skin + two eyes
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


def _fbx_node(name, props=b"", n=0, kids=b"", at=0):
    """Serialise one binary FBX node (version 7400) placed at offset `at`."""
    nm = name.encode()
    head = 13 + len(nm)
    body = props + kids
    if kids:
        body += b"\0" * 13
    return struct.pack("<IIIB", at + head + len(body), n, len(props), len(nm)) + nm + body


def _nested(name, props, n, children, at):
    head = 13 + len(name) + len(props)
    kids, o = b"", at + head
    for c in children:
        k = c(o)
        kids += k
        o += len(k)
    return _fbx_node(name, props, n, kids, at)


def _arr(t, a):
    raw = zlib.compress(a.tobytes())
    return t + struct.pack("<III", len(a), 1, len(raw)) + raw


def _s(x):
    return b"S" + struct.pack("<I", len(x)) + x


def test_binary_fbx_with_compressed_arrays_and_node_offset():
    V = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    I = np.array([0, 1, 2, ~3], np.int32)
    L = lambda v: b"L" + struct.pack("<q", v)  # noqa: E731
    D = lambda v: b"D" + struct.pack("<d", v)  # noqa: E731
    geo = lambda o: _nested("Geometry", L(1) + _s(b"g") + _s(b"Mesh"), 3, [lambda q: _fbx_node("Vertices", _arr(b"d", V.ravel()), 1, at=q), lambda q: _fbx_node("PolygonVertexIndex", _arr(b"i", I), 1, at=q)], o)  # noqa: E731
    model = lambda o: _nested("Model", L(2) + _s(b"m") + _s(b"Mesh"), 3, [lambda q: _nested("Properties70", b"", 0, [lambda r: _fbx_node("P", _s(b"Lcl Translation") + _s(b"") + _s(b"") + _s(b"A") + D(5) + D(0) + D(0), 7, at=r)], q)], o)  # noqa: E731
    con = lambda o: _nested("Connections", b"", 0, [lambda q: _fbx_node("C", _s(b"OO") + L(1) + L(2), 3, at=q)], o)  # noqa: E731
    data = b"Kaydara FBX Binary  \0\x1a\0" + struct.pack("<I", 7400)
    k = _nested("Objects", b"", 0, [geo, model], len(data))
    data += k
    data += con(len(data)) + b"\0" * 13
    Vo, F, C = importer.read_fbx(data)
    assert len(F) == 2 and np.allclose(Vo[:, 0].min(), .05)  # moved by the node, centimetres to metres


def test_obj_import_makes_standing_model_of_given_height():
    obj = b"v 0 0 0\nv 2 0 0\nv 0 0 4\nv 0 2 0\nf 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n"
    r = importer.convert({"t_imp.obj": obj}, "_t_imp", 1.8, "z")
    try:
        m = trimesh.load(importer.PROJECTS / r["src"], force="mesh")
        assert abs(m.bounds[0][1]) < 1e-4 and abs(m.bounds[1][1] - 1.8) < 1e-3
    finally:
        (importer.PROJECTS / r["src"]).unlink()


def test_block_body_with_lowered_arms_is_straightened_and_measured():
    def block(c, s):
        m = trimesh.creation.box(extents=s)
        m.apply_translation(c)
        return m
    m = trimesh.util.concatenate([block((0, 1.5, 0), (.4, .4, .4)), block((0, 1, 0), (.6, .6, .3)), block((.45, 1, 0), (.3, .6, .3)),
                                  block((-.45, 1, 0), (.3, .6, .3)), block((.15, .35, 0), (.3, .7, .3)), block((-.15, .35, 0), (.3, .7, .3))])
    V, crotch, _ = importer.straighten(np.asarray(m.vertices), np.asarray(m.faces))
    assert abs(crotch - .7) < 1e-6 and V[:, 0].max() > .85  # arms went out from .6 to .9
    b = {x["name"]: x for x in body.fit_tpose(trimesh.sample.sample_surface(trimesh.Trimesh(V, m.faces, process=False), 40000, seed=1)[0], crotch)}
    assert abs(b["hips"]["head"][1] - .7) < .01 and abs(b["shoulder.L"]["head"][0] - .3) < .03 and abs(b["upper_arm.L"]["head"][0] - .45) < .03 and b["head"]["head"][1] < 1.45


def test_classic_template_and_r6_rest_pose():
    from pazl.core import roblox
    from pazl.core.rig import anim
    a = roblox.classic([{"kind": "tshirt", "color": "#ff0000"}, {"kind": "pants", "color": "#0000ff"}], "humanoid", 1.6)
    assert a["shirt"].shape == (559, 585, 4)
    assert a["shirt"][130, 300, 0] == 255 and a["shirt"][360, 50, 3] == 255 and a["shirt"][470, 50, 3] == 0  # torso, sleeve top, bare forearm
    assert a["pants"][470, 50, 2] == 255
    k, p = body.params_for("blocky")
    _, bones = body.build(k, p, cell=.03)
    clip = anim.make(bones, "idle")
    poses, _ = roblox.r6_poses(bones, clip, 0)
    for n in ("Left Arm", "Right Arm", "Left Leg", "Head"):  # idle arms hang down = almost the R6 rest pose
        assert np.trace(poses[n]) > 2.2, n


def test_block_garment_is_a_closed_shell_per_block():
    k, p = body.params_for("blocky")
    m, bones = body.build(k, p, cell=.015)
    names = chars_skeleton.order(bones)[0]
    fit = cloth.Fit(np.asarray(m.vertices), m.faces, np.asarray(m.vertex_normals), bones, names)
    V, F, N, L = cloth.make_blocks(fit, "longsleeve", {}, "humanoid")
    assert {names[i] for i in np.unique(L)} >= {"chest", "upper_arm.L", "upper_arm.R"}
    assert (L[F] == L[F[:, :1]]).all()  # no triangle spans two blocks, so none can stretch
    tw = next(b for b in bones if b["name"] == "shoulder.L")["head"][0]
    side = V[(L == names.index("chest")) & (V[:, 1] > bones[0]["tail"][1])]
    assert side[:, 0].max() > tw  # the torso piece has its own side wall under the arm
