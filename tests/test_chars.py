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


def test_two_figures_in_one_file_are_found():
    a, b = trimesh.creation.box(extents=(1, 2, 1)), trimesh.creation.box(extents=(1, 2, 1))
    b.apply_translation((5, 0, 0))
    m = trimesh.util.concatenate([a, b])
    assert len(importer.groups(np.asarray(m.vertices), np.asarray(m.faces))) == 2


def test_figures_with_own_materials_are_split_but_head_stays():
    def box(x, y, h):
        m = trimesh.creation.box(extents=(.6, h, .4))
        m.apply_translation((x, y, 0))
        return m
    parts = [box(0, 1, 2), box(.6, 1, 2), box(0, 2.2, .4)]  # two touching bodies, a separate head material
    m = trimesh.util.concatenate(parts)
    M = np.repeat([0, 1, 2], [len(p.vertices) for p in parts])
    g = importer.groups(np.asarray(m.vertices), np.asarray(m.faces), M)
    assert sorted(len(x) for x in g) == [8, 16]


def test_block_body_is_lowpoly_like_a_roblox_avatar():
    """Lesson from a real Roblox avatar (5k triangles, body 2.4k): the block body is built from boxes, not a remeshed field."""
    k, p = body.params_for("roblox")
    m, bones = body.build(k, p, None, 8000)
    assert len(m.faces) < 2600
    for part in m.split(only_watertight=False):
        assert part.is_winding_consistent
    assert m.bounds[0][1] >= 0


def test_roblox_glb_turn_faces_minus_z(tmp_path):
    from pazl.core import roblox
    import json
    t = trimesh.Trimesh([[0, 0, 0], [1, 0, 0], [0, 1, 1]], [[0, 1, 2]])
    f = tmp_path / "m.glb"
    t.export(f)
    roblox._turn_glb(f)
    b = f.read_bytes()
    n = struct.unpack_from("<I", b, 12)[0]
    js = json.loads(b[20:20 + n])
    assert js["nodes"][js["scenes"][0]["nodes"][0]]["rotation"] == [0, 1, 0, 0]
    assert struct.unpack_from("<I", b, 8)[0] == len(b)
    assert abs(trimesh.load(f, force="scene").bounds[0][2] + 1) < 1e-6  # z 1 -> -1


def test_card_hair_and_back_beanie_are_light(tmp_path, monkeypatch):
    """Roblox-like accessories from primitives: spiky card hair under 1k triangles, slouchy beanie under 600."""
    from pazl.core import chars
    monkeypatch.setattr(chars, "CHARS", tmp_path)
    import pazl.core.rig as rig
    monkeypatch.setattr(rig, "RIGS", tmp_path / "rigs", raising=False)
    k, p = body.params_for("roblox")
    m, bones = body.build(k, p, None, 8000)
    names_ = chars_skeleton.order(bones)[0]
    r = {"bones": bones}
    V, F, N = np.asarray(m.vertices), np.asarray(m.faces), np.asarray(m.vertex_normals)
    hair, hb = chars._spiky_hair({}, r, V, F, N, {"kind": "hair_spiky"}, names_)
    hat, _ = chars._slouch_beanie({}, r, V, F, N, {"kind": "beanie_back"}, names_)
    assert sum(len(x.faces) for x, _ in hair) < 1000 and sum(len(x.faces) for x, _ in hat) < 600
    assert hb == names_.index("head")
    top = V[:, 1].max()
    assert max(x.bounds[1][1] for x, _ in hat) > top  # sits on the head
    assert min(x.bounds[0][2] for x, _ in hat) < V[:, 2].min() + .01  # hangs over the back


def test_retopo_shrinkwrap_box_and_bake():
    """1:1 rebuild tools: a grid box pulled onto a reference block keeps its size; baking copies the reference colours."""
    from PIL import Image
    from pazl.core import retopo
    ref = trimesh.creation.box([.4, 1.0, .3])
    m = retopo.shrinkwrap(ref, grow=1.08, box=6)
    assert np.allclose(m.extents, ref.extents, atol=.01) and m.volume > 0
    uv = np.c_[(ref.vertices[:, 0] + .2) / .4, (ref.vertices[:, 1] + .5)]  # left half red, right half blue
    img = Image.new("RGB", (64, 64), (255, 0, 0))
    img.paste((0, 0, 255), (32, 0, 64, 64))
    s = retopo.Sampler(ref, uv, img, count=20000)
    V, F, UV = retopo.unwrap(m)
    tex = np.asarray(retopo.bake(V, F, UV, s, 128))
    assert tex.reshape(-1, 3).max(0)[0] > 200 and tex.reshape(-1, 3).max(0)[2] > 200


def test_retopo_open_side_gets_flat_cap_and_flat_piece_one_layer():
    """Open hem: the bottom stays a flat cap instead of a funnel into the part. Flat lock of hair: one layer, not a slab."""
    from pazl.core import retopo
    box = trimesh.creation.box([.5, .5, .3])
    open_box = box.submesh([np.flatnonzero(box.face_normals[:, 1] > -.5)], append=True)  # no bottom
    m = retopo.shrinkwrap(open_box, grow=1.08, box=6)
    bottom = m.vertices[m.vertices[:, 1] < -.24]
    assert len(bottom) and np.ptp(bottom[:, 1]) < .01  # flat, at the hem
    plate = trimesh.creation.box([.4, .01, .3])
    assert retopo.is_flat(plate)
    s = retopo.sheet(plate, 4)
    assert np.ptp(s.vertices[:, 1]) < .012 and len(s.faces) <= 2 * 4 * 4


def test_loft_part_has_upright_unmirrored_uv_and_packs():
    """R15-style part: a loft with one side strip (front reads left-to-right from outside, top at v = 0) and two caps."""
    from pazl.core import retopo
    m, isl = retopo.loft(np.eye(4), [(1.0, 0, 0, .1, .08), (0.5, 0, 0, .1, .08)], n=12)
    assert m.volume > 0 and len(isl) == 3
    UV = retopo.pack(isl, 256)
    assert UV.min() >= 0 and UV.max() <= 1
    ids, uv, _ = isl[0]
    V = m.vertices[ids]
    front = (V[:, 2] > .07) & (V[:, 1] > .9)
    order = np.argsort(V[front, 0])
    assert np.all(np.diff(UV[ids][front][order, 0]) > 0)  # u grows with +X on the front
    top, bot = UV[ids][V[:, 1] > .9, 1].mean(), UV[ids][V[:, 1] < .6, 1].mean()
    assert top < bot  # glTF: the top of the part is higher in the picture


def test_mesh_check_finds_tear_and_poke_through(tmp_path):
    """A torn sheet over a box: the tear is a hole (nothing passes through it); a box dipping into a shell is poke_through."""
    from pazl.core import meshcheck
    body = trimesh.creation.box([.4, 1.0, .3])
    shirt = trimesh.creation.box([.44, .6, .34])
    shirt = shirt.subdivide().subdivide()
    c = shirt.triangles_center
    tear = (np.abs(c[:, 0]) < .12) & (np.abs(c[:, 1]) < .12) & (c[:, 2] > .16)  # cut a hole in the front
    shirt.update_faces(~tear)
    shirt.remove_unreferenced_vertices()
    sc = trimesh.Scene({"Body": body, "shirt": shirt})
    f = tmp_path / "m.glb"
    sc.export(f)
    r = meshcheck.check(f)
    kinds = [p["kind"] for p in r["problems"]]
    assert "hole" in kinds and r["problems"][kinds.index("hole")]["part"] == "shirt"
    shirt2 = trimesh.creation.box([.44, .6, .34]).subdivide().subdivide()
    v = shirt2.vertices.copy()
    v[(v[:, 2] > .16) & (np.abs(v[:, 1]) < .2) & (np.abs(v[:, 0]) < .15), 2] = .12  # the shirt dips into the body at the front
    shirt2.vertices = v
    sc2 = trimesh.Scene({"Body": body, "shirt": shirt2})
    f2 = tmp_path / "m2.glb"
    sc2.export(f2)
    assert any(p["kind"] == "poke_through" for p in meshcheck.check(f2)["problems"])


def test_push_out_lifts_a_sunk_hat_but_not_hair_cards():
    from pazl.core import meshcheck
    head = trimesh.creation.icosphere(subdivisions=3, radius=.1)
    hat = trimesh.creation.icosphere(subdivisions=2, radius=.1)
    hat.apply_scale([1.0, .6, 1.0])
    hat.apply_translation([0, .06, 0])  # the lower half of the hat is inside the head
    card = trimesh.Trimesh([[0, 0, 0], [.02, .15, 0], [-.02, .15, 0]], [[0, 1, 2]])  # root buried at the centre
    m = trimesh.util.concatenate([hat, card])
    out = meshcheck.push_out_faces(m, head)
    assert not meshcheck._inside(meshcheck._closed(head), out.vertices[:len(hat.vertices)]).any()
    assert np.allclose(out.vertices[len(hat.vertices):], card.vertices)  # cards untouched
