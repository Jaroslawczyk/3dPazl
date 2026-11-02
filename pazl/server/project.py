"""Project state: recipe, undo/redo, build cache, renders, exports. Thread-safe via a lock."""
from __future__ import annotations

import copy
import io
import json
import re
import threading
import time
import zlib
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


BULK_OPS = {"reroll", "facade", "paint", "paint_random", "interior_all", "interior_clear", "weather_all", "weather_clear",
            "shapes", "windows_fill", "fix_floating", "props_auto", "props_clear"}
SHAPE_POOL = ["rect", "rounded", "L", "U", "T", "octagon", "hexagon", "trapezoid", "wedge", "bow", "cut_corner", "round",
              "oval", "cross"]
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



def _pack(recipe: dict) -> bytes:
    return zlib.compress(json.dumps(recipe, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)


def _unpack(blob) -> dict:
    return json.loads(zlib.decompress(blob).decode("utf-8")) if isinstance(blob, bytes) else blob


class Project:
    def __init__(self, broadcast=None):
        self.lock = threading.RLock()
        self.scope: set | None = None  # while the AI fixes marked places: the only element ids it may change
        self.broadcast = broadcast or (lambda ev: None)
        self.recipe = {"name": "untitled", "style": "generic", "detail": "realistic", "elements": []}
        self.undo_stack: list[bytes] = []  # zlib-compressed JSON snapshots (a few KB each)
        self.redo_stack: list[bytes] = []
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
        from .logs import log
        log("event", project=self.recipe.get("name"), **{k: v for k, v in ev.items() if k not in ("t", "cameras")})
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
        self.check_scope(agent, what="new project")
        with self.lock:
            self._push_undo()
            self.recipe = recipe or {"name": name, "style": style, "detail": detail, "elements": elements or []}
            self.recipe.setdefault("elements", [])
            return self._changed(agent, f"new project '{self.recipe.get('name')}'")

    def load(self, name_or_path, agent="?"):
        self.check_scope(agent, what="loading a project")
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
        if path is None:
            self._autosave()
        return str(p)

    # ------------------------------------------------------------ autosave snapshots (every change is saved anyway)
    AUTOSAVE_GAP, AUTOSAVE_KEEP = 30.0, 40

    def _autosave(self):
        """A snapshot of the recipe at most every 30 s while it changes; the newest 40 are kept."""
        d = self.dir / "autosave"
        now = time.time()
        if now - getattr(self, "_last_autosave", 0.0) < self.AUTOSAVE_GAP:
            return
        self._last_autosave = now
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{time.strftime('%Y%m%d-%H%M%S')}_v{self.version}.json").write_text(
            json.dumps(self.recipe, ensure_ascii=False), "utf-8")
        for old in sorted(d.glob("*.json"))[:-self.AUTOSAVE_KEEP]:
            old.unlink(missing_ok=True)

    def autosaves(self):
        out = []
        for f in sorted((self.dir / "autosave").glob("*.json"), reverse=True):
            stamp, _, ver = f.stem.partition("_v")
            try:
                n = len(json.loads(f.read_text("utf-8")).get("elements", []))
            except (OSError, ValueError):
                continue
            t = time.strptime(stamp, "%Y%m%d-%H%M%S")
            out.append({"file": f.name, "time": time.strftime("%d.%m %H:%M:%S", t), "version": ver, "elements": n})
        return out

    def restore_autosave(self, name, agent="?"):
        f = self.dir / "autosave" / Path(name).name  # a file name only: nothing outside the folder
        if not f.exists():
            raise KeyError(name)
        with self.lock:
            self._push_undo()  # restoring can be undone
            self.recipe = json.loads(f.read_text("utf-8"))
            return self._changed(agent, f"restored autosave {f.name}")

    def _push_undo(self):
        self.undo_stack.append(_pack(self.recipe))
        self.undo_stack = self.undo_stack[-200:]
        self.redo_stack.clear()

    def undo(self, agent="?"):
        self.check_scope(agent, what="undo")
        with self.lock:
            if not self.undo_stack:
                return {"error": "nothing to undo"}
            self.redo_stack.append(_pack(self.recipe))
            self.recipe = _unpack(self.undo_stack.pop())
            return self._changed(agent, "undo")

    def redo(self, agent="?"):
        self.check_scope(agent, what="redo")
        with self.lock:
            if not self.redo_stack:
                return {"error": "nothing to redo"}
            self.undo_stack.append(_pack(self.recipe))
            self.recipe = _unpack(self.redo_stack.pop())
            return self._changed(agent, "redo")

    def _find(self, eid):
        for i, e in enumerate(self.recipe["elements"]):
            if e["id"] == eid:
                return i, e
        return None, None

    # ------------------------------------------------------------ scope lock (marks -> AI changes only those elements)
    def _in_scope(self, eid: str, scope=None) -> bool:
        """A marked element, its macro children ("m/x") and everything attached to it (host chain)."""
        scope = self.scope if scope is None else scope
        els = self._res.elements if self._res is not None else {}
        seen = set()
        while eid and eid not in seen:
            if any(eid == s or eid.startswith(s + "/") for s in scope):
                return True
            seen.add(eid)
            eid = getattr(els.get(eid), "host", None)
        return False

    def check_scope(self, agent: str, ops: list[dict] | None = None, what: str = ""):
        """AI agents (X-Agent chat:*) may only touch the marked elements (and their children) while a scope is set."""
        if not self.scope or not str(agent).startswith("chat:"):
            return
        allowed = ", ".join(sorted(self.scope))
        if what:
            raise PermissionError(f"{what} is locked: change only the marked elements ({allowed})")
        for op in ops or []:
            kind = op.get("op")
            if kind == "add":
                host = str((op.get("element") or {}).get("on") or "").partition(":")[0]
                ok = bool(host) and self._in_scope(host)
            elif kind in ("update", "remove", "nudge", "explode", "facade", "paint"):
                ok = self._in_scope(str(op.get("id", "")))
            elif kind == "paint_random" and op.get("ids"):
                ok = all(self._in_scope(str(i)) for i in op["ids"])
            else:
                ok = False
            if not ok:
                raise PermissionError(f"op {kind} {op.get('id') or ''} is outside the marked area. "
                                      f"Only these elements (and their children) may be changed: {allowed}")

    def patch(self, ops: list[dict], agent="?", note=""):
        """Apply a list of ops atomically. Ops:
        add {element}, update {id, params?, at?, on?, offset?, rot?, ...}, remove {id, cascade?},
        nudge {id, world_delta:[x,y,z], rot_delta}, explode {id}, set {key: style|detail|name, value}
        Ids inside macros ("church/roof") are stored as overrides of the macro element.
        """
        self.check_scope(agent, ops)
        with self.lock:
            before = copy.deepcopy(self.recipe)
            msgs = []
            try:
                for op in ops:
                    msgs.append(self._apply(op))
            except Exception as ex:
                self.recipe = before
                return {"error": f"{type(ex).__name__}: {ex}", "applied": 0}
            self.undo_stack.append(_pack(before))
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

    def _op_shapes(self, op):
        """Building shapes: shape='random' gives every free-standing volume its own (often asymmetric) footprint,
        a named shape applies it everywhere, 'rect' resets. Stacked volumes (jettied floors) follow the one below;
        round towers get a cone roof."""
        import random as _r
        res = self.result()
        rng = _r.Random(f"{self.recipe.get('seed', 1)}:shapes:{self.version}")
        want, chosen, n = op.get("shape", "random"), {}, 0
        for eid in res.order:
            r = res.elements[eid]
            if r.type != "block" or (r.params or {}).get("poly"):
                continue
            host = res.elements.get(r.host) if r.host else None
            if host is not None and host.type == "block" and r.host in chosen:
                pr = chosen[r.host]
            elif want == "random":
                pr = {"shape": rng.choice(SHAPE_POOL), "flip": rng.random() < 0.5, "shape_k": round(rng.uniform(0.3, 0.55), 2)}
            else:
                pr = {"shape": want, "flip": False, "shape_k": 0.4}
            chosen[eid] = pr
            self._apply({"op": "update", "id": eid, "params": pr})
            n += 1
        for eid in res.order:  # roofs on round / oval volumes: cone / dome (a gable roof cannot cover a circle)
            r = res.elements[eid]
            if r.type == "roof" and r.host in chosen and chosen[r.host]["shape"] in ("round", "oval"):
                if (r.params or {}).get("type") not in ("cone", "dome", "onion", "flat"):
                    self._apply({"op": "update", "id": eid, "params": {"type": "cone" if chosen[r.host]["shape"] == "round" else "dome"}})
        return f"shapes {want} for {n} volumes"

    def _op_fix_floating(self, op):
        """Floating parts: each one is lowered onto what is below it (or the ground); parts that cannot be moved
        (macro internals, nothing below in reach) are removed when remove=true."""
        from ..core.mesh import manifold_to_arrays
        res = self.result()
        rep = validate(res)
        whole = res.final()
        moved, removed = [], []
        for f in rep.get("floating", []):
            if len(f["elements"]) != 1:
                continue
            eid = f["elements"][0]
            r = res.elements.get(eid)
            if r is None or not r.solids:
                continue
            part = g.union([m for m, _ in r.solids])
            mn, mx = g.bbox(part)
            rest = whole - part
            below = rest.trim_by_plane([0, 0, -1], -float(mn[2]) + 1e-3)  # everything under the part's bottom
            top = 0.0
            if not below.is_empty():
                foot = g.box(mn[0], mn[1], -1, mx[0], mx[1], mn[2])
                under = below ^ foot
                if not under.is_empty():
                    top = float(g.bbox(under)[1][2])
            drop = float(mn[2]) - top - 0.01  # 1 cm overlap so it welds
            if drop > 0 and drop < 50:
                self._apply({"op": "nudge", "id": eid, "world_delta": [0, 0, -round(drop, 3)], "rot_delta": 0})
                moved.append(eid)
            elif op.get("remove"):
                self._apply({"op": "remove", "id": eid})
                removed.append(eid)
        return f"floating: lowered {moved}, removed {removed}"

    def _op_props_auto(self, op):
        """Decorations around the buildings: street lamps, benches, planters, bins in front of every free-standing
        volume; flower boxes / AC units on walls; antennas, vents, solar panels, rooftop units on flat roofs; trees
        around. density 0..1. All ids start with 'pa_' (props_clear removes them)."""
        import math
        import random as _r
        res = self.result()
        rng = _r.Random(f"{self.recipe.get('seed', 1)}:props:{self.version}")
        dens = float(op.get("density", 0.6))
        n = 0

        boxes = []  # building footprints (+1.5 m): ground props never stand in or against a building
        for x in res.order:
            if res.elements[x].solids and res.elements[x].type not in ("prop", "props_cluster"):
                mn, mx = g.bbox(g.union([m for m, _ in res.elements[x].solids]))
                if mx[2] - mn[2] > 1.0:
                    boxes.append((mn[0] - 1.5, mn[1] - 1.5, mx[0] + 1.5, mx[1] + 1.5))

        def add(el):
            nonlocal n
            if "on" not in el and any(b[0] < el["at"][0] < b[2] and b[1] < el["at"][1] < b[3] for b in boxes):
                return
            n += 1
            el["id"] = f"pa_{n}"
            self.recipe["elements"].append(el)
        blocks = [eid for eid in res.order if res.elements[eid].type == "block" and not (
            res.elements[eid].host and res.elements[eid].host in res.elements and res.elements[res.elements[eid].host].type == "block")]
        for eid in blocks:
            r = res.elements[eid]
            fr = r.anchors.get("front")
            if fr is None:
                continue
            m = fr.m
            o, xa, na = m[:3, 3], m[:3, 0], m[:3, 1]
            rot = math.degrees(math.atan2(-na[0], na[1]))  # props face the street
            k = max(1, int(fr.w / 6))
            for i in range(k + 1):  # lamps along the front, benches / planters between them
                p = o + xa * (fr.w * i / k) + na * 3.2
                add({"type": "prop", "at": [round(p[0], 2), round(p[1], 2)], "rot": round(rot, 1), "params": {"kind": "street_lamp"}})
                if i < k and rng.random() < dens:
                    q = o + xa * (fr.w * (i + 0.5) / k) + na * 2.6
                    add({"type": "prop", "at": [round(q[0], 2), round(q[1], 2)], "rot": round(rot + 180, 1),
                         "params": {"kind": rng.choice(["bench", "bench", "planter", "trash_bin", "bike_rack"])}})
            for _ in range(int(2 + 4 * dens)):  # trees around, 6-9 m out
                side = rng.choice(["back", "left", "right"])
                a = r.anchors.get(side)
                if a is None:
                    continue
                p = a.m[:3, 3] + a.m[:3, 0] * rng.uniform(0, a.w) + a.m[:3, 1] * rng.uniform(5, 8)
                add({"type": "prop", "at": [round(p[0], 2), round(p[1], 2)], "params": {"kind": rng.choice(["tree", "tree", "bush"])}})
            for side in ("left", "right", "back"):  # AC units on the walls
                a = r.anchors.get(side)
                if a is None or rng.random() > dens or a.h < 6:
                    continue
                add({"type": "prop", "on": f"{eid}:{side}", "at": [round(rng.uniform(1, max(1.2, a.w - 1)), 2), round(rng.uniform(3, a.h - 2), 2)],
                     "params": {"kind": "ac_unit"}})
        for eid in res.order:  # flat roofs: equipment
            r = res.elements[eid]
            if r.type != "roof" or (r.params or {}).get("type") != "flat" or "top" not in r.anchors:
                continue
            fp = r.anchors["top"].footprint or []
            if not fp:
                continue
            xs, ys = [q[0] for q in fp], [q[1] for q in fp]
            for _ in range(int(1 + 3 * dens)):
                x, y = rng.uniform(min(xs) * 0.6, max(xs) * 0.6), rng.uniform(min(ys) * 0.6, max(ys) * 0.6)
                add({"type": "prop", "on": f"{eid}:top", "at": [round(x, 2), round(y, 2)],
                     "params": {"kind": rng.choice(["vent", "rooftop_unit", "antenna", "satellite_dish", "solar_panel", "water_tank"])}})
        self.recipe["props"] = True
        return f"props_auto: {n} decorations"

    def _op_props_clear(self, op):
        before = len(self.recipe["elements"])
        self.recipe["elements"] = [e for e in self.recipe["elements"] if not str(e.get("id", "")).startswith("pa_")]
        return f"props_clear: {before - len(self.recipe['elements'])} removed"

    def measure(self, eid=""):
        """Sizes for the AI: bbox of the element (or the whole model), triangles, and its faces (w x h)."""
        res = self.result()
        if eid:
            r = res.elements.get(eid)
            if r is None:
                raise KeyError(eid)
            sol = [m for x in res.order if self._in_scope(x, {eid}) for m, _ in res.elements[x].solids]
            m = g.union(sol) if sol else None
            faces = {k: [round(a.w, 2), round(a.h, 2)] for k, a in r.anchors.items() if a.kind == "face" and not k.startswith("face")}
        else:
            m, faces = res.final(), {}
        if m is None or m.is_empty():
            return {"element": eid, "empty": True}
        mn, mx = g.bbox(m)
        return {"element": eid or "(model)", "min": [round(float(x), 2) for x in mn], "max": [round(float(x), 2) for x in mx],
                "size": [round(float(x), 2) for x in mx - mn], "triangles": m.num_tri(), "volume_m3": round(m.volume(), 2),
                "faces": faces}

    def _op_windows_fill(self, op):
        """Every window grid: which slots are real windows (fill=all/random/checker/alternate/symmetric/formula) and
        what the others get (fill_other=mix/blind/shutters/boarded/none)."""
        res = self.result()
        pr = {k: op[k] for k in ("fill", "fill_share", "fill_formula", "fill_other") if k in op}
        if pr.get("fill") == "formula":
            from ..core.elements.openings import _formula
            _formula(pr.get("fill_formula") or "True")  # reject a bad formula before touching anything
        ids = [eid for eid in res.order if res.elements[eid].type == "windows" and (not op.get("ids") or eid in op["ids"])]
        for eid in ids:
            self._apply({"op": "update", "id": eid, "params": pr})
        if op.get("reroll"):
            self.recipe["seed"] = int(self.recipe.get("seed", 1)) + 1
        return f"windows fill={pr.get('fill')} on {len(ids)} grids"

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
            out.append({"id": eid, "type": r.type, "host": r.host, "on": r.src.get("on"), "error": r.error,
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
            res_ = self.result()
            model = self.final()
            if res_.movables():  # renders show the doors (closed) - they are separate objects, not in the shell
                model = g.union([model] + [mv["m"] for _, _, mv in res_.movables()])
            info = render_sheet(model, out, views=views, tile=tile, highlight=bad,
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

    def fracture_glb(self) -> bytes:
        """Chunks of the destructible model for the viewer (cached per version)."""
        from ..core.mesh import fracture_scene
        with self.lock:
            key = (self.version, json.dumps(self.recipe.get("fracture"), sort_keys=True))
            if getattr(self, "_frac_cache", (None,))[0] != key:
                sc = fracture_scene(self.result())
                if not sc.geometry:
                    raise ValueError("destruction is off: switch on «Разрушаемое здание»")
                self._frac_cache = (key, sc.export(file_type="glb"))
            return self._frac_cache[1]

    def model_glb(self) -> bytes:
        with self.lock:
            res = self.result()
            return to_scene(self.final(), self.tex_dir, textured=res.detail == "realistic", result=res).export(file_type="glb")

    def export(self, fmt="glb", lod_tris=None, force=False, agent="?", path=None, only=None):
        """Whole model, or `only` = element ids: those elements with their macro children and everything attached."""
        with self.lock:
            res = self.result()
            name = slug(self.recipe.get("name", "model"))
            ids = None
            if only:
                ids = {eid for eid in res.order if self._in_scope(eid, set(only))}
                solids = [m for eid in ids for m, _ in res.elements[eid].solids]
                if not solids:
                    return {"error": f"nothing to export in {only}"}
                model = optimize(g.union(solids))
                name += "_" + slug("_".join(only).replace("/", "-"))
            else:
                rep = validate(res)
                if not rep["ok"] and not force:
                    return {"error": "model has problems; fix them or pass force=true", "problems": rep["errors"][:20]}
                model = self.final()
            suffix = f"_lod{lod_tris}" if lod_tris else ""
            out = Path(path) if path else self.dir / "export" / f"{name}{suffix}.{fmt}"
            _, ntri = export_mesh(model, out, fmt, self.tex_dir, lod_tris, textured=res.detail == "realistic", result=res, only=ids)
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
                "build_mode": self.recipe.get("build_mode", "solid"), "brick_size": self.recipe.get("brick_size", 0.5),
                "brick_cull": self.recipe.get("brick_cull", True), "doors_separate": self.recipe.get("doors_separate", True),
                "fracture": self.recipe.get("fracture") or {"on": False}, "props": self.recipe.get("props", True),
                "decals": self.recipe.get("decals", True), "colors": self.recipe.get("colors")}
