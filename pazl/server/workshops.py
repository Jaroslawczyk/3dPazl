"""Workshops: separate workspaces of the app next to the building constructor. Each keeps its models in its own
folder under projects/ and has its own UI module in web/ws/<id>.js. Shared endpoints live here; each workshop
adds its own under /api/ws/<id>/..."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..core import blender
from .project import PROJECTS

WORKSHOPS = {
    "items": {"title": "Предметы", "dir": "items",
              "about": "Мелкие объекты и декали: посуда, еда, книги, инструменты, мелочи для интерьера."},
    "clothes": {"title": "Одежда", "dir": "clothes",
                "about": "Одежда для разных персонажей: подгонка под тело, слои, ткань."},
    "rig": {"title": "Риг и анимация", "dir": "rigs",
            "about": "Кости, веса, анимации и проверка движения: пересечения, растяжения, реалистичность."},
    # ---- 2D
    "frames": {"title": "Кадры и анимация", "dir": "frames2d", "dim": "2d",
               "about": "Рисованная 2D-анимация: ключевые кадры, промежуточные кадры (интерполяция), калька, раскраска скетчей."},
    "sprites": {"title": "Спрайты", "dir": "sprites", "dim": "2d",
                "about": "2D-объекты для игр: спрайты, листы анимации (sprite sheets), иконки, декали."},
}
router = APIRouter(prefix="/api/ws")


@router.get("")
def workshops():
    return [{"id": k, "title": v["title"], "about": v["about"], "dir": v["dir"], "dim": v.get("dim", "3d")} for k, v in WORKSHOPS.items()]


@router.get("/blender")
async def blender_info():
    return await asyncio.to_thread(blender.info)


@router.get("/{wid}/models")
def models(wid: str):
    """GLB files of a workshop (paths relative to projects/, viewable via /files/...)."""
    if wid not in WORKSHOPS:
        raise HTTPException(404, f"unknown workshop {wid}")
    d = PROJECTS / WORKSHOPS[wid]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return [{"path": p.relative_to(PROJECTS).as_posix(), "name": p.stem, "kb": round(p.stat().st_size / 1e3)}
            for p in sorted(d.rglob("*.png" if WORKSHOPS[wid].get("dim") == "2d" else "*.glb"))]


# ---------------------------------------------------------------- items workshop
@router.get("/items/kinds")
def item_kinds():
    from ..core import items
    return items.catalog()


@router.post("/items/make")
async def item_make(body: dict):
    """body: {kind, name?, params: {size, width, height, seed, seg, color}} -> builds projects/items/<name>.glb."""
    import re
    from ..core import items
    kind = body.get("kind", "")
    if kind not in items.FUNCS:
        raise HTTPException(400, f"unknown item kind {kind}")
    name = re.sub(r"[^\w\-]+", "_", body.get("name") or kind).strip("_") or kind
    path = PROJECTS / WORKSHOPS["items"]["dir"] / f"{name}.glb"
    info = await asyncio.to_thread(items.export_glb, kind, body.get("params") or {}, path)
    return {**info, "path": path.relative_to(PROJECTS).as_posix()}


# ---------------------------------------------------------------- rig & animation workshop (native, no Blender)
def _rig_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (FileNotFoundError, KeyError, ValueError) as e:
        raise HTTPException(400, str(e).strip("'\""))


@router.get("/rig/templates")
def rig_templates():
    from ..core import rig
    return {"templates": {k: v[0] for k, v in rig.skeleton.TEMPLATES.items()}, "presets": rig.anim.PRESETS,
            "rigs": sorted(p.name[:-9] for p in rig.RIGS.glob("*.rig.json")) if rig.RIGS.exists() else []}


@router.post("/rig/mannequin")
async def rig_mannequin(body: dict):
    from ..core import rig
    return await asyncio.to_thread(rig.mannequin, body.get("name") or "mannequin", float(body.get("height") or 1.8))


@router.get("/rig/get/{name}")
def rig_get(name: str):
    from ..core import rig
    r = _rig_call(rig.load, name)
    return {"name": r["name"], "src": r["src"], "template": r["template"], "bones": r["bones"],
            "clips": {k: {"frames": c["frames"], "fps": c["fps"], "edited": c.get("edited", False)} for k, c in r["clips"].items()}}


@router.post("/rig/auto")
async def rig_auto(body: dict):
    """body: {name, src (path under projects/), template} -> skeleton fitted to the mesh."""
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.auto, body.get("name") or "rig", body["src"], body.get("template") or "humanoid")


@router.post("/rig/bones")
async def rig_bones(body: dict):
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.set_bones, body["name"], body.get("bones") or [])


@router.post("/rig/weights")
async def rig_weights(body: dict):
    from ..core import rig
    _, _, st = await asyncio.to_thread(_rig_call, rig.weights, body["name"], True)
    return st


@router.post("/rig/anim")
async def rig_anim(body: dict):
    """body: {name, preset, clip?, frames?, fps?}"""
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.make_anim, body["name"], body.get("preset") or "walk",
                                   body.get("clip") or "", body.get("frames"), int(body.get("fps") or 30))


@router.post("/rig/key")
async def rig_key(body: dict):
    """body: {name, clip, bone, frame, euler:[x,y,z] degrees, span?}"""
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.set_key, body["name"], body["clip"], body["bone"], body["frame"],
                                   body["euler"], int(body.get("span", 4)))


@router.post("/rig/check")
async def rig_check(body: dict):
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.run_check, body["name"], body["clip"], int(body.get("samples") or 24))


@router.post("/rig/export")
async def rig_export(body: dict):
    from ..core import rig
    return await asyncio.to_thread(_rig_call, rig.export, body["name"])
