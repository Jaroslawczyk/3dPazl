"""HTTP API + WebSocket live feed. Run: python -m pazl.server  (headless)  or  python -m pazl  (with window)."""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..core.materials import MATS
from ..core.registry import ELEMENTS
from ..core.styles import load_styles, summary as styles_summary
from .chat import Chat, usage_total
from . import library as LIB
from .logs import log, log_exception, report_zip
from .project import PROJECTS, ROOT, Project
from .workshops import router as workshops_router

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
CHAT = Chat(broadcast, P)


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
    except PermissionError as ex:
        log("refused", where=getattr(fn, "__name__", "?"), error=str(ex))
        raise HTTPException(403, str(ex))
    except Exception as ex:
        log_exception(getattr(fn, "__name__", "?"), ex)
        raise HTTPException(400, f"{type(ex).__name__}: {ex}")


# ------------------------------------------------------------------ catalog
@app.get("/api/about")
def about():
    from .. import __author__, __copyright__, __email__, __license__
    lic = ROOT / "LICENSE"
    return {"name": "3dPazl", "version": __version__, "author": __author__, "email": __email__, "license": __license__,
            "copyright": __copyright__, "license_text": lic.read_text("utf-8") if lic.exists() else ""}


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
def tree(compact: bool = False, root: str = "", depth: int = 99):
    """compact=1 -> indented text outline (few tokens): runs of same-type siblings named like awL0..awL5 fold
    into one line `awL0..5 hull x6`; `root` limits it to one subtree, `depth` to N levels."""
    items = _run(P.tree)
    return Response(tree_outline(items, root, depth), media_type="text/plain") if compact else items


def tree_outline(items, root="", depth=99) -> str:
    kids: dict[str, list] = {}
    for t in items:
        kids.setdefault(t.get("host") or "", []).append(t)
    out: list[str] = []

    def walk(parent, lvl):
        if lvl >= depth:
            return
        rows = kids.get(parent, [])
        i = 0
        while i < len(rows):
            t = rows[i]
            short = t["id"].split("/")[-1]
            m = re.fullmatch(r"(.*?)(\d+)", short)
            j = i + 1
            if m and t["id"] not in kids:  # fold leaf runs with the same prefix and type
                while j < len(rows) and rows[j]["type"] == t["type"] and rows[j]["id"] not in kids \
                        and re.fullmatch(re.escape(m.group(1)) + r"\d+", rows[j]["id"].split("/")[-1]):
                    j += 1
            pad = "  " * lvl
            if j - i > 1:
                last = rows[j - 1]["id"].split("/")[-1][len(m.group(1)):]
                out.append(f"{pad}{short}..{last} {t['type']} x{j - i}")
            else:
                err = f" !{t['error']}" if t.get("error") else ""
                more = f" (+{_count(t['id'])})" if lvl + 1 >= depth and t["id"] in kids else ""
                out.append(f"{pad}{short} {t['type']}{more}{err}")
                walk(t["id"], lvl + 1)
            i = j

    def _count(eid):
        return sum(1 + _count(c["id"]) for c in kids.get(eid, []))

    walk(root, 0)
    return "\n".join(out)


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


@app.get("/api/fracture.glb")
def fracture_glb():
    return Response(_run(P.fracture_glb), media_type="model/gltf-binary")


@app.get("/api/preview.glb")
def preview_glb():
    return Response(_run(P.preview_glb), media_type="model/gltf-binary")


@app.get("/api/model.glb")
def model_glb():
    return Response(_run(P.model_glb), media_type="model/gltf-binary")


@app.post("/api/export")
def export(body: dict = Body(default={}), x_agent: str = Header("user")):
    return _run(P.export, body.get("format", "glb"), body.get("lod_tris"), body.get("force", False), x_agent, body.get("path"),
                body.get("only"))


@app.post("/api/export/open")
def export_open():
    """Open the project's export folder in the file manager (desktop app)."""
    import os
    import subprocess
    d = P.dir / "export"
    d.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(d)  # noqa: S606 - our own folder
    else:
        subprocess.Popen(["xdg-open", str(d)])
    return {"path": str(d)}


@app.get("/api/autosaves")
def autosaves():
    return _run(P.autosaves)


@app.post("/api/autosaves/restore")
def autosave_restore(body: dict = Body(...), x_agent: str = Header("user")):
    return _run(P.restore_autosave, body.get("file", ""), x_agent)


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
        CHAT.send(str(body.get("text", "")), scope=body.get("scope"), image=body.get("image"))
    except (RuntimeError, ValueError) as ex:
        raise HTTPException(409, str(ex))
    return {"ok": True}


@app.post("/api/chat/settings")
def chat_settings(body: dict = Body(...)):
    return CHAT.save_settings(body)


def _usage():
    f = P.dir / "usage.json"
    try:
        data = json.loads(f.read_text("utf-8"))
    except (OSError, ValueError):
        data = {"runs": []}
    data["total"] = usage_total(data.get("runs", []))
    return data


# ------------------------------------------------------------------ my elements (shared between projects)
@app.get("/api/library")
def library_list():
    return _run(LIB.listing)


@app.post("/api/library/save")
def library_save(body: dict = Body(...), x_agent: str = Header("user")):
    out = _run(LIB.save, P, body["element"], body.get("name", ""), body.get("category", ""), body.get("description", ""))
    P.event("library", x_agent, f"saved {body['element']} as '{out['name']}' ({out['category']})")
    return out


@app.post("/api/library/insert")
def library_insert(body: dict = Body(...), x_agent: str = Header("user")):
    ops, new_id = _run(LIB.insert_ops, P, body["id"], body.get("on", ""), body.get("at"), body.get("rot", 0))
    out = _run(P.patch, ops, x_agent, f"+{new_id} from my elements")
    if "error" in out:
        raise HTTPException(400, out["error"])
    return {**out, "id": new_id}


@app.post("/api/library/update")
def library_update(body: dict = Body(...)):
    return _run(LIB.update, body["id"], name=body.get("name"), category=body.get("category"), description=body.get("description"))


@app.post("/api/library/delete")
def library_delete(body: dict = Body(...)):
    return _run(LIB.delete, body["id"])


@app.get("/my_library/{name}")
def library_thumb(name: str):
    f = LIB.LIB / Path(name).name
    if not f.exists() or f.suffix != ".png":
        raise HTTPException(404, name)
    return FileResponse(f)


@app.get("/api/measure")
def measure(eid: str = ""):
    return _run(P.measure, eid)


@app.get("/api/usage")
def usage():
    d = _usage()
    return {"total": d["total"], "runs": d["runs"][-50:]}


@app.get("/api/report.zip")
def report():
    name = f"3dpazl_report_{time.strftime('%Y%m%d_%H%M')}.zip"
    return Response(report_zip(P, _usage()), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/api/report/save")
def report_save():
    """Write the report ZIP next to the logs and open the folder (works in the desktop window too)."""
    import os
    import subprocess
    from .logs import LOG_DIR
    d = LOG_DIR.parent / "reports"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"3dpazl_report_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    f.write_bytes(report_zip(P, _usage()))
    if os.name == "nt":
        subprocess.Popen(["explorer", "/select,", str(f)])
    return {"path": str(f)}


@app.post("/api/log")
def client_log(body: dict = Body(...)):
    log("client_error", **{k: str(v)[:4000] for k, v in body.items()})
    return {"ok": True}


@app.get("/api/chat/account")
def chat_account(provider: str):
    return CHAT.account(provider)


@app.post("/api/chat/console")
def chat_console(body: dict = Body(...)):
    try:
        return CHAT.open_console(body["provider"], body.get("what", "login"))
    except (KeyError, RuntimeError) as ex:
        raise HTTPException(400, str(ex))


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


@app.get("/api/glbs")
def list_glbs():
    """Every .glb under projects/ (script-built models, references, exports) for the viewer."""
    out = []
    for p in sorted(PROJECTS.rglob("*.glb")):
        rel = p.relative_to(PROJECTS).as_posix()
        if rel.startswith(("_", "gallery/")) or "/_" in rel or "_lod" in rel:   # tests, gallery copies, LODs
            continue
        out.append({"path": rel, "mb": round(p.stat().st_size / 1e6, 1), "ref": p.name.startswith("ref") or p.name.endswith("_v3.glb")})
    out.sort(key=lambda g: (g["ref"], g["path"]))                                # my models first, references after
    return out


PROJECTS.mkdir(exist_ok=True)
app.include_router(workshops_router)
app.mount("/files", StaticFiles(directory=str(PROJECTS)), name="files")
app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")


def serve(host=HOST, port=PORT):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")
