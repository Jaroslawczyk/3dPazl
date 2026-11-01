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
    "validate -> render_views (ONE contact-sheet image with 12 views incl. sections; red = problems) -> fix -> export. "
    "Ids inside macros look like 'b/roof' and can be patched directly. Use note() to tell the user what you are doing."))


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


@mcp.tool()
def guide() -> str:
    """How to build with 3dPazl: recipe format, anchors, workflow, tips. Read once."""
    return (ROOT / "docs" / "AI_GUIDE.md").read_text("utf-8")


@mcp.tool()
def list_styles() -> str:
    """Architectural styles with era/region, recommended macros and tips."""
    return _j(_call("GET", "/api/catalog/styles"))


@mcp.tool()
def list_elements(category: str = "") -> str:
    """Element types (compact). Categories: structure, openings, roofs, columns, decor, primitive, macros."""
    els = _call("GET", "/api/catalog/elements" + (f"?category={category}" if category else ""))
    return "\n".join(f"{e['type']} [{e['category']}{', macro' if e['macro'] else ''}; attach={e['attach']}]: {e['desc']}"
                     for e in els)


@mcp.tool()
def describe_element(type: str) -> str:
    """Full param schema (defaults, choices) and anchors of one element type."""
    return _j(_call("GET", f"/api/catalog/element/{type}"))


@mcp.tool()
def new_building(name: str, style: str = "generic", detail: str = "realistic", elements: list | None = None) -> str:
    """Start a new project. detail: realistic | lowpoly. elements: list of recipe elements (may be one macro)."""
    return _j(_call("POST", "/api/new", {"name": name, "style": style, "detail": detail, "elements": elements or []}))


@mcp.tool()
def load_project(name: str) -> str:
    """Open a saved project by name."""
    return _j(_call("POST", "/api/load", {"name": name}))


@mcp.tool()
def list_projects() -> str:
    return _j(_call("GET", "/api/projects"))


@mcp.tool()
def get_recipe() -> str:
    """Current recipe JSON (source of truth)."""
    return _j(_call("GET", "/api/recipe"))


@mcp.tool()
def tree() -> str:
    """Built elements (incl. macro children) with host, errors and anchor names."""
    return _j(_call("GET", "/api/tree"))


@mcp.tool()
def anchors(element_id: str) -> str:
    """Anchors of a built element (frames, sizes, floors) for attaching things."""
    return _j(_call("GET", f"/api/anchors/{element_id}"))


@mcp.tool()
def patch(ops: list, note: str = "") -> str:
    """Edit atomically. ops: {op:add, element:{...}} | {op:update, id, params?, at?, on?, offset?, rot?, ...}
    | {op:remove, id} | {op:nudge, id, world_delta:[x,y,z], rot_delta} | {op:explode, id} | {op:set, key, value}."""
    return _j(_call("POST", "/api/patch", {"ops": ops, "note": note}))


@mcp.tool()
def undo() -> str:
    return _j(_call("POST", "/api/undo"))


@mcp.tool()
def redo() -> str:
    return _j(_call("POST", "/api/redo"))


@mcp.tool()
def validate() -> str:
    """Check watertightness, floating/disconnected parts (with element ids), errors, triangle counts, bbox."""
    rep = _call("POST", "/api/validate")
    if isinstance(rep, dict):
        rep.pop("floating", None)
    return _j(rep)


@mcp.tool()
def render_views(views: list | None = None, tile_w: int = 384) -> list:
    """Render ONE contact sheet (default 12 views: front/right/back/left, 4 isometric, top, below, 2 sections).
    Red parts = floating/problem elements. Use views=['iso_fl','front'] + tile_w=640 for a closer look."""
    info = _call("POST", "/api/render", {"views": views, "tile": [tile_w, int(tile_w * 0.75)]})
    if "error" in info:
        return [_j(info)]
    return [Image(path=info["path"]), _j({k: info[k] for k in ("views", "problems", "url")})]


@mcp.tool()
def render_custom(az: float = -45, el: float = 25, dist: float | None = None, target: list | None = None, size: int = 768) -> list:
    """One view from any camera: azimuth deg (0=+X, -90=front/-Y), elevation deg, distance m, target [x,y,z]."""
    custom = {"az": az, "el": el, "dist": dist}
    if target:
        custom["target"] = target
    info = _call("POST", "/api/render", {"views": ["custom"], "custom": custom, "tile": [size, int(size * 0.75)]})
    if "error" in info:
        return [_j(info)]
    return [Image(path=info["path"])]


@mcp.tool()
def note(text: str) -> str:
    """Show a progress message to the user in the app's live log."""
    return _j(_call("POST", "/api/note", {"text": text}))


@mcp.tool()
def export(format: str = "glb", lod_tris: int | None = None, force: bool = False) -> str:
    """Export the welded, watertight model (glb/gltf/obj/stl). lod_tris = decimate to N triangles (LOD)."""
    return _j(_call("POST", "/api/export", {"format": format, "lod_tris": lod_tris, "force": force}))


@mcp.tool()
def texture_manifest() -> str:
    """Write textures/manifest.json + PROMPTS.md (prompts for a texture AI, file names, folders)."""
    return _j(_call("POST", "/api/textures/manifest"))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
