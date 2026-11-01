"""HTTP API + WebSocket live feed. Run: python -m pazl.server  (headless)  or  python -m pazl  (with window)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..core.materials import MATS
from ..core.registry import ELEMENTS
from ..core.styles import load_styles, summary as styles_summary
from .chat import Chat
from .project import PROJECTS, ROOT, Project

HOST, PORT = "127.0.0.1", 8765
WEB = ROOT / "web"

app = FastAPI(title="3dPazl building constructor", version=__version__)
_clients: set[WebSocket] = set()
_loop: asyncio.AbstractEventLoop | None = None


def broadcast(ev: dict):
    if not _clients or _loop is None:
        return
    msg = json.dumps(ev, ensure_ascii=False, default=str)

    async def send():
        for ws in list(_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                _clients.discard(ws)
    try:
        asyncio.run_coroutine_threadsafe(send(), _loop)
    except RuntimeError:
        pass


P = Project(broadcast)
CHAT = Chat(broadcast)


@app.on_event("startup")
async def _startup():
    global _loop
    _loop = asyncio.get_running_loop()
    last = sorted(PROJECTS.glob("*/recipe.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    last = [p for p in last if not p.parent.name.startswith("_")]
    if last:
        try:
            P.load(last[0], "system")
        except Exception:
            pass


def _run(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except KeyError as ex:
        raise HTTPException(404, str(ex))
    except Exception as ex:
        raise HTTPException(400, f"{type(ex).__name__}: {ex}")


# ------------------------------------------------------------------ catalog
@app.get("/api/state")
def state():
    return _run(P.summary)


@app.get("/api/guide")
def guide():
    return Response((ROOT / "docs" / "AI_GUIDE.md").read_text("utf-8"), media_type="text/markdown; charset=utf-8")


@app.get("/api/catalog/styles")
def styles():
    return styles_summary()


@app.get("/api/catalog/style/{sid}")
def style(sid: str):
    s = load_styles().get(sid)
    if not s:
        raise HTTPException(404, sid)
    return s


@app.get("/api/catalog/elements")
def elements(category: str | None = None, full: bool = False):
    return [e.schema(full) for e in ELEMENTS.values() if not category or e.category == category]


@app.get("/api/catalog/element/{etype}")
def element(etype: str):
    if etype not in ELEMENTS:
        raise HTTPException(404, f"unknown element {etype}")
    return ELEMENTS[etype].schema(True)


@app.get("/api/catalog/materials")
def materials():
    return {k: {"color": v.get("color"), "prompt": v.get("prompt")} for k, v in MATS.lib.items()}


# ------------------------------------------------------------------ project
@app.get("/api/recipe")
def recipe():
    return P.recipe


@app.get("/api/projects")
def projects():
    return sorted(p.parent.name for p in PROJECTS.glob("*/recipe.json") if not p.parent.name.startswith("_"))


@app.post("/api/new")
def new(body: dict = Body(...), x_agent: str = Header("user")):
    return _run(P.new, body.get("name", "untitled"), body.get("style", "generic"), body.get("detail", "realistic"),
                body.get("elements"), x_agent, body.get("recipe"))


@app.post("/api/load")
def load(body: dict = Body(...), x_agent: str = Header("user")):
    return _run(P.load, body.get("path") or body.get("name"), x_agent)


@app.post("/api/save")
def save(body: dict = Body(default={})):
    return {"path": _run(P.save, body.get("path"))}


@app.post("/api/patch")
def patch(body: dict = Body(...), x_agent: str = Header("user")):
    out = _run(P.patch, body.get("ops", []), x_agent, body.get("note", ""))
    if "error" in out:
        raise HTTPException(400, out["error"])
    return out


@app.post("/api/undo")
def undo(x_agent: str = Header("user")):
    return _run(P.undo, x_agent)


@app.post("/api/redo")
def redo(x_agent: str = Header("user")):
    return _run(P.redo, x_agent)


@app.get("/api/tree")
def tree():
    return _run(P.tree)


@app.get("/api/element/{eid:path}")
def element_src(eid: str):
    r = P.result().elements.get(eid)
    if r is None:
        raise HTTPException(404, eid)
    return {"src": r.src, "error": r.error, "host": r.host, "in_recipe": any(e["id"] == eid for e in P.recipe["elements"]),
            "info": r.info, "params": r.params, "faces": sorted(k for k, a in r.anchors.items() if a.kind == "face")}


@app.get("/api/floorplan")
def floorplan(id: str | None = None):
    return _run(P.floorplan, id)


@app.get("/api/catalog/periods")
def periods():
    from ..core.styles import PERIODS, REGIONS
    return {"periods": [{"id": a, "name_ru": b, "from": c, "to": d} for a, b, c, d in PERIODS], "regions": REGIONS}


@app.post("/api/textures/download")
def tex_download(body: dict = Body(default={}), x_agent: str = Header("user")):
    """Download CC0 PBR packs (ambientCG) for the project's materials (which="project"), all, or a list. Runs in background."""
    import threading
    threading.Thread(target=P.download_textures, args=(body.get("which", "project"), body.get("res", "1K"), x_agent),
                     daemon=True).start()
    return {"started": True}


@app.get("/api/textures/available")
def tex_available():
    from ..core.materials import TEX_LIB
    out: dict[str, list] = {}
    for f in TEX_LIB.glob("*_*.*"):
        base, _, kind = f.stem.rpartition("_")
        if kind in ("albedo", "normal", "roughness", "ao", "height", "metal"):
            out.setdefault(base, []).append(kind)
    return out


@app.get("/tex/{name}/{kind}")
def tex_file(name: str, kind: str):
    """Texture map for the viewer: albedo|normal|roughness|ao|height of a material, or a decal/interior picture."""
    from ..core.decals import ensure_all, file_for
    f = file_for(name)
    if f is not None:
        ensure_all()
        if f.exists():
            return FileResponse(f)
    found = MATS.texture_files(name, P.tex_dir)
    if kind in found:
        return FileResponse(found[kind])
    raise HTTPException(404, "no texture")


@app.get("/api/anchors/{eid:path}")
def anchors(eid: str):
    return _run(P.anchors, eid)


@app.post("/api/validate")
def validate(x_agent: str = Header("user")):
    return _run(P.validate, x_agent)


@app.post("/api/render")
def render(body: dict = Body(default={}), x_agent: str = Header("user")):
    tile = tuple(body.get("tile") or (384, 288))
    return _run(P.render, body.get("views"), x_agent, tile, body.get("custom"))


@app.get("/api/render/latest.png")
def latest_png():
    if not P.last_render:
        raise HTTPException(404, "no render yet")
    return FileResponse(P.last_render["path"])


@app.get("/api/preview.glb")
def preview_glb():
    return Response(_run(P.preview_glb), media_type="model/gltf-binary")


@app.get("/api/model.glb")
def model_glb():
    return Response(_run(P.model_glb), media_type="model/gltf-binary")


@app.post("/api/export")
def export(body: dict = Body(default={}), x_agent: str = Header("user")):
    return _run(P.export, body.get("format", "glb"), body.get("lod_tris"), body.get("force", False), x_agent, body.get("path"))


@app.post("/api/textures/manifest")
def tex_manifest(x_agent: str = Header("user")):
    return _run(P.texture_manifest, x_agent)


@app.post("/api/textures/apply")
def tex_apply(x_agent: str = Header("user")):
    P.event("textures", x_agent, "textures applied (welded view reloads)")
    return {"ok": True, "have": {m["slot"]: m["have"] for m in P.texture_manifest(x_agent)["materials"]}}


@app.post("/api/camera")
def camera(body: dict = Body(...), x_agent: str = Header("user")):
    """An agent can show the user where it is looking: {az, el, dist?, target?}."""
    P.event("camera", x_agent, body.get("note", ""), camera=body)
    return {"ok": True}


@app.post("/api/note")
def note(body: dict = Body(...), x_agent: str = Header("user")):
    """Free-text progress message shown in the live log (what the AI is doing / planning)."""
    P.event("note", x_agent, body.get("text", ""))
    return {"ok": True}


@app.get("/api/log")
def log(since: float = 0):
    return [e for e in P.log if e["t"] > since]


# ------------------------------------------------------------------ live + static
# ------------------------------------------------------------------ AI chat (any provider, same tools as MCP)
@app.get("/api/chat")
def chat_state():
    return CHAT.state()


@app.post("/api/chat")
def chat_send(body: dict = Body(...)):
    try:
        CHAT.send(str(body.get("text", "")))
    except (RuntimeError, ValueError) as ex:
        raise HTTPException(409, str(ex))
    return {"ok": True}


@app.post("/api/chat/settings")
def chat_settings(body: dict = Body(...)):
    return CHAT.save_settings(body)


@app.post("/api/chat/stop")
def chat_stop():
    CHAT.stop()
    return {"ok": True}


@app.post("/api/chat/reset")
def chat_reset():
    try:
        CHAT.reset()
    except RuntimeError as ex:
        raise HTTPException(409, str(ex))
    return {"ok": True}


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    _clients.add(sock)
    try:
        await sock.send_text(json.dumps({"type": "hello", "state": P.summary()}, default=str))
        while True:
            await sock.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(sock)


PROJECTS.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory=str(PROJECTS)), name="files")
app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")


def serve(host=HOST, port=PORT):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")
