import sys
from pathlib import Path

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
