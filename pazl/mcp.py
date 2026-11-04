"""MCP server (stdio) for Claude Code / Cursor / any MCP client. Thin wrapper over the HTTP API.
Starts the app (window) automatically if it is not running; set PAZL_HEADLESS=1 to start it without a window.

    python -m pazl.mcp
"""
from __future__ import annotations

import json
import os
import socket
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


from urllib.parse import quote  # noqa: E402


def tool(fn):
    TOOLS[fn.__name__] = fn
    mcp.tool()(fn)
    return fn


def _alive() -> bool:
    # a busy server (long render/export) answers HTTP late but still holds the port: check the port, not a request,
    # or every slow call spawns one more app window + console
    u = httpx.URL(BASE)
    try:
        socket.create_connection((u.host, u.port or 80), timeout=1).close()
        return True
    except OSError:
        return False


def _ensure():
    if _alive():
        return
    args = [sys.executable, "-m", "pazl.server" if os.environ.get("PAZL_HEADLESS") else "pazl"]
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen(args, cwd=str(ROOT), creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(150):
        time.sleep(0.2)
        if _alive():
            return
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
def make_item(kind: str = "", name: str = "", size: float = 1.0, width: float = 1.0, height: float = 1.0,
              seed: int = 1, color: str = "") -> str:
    """Items workshop: generate a small object GLB into projects/items/<name>.glb (metres, origin bottom centre).
    Empty kind lists available kinds. width/height scale proportions, seed picks a variant, color '#rrggbb' main colour."""
    if not kind:
        return _j(_call("GET", "/api/ws/items/kinds"))
    return _j(_call("POST", "/api/ws/items/make", {"kind": kind, "name": name, "params": {
        "size": size, "width": width, "height": height, "seed": seed, "color": color}}))


@tool
def make_vehicle(kind: str = "", name: str = "", color: str = "", color2: str = "", livery: str = "plain", text: str = "",
                 detail: int = 2, length: float = 1.0, size: float = 1.0, seed: int = 1) -> str:
    """Transport workshop: generate a vehicle GLB into projects/transport/<name>.glb (metres, Y up, facing +Z, wheels and rotors
    are separate nodes, one palette texture). Empty kind lists kinds and liveries. color/color2 '#rrggbb', text = plate, route or
    side number, detail 1-3 (3 adds the smallest parts), length 0.7-1.5 stretches the body, seed picks a variant."""
    if not kind:
        return _j(_call("GET", "/api/ws/transport/kinds"))
    return _j(_call("POST", "/api/ws/transport/make", {"kind": kind, "name": name, "params": {
        "color": color, "color2": color2, "livery": livery, "text": text, "detail": detail, "length": length, "size": size, "seed": seed}}))


@tool
def rig_auto(src: str = "", name: str = "", template: str = "humanoid") -> str:
    """Rig workshop (native, no Blender): fit a skeleton template (humanoid|quadruped|simple) to a GLB under projects/
    (e.g. 'items/x.glb'). Empty src builds a test mannequin. Then: rig_weights -> anim_make -> anim_check -> rig_export."""
    if not src:
        src = _call("POST", "/api/ws/rig/mannequin", {"name": name or "mannequin"}).get("src", "")
    return _j(_call("POST", "/api/ws/rig/auto", {"name": name or Path(src).stem, "src": src, "template": template}))


@tool
def rig_weights(name: str, bones: list | None = None) -> str:
    """Optionally move joints (bones=[{name, head:[x,y,z], tail:[x,y,z]}]), then compute automatic skin weights
    (max 4 influences). Returns verts, unweighted count, bones that got no vertices."""
    if bones:
        r = _call("POST", "/api/ws/rig/bones", {"name": name, "bones": bones})
        if "error" in r:
            return _j(r)
    return _j(_call("POST", "/api/ws/rig/weights", {"name": name}))


@tool
def anim_make(name: str, preset: str = "walk", clip: str = "", frames: int = 0, key: dict | None = None) -> str:
    """Create a clip from a preset (idle|walk|run|wave|jump), or with key={clip, bone, frame, euler:[x,y,z] deg, span}
    edit one bone rotation (neighbour frames blend). Rotations are about world-aligned axes: x pitch, y twist, z side."""
    if key:
        return _j(_call("POST", "/api/ws/rig/key", {"name": name, **key}))
    return _j(_call("POST", "/api/ws/rig/anim", {"name": name, "preset": preset, "clip": clip, "frames": frames or None}))


@tool
def anim_check(name: str, clip: str = "walk", samples: int = 24) -> str:
    """Compact motion check: unweighted verts, joint limits, limb penetration, stretch, ground, foot sliding,
    bone length; BAD lines name bones and frames."""
    r = _call("POST", "/api/ws/rig/check", {"name": name, "clip": clip, "samples": samples})
    return r.get("text") or _j(r)


@tool
def rig_export(name: str) -> str:
    """Write projects/rigs/<name>.glb: skinned mesh + skeleton + all clips (opens in any glTF viewer/engine)."""
    return _j(_call("POST", "/api/ws/rig/export", {"name": name}))


@tool
def char_make(name: str = "", preset: str = "", params: dict | None = None, src: str = "", template: str = "humanoid",
              skin: str = "", anim: str = "", quality: str = "") -> str:
    """Characters workshop: organic one-piece body, skeleton and idle/walk clips -> projects/chars/<name>.glb.
    Empty name lists presets, clothes, skins. New: preset (man woman athlete chubby elder child toon goblin chibi blocky blocky_slim blocky_big dog cat horse monster)
    or src = any GLB under projects/. Existing name with params {height, build, head, hips...} reshapes the body and refits clothes;
    skin = preset/saved skin name; anim = idle|walk|run|wave|jump; quality = low|mid|high|ultra (triangles of body and clothes)."""
    if not name:
        return _j(_call("GET", "/api/ws/chars/catalog"))
    r = None
    if preset or src:
        r = _call("POST", "/api/ws/chars/create", {"name": name, "preset": preset, "params": params, "src": src, "template": template, "quality": quality or "high"})
    elif params or quality:
        r = _call("POST", "/api/ws/chars/update", {"name": name, "params": params, "quality": quality or None})
    if skin:
        r = _call("POST", "/api/ws/chars/skin", {"name": name, "skin": skin})
    if anim:
        r = _call("POST", "/api/ws/chars/anim", {"name": name, "preset": anim})
    return _j(r or _call("GET", f"/api/ws/chars/get/{name}"))


@tool
def char_import(path: str, name: str = "", height: float = 0, up: str = "auto", turn: int = 0, template: str = "humanoid", quality: str = "high") -> str:
    """Make a character from a model file on this computer: OBJ (its .mtl and textures beside it are picked up), FBX (binary), GLB, DAE, STL, PLY.
    height in metres (0 keeps size), up auto|y|z, turn degrees so it faces +Z. Bones inside the file are replaced by a skeleton measured from the figure; lowered arms of block bodies are swung into T-pose."""
    import base64
    p = Path(path)
    fs = [p] + [x for x in p.parent.iterdir() if x != p and x.suffix.lower() in (".mtl", ".png", ".jpg", ".jpeg", ".bin")]
    files = [{"name": f.name, "data": base64.b64encode(f.read_bytes()).decode()} for f in fs]
    return _j(_call("POST", "/api/ws/chars/import", {"name": name, "files": files, "height": height, "up": up, "turn": turn, "template": template, "quality": quality}))


@tool
def char_sculpt(name: str, strokes: list | None = None, undo: bool = False) -> str:
    """Clay on a character (generated or imported): strokes=[{p:[x,y,z], r: radius m, amount: m (minus dents), mirror: true}]."""
    return _j(_call("POST", "/api/ws/chars/sculpt", {"name": name, "strokes": strokes, "undo": undo}))


@tool
def char_wear(char: str, kind: str = "", color: str = "", skin: str = "", ease: float = 0, length: float = 1,
              remove: bool = False, copy_from: str = "") -> str:
    """Clothes fitted from the body itself, so one recipe suits any character. Humanoid: tshirt longsleeve tank jacket pants shorts skirt
    dress cloak boots shoes gloves scarf belt beanie hat hair_short hair_long beard; quadruped: coat collar paws; any object: wrap.
    copy_from dresses `char` in another character's outfit."""
    if copy_from:
        return _j(_call("POST", "/api/ws/clothes/copy", {"from": copy_from, "to": char}))
    if remove:
        return _j(_call("POST", "/api/ws/clothes/remove", {"char": char, "kind": kind}))
    return _j(_call("POST", "/api/ws/clothes/wear", {"char": char, "kind": kind, "color": color, "skin": skin or None, "ease": ease or None, "length": length}))


@tool
def skin_apply(src: str, skin: str | dict, name: str = "", parts: list | None = None) -> str:
    """Skin any static GLB under projects/ (items, exports, imports) -> projects/skins/<name>.glb. skin: preset name
    (denim tartan camo dragon tiger oak marble rust ...) or {pattern, colors, tile (m), seed, metal, rough}."""
    return _j(_call("POST", "/api/ws/skins/apply", {"src": src, "skin": skin, "name": name, "parts": parts}))


@tool
def skin_search(query: str) -> str:
    """Find free CC0 textures on the internet (Poly Haven, ambientCG). Then skin_download. Instructions: docs/ROBLOX.md."""
    return _j(_call("GET", "/api/ws/skins/web?q=" + quote(query)))


@tool
def skin_download(source: str, id: str) -> str:
    """Download a skin_search result as a skin usable in char_wear, char_make, skin_apply."""
    return _j(_call("POST", "/api/ws/skins/web", {"source": source, "id": id}))


@tool
def roblox_export(char: str = "", path: str = "") -> str:
    """Files ready for Roblox in projects/roblox/<name>/ with README: char -> shirt.png, pants.png (585x559 template), model.glb,
    anim_*.rbxmx (R6), accessories; path -> any GLB or picture under projects/. Limits and links: docs/ROBLOX.md."""
    return _j(_call("POST", "/api/ws/roblox/export", {"char": char, "path": path}))


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
def tree(full: bool = False, root: str = "", depth: int = 99) -> str:
    """Element hierarchy as a compact indented outline (cheap in tokens; runs like awL0..5 folded).
    root = only that subtree, depth = levels. full=True -> JSON with host, errors and anchor names."""
    if full:
        return _j(_call("GET", "/api/tree"))
    from urllib.parse import quote
    r = _call("GET", f"/api/tree?compact=1&root={quote(root)}&depth={depth}", raw=True)
    return r.decode("utf-8") if isinstance(r, bytes) else _j(r)


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


# ---------------------------------------------------------------- 2D frames / sprites
NL = chr(10)


@tool
def frames_load(seq: str = "", sample: bool = False) -> str:
    """2D frames workshop. List sequences (projects/frames2d/<seq>/key/*.png keyframes), or one seq's state.
    sample=True creates procedural test sequences sample_sketch / sample_color. Next: frames_interpolate -> frames_check."""
    if sample:
        seq = _call("POST", "/api/ws/frames/sample")["name"]
    if not seq:
        return NL.join(f"{s['name']}: {s['keys']} keys, {s['frames']} frames, fps {s['fps']}, {s['method'] or '-'}"
                         for s in _call("GET", "/api/ws/frames/seqs")) or "no sequences"
    j = _call("GET", f"/api/ws/frames/seq/{seq}")
    return f"{j['name']}: {len(j['keys'])} keys, {len(j['frames'])} frames, fps {j['fps']}, method {j['method'] or '-'}"


@tool
def frames_interpolate(seq: str, n: int = 1, method: str = "flow", lineart: str = "auto", fps: int = 0) -> str:
    """Generate n inbetweens between every pair of keyframes. method: flow (native optical flow, default) | blend |
    rife (needs PAZL_RIFE=rife-ncnn-vulkan). lineart: auto|true|false (keeps strokes crisp). Returns ghost per inbetween
    (0 = both warped keys agree; >0.3 = likely ghosting/double lines -> add a key or use fewer inbetweens)."""
    j = _call("POST", "/api/ws/frames/interpolate", {"seq": seq, "n": n, "method": method,
              "lineart": None if lineart == "auto" else lineart in ("true", "1", True), "fps": fps or None})
    return f"{j['frames']} frames from {j['keys']} keys" + NL + NL.join(f"{p['pair']} ghost {p['ghost']}" for p in j["pairs"])


@tool
def frames_check(seq: str) -> list:
    """Quality report + ONE contact-sheet image of all frames (blue = keys, orange = inbetweens). pacing_flicker:
    0 = even motion; jumps_at = frame numbers with abrupt change."""
    j = _call("GET", f"/api/ws/frames/check/{seq}")
    txt = (f"{j['frames']} frames {j['size'][0]}x{j['size'][1]} fps {j['fps']} method {j['method']} "
           f"flicker {j['pacing_flicker']} jumps {j['jumps_at']}" + NL + NL.join(f"{p['pair']} ghost {p['ghost']}" for p in j["pairs"]))
    return [Image(path=str(Path(__file__).resolve().parents[1] / "projects" / j["contact"])), txt]


@tool
def frames_export(seq: str, kind: str = "gif", fps: int = 0, cols: int = 0) -> str:
    """Export a sequence: kind gif (anim.gif) | sheet (sheet.png + sheet.json atlas). PNG frames are already in out/."""
    j = _call("POST", "/api/ws/frames/export", {"seq": seq, "kind": kind, "fps": fps or None, "cols": cols})
    return _j(j)


@tool
def sprite_sheet(paths: list | None = None, name: str = "sheet", cols: int = 0, op: str = "pack", path: str = "",
                 color: str = "auto", tol: float = 0.12, x: float = 0.5, y: float = 1.0, rows: int = 0) -> str:
    """Sprites workshop (files under projects/, e.g. 'sprites/hero.png'). op: pack (paths -> sprites/<name>.png grid +
    .json atlas) | unpack (path; cols+rows or auto by islands) | colorkey (path; color '#rrggbb' or auto, tol) ->
    <name>_key.png | trim (path) | pivot (path, x, y in 0..1)."""
    if op == "pack":
        return _j(_call("POST", "/api/ws/sprites/pack", {"paths": paths or [], "name": name, "cols": cols}))
    return _j(_call("POST", "/api/ws/sprites/op", {"path": path, "op": op, "color": color, "tol": tol, "x": x, "y": y,
                                                    "cols": cols, "rows": rows}))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
