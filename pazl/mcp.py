"""MCP server (stdio) for Claude Code / Cursor / any MCP client. Thin wrapper over the HTTP API.
Starts the app (window) automatically if it is not running; set PAZL_HEADLESS=1 to start it without a window.

    python -m pazl.mcp
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import logging

import httpx
try:  # mcp >= 2
    from mcp.server.mcpserver import Image, MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP, Image

logging.getLogger("httpx").setLevel(logging.WARNING)

BASE = os.environ.get("PAZL_URL", "http://127.0.0.1:8765")
AGENT = os.environ.get("PAZL_AGENT", "claude")
ROOT = Path(__file__).resolve().parent.parent

mcp = FastMCP("pazl", instructions=(
    "3dPazl building constructor. Read `guide` once per session. Workflow: new_building (macro or blocks) -> patch -> "
    "validate -> render_views (ONE contact-sheet image: sides, isometric, eye-level, top, below, a section and two floor plans; red = problems) -> fix -> export. "
    "Ids inside macros look like 'b/roof' and can be patched directly. Use note() to tell the user what you are doing."))


TOOLS: dict = {}  # name -> function: the in-app AI chat (pazl.server.chat) offers the very same tools to any AI


def tool(fn):
    TOOLS[fn.__name__] = fn
    mcp.tool()(fn)
    return fn


def _ensure():
    try:
        httpx.get(BASE + "/api/state", timeout=2)
        return
    except Exception:
        pass
    args = [sys.executable, "-m", "pazl.server" if os.environ.get("PAZL_HEADLESS") else "pazl"]
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen(args, cwd=str(ROOT), creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(150):
        time.sleep(0.2)
        try:
            httpx.get(BASE + "/api/state", timeout=1)
            return
        except Exception:
            pass
    raise RuntimeError("3dPazl server did not start")


def _call(method, path, body=None, raw=False):
    _ensure()
    r = httpx.request(method, BASE + path, json=body, headers={"X-Agent": AGENT}, timeout=300)
    if r.status_code >= 400:
        try:
            return {"error": r.json().get("detail", r.text)}
        except Exception:
            return {"error": r.text}
    return r.content if raw else r.json()


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), default=str)


@tool
def guide() -> str:
    """How to build with 3dPazl: recipe format, anchors, workflow, tips. Read once."""
    return (ROOT / "docs" / "AI_GUIDE.md").read_text("utf-8")


@tool
def list_styles() -> str:
    """Architectural styles with era/region, recommended macros and tips."""
    return _j(_call("GET", "/api/catalog/styles"))


@tool
def list_elements(category: str = "") -> str:
    """Element types (compact). Categories: structure, openings, roofs, columns, decor, primitive, macros."""
    els = _call("GET", "/api/catalog/elements" + (f"?category={category}" if category else ""))
    return "\n".join(f"{e['type']} [{e['category']}{', macro' if e['macro'] else ''}; attach={e['attach']}]: {e['desc']}"
                     for e in els)


@tool
def describe_element(type: str) -> str:
    """Full param schema (defaults, choices) and anchors of one element type."""
    return _j(_call("GET", f"/api/catalog/element/{type}"))


@tool
def new_building(name: str, style: str = "generic", detail: str = "realistic", elements: list | None = None) -> str:
    """Start a new project. detail: realistic | lowpoly. elements: list of recipe elements (may be one macro)."""
    return _j(_call("POST", "/api/new", {"name": name, "style": style, "detail": detail, "elements": elements or []}))


@tool
def load_project(name: str) -> str:
    """Open a saved project by name."""
    return _j(_call("POST", "/api/load", {"name": name}))


@tool
def list_projects() -> str:
    return _j(_call("GET", "/api/projects"))


@tool
def get_recipe() -> str:
    """Current recipe JSON (source of truth)."""
    return _j(_call("GET", "/api/recipe"))


@tool
def tree() -> str:
    """Built elements (incl. macro children) with host, errors and anchor names."""
    return _j(_call("GET", "/api/tree"))


@tool
def anchors(element_id: str) -> str:
    """Anchors of a built element (frames, sizes, floors) for attaching things."""
    return _j(_call("GET", f"/api/anchors/{element_id}"))


@tool
def patch(ops: list, note: str = "") -> str:
    """Edit atomically. ops: {op:add, element:{...}} | {op:update, id, params?, at?, on?, offset?, rot?, ...}
    | {op:remove, id} | {op:nudge, id, world_delta:[x,y,z], rot_delta} | {op:explode, id} | {op:set, key, value}."""
    return _j(_call("POST", "/api/patch", {"ops": ops, "note": note}))


@tool
def undo() -> str:
    return _j(_call("POST", "/api/undo"))


@tool
def redo() -> str:
    return _j(_call("POST", "/api/redo"))


@tool
def validate() -> str:
    """Check watertightness, floating/disconnected parts (with element ids), errors, triangle counts, bbox."""
    rep = _call("POST", "/api/validate")
    if isinstance(rep, dict):
        rep.pop("floating", None)
    return _j(rep)


@tool
def render_views(views: list | None = None, tile_w: int = 384) -> list:
    """Render ONE contact sheet (default 16 views: 4 sides, 4 isometric, 3 eye-level from the ground, top, below,
    section, floor plans of the 1st floor and mid height - check floors and walls inside the cuts too).
    Red parts = floating/problem elements. Use views=['iso_fl','front'] + tile_w=640 for a closer look."""
    info = _call("POST", "/api/render", {"views": views, "tile": [tile_w, int(tile_w * 0.75)]})
    if "error" in info:
        return [_j(info)]
    return [Image(path=info["path"]), _j({k: info[k] for k in ("views", "problems", "url")})]


@tool
def render_custom(az: float = -45, el: float = 25, dist: float | None = None, target: list | None = None, size: int = 768) -> list:
    """One view from any camera: azimuth deg (0=+X, -90=front/-Y), elevation deg, distance m, target [x,y,z]."""
    custom = {"az": az, "el": el, "dist": dist}
    if target:
        custom["target"] = target
    info = _call("POST", "/api/render", {"views": ["custom"], "custom": custom, "tile": [size, int(size * 0.75)]})
    if "error" in info:
        return [_j(info)]
    return [Image(path=info["path"])]


@tool
def note(text: str) -> str:
    """Show a progress message to the user in the app's live log."""
    return _j(_call("POST", "/api/note", {"text": text}))


@tool
def export(format: str = "glb", lod_tris: int | None = None, force: bool = False, only: list | None = None) -> str:
    """Export the welded, watertight model: glb, gltf, obj (+mtl+textures), dae, 3mf, stl, ply (colours), off.
    lod_tris = decimate to N triangles (LOD). only = element ids to export just them (with their children and
    everything attached), e.g. ["d/h1"]."""
    return _j(_call("POST", "/api/export", {"format": format, "lod_tris": lod_tris, "force": force, "only": only}))


@tool
def texture_manifest() -> str:
    """Write textures/manifest.json + PROMPTS.md (prompts for a texture AI, file names, folders)."""
    return _j(_call("POST", "/api/textures/manifest"))


@tool
def set_facade(element_id: str, face: str = "front", windows: dict | str = "none") -> str:
    """Replace the windows on one side ('front','back','left','right','faceN' or 'all') of a block/tower:
    windows='none' removes them, or a dict of window params e.g. {"kind":"arch","trim":"classic","w":1.2,"h":2}."""
    return _j(_call("POST", "/api/patch", {"ops": [{"op": "facade", "id": element_id, "face": face, "windows": windows}]}))


@tool
def paint(element_id: str = "", colors: dict | None = None, random: bool = False) -> str:
    """Paint facades. colors = {"wall":"#e3c38a","roof":"#5d6066","trim":"#ffffff","frame":..,"door":..,"plinth":..}.
    random=true picks colours from the style palette (element_id empty = all elements). Low-poly shows the colour,
    realistic tints the texture."""
    if random:
        op = {"op": "paint_random", **({"ids": [element_id]} if element_id else {})}
    else:
        op = {"op": "paint", "id": element_id, "colors": colors}
    return _j(_call("POST", "/api/patch", {"ops": [op]}))


@tool
def generate_interior(element_id: str = "", program: str = "", plan: list | None = None, furniture: bool = True) -> str:
    """Interior: rooms, corridors, doors, stairs, elevators (era-aware), furniture. element_id empty = every block of the
    building (program guessed from the macro: residential/office/palace/worship/hall/industrial). For one block give its
    id and optionally your own plan: [{"floor":0,"rooms":[{"name":"kitchen","rect":[x0,y0,x1,y1]}]}]."""
    if not element_id:
        ops = [{"op": "interior_all", **({"program": program} if program else {}), "furniture": furniture}]
    else:
        params = {"furniture": furniture, **({"program": program} if program else {}), **({"plan": plan} if plan else {})}
        ops = [{"op": "add", "element": {"id": "int_" + element_id.replace("/", "_"), "type": "interior",
                                          "on": f"{element_id}:inner", "params": params}}]
    out = _call("POST", "/api/patch", {"ops": ops})
    return _j({"patch": out, "floorplan_summary": {k: v["summary"] for k, v in _call("GET", "/api/floorplan").items()}})


@tool
def floorplan(element_id: str = "") -> str:
    """Rooms per floor (name, rect in meters from the inner corner, area) of generated interiors."""
    return _j(_call("GET", "/api/floorplan" + (f"?id={element_id}" if element_id else "")))


@tool
def weather(amount: float = 0.6, clear: bool = False) -> str:
    """Add (or clear) weathering decals on all walls: dirt, soot, rust, cracks, moss (old styles), graffiti (20th c.)."""
    op = {"op": "weather_clear"} if clear else {"op": "weather_all", "amount": amount}
    return _j(_call("POST", "/api/patch", {"ops": [op]}))


@tool
def set_options(interiors: bool | None = None, decals: bool | None = None, rooms: bool | None = None, detail: str | None = None,
                style: str | None = None, reroll: bool = False, build_mode: str | None = None, brick_size: float | None = None,
                brick_cull: bool | None = None, doors_separate: bool | None = None, fracture: dict | None = None) -> str:
    """Project switches: fake interiors behind windows (window plugs), rooms (real interior geometry on/off), decals, detail (realistic = PBR textures | lowpoly = flat colours),
    style (mix with '+', e.g. 'gothic+russian_orthodox'), reroll = new random seed for ranges/mixes/decals.
    build_mode: "solid" (welded shell) | "bricks" (everything made of cubic bricks of brick_size m, voxel / toy look);
    brick_cull: true = hidden brick faces removed, false = every brick a full cube.
    doors_separate: door leaves are separate objects with hinges (open in games); false = welded.
    fracture: destructible model, e.g. {"on": true, "level": "light|medium|heavy|extreme", "pieces": 60,
    "mode": "voronoi|elements", "seed": 1}; exports then contain one object per chunk (+ .objects.json)."""
    ops = [{"op": "set", "key": k, "value": v} for k, v in (("interiors", interiors), ("rooms", rooms), ("decals", decals), ("detail", detail),
                                                              ("style", style), ("build_mode", build_mode), ("brick_size", brick_size),
                                                              ("brick_cull", brick_cull), ("doors_separate", doors_separate),
                                                              ("fracture", fracture)) if v is not None]
    if reroll:
        ops.append({"op": "reroll"})
    return _j(_call("POST", "/api/patch", {"ops": ops}))


@tool
def download_textures(which: str = "project") -> str:
    """Download free CC0 PBR texture packs (ambientCG: albedo, normal, roughness, AO, height) for the project's
    materials ('project') or for the whole library ('all'). Runs in the background; progress goes to the live log."""
    return _j(_call("POST", "/api/textures/download", {"which": which}))



@tool
def measure(element_id: str = "") -> str:
    """Exact sizes: bbox min/max/size in metres, triangles, volume, and the faces (w x h) of an element - or of the
    whole model when element_id is empty. Use it to place things precisely and to check proportions against a reference."""
    return _j(_call("GET", "/api/measure?eid=" + element_id))


@tool
def fix_floating(remove: bool = False) -> str:
    """Lower every floating part onto what is below it (or the ground); remove=true deletes parts that cannot be
    lowered. Run validate after."""
    return _j(_call("POST", "/api/patch", {"ops": [{"op": "fix_floating", "remove": remove}], "note": "fix floating"}))


@tool
def add_prop(kind: str, at: list | None = None, on: str = "", rot: float = 0.0, scale: float = 1.0, count: int = 1,
             spacing: float = 3.0, ring: bool = False, radius: float = 5.0) -> str:
    """Add decorations / small objects: bench, street_lamp, planter, trash_bin, bollard, hydrant, bike_rack, barrel, crate,
    tree, bush, fountain, table_umbrella, flag, bus_stop, statue, well, lantern_post (ground or `top`); flower_box, ac_unit,
    wall_lamp, sign, mailbox, awning, satellite_dish, drainpipe, clock (on a face, at=[u, v]); antenna, water_tank,
    solar_panel, vent, rooftop_unit, chimney_pot (roofs: on="<roof>:top"). Free-standing: no `on`, at=[x, y] in metres.
    count>1 = a row (spacing) or ring (radius)."""
    el = {"type": "prop" if count <= 1 else "props_cluster", "id": kind,
          "params": {"kind": kind, "scale": scale} if count <= 1 else {"kind": kind, "scale": scale, "count": count,
                                                                      "spacing": spacing, "ring": ring, "radius": radius}}
    if at:
        el["at"] = at
    if on:
        el["on"] = on
    if rot:
        el["rot"] = rot
    return _j(_call("POST", "/api/patch", {"ops": [{"op": "add", "element": el}], "note": f"+{kind}"}))


@tool
def props_auto(density: float = 0.6, clear: bool = False) -> str:
    """Decorate the whole scene automatically: street lamps, benches, planters, bins in front of the buildings, trees
    around, AC units on walls, roof equipment on flat roofs. density 0..1. clear=true removes those decorations."""
    op = {"op": "props_clear"} if clear else {"op": "props_auto", "density": density}
    return _j(_call("POST", "/api/patch", {"ops": [op], "note": "decorations"}))


@tool
def usage() -> str:
    """Tokens and money spent by AI runs on this project (per provider)."""
    return _j(_call("GET", "/api/usage"))



@tool
def library_list() -> str:
    """My elements: things saved from any project (buildings, parts, decorations), grouped by category."""
    return _j(_call("GET", "/api/library"))


@tool
def library_save(element_id: str, name: str = "", category: str = "", description: str = "") -> str:
    """Save an element of the current project (with everything attached to it) to My elements, to reuse it in other
    projects. category: Здания, Части зданий, Окна и двери, Крыши и купола, Декор, Украшения, Природа, Мебель и интерьер,
    Небоскрёбы, Другое or a new one (empty = automatic)."""
    return _j(_call("POST", "/api/library/save", {"element": element_id, "name": name, "category": category,
                                                    "description": description}))


@tool
def library_insert(item_id: str, on: str = "", at: list | None = None, rot: float = 0.0) -> str:
    """Insert an item from My elements into the current project: on = "host:anchor" (e.g. "b/main:front" for a facade
    part, "b/roof:top"), at = [u, v] on a face / [x, y] on the ground; empty = on the ground beside the model."""
    return _j(_call("POST", "/api/library/insert", {"id": item_id, "on": on, "at": at, "rot": rot}))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
