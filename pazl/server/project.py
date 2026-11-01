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

ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS = ROOT / "projects"


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
            return to_scene(self.final(), self.tex_dir).export(file_type="glb")

    def export(self, fmt="glb", lod_tris=None, force=False, agent="?", path=None):
        with self.lock:
            rep = validate(self.result())
            if not rep["ok"] and not force:
                return {"error": "model has problems; fix them or pass force=true", "problems": rep["errors"][:20]}
            name = slug(self.recipe.get("name", "model"))
            suffix = f"_lod{lod_tris}" if lod_tris else ""
            out = Path(path) if path else self.dir / "export" / f"{name}{suffix}.{fmt}"
            _, ntri = export_mesh(self.final(), out, fmt, self.tex_dir, lod_tris)
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
                "can_undo": bool(self.undo_stack), "can_redo": bool(self.redo_stack), "dir": str(self.dir)}
