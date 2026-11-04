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
    if wid == "frames":  # one entry per sequence (its first frame), not every frame
        return [{"path": f.relative_to(PROJECTS).as_posix(), "name": s.name, "kb": len(list((s / "key").glob("*.png"))), "seq": s.name}
                for s in sorted(d.iterdir()) if (s / "key").is_dir() for f in sorted((s / "key").glob("*.png"))[:1]]
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


# ---------------------------------------------------------------- 2D: frames workshop
def _seq(name: str):
    import re
    n = re.sub(r"[^\w\-]+", "_", name or "").strip("_")
    if not n:
        raise HTTPException(400, "нужно имя последовательности")
    return PROJECTS / WORKSHOPS["frames"]["dir"] / n


def _rel(p):
    return p.relative_to(PROJECTS).as_posix()


def _save_dataurl(data: str, path):
    import base64
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(data.split(",", 1)[-1]))


@router.get("/frames/seqs")
def frames_seqs():
    from ..core import frames2d as f
    d = PROJECTS / WORKSHOPS["frames"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return [{"name": s.name, "keys": len(f.keys(s)), "frames": len(f.outs(s)), **{k: f.meta(s).get(k) for k in ("fps", "method", "n")}}
            for s in sorted(d.iterdir()) if (s / "key").is_dir()]


@router.get("/frames/seq/{name}")
def frames_seq(name: str):
    from ..core import frames2d as f
    s = _seq(name)
    ks = f.keys(s)
    os_ = f.outs(s)
    m = f.meta(s)
    n = m.get("n", 0) if os_ else 0
    frames = [{"path": _rel(p), "key": (i % (n + 1) == 0) if n else True} for i, p in enumerate(os_ or ks)]
    return {"name": s.name, "fps": m.get("fps", 12), "method": m.get("method"), "pairs": m.get("pairs", []),
            "keys": [_rel(k) for k in ks], "frames": frames}


@router.post("/frames/sample")
async def frames_sample():
    from ..core import frames2d as f
    s = await asyncio.to_thread(f.make_sample, PROJECTS / WORKSHOPS["frames"]["dir"])
    return {"name": s.name}


@router.post("/frames/upload")
def frames_upload(body: dict):
    """body: {seq, files: [{name, data: dataURL}]} -> key/0001.png... (appended, sorted by file name)."""
    s = _seq(body.get("seq"))
    from ..core import frames2d as f
    start = len(f.keys(s))
    for i, fl in enumerate(sorted(body.get("files", []), key=lambda x: x.get("name", ""))):
        _save_dataurl(fl["data"], s / "key" / f"{start + i + 1:04d}.png")
    return {"name": s.name, "keys": len(f.keys(s))}


@router.post("/frames/interpolate")
async def frames_interpolate(body: dict):
    from ..core import frames2d as f
    lin = body.get("lineart")
    try:
        return await asyncio.to_thread(f.interpolate, _seq(body.get("seq")), int(body.get("n", 1)), body.get("method", "flow"),
                                       None if lin in (None, "auto") else bool(lin), body.get("fps"))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))


@router.get("/frames/check/{name}")
async def frames_check(name: str):
    from ..core import frames2d as f
    r = await asyncio.to_thread(f.check, _seq(name))
    r["contact"] = _rel(_seq(name) / "contact.png")
    return r


@router.post("/frames/export")
async def frames_export(body: dict):
    """body: {seq, kind: gif|sheet, fps?, size?, cols?}"""
    from ..core import frames2d as f
    s = _seq(body.get("seq"))
    if body.get("kind") == "sheet":
        r = await asyncio.to_thread(f.export_sheet, s, int(body.get("cols", 0)), body.get("size"))
        return {**r, "path": _rel(s / "sheet.png")}
    p = await asyncio.to_thread(f.export_gif, s, body.get("fps"), body.get("size", 512))
    return {"path": _rel(p)}


# ---------------------------------------------------------------- 2D: sprites workshop
def _spr(path: str):
    p = (PROJECTS / path).resolve()
    if PROJECTS.resolve() not in p.parents or not p.exists():
        raise HTTPException(404, f"нет файла {path}")
    return p


@router.post("/sprites/sample")
def sprites_sample():
    from ..core import sprites
    return {"path": _rel(sprites.make_sample(PROJECTS / WORKSHOPS["sprites"]["dir"]))}


@router.post("/sprites/upload")
def sprites_upload(body: dict):
    """body: {files: [{name, data: dataURL}]} -> projects/sprites/<name>.png"""
    import re
    from PIL import Image
    out = []
    for fl in body.get("files", []):
        n = re.sub(r"[^\w\-]+", "_", fl.get("name", "img").rsplit(".", 1)[0]).strip("_") or "img"
        p = PROJECTS / WORKSHOPS["sprites"]["dir"] / f"{n}.png"
        _save_dataurl(fl["data"], p)
        Image.open(p).convert("RGBA").save(p)
        out.append(_rel(p))
    return {"paths": out}


@router.get("/sprites/info")
def sprites_info(path: str):
    from ..core import sprites
    return sprites.info(_spr(path))


@router.post("/sprites/op")
async def sprites_op(body: dict):
    """body: {path, op: colorkey|trim|pivot|unpack, ...args} (colorkey edits a copy <name>_key.png unless inplace)."""
    from ..core import sprites
    p, op = _spr(body.get("path", "")), body.get("op")
    if op == "colorkey":
        out = p if body.get("inplace") else p.with_name(p.stem.removesuffix("_key") + "_key.png")
        r = await asyncio.to_thread(sprites.colorkey, p, body.get("color", "auto"), float(body.get("tol", .12)), float(body.get("soft", .06)), out)
        return {**r, "path": _rel(out)}
    if op == "trim":
        return {**sprites.trim(p, int(body.get("pad", 1)), body.get("box")), "path": _rel(p)}
    if op == "pivot":
        return {**sprites.set_pivot(p, body.get("x", .5), body.get("y", 1)), "path": _rel(p)}
    if op == "unpack":
        r = await asyncio.to_thread(sprites.unpack, p, p.with_name(p.stem + "_frames"), int(body.get("cols", 0)), int(body.get("rows", 0)))
        return {**r, "dir": _rel(p.with_name(p.stem + "_frames"))}
    raise HTTPException(400, f"unknown op {op}")


@router.post("/sprites/pack")
async def sprites_pack(body: dict):
    """body: {paths: [...], name, cols?, pad?} -> projects/sprites/<name>.png + .json atlas"""
    import re
    from ..core import sprites
    ps = [_spr(x) for x in body.get("paths", [])]
    if not ps:
        raise HTTPException(400, "нет кадров")
    n = re.sub(r"[^\w\-]+", "_", body.get("name") or "sheet").strip("_") or "sheet"
    out = PROJECTS / WORKSHOPS["sprites"]["dir"] / f"{n}.png"
    r = await asyncio.to_thread(sprites.pack, ps, out, int(body.get("cols", 0)), int(body.get("pad", 2)))
    return {**r, "path": _rel(out)}
