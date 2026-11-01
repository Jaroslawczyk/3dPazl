"""Project state: recipe, undo/redo, build cache, renders, exports. Thread-safe via a lock."""
from __future__ import annotations

import copy
import io
import json
import re
import threading
import time
from pathlib import Path

import numpy as np

from ..core import elements  # noqa: F401
from ..core import geo as g
from ..core.builder import build
from ..core.materials import MATS, write_manifest
from ..core.mesh import export as export_mesh, optimize, preview_scene, to_scene, validate
from ..core.registry import ELEMENTS
from ..core.render import VIEWS, render_sheet

from ..paths import PROJECTS, ROOT  # noqa: E402


BULK_OPS = {"reroll", "facade", "paint", "paint_random", "interior_all", "interior_clear", "weather_all", "weather_clear"}
PROGRAM_BY_MACRO = {
    "residential": {"house", "izba", "fachwerk_house", "panel_building", "stalinka", "dutch_house", "victorian_house",
                    "alpine_chalet", "japanese_house"},
    "office": {"glass_tower", "art_deco_tower", "brutalist_block", "constructivist"},
    "palace": {"palazzo", "moorish_palace"},
    "worship": {"gothic_cathedral", "orthodox_church", "romanesque_church", "baroque_church", "lithuanian_church",
                "byzantine_church", "caucasian_church", "ottoman_mosque", "persian_mosque", "mughal_mausoleum", "hindu_temple",
                "chinese_temple", "greek_temple", "roman_pantheon", "egyptian_temple", "stave_church"},
    "hall": {"castle_keep", "bunker", "ziggurat", "maya_pyramid", "pagoda"},
    "industrial": {"factory"},
}


def slug(s: str) -> str:
    return re.sub(r"[^\w\-]+", "_", s.strip(), flags=re.U)[:60] or "untitled"


class Project:
    def __init__(self, broadcast=None):
        self.lock = threading.RLock()
        self.broadcast = broadcast or (lambda ev: None)
        self.recipe = {"name": "untitled", "style": "generic", "detail": "realistic", "elements": []}
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []
        self.version = 0
        self._res = None
        self._final_opt = None
        self.log: list[dict] = []
        self.last_render = None
        self.last_validation = None

    # ------------------------------------------------------------ paths
    @property
    def dir(self) -> Path:
        d = PROJECTS / slug(self.recipe.get("name", "untitled"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def tex_dir(self) -> Path:
        return self.dir / "textures"

    # ------------------------------------------------------------ events
    def event(self, kind, agent="?", note="", **data):
        ev = {"type": kind, "t": time.time(), "agent": agent, "note": note, "version": self.version, **data}
        self.log.append(ev)
        self.log = self.log[-500:]
        self.broadcast(ev)
        return ev

    # ------------------------------------------------------------ build
    def result(self):
        with self.lock:
            if self._res is None:
                self._res = build(self.recipe)
                self._final_opt = None
            return self._res

    def final(self, optimized=True):
        res = self.result()
        if not optimized:
            return res.final()
        if self._final_opt is None:
            self._final_opt = optimize(res.final())
        return self._final_opt

    def _changed(self, agent, note, save=True):
        self.version += 1
        self._res = None
        self.last_validation = None
        res = self.result()
        if save:
            self.save()
        errs = [{"id": e.get("id"), "error": e.get("error")} for e in res.errors]
        self.event("updated", agent, note, errors=errs, elements=len(res.elements))
        return {"version": self.version, "errors": errs}

    # ------------------------------------------------------------ recipe ops
    def new(self, name, style="generic", detail="realistic", elements=None, agent="?", recipe=None):
        with self.lock:
            self._push_undo()
            self.recipe = recipe or {"name": name, "style": style, "detail": detail, "elements": elements or []}
            self.recipe.setdefault("elements", [])
            return self._changed(agent, f"new project '{self.recipe.get('name')}'")

    def load(self, name_or_path, agent="?"):
        p = Path(name_or_path)
        if not p.exists():
            p = PROJECTS / slug(str(name_or_path)) / "recipe.json"
        with self.lock:
            self._push_undo()
            self.recipe = json.loads(p.read_text("utf-8"))
            return self._changed(agent, f"loaded {p.name}", save=False)

    def save(self, path=None):
        p = Path(path) if path else self.dir / "recipe.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.recipe, ensure_ascii=False, indent=1), "utf-8")
        return str(p)

    def _push_undo(self):
        self.undo_stack.append(copy.deepcopy(self.recipe))
        self.undo_stack = self.undo_stack[-200:]
        self.redo_stack.clear()

    def undo(self, agent="?"):
        with self.lock:
            if not self.undo_stack:
                return {"error": "nothing to undo"}
            self.redo_stack.append(copy.deepcopy(self.recipe))
            self.recipe = self.undo_stack.pop()
            return self._changed(agent, "undo")

    def redo(self, agent="?"):
        with self.lock:
            if not self.redo_stack:
                return {"error": "nothing to redo"}
            self.undo_stack.append(copy.deepcopy(self.recipe))
            self.recipe = self.redo_stack.pop()
            return self._changed(agent, "redo")

    def _find(self, eid):
        for i, e in enumerate(self.recipe["elements"]):
            if e["id"] == eid:
                return i, e
        return None, None

    def patch(self, ops: list[dict], agent="?", note=""):
        """Apply a list of ops atomically. Ops:
        add {element}, update {id, params?, at?, on?, offset?, rot?, ...}, remove {id, cascade?},
        nudge {id, world_delta:[x,y,z], rot_delta}, explode {id}, set {key: style|detail|name, value}
        Ids inside macros ("church/roof") are stored as overrides of the macro element.
        """
        with self.lock:
            before = copy.deepcopy(self.recipe)
            msgs = []
            try:
                for op in ops:
                    msgs.append(self._apply(op))
            except Exception as ex:
                self.recipe = before
                return {"error": f"{type(ex).__name__}: {ex}", "applied": 0}
            self.undo_stack.append(before)
            self.redo_stack.clear()
            note = note or "; ".join(m for m in msgs if m)
            out = self._changed(agent, note)
            out["applied"] = len(ops)
            return out

    def _apply(self, op):
        kind = op.get("op")
        els = self.recipe["elements"]
        if kind == "add":
            e = op["element"]
            if e.get("type") not in ELEMENTS:
                raise ValueError(f"unknown type {e.get('type')}")
            base = e.get("id") or e["type"]
            eid, k = base, 1
            ids = {x["id"] for x in els}
            while eid in ids:
                k += 1
                eid = f"{base}{k}"
            e["id"] = eid
            els.append(e)
            return f"+{eid}"
        if kind == "set":
            self.recipe[op["key"]] = op["value"]
            return f"{op['key']}={op['value']}"
        if kind in BULK_OPS:
            return getattr(self, "_op_" + kind)(op)
        eid = op["id"]
        root, _, sub = eid.partition("/")
        i, e = self._find(root)
        if e is None:
            raise KeyError(f"element '{root}' not found")
        if sub:  # inside a macro -> overrides
            ov = e.setdefault("overrides", {}).setdefault(sub, {})
            if kind == "remove":
                ov["remove"] = True
                return f"-{eid}"
            if kind == "nudge":
                self._nudge(ov, eid, op)
                return f"~{eid}"
            if kind == "update":
                for k, v in op.items():
                    if k in ("op", "id"):
                        continue
                    if k == "params":
                        ov.setdefault("params", {}).update(v)
                    else:
                        ov[k] = v
                return f"*{eid}"
            raise ValueError(f"op {kind} not supported inside a macro (use explode first)")
        if kind == "remove":
            dependents = [x["id"] for x in els if (x.get("on") or "").partition(":")[0] == eid]
            if dependents and not op.get("cascade", True):
                raise ValueError(f"{eid} has attached elements {dependents}")
            rm = {eid}
            changed = True
            while changed and op.get("cascade", True):
                changed = False
                for x in els:
                    if x["id"] not in rm and (x.get("on") or "").partition(":")[0] in rm:
                        rm.add(x["id"])
                        changed = True
            self.recipe["elements"] = [x for x in els if x["id"] not in rm]
            return "-" + ",".join(sorted(rm))
        if kind == "update":
            for k, v in op.items():
                if k in ("op", "id"):
                    continue
                if k == "params":
                    e.setdefault("params", {}).update(v)
                    for pk in [pk for pk, pv in v.items() if pv is None]:
                        e["params"].pop(pk, None)
                elif v is None:
                    e.pop(k, None)
                else:
                    e[k] = v
            return f"*{eid}"
        if kind == "nudge":
            self._nudge(e, eid, op)
            return f"~{eid}"
        if kind == "explode":
            from ..core.builder import expand
            from ..core.styles import get_style
            flat = expand([e], get_style(self.recipe.get("style")), self.recipe.get("detail", "realistic"))
            children = []
            for c in flat:
                c = dict(c)
                if c.get("type") == "_group":
                    c = {k: v for k, v in c.items() if k in ("id", "on", "at", "offset", "rot")}
                    c["type"] = "box"
                    c["hidden"] = True
                    c["note"] = "group frame of exploded macro"
                children.append(c)
            self.recipe["elements"] = els[:i] + children + els[i + 1:]
            return f"exploded {eid} into {len(children)}"
        raise ValueError(f"unknown op {kind}")

    def _nudge(self, target: dict, eid: str, op):
        res = self.result()
        r = res.elements.get(eid)
        d = np.asarray(op.get("world_delta", [0, 0, 0]), float)
        if r is not None and r.host and r.host in res.elements:
            an = (target.get("on") or "").partition(":")[2] or "origin"
            # anchor rotation (no translation): world delta -> anchor-local delta
            hostr = res.elements[r.host]
            A = hostr.anchors.get(an)
            if A is not None:
                d = A.m[:3, :3].T @ d
        off = list(target.get("offset") or [0, 0, 0]) + [0, 0, 0]
        target["offset"] = [round(float(off[k]) + float(d[k]), 4) for k in range(3)]
        if op.get("rot_delta"):
            target["rot"] = round(float(target.get("rot", 0)) + float(op["rot_delta"]), 3)

    # ------------------------------------------------------------ bulk / helper ops
    def _built(self):
        return self.result().elements

    def _op_reroll(self, op):
        import random
        self.recipe["seed"] = op.get("seed") or random.randint(1, 999999)
        return f"seed={self.recipe['seed']}"

    def _op_facade(self, op):
        """Change or remove the windows on one face (or all faces) of an element."""
        host, face = op["id"], op.get("face", "front")
        faces = None if face == "all" else {face}
        found = [eid for eid, r in self._built().items()
                 if r.host == host and r.type in ("windows", "window")
                 and (faces is None or (r.src.get("on") or "").partition(":")[2] in faces)]
        win = op.get("windows")
        for eid in found:
            if win in (None, "none"):
                self._apply({"op": "remove", "id": eid})
            else:
                self._apply({"op": "update", "id": eid, "params": win})
        if not found and isinstance(win, dict):
            for f in ([face] if faces else ["front", "back", "left", "right"]):
                self._apply({"op": "add", "element": {"id": f"{host.replace('/', '_')}_{f}_win", "type": "windows",
                                                       "on": f"{host}:{f}", "params": win}})
        return f"facade {host}:{face} -> {'no windows' if win in (None, 'none') else 'windows ' + str(win)}"

    def _op_paint(self, op):
        self._apply({"op": "update", "id": op["id"], "colors": op.get("colors") or None})
        return f"paint {op['id']}"

    def _op_paint_random(self, op):
        import random
        from ..core.styles import get_style
        rng = random.Random(op.get("seed") or random.random())
        ids = op.get("ids") or [e["id"] for e in self.recipe["elements"]]
        for eid in ids:
            _, e = self._find(eid.partition("/")[0])
            if e is None:
                continue
            st = get_style(e.get("style") or self.recipe.get("style"))
            pal = st.get("palette") or {"wall": ["#e8e4da", "#d9c7a4", "#c9d3d6", "#e3c38a"], "trim": ["#f4f2ec"],
                                        "roof": ["#8a4a35", "#5a5d64"]}
            colors = {role: rng.choice(v) for role, v in pal.items() if v}
            self._apply({"op": "update", "id": eid, "colors": colors})
        return f"random paint x{len(ids)}"

    def _host_blocks(self, types=("block",)):
        return [eid for eid, r in self._built().items()
                if r.type in types and "inner" in r.anchors and not r.src.get("hidden")]

    def _program_for(self, eid):
        _, e = self._find(eid.partition("/")[0])
        mt = (e or {}).get("type", "")
        for prog, types in PROGRAM_BY_MACRO.items():
            if mt in types:
                return prog
        return "residential"

    def _op_interior_all(self, op):
        have = {(e.get("on") or "").partition(":")[0] for e in self.recipe["elements"] if e.get("type") == "interior"}
        n = 0
        for b in self._host_blocks():
            if b in have:
                continue
            params = {"program": op.get("program") or self._program_for(b)}
            if op.get("furniture") is not None:
                params["furniture"] = op["furniture"]
            self._apply({"op": "add", "element": {"id": "int_" + b.replace("/", "_"), "type": "interior", "on": f"{b}:inner",
                                                   "params": params}})
            n += 1
        return f"interior for {n} volumes"

    def _op_interior_clear(self, op):
        self.recipe["elements"] = [e for e in self.recipe["elements"] if e.get("type") != "interior"]
        return "interiors removed"

    def _op_weather_all(self, op):
        have = {(e.get("on") or "").partition(":")[0] for e in self.recipe["elements"] if e.get("type") == "weathering"}
        n = 0
        for b in self._host_blocks():
            if b in have:
                continue
            self._apply({"op": "add", "element": {"id": "dirt_" + b.replace("/", "_"), "type": "weathering", "on": f"{b}:top",
                                                   "params": {"amount": op.get("amount", 0.6)}}})
            n += 1
        return f"weathering on {n} volumes"

    def _op_weather_clear(self, op):
        self.recipe["elements"] = [e for e in self.recipe["elements"] if e.get("type") != "weathering"]
        return "weathering removed"

    def floorplan(self, eid=None):
        out = {}
        for k, r in self.result().elements.items():
            if r.type == "interior" and (eid is None or k == eid or r.host == eid):
                out[k] = {"host": r.host, "program": r.info.get("program"), "summary": r.info.get("summary"),
                          "rooms": r.info.get("plan")}
        return out

    def download_textures(self, which="project", res="1K", agent="?"):
        from ..core.texpacks import QUERIES, download
        slots = list(QUERIES) if which == "all" else (which if isinstance(which, list) else self.used_materials())
        self.event("textures", agent, f"downloading up to {len(slots)} PBR packs (ambientCG, CC0)")

        def prog(i, n, slot, asset, size):
            self.event("textures", agent, f"[{i + 1}/{n}] {slot} <- {asset} ({size // 1_000_000} MB)")
        out = download(slots, res, progress=prog)
        got = [k for k, v in out.items() if not str(v).startswith(("skip", "error"))]
        self.event("textures", agent, f"done: {len(got)} new packs", downloaded=got)
        return out

    # ------------------------------------------------------------ queries
    def tree(self):
        res = self.result()
        out = []
        for eid in res.order:
            r = res.elements[eid]
            out.append({"id": eid, "type": r.type, "host": r.host, "error": r.error,
                        "anchors": sorted(r.anchors.keys()) if len(r.anchors) < 40 else sorted(r.anchors.keys())[:40]})
        return out

    def anchors(self, eid):
        res = self.result()
        r = res.elements.get(eid)
        if r is None:
            raise KeyError(eid)
        return {k: a.to_json() for k, a in r.anchors.items()}

    def validate(self, agent="?"):
        with self.lock:
            rep = validate(self.result())
            rep["triangles_optimized"] = self.final().num_tri()
            self.last_validation = rep
            self.event("validated", agent, "ok" if rep["ok"] else f"{len(rep['errors'])} problems",
                       ok=rep["ok"], problems=rep["errors"][:20],
                       highlight=sorted({e for f in rep.get("floating", []) for e in f["elements"]}))
            return rep

    def render(self, views=None, agent="?", tile=(384, 288), custom=None):
        with self.lock:
            rep = self.last_validation or validate(self.result())
            bad = sorted({e for f in rep.get("floating", []) for e in f["elements"]})
            n = len(list((self.dir / "renders").glob("*.png"))) if (self.dir / "renders").exists() else 0
            out = self.dir / "renders" / f"r{n + 1:03d}_v{self.version}.png"
            info = render_sheet(self.final(), out, views=views, tile=tile, highlight=bad,
                                title=f"{self.recipe.get('name')} [{self.recipe.get('style')}/{self.result().detail}] v{self.version}",
                                custom=custom)
            info["url"] = f"/files/{out.relative_to(PROJECTS).as_posix()}"
            info["problems"] = bad
            self.last_render = info
            self.event("render", agent, f"{len(info['views'])} views", url=info["url"], cameras=info["cameras"],
                       center=info["center"], radius=info["radius"])
            return info

    def preview_glb(self) -> bytes:
        with self.lock:
            return preview_scene(self.result()).export(file_type="glb")

    def model_glb(self) -> bytes:
        with self.lock:
            res = self.result()
            return to_scene(self.final(), self.tex_dir, textured=res.detail == "realistic", result=res).export(file_type="glb")

    def export(self, fmt="glb", lod_tris=None, force=False, agent="?", path=None):
        with self.lock:
            rep = validate(self.result())
            if not rep["ok"] and not force:
                return {"error": "model has problems; fix them or pass force=true", "problems": rep["errors"][:20]}
            name = slug(self.recipe.get("name", "model"))
            suffix = f"_lod{lod_tris}" if lod_tris else ""
            out = Path(path) if path else self.dir / "export" / f"{name}{suffix}.{fmt}"
            res = self.result()
            _, ntri = export_mesh(self.final(), out, fmt, self.tex_dir, lod_tris, textured=res.detail == "realistic", result=res)
            self.event("exported", agent, f"{out.name} ({ntri} tris)", path=str(out))
            return {"path": str(out), "triangles": ntri, "format": fmt,
                    "materials": self.used_materials()}

    def used_materials(self):
        from ..core.mesh import manifold_to_arrays, tri_materials
        _, _, oid = manifold_to_arrays(self.final())
        mats, _ = tri_materials(np.unique(oid))
        return sorted(set(mats))

    def texture_manifest(self, agent="?"):
        with self.lock:
            p = write_manifest(self.used_materials(), self.tex_dir)
            data = json.loads(p.read_text("utf-8"))
            data["manifest_path"] = str(p)
            data["prompts_md"] = str(self.tex_dir / "PROMPTS.md")
            self.event("textures", agent, "manifest written", path=str(p))
            return data

    def summary(self):
        res = self.result()
        return {"name": self.recipe.get("name"), "style": self.recipe.get("style"), "detail": res.detail,
                "version": self.version, "elements": len(self.recipe["elements"]), "built": len(res.elements),
                "errors": [{"id": e.get("id"), "error": e.get("error")} for e in res.errors],
                "can_undo": bool(self.undo_stack), "can_redo": bool(self.redo_stack), "dir": str(self.dir),
                "seed": self.recipe.get("seed", 1), "interiors": self.recipe.get("interiors", True),
                "rooms": self.recipe.get("rooms", True), "textures": self.recipe.get("textures", True),
                "decals_off": self.recipe.get("decals_off") or [], "tex_swap": self.recipe.get("tex_swap") or {},
                "decals": self.recipe.get("decals", True), "colors": self.recipe.get("colors")}
